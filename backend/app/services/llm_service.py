import json

import httpx

from app.core.config import settings

SUMMARY_PREFIX = "请围绕以下主题总结关键制度、规则和流程："
COMPARISON_PREFIX = "请提取以下问题中的对比对象、差异点、相同点和规则依据："


def generate_answer(question: str, context_lines: list[str], route_type: str = "qa") -> str:
    """优先尝试真实模型；未配置时回退到本地调试回答。"""
    if not settings.openai_api_key or not settings.openai_base_url:
        return _fallback_answer(context_lines, route_type)

    try:
        return _call_openai_compatible(question, context_lines, route_type)
    except Exception:
        return _fallback_answer(context_lines, route_type)


def select_tool(question: str, route_type: str) -> tuple[str, str]:
    """规则优先，必要时由模型辅助判断工具选择。"""
    fallback_tool, fallback_reason = _fallback_select_tool(route_type)

    if not settings.openai_api_key or not settings.openai_base_url:
        return fallback_tool, fallback_reason

    try:
        llm_tool, llm_reason = _call_tool_selector(question, route_type)
    except Exception:
        return fallback_tool, fallback_reason

    if llm_tool not in {"build_qa_context", "summarize_context", "compare_contexts"}:
        return fallback_tool, fallback_reason

    return llm_tool, f"{fallback_reason} 模型辅助判断：{llm_reason}"


def rewrite_query(question: str, route_type: str) -> tuple[str, str]:
    """在检索前对问题做轻量改写，优先使用规则，模型可用时再做增强。"""
    fallback_query, fallback_reason = _fallback_rewrite_query(question, route_type)

    if not settings.openai_api_key or not settings.openai_base_url:
        return fallback_query, fallback_reason

    try:
        llm_query, llm_reason = _call_query_rewriter(question, route_type)
    except Exception:
        return fallback_query, fallback_reason

    normalized = _normalize_rewritten_query(llm_query or "", route_type)
    if not normalized:
        return fallback_query, fallback_reason

    return normalized, f"{fallback_reason} 模型辅助改写：{llm_reason}"


def assess_query_rewrite(
    question: str,
    rewritten_query: str,
    route_type: str,
) -> tuple[bool, str]:
    """评估本次改写是否值得参与后续检索。"""
    question_text = " ".join(question.strip().split())
    rewritten_text = " ".join(rewritten_query.strip().split())

    if route_type == "qa":
        return False, "标准问答优先保持原问题，避免过度改写。"
    if not rewritten_text:
        return False, "改写结果为空，回退到原问题。"
    if rewritten_text == question_text:
        return False, "改写结果与原问题一致，没有额外检索价值。"

    if route_type == "summary":
        body = _strip_prefix(rewritten_text, SUMMARY_PREFIX).strip()
        if not body:
            return False, "总结类改写缺少主题内容，回退到原问题。"
        if len(body) < 4:
            return False, "总结类改写过短，回退到原问题。"
        return True, "总结类问题适合同时使用原问题和改写问题进行检索。"

    if route_type == "comparison":
        body = _strip_prefix(rewritten_text, COMPARISON_PREFIX).strip()
        if not body:
            return False, "对比类改写缺少主体内容，回退到原问题。"
        if len(body) < 4:
            return False, "对比类改写过短，回退到原问题。"
        return True, "对比类问题适合同时使用原问题和改写问题进行检索。"

    return False, "当前任务类型不启用改写增强检索。"


def _fallback_select_tool(route_type: str) -> tuple[str, str]:
    if route_type == "summary":
        return "summarize_context", "规则判断当前问题更偏总结任务。"
    if route_type == "comparison":
        return "compare_contexts", "规则判断当前问题更偏对比任务。"
    return "build_qa_context", "规则判断当前问题属于标准问答。"


def _fallback_rewrite_query(question: str, route_type: str) -> tuple[str, str]:
    normalized = _normalize_rewritten_query(question, route_type)
    if route_type == "summary":
        return f"{SUMMARY_PREFIX}{normalized}", "规则将总结类问题改写为更适合汇总检索的表达。"
    if route_type == "comparison":
        return f"{COMPARISON_PREFIX}{normalized}", "规则将对比类问题改写为更适合差异检索的表达。"
    return normalized, "标准问答保持原问题作为检索查询。"


def _normalize_rewritten_query(text: str, route_type: str) -> str:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return ""

    if route_type == "summary":
        return _strip_prefix(normalized, SUMMARY_PREFIX).strip()
    if route_type == "comparison":
        return _strip_prefix(normalized, COMPARISON_PREFIX).strip()
    return normalized


def _strip_prefix(text: str, prefix: str) -> str:
    normalized = text
    while normalized.startswith(prefix):
        normalized = normalized[len(prefix) :].strip()
    return normalized


def _fallback_answer(context_lines: list[str], route_type: str) -> str:
    if not context_lines:
        return "当前没有检索到相关内容，请尝试换一种问法。"

    if route_type == "summary":
        return "基于检索结果，系统整理出以下总结：\n\n" + "\n\n".join(context_lines)

    if route_type == "comparison":
        return "基于检索结果，系统整理出以下对比信息：\n\n" + "\n\n".join(context_lines)

    return "基于检索到的知识片段，系统整理出以下内容：\n\n" + "\n\n".join(context_lines)


def _call_openai_compatible(question: str, context_lines: list[str], route_type: str) -> str:
    context_text = "\n".join(context_lines)
    headers = _build_headers()
    system_prompt, user_prompt = _build_answer_prompts(question, context_text, route_type)
    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    data = _post_chat_completion(payload, headers)
    return data["choices"][0]["message"]["content"].strip()


def _call_tool_selector(question: str, route_type: str) -> tuple[str, str]:
    headers = _build_headers()
    system_prompt = (
        "你是企业知识库智能体的工具选择器。"
        "你只能在三个工具中选择一个：build_qa_context、summarize_context、compare_contexts。"
        "请基于问题和已有路由类型输出 JSON，不要输出额外说明。"
    )
    user_prompt = (
        "请为当前问题选择最合适的上下文工具。\n"
        f"问题：{question}\n"
        f"已有路由：{route_type}\n\n"
        '请输出 JSON，格式为：{"selected_tool":"...", "reason":"..."}'
    )
    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    data = _post_chat_completion(payload, headers)
    content = data["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)
    return parsed.get("selected_tool", ""), parsed.get("reason", "")


def _call_query_rewriter(question: str, route_type: str) -> tuple[str, str]:
    headers = _build_headers()
    system_prompt = (
        "你是企业知识库智能体的查询改写器。"
        "你的目标是把用户问题改写成更适合知识检索的表达。"
        "不得改变问题意图，不要引入原问题中没有的新事实。"
        "请输出 JSON，不要输出额外说明。"
    )
    user_prompt = (
        "请改写下面的问题，使其更适合知识库检索。\n"
        f"原问题：{question}\n"
        f"任务类型：{route_type}\n\n"
        '请输出 JSON，格式为：{"rewritten_query":"...", "reason":"..."}'
    )
    payload = {
        "model": settings.chat_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    data = _post_chat_completion(payload, headers)
    content = data["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)
    return parsed.get("rewritten_query", ""), parsed.get("reason", "")


def _post_chat_completion(payload: dict, headers: dict) -> dict:
    endpoint = settings.openai_base_url.rstrip("/") + "/chat/completions"
    timeout = httpx.Timeout(30.0, connect=10.0)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }


def _build_answer_prompts(question: str, context_text: str, route_type: str) -> tuple[str, str]:
    if route_type == "summary":
        return (
            "你是企业知识库总结助手。请严格基于提供的上下文做总结，按主题归纳重点，不要编造未出现的信息。",
            f"请总结下面问题对应的知识内容。\n问题：{question}\n\n可用上下文：\n{context_text}",
        )

    if route_type == "comparison":
        return (
            "你是企业知识库对比助手。请严格基于提供的上下文回答，优先输出比较维度、相同点、差异点和依据。",
            f"请基于上下文回答这个对比问题。\n问题：{question}\n\n可用上下文：\n{context_text}",
        )

    return (
        "你是企业知识库问答助手。请严格基于提供的上下文回答，优先给出直接答案，再补充必要依据，不要编造。",
        f"问题：{question}\n\n可用上下文：\n{context_text}",
    )
