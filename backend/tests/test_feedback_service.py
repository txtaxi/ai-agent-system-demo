from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import TestCase

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.feedback_service import (
    _summary_from_trace,
    get_feedback_stats,
    list_negative_feedback_samples,
)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _stmt):
        return FakeExecuteResult(self._rows)


class FeedbackServiceTests(TestCase):
    def test_summary_from_trace_supports_flat_trace(self):
        trace = {
            "route_type": "summary",
            "selected_tool": "summarize_context",
            "retrieval_quality": "high",
            "selected_knowledge_bases": [{"name": "HR KB"}],
        }

        summary = _summary_from_trace(trace)

        self.assertEqual(summary["route_type"], "summary")
        self.assertEqual(summary["selected_tool"], "summarize_context")
        self.assertEqual(summary["retrieval_quality"], "high")
        self.assertEqual(summary["selected_knowledge_bases"][0]["name"], "HR KB")

    def test_summary_from_trace_merges_nested_summary(self):
        trace = {
            "route_type": "qa",
            "summary": {
                "route_type": "comparison",
                "selected_tool": "compare_contexts",
            },
        }

        summary = _summary_from_trace(trace)

        self.assertEqual(summary["route_type"], "comparison")
        self.assertEqual(summary["selected_tool"], "compare_contexts")

    def test_get_feedback_stats_aggregates_real_trace_fields(self):
        now = datetime.now(timezone.utc)
        feedback_positive = SimpleNamespace(
            id=1,
            agent_run_id=101,
            conversation_id=10,
            rating="positive",
            comment=None,
            created_at=now,
        )
        feedback_negative = SimpleNamespace(
            id=2,
            agent_run_id=102,
            conversation_id=10,
            rating="negative",
            comment="evidence weak",
            created_at=now,
        )
        run_positive = SimpleNamespace(
            id=101,
            conversation_id=10,
            user_query="请总结员工入职流程",
            route="summary",
            trace_json={
                "route_type": "summary",
                "selected_tool": "summarize_context",
                "retrieval_quality": "high",
                "human_review_required": False,
                "selected_knowledge_bases": [{"name": "HR KB"}],
            },
        )
        run_negative = SimpleNamespace(
            id=102,
            conversation_id=10,
            user_query="报销能否直接付款",
            route="qa",
            trace_json={
                "route_type": "qa",
                "selected_tool": "build_qa_context",
                "retrieval_quality": "medium",
                "human_review_required": True,
                "selected_knowledge_bases": [{"name": "Finance KB"}],
            },
        )
        db = FakeSession([(feedback_positive, run_positive), (feedback_negative, run_negative)])

        stats = get_feedback_stats(db)

        self.assertEqual(stats.total, 2)
        self.assertEqual(stats.positive, 1)
        self.assertEqual(stats.negative, 1)
        self.assertEqual(stats.by_tool[0].label, "build_qa_context")
        self.assertEqual({item.label for item in stats.by_tool}, {"summarize_context", "build_qa_context"})
        self.assertEqual({item.label for item in stats.by_retrieval_quality}, {"high", "medium"})
        self.assertEqual({item.label for item in stats.by_knowledge_base}, {"HR KB", "Finance KB"})

    def test_list_negative_feedback_samples_uses_trace_metadata(self):
        now = datetime.now(timezone.utc)
        feedback_negative = SimpleNamespace(
            id=2,
            agent_run_id=102,
            conversation_id=10,
            rating="negative",
            comment="evidence weak",
            created_at=now,
        )
        run_negative = SimpleNamespace(
            id=102,
            conversation_id=10,
            user_query="报销能否直接付款",
            route="qa",
            trace_json={
                "route_type": "qa",
                "selected_tool": "build_qa_context",
                "retrieval_quality": "medium",
                "human_review_required": True,
                "selected_knowledge_bases": [{"name": "Finance KB"}],
            },
        )
        db = FakeSession([(feedback_negative, run_negative)])

        items = list_negative_feedback_samples(db)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].selected_tool, "build_qa_context")
        self.assertEqual(items[0].retrieval_quality, "medium")
        self.assertEqual(items[0].knowledge_base_names, ["Finance KB"])
