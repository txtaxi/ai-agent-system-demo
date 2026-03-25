from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackBucketStatRead,
    FeedbackCreate,
    FeedbackStatsRead,
    NegativeFeedbackSampleRead,
)


def create_or_update_feedback(db: Session, payload: FeedbackCreate) -> Feedback:
    agent_run = db.get(AgentRun, payload.agent_run_id)
    if agent_run is None:
        raise ValueError("对应的运行记录不存在。")

    existing = db.scalar(
        select(Feedback).where(Feedback.agent_run_id == payload.agent_run_id)
    )
    if existing is None:
        feedback = Feedback(
            agent_run_id=payload.agent_run_id,
            conversation_id=payload.conversation_id,
            rating=payload.rating,
            comment=payload.comment,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback

    existing.rating = payload.rating
    existing.comment = payload.comment
    if payload.conversation_id is not None:
        existing.conversation_id = payload.conversation_id
    db.commit()
    db.refresh(existing)
    return existing


def _update_bucket(
    buckets: dict[str, dict[str, int]],
    label: str,
    rating: str,
) -> None:
    stats = buckets[label]
    stats["total"] += 1
    if rating == "positive":
        stats["positive"] += 1
    elif rating == "negative":
        stats["negative"] += 1


def _bucket_list(buckets: dict[str, dict[str, int]]) -> list[FeedbackBucketStatRead]:
    items = [
        FeedbackBucketStatRead(
            label=label,
            total=values["total"],
            positive=values["positive"],
            negative=values["negative"],
        )
        for label, values in buckets.items()
    ]
    return sorted(items, key=lambda item: (-item.total, item.label))


def _normalize_human_review_label(value: bool | None) -> str:
    if value is True:
        return "建议人工确认"
    if value is False:
        return "无需人工确认"
    return "未知"


def _summary_from_trace(trace_json: dict | None) -> dict:
    if not isinstance(trace_json, dict):
        return {}
    summary = trace_json.get("summary")
    if isinstance(summary, dict):
        merged = dict(trace_json)
        merged.update(summary)
        return merged
    return trace_json


def _extract_knowledge_base_names(summary: dict) -> list[str]:
    items = summary.get("selected_knowledge_bases") or []
    names: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                names.append(item["name"])
    return names


def _trace_value(summary: dict, key: str, default=None):
    value = summary.get(key, default)
    return default if value in (None, "") else value


def get_feedback_stats(db: Session) -> FeedbackStatsRead:
    rows = db.execute(
        select(Feedback, AgentRun)
        .join(AgentRun, AgentRun.id == Feedback.agent_run_id)
        .order_by(Feedback.created_at.desc())
    ).all()

    total = 0
    positive = 0
    negative = 0

    by_route: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "positive": 0, "negative": 0}
    )
    by_tool: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "positive": 0, "negative": 0}
    )
    by_retrieval_quality: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "positive": 0, "negative": 0}
    )
    by_human_review: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "positive": 0, "negative": 0}
    )
    by_knowledge_base: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "positive": 0, "negative": 0}
    )

    for feedback, agent_run in rows:
        total += 1
        if feedback.rating == "positive":
            positive += 1
        elif feedback.rating == "negative":
            negative += 1

        summary = _summary_from_trace(agent_run.trace_json)
        route_label = agent_run.route or _trace_value(summary, "route_type", "unknown")
        tool_label = _trace_value(summary, "selected_tool", "unknown")
        retrieval_quality_label = _trace_value(summary, "retrieval_quality", "unknown")
        human_review_label = _normalize_human_review_label(
            summary.get("human_review_required")
        )

        _update_bucket(by_route, route_label, feedback.rating)
        _update_bucket(by_tool, tool_label, feedback.rating)
        _update_bucket(by_retrieval_quality, retrieval_quality_label, feedback.rating)
        _update_bucket(by_human_review, human_review_label, feedback.rating)

        knowledge_base_names = _extract_knowledge_base_names(summary)
        if knowledge_base_names:
            for kb_name in knowledge_base_names:
                _update_bucket(by_knowledge_base, kb_name, feedback.rating)
        else:
            _update_bucket(by_knowledge_base, "unknown", feedback.rating)

    return FeedbackStatsRead(
        total=total,
        positive=positive,
        negative=negative,
        positive_rate=(positive / total) if total else 0.0,
        negative_rate=(negative / total) if total else 0.0,
        by_route=_bucket_list(by_route),
        by_tool=_bucket_list(by_tool),
        by_retrieval_quality=_bucket_list(by_retrieval_quality),
        by_human_review=_bucket_list(by_human_review),
        by_knowledge_base=_bucket_list(by_knowledge_base),
    )


def list_negative_feedback_samples(
    db: Session,
    limit: int = 20,
) -> list[NegativeFeedbackSampleRead]:
    rows = db.execute(
        select(Feedback, AgentRun)
        .join(AgentRun, AgentRun.id == Feedback.agent_run_id)
        .where(Feedback.rating == "negative")
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    ).all()

    items: list[NegativeFeedbackSampleRead] = []
    for feedback, agent_run in rows:
        summary = _summary_from_trace(agent_run.trace_json)
        items.append(
            NegativeFeedbackSampleRead(
                feedback_id=int(feedback.id),
                agent_run_id=int(feedback.agent_run_id),
                conversation_id=feedback.conversation_id,
                rating=feedback.rating,
                comment=feedback.comment,
                created_at=feedback.created_at,
                user_query=agent_run.user_query or "",
                route=agent_run.route or _trace_value(summary, "route_type", "unknown"),
                selected_tool=_trace_value(summary, "selected_tool", "unknown"),
                retrieval_quality=_trace_value(summary, "retrieval_quality", "unknown"),
                human_review_required=summary.get("human_review_required"),
                knowledge_base_names=_extract_knowledge_base_names(summary),
            )
        )
    return items
