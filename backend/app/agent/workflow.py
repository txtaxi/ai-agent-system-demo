from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agent import (
    assess_human_review_need,
    analyze_retrieval_quality,
    build_citations,
    build_qa_context,
    compare_contexts,
    decide_need_more_context,
    rerank_retrieved_items,
    search_knowledge,
    summarize_context,
)
from app.schemas.chat import ChatAskResponse
from app.services.llm_service import (
    assess_query_rewrite,
    generate_answer,
    rewrite_query,
    select_tool,
)
from app.services.query_router_service import classify_query


class AgentState(TypedDict, total=False):
    # AgentState 是整个 LangGraph 工作流共享的状态对象。
    db: Session
    question: str
    rewritten_query: str
    rewrite_reason: str
    rewrite_accepted: bool
    rewrite_assessment_reason: str
    knowledge_base_id: int | None
    top_k: int
    route_type: str
    route_reason: str
    selected_tool: str
    selected_tool_reason: str
    selected_knowledge_bases: list[Any]
    retrieved_items: list[Any]
    organized_items: list[Any]
    context_lines: list[str]
    answer: str
    citations: list[Any]
    citations_json: list[dict]
    context_count: int
    retrieval_quality: str
    retrieval_quality_reason: str
    retrieval_queries: list[str]
    rerank_applied: bool
    rerank_reason: str
    human_review_required: bool
    human_review_reason: str
    need_more_context: bool
    need_more_context_reason: str
    search_round: int
    trace_steps: list[dict]


def run_agent_workflow(
    db: Session,
    question: str,
    knowledge_base_id: int | None,
    top_k: int,
) -> AgentState:
    # 工作流入口：为一次问答准备初始状态并交给 LangGraph 执行。
    graph = _get_compiled_graph()
    return graph.invoke(
        {
            "db": db,
            "question": question,
            "rewritten_query": question,
            "rewrite_accepted": False,
            "rewrite_assessment_reason": "初始状态尚未执行改写评估。",
            "knowledge_base_id": knowledge_base_id,
            "top_k": top_k,
            "retrieval_queries": [question],
            "rerank_applied": False,
            "rerank_reason": "初始状态尚未执行重排。",
            "human_review_required": False,
            "human_review_reason": "初始状态尚未执行人工确认评估。",
            "search_round": 1,
            "trace_steps": [],
        }
    )


def _route_question(state: AgentState) -> AgentState:
    # 先判断当前问题属于哪类任务，决定后续主分支。
    route = classify_query(state["question"])
    trace_steps = _append_trace(
        state,
        node="route_question",
        meta={
            "route_type": route.route_type,
            "route_reason": route.route_reason,
        },
    )
    return {
        "route_type": route.route_type,
        "route_reason": route.route_reason,
        "trace_steps": trace_steps,
    }


def _rewrite_query(state: AgentState) -> AgentState:
    rewritten_query, rewrite_reason = rewrite_query(
        question=state["question"],
        route_type=state["route_type"],
    )
    trace_steps = _append_trace(
        state,
        node="rewrite_query",
        meta={
            "rewritten_query": rewritten_query,
            "rewrite_reason": rewrite_reason,
        },
    )
    return {
        "rewritten_query": rewritten_query,
        "rewrite_reason": rewrite_reason,
        "trace_steps": trace_steps,
    }


def _assess_rewrite(state: AgentState) -> AgentState:
    rewrite_accepted, rewrite_assessment_reason = assess_query_rewrite(
        question=state["question"],
        rewritten_query=state.get("rewritten_query", state["question"]),
        route_type=state["route_type"],
    )
    trace_steps = _append_trace(
        state,
        node="assess_rewrite",
        meta={
            "rewrite_accepted": rewrite_accepted,
            "rewrite_assessment_reason": rewrite_assessment_reason,
        },
    )
    return {
        "rewrite_accepted": rewrite_accepted,
        "rewrite_assessment_reason": rewrite_assessment_reason,
        "trace_steps": trace_steps,
    }


def _select_tool(state: AgentState) -> AgentState:
    selected_tool, selected_tool_reason = select_tool(
        question=state["question"],
        route_type=state["route_type"],
    )
    trace_steps = _append_trace(
        state,
        node="tool_select",
        meta={
            "selected_tool": selected_tool,
            "selected_tool_reason": selected_tool_reason,
        },
    )
    return {
        "selected_tool": selected_tool,
        "selected_tool_reason": selected_tool_reason,
        "trace_steps": trace_steps,
    }


def _search_knowledge(state: AgentState) -> AgentState:
    # 检索节点内部封装了自动选库和双路检索逻辑。
    selected_knowledge_bases, items, queries_used = search_knowledge(
        db=state["db"],
        question=state["question"],
        rewritten_query=state.get("rewritten_query") if state.get("rewrite_accepted") else None,
        route_type=state["route_type"],
        knowledge_base_id=state.get("knowledge_base_id"),
        top_k=state["top_k"],
    )
    trace_steps = _append_trace(
        state,
        node="search_knowledge",
        meta={
            "search_round": state.get("search_round", 1),
            "queries_used": queries_used,
            "selected_knowledge_bases": [item.name for item in selected_knowledge_bases],
            "retrieved_count": len(items),
        },
    )
    return {
        "selected_knowledge_bases": selected_knowledge_bases,
        "retrieved_items": items,
        "retrieval_queries": queries_used,
        "trace_steps": trace_steps,
    }


def _analyze_retrieval(state: AgentState) -> AgentState:
    retrieval_quality, retrieval_quality_reason = analyze_retrieval_quality(
        route_type=state["route_type"],
        selected_knowledge_bases=state.get("selected_knowledge_bases", []),
        items=state.get("retrieved_items", []),
    )
    trace_steps = _append_trace(
        state,
        node="analyze_retrieval",
        meta={
            "retrieval_quality": retrieval_quality,
            "retrieval_quality_reason": retrieval_quality_reason,
        },
    )
    return {
        "retrieval_quality": retrieval_quality,
        "retrieval_quality_reason": retrieval_quality_reason,
        "trace_steps": trace_steps,
    }


def _decide_more_context(state: AgentState) -> AgentState:
    need_more_context, need_more_context_reason = decide_need_more_context(
        route_type=state["route_type"],
        retrieval_quality=state.get("retrieval_quality", "unknown"),
        items=state.get("retrieved_items", []),
        search_round=state.get("search_round", 1),
    )
    trace_steps = _append_trace(
        state,
        node="decide_more_context",
        meta={
            "need_more_context": need_more_context,
            "need_more_context_reason": need_more_context_reason,
        },
    )
    return {
        "need_more_context": need_more_context,
        "need_more_context_reason": need_more_context_reason,
        "trace_steps": trace_steps,
    }


def _rerank_results(state: AgentState) -> AgentState:
    # 检索完成后按任务类型再重排一次，提升下游上下文质量。
    reranked_items, rerank_reason = rerank_retrieved_items(
        route_type=state["route_type"],
        items=state.get("retrieved_items", []),
    )
    trace_steps = _append_trace(
        state,
        node="rerank_results",
        meta={
            "rerank_applied": True,
            "rerank_reason": rerank_reason,
            "reranked_count": len(reranked_items),
        },
    )
    return {
        "retrieved_items": reranked_items,
        "rerank_applied": True,
        "rerank_reason": rerank_reason,
        "trace_steps": trace_steps,
    }


def _assess_human_review(state: AgentState) -> AgentState:
    human_review_required, human_review_reason = assess_human_review_need(
        question=state["question"],
        route_type=state["route_type"],
        retrieval_quality=state.get("retrieval_quality", "unknown"),
        selected_tool=state.get("selected_tool", "build_qa_context"),
        items=state.get("retrieved_items", []),
    )
    trace_steps = _append_trace(
        state,
        node="assess_human_review",
        meta={
            "human_review_required": human_review_required,
            "human_review_reason": human_review_reason,
        },
    )
    return {
        "human_review_required": human_review_required,
        "human_review_reason": human_review_reason,
        "trace_steps": trace_steps,
    }


def _expand_search(state: AgentState) -> AgentState:
    expanded_top_k = min(state.get("top_k", 4) + 2, 10)
    selected_knowledge_bases, items, queries_used = search_knowledge(
        db=state["db"],
        question=state["question"],
        rewritten_query=state.get("rewritten_query") if state.get("rewrite_accepted") else None,
        route_type=state["route_type"],
        knowledge_base_id=state.get("knowledge_base_id"),
        top_k=expanded_top_k,
    )
    next_search_round = state.get("search_round", 1) + 1
    trace_steps = _append_trace(
        state,
        node="expand_search",
        meta={
            "search_round": next_search_round,
            "expanded_top_k": expanded_top_k,
            "queries_used": queries_used,
            "retrieved_count": len(items),
        },
    )
    return {
        "top_k": expanded_top_k,
        "search_round": next_search_round,
        "selected_knowledge_bases": selected_knowledge_bases,
        "retrieved_items": items,
        "retrieval_queries": queries_used,
        "trace_steps": trace_steps,
    }


def _prepare_qa_context(state: AgentState) -> AgentState:
    return _prepare_context_with_tool(state, "prepare_qa_context", "build_qa_context")


def _prepare_summary_context(state: AgentState) -> AgentState:
    return _prepare_context_with_tool(state, "prepare_summary_context", "summarize_context")


def _prepare_comparison_context(state: AgentState) -> AgentState:
    return _prepare_context_with_tool(state, "prepare_comparison_context", "compare_contexts")


def _prepare_context_with_tool(state: AgentState, node: str, tool_name: str) -> AgentState:
    items = state.get("retrieved_items", [])
    if tool_name == "summarize_context":
        organized_items, context_lines = summarize_context(items)
    elif tool_name == "compare_contexts":
        organized_items, context_lines = compare_contexts(items)
    else:
        organized_items, context_lines = build_qa_context(items)

    citations, citations_json = build_citations(organized_items)
    trace_steps = _append_trace(
        state,
        node=node,
        meta={
            "selected_tool": tool_name,
            "organized_count": len(organized_items),
            "context_preview": context_lines[:3],
        },
    )
    return {
        "organized_items": organized_items,
        "context_lines": context_lines,
        "citations": citations,
        "citations_json": citations_json,
        "context_count": len(organized_items),
        "trace_steps": trace_steps,
    }


def _generate_answer(state: AgentState) -> AgentState:
    items = state.get("retrieved_items", [])
    selected_knowledge_bases = state.get("selected_knowledge_bases", [])

    if not selected_knowledge_bases:
        answer = "当前系统还没有可用知识库，请先创建知识库并上传文档。"
        trace_steps = _append_trace(state, "generate_answer", {"status": "no_knowledge_base"})
        return {
            "answer": answer,
            "context_count": 0,
            "citations": [],
            "citations_json": [],
            "trace_steps": trace_steps,
        }

    if not items:
        answer = "已完成知识库路由，但暂时没有检索到相关内容，请尝试换一种问法。"
        trace_steps = _append_trace(state, "generate_answer", {"status": "no_retrieval_result"})
        return {
            "answer": answer,
            "context_count": 0,
            "citations": [],
            "citations_json": [],
            "trace_steps": trace_steps,
        }

    answer = generate_answer(
        state["question"],
        state.get("context_lines", []),
        route_type=state["route_type"],
    )
    if state.get("human_review_required"):
        answer = f"以下内容建议人工确认后再执行。\n\n{answer}"
    trace_steps = _append_trace(
        state,
        node="generate_answer",
        meta={"status": "completed", "answer_preview": answer[:120]},
    )
    return {"answer": answer, "trace_steps": trace_steps}


def compose_response_from_state(
    conversation_id: int,
    agent_run_id: int,
    question: str,
    state: AgentState,
) -> ChatAskResponse:
    return ChatAskResponse(
        conversation_id=conversation_id,
        agent_run_id=agent_run_id,
        question=question,
        answer=state["answer"],
        citations=state.get("citations", []),
        context_count=state.get("context_count", 0),
        route_type=state["route_type"],
        route_reason=_compose_route_reason(state["route_reason"], state["route_type"]),
        selected_tool=state["selected_tool"],
        selected_tool_reason=state["selected_tool_reason"],
        human_review_required=state.get("human_review_required", False),
        human_review_reason=state.get("human_review_reason", ""),
        selected_knowledge_bases=state.get("selected_knowledge_bases", []),
    )


def build_trace_payload(state: AgentState) -> dict:
    return {
        "route_type": state.get("route_type"),
        "route_reason": state.get("route_reason"),
        "rewritten_query": state.get("rewritten_query"),
        "rewrite_reason": state.get("rewrite_reason"),
        "rewrite_accepted": state.get("rewrite_accepted"),
        "rewrite_assessment_reason": state.get("rewrite_assessment_reason"),
        "selected_tool": state.get("selected_tool"),
        "selected_tool_reason": state.get("selected_tool_reason"),
        "retrieval_quality": state.get("retrieval_quality"),
        "retrieval_quality_reason": state.get("retrieval_quality_reason"),
        "retrieval_queries": state.get("retrieval_queries", []),
        "rerank_applied": state.get("rerank_applied"),
        "rerank_reason": state.get("rerank_reason"),
        "human_review_required": state.get("human_review_required"),
        "human_review_reason": state.get("human_review_reason"),
        "need_more_context": state.get("need_more_context"),
        "need_more_context_reason": state.get("need_more_context_reason"),
        "search_round": state.get("search_round", 1),
        "selected_knowledge_bases": [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in state.get("selected_knowledge_bases", [])
        ],
        "context_count": state.get("context_count", 0),
        "steps": state.get("trace_steps", []),
    }


def _compose_route_reason(base_reason: str, route_type: str) -> str:
    if route_type == "summary":
        return f"{base_reason} 当前使用扩展检索和分组汇总策略。"
    if route_type == "comparison":
        return f"{base_reason} 当前使用跨知识库均衡取样和对比组织策略。"
    return f"{base_reason} 当前使用精简问答策略。"


def _append_trace(state: AgentState, node: str, meta: dict) -> list[dict]:
    trace_steps = list(state.get("trace_steps", []))
    if node == "route_question":
        detail = f"任务路由命中 {meta.get('route_type', 'unknown')}。"
    elif node == "rewrite_query":
        detail = "已完成检索前查询改写。"
    elif node == "assess_rewrite":
        detail = "已完成查询改写质量评估与回退判断。"
    elif node == "tool_select":
        detail = f"工具选择命中 {meta.get('selected_tool', 'unknown')}。"
    elif node == "search_knowledge":
        detail = (
            f"第 {meta.get('search_round', 1)} 轮完成知识库候选路由与检索，"
            f"共返回 {meta.get('retrieved_count', 0)} 条结果。"
        )
    elif node == "analyze_retrieval":
        detail = f"检索质量评估结果：{meta.get('retrieval_quality', 'unknown')}。"
    elif node == "rerank_results":
        detail = "已完成检索结果重排，准备进入上下文整理。"
    elif node == "assess_human_review":
        detail = "已完成人工确认需求评估。"
    elif node == "decide_more_context":
        detail = "已完成是否补充上下文的判断。"
    elif node == "expand_search":
        detail = (
            f"执行补充检索，进入第 {meta.get('search_round', 1)} 轮搜索，"
            f"当前返回 {meta.get('retrieved_count', 0)} 条结果。"
        )
    elif node.startswith("prepare_"):
        detail = f"完成上下文整理，共保留 {meta.get('organized_count', 0)} 条内容。"
    elif node == "generate_answer":
        detail = f"回答生成状态：{meta.get('status', 'unknown')}。"
    else:
        detail = "完成工作流节点处理。"
    trace_steps.append({"node": node, "detail": detail, "meta": meta})
    return trace_steps


def _prepare_branch_selector(state: AgentState) -> str:
    selected_tool = state.get("selected_tool", "build_qa_context")
    if selected_tool == "summarize_context":
        return "prepare_summary_context"
    if selected_tool == "compare_contexts":
        return "prepare_comparison_context"
    return "prepare_qa_context"


def _decision_selector(state: AgentState) -> str:
    if state.get("need_more_context"):
        return "expand_search"
    return "rerank_results"


_compiled_graph = None


def _get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        graph = StateGraph(AgentState)
        graph.add_node("route_question", _route_question)
        graph.add_node("rewrite_query", _rewrite_query)
        graph.add_node("assess_rewrite", _assess_rewrite)
        graph.add_node("tool_select", _select_tool)
        graph.add_node("search_knowledge", _search_knowledge)
        graph.add_node("analyze_retrieval", _analyze_retrieval)
        graph.add_node("decide_more_context", _decide_more_context)
        graph.add_node("rerank_results", _rerank_results)
        graph.add_node("assess_human_review", _assess_human_review)
        graph.add_node("expand_search", _expand_search)
        graph.add_node("prepare_qa_context", _prepare_qa_context)
        graph.add_node("prepare_summary_context", _prepare_summary_context)
        graph.add_node("prepare_comparison_context", _prepare_comparison_context)
        graph.add_node("generate_answer", _generate_answer)

        graph.add_edge(START, "route_question")
        graph.add_edge("route_question", "rewrite_query")
        graph.add_edge("rewrite_query", "assess_rewrite")
        graph.add_edge("assess_rewrite", "tool_select")
        graph.add_edge("tool_select", "search_knowledge")
        graph.add_edge("search_knowledge", "analyze_retrieval")
        graph.add_edge("analyze_retrieval", "decide_more_context")
        graph.add_conditional_edges(
            "decide_more_context",
            _decision_selector,
            {
                "expand_search": "expand_search",
                "rerank_results": "rerank_results",
            },
        )
        graph.add_edge("expand_search", "analyze_retrieval")
        graph.add_conditional_edges(
            "rerank_results",
            lambda _state: "assess_human_review",
            {
                "assess_human_review": "assess_human_review",
            },
        )
        graph.add_conditional_edges(
            "assess_human_review",
            _prepare_branch_selector,
            {
                "prepare_qa_context": "prepare_qa_context",
                "prepare_summary_context": "prepare_summary_context",
                "prepare_comparison_context": "prepare_comparison_context",
            },
        )
        graph.add_edge("prepare_qa_context", "generate_answer")
        graph.add_edge("prepare_summary_context", "generate_answer")
        graph.add_edge("prepare_comparison_context", "generate_answer")
        graph.add_edge("generate_answer", END)
        _compiled_graph = graph.compile()
    return _compiled_graph
