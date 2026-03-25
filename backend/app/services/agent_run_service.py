from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.services.conversation_service import save_message


def create_agent_run(
    db: Session,
    conversation_id: int | None,
    user_query: str,
) -> AgentRun:
    agent_run = AgentRun(
        conversation_id=conversation_id,
        user_query=user_query,
        status="running",
        trace_json={"steps": []},
    )
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def complete_agent_run(
    db: Session,
    agent_run_id: int,
    route: str,
    trace_json: dict,
) -> AgentRun:
    agent_run = _require_agent_run(db, agent_run_id)
    agent_run.route = route
    agent_run.status = "completed"
    agent_run.trace_json = trace_json
    agent_run.finished_at = datetime.now(timezone.utc)
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def mark_agent_run_pending_review(
    db: Session,
    agent_run_id: int,
    route: str,
    trace_json: dict,
) -> AgentRun:
    agent_run = _require_agent_run(db, agent_run_id)
    agent_run.route = route
    agent_run.status = "pending_review"
    agent_run.trace_json = trace_json
    agent_run.finished_at = None
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def fail_agent_run(
    db: Session,
    agent_run_id: int,
    route: str | None,
    trace_json: dict,
) -> AgentRun:
    agent_run = _require_agent_run(db, agent_run_id)
    agent_run.route = route
    agent_run.status = "failed"
    agent_run.trace_json = trace_json
    agent_run.finished_at = datetime.now(timezone.utc)
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def review_agent_run(
    db: Session,
    agent_run_id: int,
    action: str,
    comment: str | None = None,
) -> AgentRun:
    agent_run = _require_agent_run(db, agent_run_id)
    if agent_run.status != "pending_review":
        raise ValueError("当前运行记录不处于待人工审核状态。")

    trace_json = agent_run.trace_json if isinstance(agent_run.trace_json, dict) else {}
    trace_json["review_status"] = action
    trace_json["review_comment"] = comment

    pending_response = trace_json.get("pending_response") or {}
    conversation_id = agent_run.conversation_id

    if action == "approve":
        if conversation_id is not None and pending_response.get("answer"):
            save_message(
                db,
                conversation_id=conversation_id,
                role="assistant",
                content=pending_response["answer"],
                citations_json=pending_response.get("citations_json", []),
            )
        agent_run.status = "completed"
    else:
        if conversation_id is not None:
            save_message(
                db,
                conversation_id=conversation_id,
                role="assistant",
                content="本次回答已被人工审核驳回，请重新提问或由人工处理。",
                citations_json=[],
            )
        agent_run.status = "rejected"

    agent_run.trace_json = trace_json
    agent_run.finished_at = datetime.now(timezone.utc)
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def list_agent_runs(
    db: Session,
    conversation_id: int | None = None,
    limit: int = 20,
) -> list[AgentRun]:
    stmt = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if conversation_id is not None:
        stmt = stmt.where(AgentRun.conversation_id == conversation_id)
    return list(db.scalars(stmt))


def get_agent_run(db: Session, agent_run_id: int) -> AgentRun | None:
    return db.get(AgentRun, agent_run_id)


def _require_agent_run(db: Session, agent_run_id: int) -> AgentRun:
    agent_run = db.get(AgentRun, agent_run_id)
    if agent_run is None:
        raise ValueError("智能体运行记录不存在。")
    return agent_run
