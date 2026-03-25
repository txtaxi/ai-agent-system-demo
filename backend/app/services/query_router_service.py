from dataclasses import dataclass
import re


@dataclass
class QueryRoute:
    route_type: str
    route_reason: str


SUMMARY_PATTERNS = (
    r"总结",
    r"概括",
    r"梳理",
    r"提炼",
    r"摘要",
)

COMPARE_PATTERNS = (
    r"区别",
    r"不同",
    r"对比",
    r"比较",
    r"差异",
    r"相比",
)


def classify_query(question: str) -> QueryRoute:
    normalized = question.strip()

    if _matches_any(normalized, SUMMARY_PATTERNS):
        return QueryRoute(
            route_type="summary",
            route_reason="命中总结类关键词，按总结模式处理。",
        )

    if _matches_any(normalized, COMPARE_PATTERNS):
        return QueryRoute(
            route_type="comparison",
            route_reason="命中对比类关键词，按对比模式处理。",
        )

    return QueryRoute(
        route_type="qa",
        route_reason="未命中特殊任务关键词，按标准问答模式处理。",
    )


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
