from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.agent_run import (
    AgentRunRead,
    AgentRunReviewRequest,
    AgentRunStepRead,
    AgentRunSummaryRead,
    AgentRunTraceRead,
)
from app.services.agent_run_service import get_agent_run, list_agent_runs, review_agent_run

router = APIRouter(prefix="/agent-runs")


@router.get("", response_model=list[AgentRunRead])
def list_agent_runs_endpoint(
    conversation_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AgentRunRead]:
    return list_agent_runs(db, conversation_id=conversation_id, limit=limit)


@router.get("/{agent_run_id}", response_model=AgentRunTraceRead)
def get_agent_run_endpoint(
    agent_run_id: int,
    db: Session = Depends(get_db),
) -> AgentRunTraceRead:
    agent_run = get_agent_run(db, agent_run_id)
    if agent_run is None:
        raise HTTPException(status_code=404, detail="运行记录不存在。")
    return _build_trace_response(agent_run)


@router.post("/{agent_run_id}/review", response_model=AgentRunTraceRead)
def review_agent_run_endpoint(
    agent_run_id: int,
    payload: AgentRunReviewRequest,
    db: Session = Depends(get_db),
) -> AgentRunTraceRead:
    try:
        agent_run = review_agent_run(db, agent_run_id, payload.action, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_trace_response(agent_run)


def _build_trace_response(agent_run) -> AgentRunTraceRead:
    trace_json = agent_run.trace_json if isinstance(agent_run.trace_json, dict) else {}
    raw_steps = trace_json.get("steps", []) or []

    steps = [
        AgentRunStepRead(
            node=item.get("node", ""),
            detail=item.get("detail", ""),
            meta=item.get("meta"),
        )
        for item in raw_steps
        if isinstance(item, dict)
    ]

    summary = AgentRunSummaryRead(
        route_type=trace_json.get("route_type"),
        route_reason=trace_json.get("route_reason"),
        rewritten_query=trace_json.get("rewritten_query"),
        rewrite_reason=trace_json.get("rewrite_reason"),
        rewrite_accepted=trace_json.get("rewrite_accepted"),
        rewrite_assessment_reason=trace_json.get("rewrite_assessment_reason"),
        selected_tool=trace_json.get("selected_tool"),
        selected_tool_reason=trace_json.get("selected_tool_reason"),
        retrieval_quality=trace_json.get("retrieval_quality"),
        retrieval_quality_reason=trace_json.get("retrieval_quality_reason"),
        retrieval_queries=trace_json.get("retrieval_queries", []) or [],
        rerank_applied=trace_json.get("rerank_applied"),
        rerank_reason=trace_json.get("rerank_reason"),
        human_review_required=trace_json.get("human_review_required"),
        human_review_reason=trace_json.get("human_review_reason"),
        review_status=trace_json.get("review_status"),
        review_comment=trace_json.get("review_comment"),
        need_more_context=trace_json.get("need_more_context"),
        need_more_context_reason=trace_json.get("need_more_context_reason"),
        search_round=trace_json.get("search_round", 1) or 1,
        selected_knowledge_bases=trace_json.get("selected_knowledge_bases", []) or [],
        context_count=trace_json.get("context_count", 0) or 0,
    )

    return AgentRunTraceRead(
        id=agent_run.id,
        conversation_id=agent_run.conversation_id,
        user_query=agent_run.user_query,
        route=agent_run.route,
        status=agent_run.status,
        started_at=agent_run.started_at,
        finished_at=agent_run.finished_at,
        summary=summary,
        steps=steps,
    )
