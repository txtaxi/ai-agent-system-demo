from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import TestCase

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.conversation_service import (
    _build_message_payload,
    _build_pending_message_payload,
)


class ConversationServiceTests(TestCase):
    def test_build_message_payload_keeps_agent_run_metadata(self):
        now = datetime.now(timezone.utc)
        message = SimpleNamespace(
            id=1,
            conversation_id=10,
            role="assistant",
            content="这是正常回答",
            citations_json=[{"chunk_id": 1}],
            created_at=now,
            updated_at=now,
        )
        agent_run = SimpleNamespace(
            id=88,
            status="completed",
            trace_json={
                "route_type": "summary",
                "route_reason": "命中总结任务",
                "selected_tool": "summarize_context",
                "selected_tool_reason": "总结任务优先使用总结工具",
                "human_review_required": False,
                "human_review_reason": "无需人工确认",
                "selected_knowledge_bases": [{"id": 1, "name": "HR KB"}],
                "review_status": "completed",
            },
        )
        feedback = SimpleNamespace(rating="positive")

        payload = _build_message_payload(message, agent_run, feedback)

        self.assertEqual(payload["agent_run_id"], 88)
        self.assertEqual(payload["route_type"], "summary")
        self.assertEqual(payload["selected_tool"], "summarize_context")
        self.assertFalse(payload["awaiting_human_review"])
        self.assertEqual(payload["feedback_rating"], "positive")

    def test_build_pending_message_payload_restores_waiting_review_message(self):
        now = datetime.now(timezone.utc)
        agent_run = SimpleNamespace(
            id=99,
            status="pending_review",
            started_at=now,
            trace_json={
                "route_type": "qa",
                "route_reason": "高风险问题",
                "selected_tool": "build_qa_context",
                "selected_tool_reason": "标准问答",
                "human_review_required": True,
                "human_review_reason": "涉及付款且证据不足",
                "selected_knowledge_bases": [{"id": 2, "name": "Finance KB"}],
                "pending_response": {
                    "answer": "以下内容建议人工确认后再执行。",
                    "citations_json": [{"chunk_id": 2}],
                },
                "review_status": "pending",
            },
        )

        payload = _build_pending_message_payload(10, agent_run, feedback=None)

        self.assertEqual(payload["id"], -99)
        self.assertEqual(payload["agent_run_id"], 99)
        self.assertTrue(payload["awaiting_human_review"])
        self.assertEqual(payload["content"], "以下内容建议人工确认后再执行。")
        self.assertEqual(payload["selected_knowledge_bases"][0]["name"], "Finance KB")
