import json
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.agent.workflow import build_trace_payload, compose_response_from_state, run_agent_workflow
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.agent_run_service import (
    complete_agent_run,
    create_agent_run,
    fail_agent_run,
    mark_agent_run_pending_review,
)
from app.services.conversation_service import get_or_create_conversation, save_message


def ask_with_rag(db: Session, payload: ChatAskRequest) -> ChatAskResponse:
    # 问答主入口：准备会话、执行 Agent 工作流、保存消息和运行记录。
    conversation = get_or_create_conversation(db, payload.conversation_id, payload.question)
    agent_run = create_agent_run(
        db,
        conversation_id=conversation.id,
        user_query=payload.question,
    )

    save_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )

    try:
        state = run_agent_workflow(
            db=db,
            question=payload.question,
            knowledge_base_id=payload.knowledge_base_id,
            top_k=payload.top_k,
        )

        response = compose_response_from_state(
            conversation_id=conversation.id,
            agent_run_id=agent_run.id,
            question=payload.question,
            state=state,
        )
        trace_payload = build_trace_payload(state)

        if state.get("human_review_required"):
            # 命中高风险分支时，回答先进入待审核状态，不直接写入会话。
            trace_payload["pending_response"] = {
                "answer": state["answer"],
                "citations_json": state.get("citations_json", []),
            }
            trace_payload["review_status"] = "pending"
            mark_agent_run_pending_review(
                db,
                agent_run_id=agent_run.id,
                route=state.get("route_type", "unknown"),
                trace_json=trace_payload,
            )
            response.awaiting_human_review = True
            response.review_status = "pending_review"
            return response

        save_message(
            db,
            conversation_id=conversation.id,
            role="assistant",
            content=state["answer"],
            citations_json=state.get("citations_json", []),
        )

        complete_agent_run(
            db,
            agent_run_id=agent_run.id,
            route=state.get("route_type", "unknown"),
            trace_json=trace_payload,
        )
        return response
    except Exception:
        fail_agent_run(
            db,
            agent_run_id=agent_run.id,
            route=None,
            trace_json={
                "steps": [
                    {
                        "node": "workflow",
                        "detail": "工作流执行失败。",
                        "meta": {"status": "failed"},
                    }
                ]
            },
        )
        raise


def stream_ask_with_rag(db: Session, payload: ChatAskRequest) -> Iterator[str]:
    # 流式问答复用普通问答主流程，仅在返回阶段拆成 SSE 事件。
    response = ask_with_rag(db, payload)

    yield _sse_event(
        "meta",
        {
            "conversation_id": response.conversation_id,
            "agent_run_id": response.agent_run_id,
            "question": response.question,
            "context_count": response.context_count,
            "route_type": response.route_type,
            "route_reason": response.route_reason,
            "selected_tool": response.selected_tool,
            "selected_tool_reason": response.selected_tool_reason,
            "human_review_required": response.human_review_required,
            "human_review_reason": response.human_review_reason,
            "awaiting_human_review": response.awaiting_human_review,
            "review_status": response.review_status,
            "selected_knowledge_bases": [item.model_dump() for item in response.selected_knowledge_bases],
        },
    )

    for chunk in _split_answer_for_stream(response.answer):
        yield _sse_event("chunk", {"content": chunk})

    yield _sse_event(
        "done",
        {
            "conversation_id": response.conversation_id,
            "agent_run_id": response.agent_run_id,
            "citations": [item.model_dump() for item in response.citations],
            "route_type": response.route_type,
            "route_reason": response.route_reason,
            "selected_tool": response.selected_tool,
            "selected_tool_reason": response.selected_tool_reason,
            "human_review_required": response.human_review_required,
            "human_review_reason": response.human_review_reason,
            "awaiting_human_review": response.awaiting_human_review,
            "review_status": response.review_status,
            "selected_knowledge_bases": [item.model_dump() for item in response.selected_knowledge_bases],
        },
    )


def _split_answer_for_stream(answer: str, chunk_size: int = 80) -> list[str]:
    return [answer[index : index + chunk_size] for index in range(0, len(answer), chunk_size)] or [""]


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
