from collections import OrderedDict, defaultdict

from sqlalchemy.orm import Session

from app.schemas.chat import CitationItem, KnowledgeBaseSelection
from app.schemas.retrieval import RetrievalSearchResultItem
from app.services.knowledge_base_router_service import resolve_knowledge_base_candidates
from app.services.retrieval_service import retrieve_relevant_chunks


def search_knowledge(
    db: Session,
    question: str,
    rewritten_query: str | None,
    route_type: str,
    knowledge_base_id: int | None,
    top_k: int,
) -> tuple[list[KnowledgeBaseSelection], list[RetrievalSearchResultItem], list[str]]:
    candidates, _ = resolve_knowledge_base_candidates(
        db=db,
        question=question,
        knowledge_base_id=knowledge_base_id,
        limit=3,
    )
    selected_knowledge_bases = [
        KnowledgeBaseSelection(
            id=item.knowledge_base.id,
            name=item.knowledge_base.name,
            description=item.knowledge_base.description,
            selection_reason=item.reason,
            score=item.score,
        )
        for item in candidates
    ]
    knowledge_base_ids = [item.id for item in selected_knowledge_bases]
    if not knowledge_base_ids:
        return [], [], []

    queries_used = _build_queries_used(
        question=question,
        rewritten_query=rewritten_query,
        route_type=route_type,
    )
    limit = _resolve_search_limit(route_type, top_k)

    merged_items: OrderedDict[int, RetrievalSearchResultItem] = OrderedDict()
    for query in queries_used:
        items = retrieve_relevant_chunks(
            db=db,
            query=query,
            knowledge_base_ids=knowledge_base_ids,
            limit=limit,
        )
        for item in items:
            existing = merged_items.get(item.chunk_id)
            if existing is None or item.score > existing.score:
                merged_items[item.chunk_id] = item

    ranked_items = sorted(
        merged_items.values(),
        key=lambda item: (-item.score, item.filename, item.chunk_index),
    )
    return selected_knowledge_bases, ranked_items[:limit], queries_used


def analyze_retrieval_quality(
    route_type: str,
    selected_knowledge_bases: list[KnowledgeBaseSelection],
    items: list[RetrievalSearchResultItem],
) -> tuple[str, str]:
    if not selected_knowledge_bases:
        return "empty", "当前没有命中的知识库候选。"
    if not items:
        return "low", "已完成知识库路由，但没有检索到相关内容。"

    top_score = items[0].score
    kb_count = len({item.knowledge_base_id for item in items})

    if route_type == "comparison" and kb_count >= 2 and len(items) >= 4:
        return "high", f"对比任务已命中 {kb_count} 个知识库，共 {len(items)} 条内容。"
    if top_score >= 0.75 and len(items) >= 3:
        return "high", f"最高分 {top_score:.3f}，共检索到 {len(items)} 条内容。"
    if top_score >= 0.55 and len(items) >= 2:
        return "medium", f"最高分 {top_score:.3f}，当前结果可用于继续回答。"
    return "low", f"最高分仅 {top_score:.3f}，结果数量 {len(items)}，建议补充上下文。"


def decide_need_more_context(
    route_type: str,
    retrieval_quality: str,
    items: list[RetrievalSearchResultItem],
    search_round: int,
) -> tuple[bool, str]:
    if search_round >= 2:
        return False, "当前已经执行过补充检索，避免继续扩展。"
    if retrieval_quality == "low":
        return True, "检索质量偏低，需要扩大搜索范围。"
    if route_type == "comparison" and len(items) < 4:
        return True, "对比任务需要更多候选内容支撑差异分析。"
    if route_type == "summary" and len(items) < 3:
        return True, "总结任务当前上下文偏少，建议补充搜索。"
    return False, "当前检索结果已满足本轮回答需要。"


def rerank_retrieved_items(
    route_type: str,
    items: list[RetrievalSearchResultItem],
) -> tuple[list[RetrievalSearchResultItem], str]:
    if not items:
        return [], "当前没有可用于重排的检索结果。"

    if route_type == "comparison":
        reranked = _interleave_by_knowledge_base(items)
        return reranked, "对比任务采用跨知识库均衡重排，避免单一知识库占满结果。"

    if route_type == "summary":
        reranked = _interleave_by_document(items)
        return reranked, "总结任务采用按文档分散重排，优先扩大主题覆盖面。"

    reranked = sorted(items, key=lambda item: (-item.score, item.filename, item.chunk_index))
    return reranked, "标准问答采用分数优先重排，保持高相关结果靠前。"


def assess_human_review_need(
    question: str,
    route_type: str,
    retrieval_quality: str,
    selected_tool: str,
    items: list[RetrievalSearchResultItem],
) -> tuple[bool, str]:
    normalized_question = question.strip()
    high_risk_keywords = [
        "付款",
        "转账",
        "报销",
        "审批",
        "合同",
        "裁员",
        "离职",
        "薪资",
        "处罚",
        "权限删除",
        "账号停用",
        "发票",
        "法务",
    ]
    matched_keywords = [keyword for keyword in high_risk_keywords if keyword in normalized_question]

    if matched_keywords and retrieval_quality != "high":
        return True, f"问题涉及高风险主题 {', '.join(matched_keywords)}，且当前检索质量不是 high。"
    if selected_tool == "compare_contexts" and len(items) < 3:
        return True, "对比任务当前证据不足，建议人工确认后再采用结论。"
    if route_type == "summary" and retrieval_quality == "low":
        return True, "总结任务检索质量偏低，建议人工确认摘要内容。"
    return False, "当前无需人工确认，可继续自动回答。"


def summarize_context(
    items: list[RetrievalSearchResultItem],
) -> tuple[list[RetrievalSearchResultItem], list[str]]:
    grouped: dict[str, list[RetrievalSearchResultItem]] = defaultdict(list)
    for item in items:
        grouped[item.knowledge_base_name].append(item)

    organized_items: list[RetrievalSearchResultItem] = []
    context_lines: list[str] = []
    for knowledge_base_name, grouped_items in grouped.items():
        context_lines.append(f"知识库：{knowledge_base_name}")
        for item in grouped_items[:3]:
            organized_items.append(item)
            context_lines.append(f"[{item.filename}#{item.chunk_index}] {item.content.strip()}")
    return organized_items, context_lines


def compare_contexts(
    items: list[RetrievalSearchResultItem],
) -> tuple[list[RetrievalSearchResultItem], list[str]]:
    grouped: dict[str, list[RetrievalSearchResultItem]] = defaultdict(list)
    for item in items:
        grouped[item.knowledge_base_name].append(item)

    organized_items: list[RetrievalSearchResultItem] = []
    context_lines: list[str] = []
    for knowledge_base_name, grouped_items in grouped.items():
        context_lines.append(f"对比来源：{knowledge_base_name}")
        for item in grouped_items[:2]:
            organized_items.append(item)
            context_lines.append(f"[{item.filename}#{item.chunk_index}] {item.content.strip()}")
    return organized_items, context_lines


def build_qa_context(
    items: list[RetrievalSearchResultItem],
) -> tuple[list[RetrievalSearchResultItem], list[str]]:
    organized_items = items[:4]
    context_lines = [
        f"[{item.knowledge_base_name}] [{item.filename}#{item.chunk_index}] {item.content.strip()}"
        for item in organized_items
    ]
    return organized_items, context_lines


def build_citations(items: list[RetrievalSearchResultItem]) -> tuple[list[CitationItem], list[dict]]:
    citations = [
        CitationItem(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            filename=item.filename,
            chunk_index=item.chunk_index,
            score=item.score,
            knowledge_base_id=item.knowledge_base_id,
            knowledge_base_name=item.knowledge_base_name,
        )
        for item in items
    ]
    return citations, [item.model_dump() for item in citations]


def _build_queries_used(
    question: str,
    rewritten_query: str | None,
    route_type: str,
) -> list[str]:
    queries = [question.strip()]
    normalized_rewritten = (rewritten_query or "").strip()
    if route_type != "qa" and normalized_rewritten and normalized_rewritten != queries[0]:
        queries.append(normalized_rewritten)
    return list(OrderedDict.fromkeys(query for query in queries if query))


def _resolve_search_limit(route_type: str, top_k: int) -> int:
    if route_type in {"summary", "comparison"}:
        return min(max(top_k + 2, top_k), 8)
    return top_k


def _interleave_by_knowledge_base(items: list[RetrievalSearchResultItem]) -> list[RetrievalSearchResultItem]:
    grouped: dict[int, list[RetrievalSearchResultItem]] = defaultdict(list)
    for item in sorted(items, key=lambda value: (-value.score, value.filename, value.chunk_index)):
        grouped[item.knowledge_base_id].append(item)

    ordered_ids = [
        knowledge_base_id
        for knowledge_base_id, _ in sorted(
            grouped.items(),
            key=lambda pair: (-pair[1][0].score, pair[1][0].knowledge_base_name),
        )
    ]

    reranked: list[RetrievalSearchResultItem] = []
    while ordered_ids:
        next_round: list[int] = []
        for knowledge_base_id in ordered_ids:
            bucket = grouped[knowledge_base_id]
            if bucket:
                reranked.append(bucket.pop(0))
            if bucket:
                next_round.append(knowledge_base_id)
        ordered_ids = next_round
    return reranked


def _interleave_by_document(items: list[RetrievalSearchResultItem]) -> list[RetrievalSearchResultItem]:
    grouped: dict[int, list[RetrievalSearchResultItem]] = defaultdict(list)
    for item in sorted(items, key=lambda value: (-value.score, value.filename, value.chunk_index)):
        grouped[item.document_id].append(item)

    ordered_document_ids = [
        document_id
        for document_id, _ in sorted(
            grouped.items(),
            key=lambda pair: (-pair[1][0].score, pair[1][0].filename),
        )
    ]

    reranked: list[RetrievalSearchResultItem] = []
    while ordered_document_ids:
        next_round: list[int] = []
        for document_id in ordered_document_ids:
            bucket = grouped[document_id]
            if bucket:
                reranked.append(bucket.pop(0))
            if bucket:
                next_round.append(document_id)
        ordered_document_ids = next_round
    return reranked
