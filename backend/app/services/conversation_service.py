from collections import deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.conversation import Conversation
from app.models.feedback import Feedback
from app.models.message import Message


def get_or_create_conversation(db: Session, conversation_id: int | None, question: str) -> Conversation:
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None:
            return conversation
        raise ValueError("会话不存在。")

    title = question[:50] if question else "新对话"
    conversation = Conversation(title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def save_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    citations_json: list[dict] | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations_json=citations_json,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_conversations(db: Session) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(db.scalars(stmt))


def list_messages(db: Session, conversation_id: int) -> list[dict]:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError("会话不存在。")

    message_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    messages = list(db.scalars(message_stmt))

    agent_run_stmt = (
        select(AgentRun)
        .where(AgentRun.conversation_id == conversation_id)
        .order_by(AgentRun.started_at.asc(), AgentRun.id.asc())
    )
    agent_runs = list(db.scalars(agent_run_stmt))
    if not agent_runs:
        return [_build_plain_message_payload(message) for message in messages]

    agent_run_ids = [agent_run.id for agent_run in agent_runs]
    feedback_rows = db.scalars(select(Feedback).where(Feedback.agent_run_id.in_(agent_run_ids)))
    feedback_by_run_id = {feedback.agent_run_id: feedback for feedback in feedback_rows}

    completed_runs = deque(agent_run for agent_run in agent_runs if agent_run.status != "pending_review")
    payloads: list[dict] = []
    for message in messages:
        agent_run = None
        if message.role == "assistant" and completed_runs:
            agent_run = completed_runs.popleft()
        payloads.append(
            _build_message_payload(
                message=message,
                agent_run=agent_run,
                feedback=feedback_by_run_id.get(agent_run.id) if agent_run is not None else None,
            )
        )

    for agent_run in agent_runs:
        if agent_run.status == "pending_review":
            payloads.append(
                _build_pending_message_payload(
                    conversation_id=conversation_id,
                    agent_run=agent_run,
                    feedback=feedback_by_run_id.get(agent_run.id),
                )
            )

    payloads.sort(key=lambda item: (item["created_at"], item["id"]))
    return payloads


def _build_plain_message_payload(message: Message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "citations_json": message.citations_json,
        "agent_run_id": None,
        "route_type": None,
        "route_reason": None,
        "selected_tool": None,
        "selected_tool_reason": None,
        "human_review_required": None,
        "human_review_reason": None,
        "awaiting_human_review": False,
        "review_status": None,
        "selected_knowledge_bases": [],
        "feedback_rating": None,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def _build_message_payload(
    message: Message,
    agent_run: AgentRun | None,
    feedback: Feedback | None,
) -> dict:
    payload = _build_plain_message_payload(message)
    if agent_run is None:
        return payload

    trace = _normalize_trace(agent_run.trace_json)
    payload.update(
        {
            "agent_run_id": agent_run.id,
            "route_type": trace.get("route_type"),
            "route_reason": trace.get("route_reason"),
            "selected_tool": trace.get("selected_tool"),
            "selected_tool_reason": trace.get("selected_tool_reason"),
            "human_review_required": trace.get("human_review_required"),
            "human_review_reason": trace.get("human_review_reason"),
            "awaiting_human_review": agent_run.status == "pending_review",
            "review_status": trace.get("review_status") or agent_run.status,
            "selected_knowledge_bases": trace.get("selected_knowledge_bases", []) or [],
            "feedback_rating": feedback.rating if feedback is not None else None,
        }
    )
    return payload


def _build_pending_message_payload(
    conversation_id: int,
    agent_run: AgentRun,
    feedback: Feedback | None,
) -> dict:
    trace = _normalize_trace(agent_run.trace_json)
    pending_response = trace.get("pending_response") or {}
    return {
        "id": -agent_run.id,
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": pending_response.get("answer") or "该回答正在等待人工审核。",
        "citations_json": pending_response.get("citations_json", []),
        "agent_run_id": agent_run.id,
        "route_type": trace.get("route_type"),
        "route_reason": trace.get("route_reason"),
        "selected_tool": trace.get("selected_tool"),
        "selected_tool_reason": trace.get("selected_tool_reason"),
        "human_review_required": trace.get("human_review_required"),
        "human_review_reason": trace.get("human_review_reason"),
        "awaiting_human_review": True,
        "review_status": trace.get("review_status") or agent_run.status,
        "selected_knowledge_bases": trace.get("selected_knowledge_bases", []) or [],
        "feedback_rating": feedback.rating if feedback is not None else None,
        "created_at": agent_run.started_at,
        "updated_at": agent_run.started_at,
    }


def _normalize_trace(trace_json: dict | None) -> dict:
    return trace_json if isinstance(trace_json, dict) else {}
