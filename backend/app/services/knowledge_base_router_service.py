import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.embedding_service import generate_embedding


@dataclass
class KnowledgeBaseCandidate:
    knowledge_base: KnowledgeBase
    score: float
    reason: str


def resolve_knowledge_base_candidates(
    db: Session,
    question: str,
    knowledge_base_id: int | None = None,
    limit: int = 3,
) -> tuple[list[KnowledgeBaseCandidate], str]:
    """解析本次请求应该优先使用的知识库候选列表。"""

    if knowledge_base_id is not None:
        knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
        if knowledge_base is None:
            return [], "指定的知识库不存在。"
        return [
            KnowledgeBaseCandidate(
                knowledge_base=knowledge_base,
                score=1.0,
                reason="使用用户显式选择的知识库。",
            )
        ], "使用用户显式选择的知识库。"

    knowledge_bases = list(db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())))
    if not knowledge_bases:
        return [], "当前系统还没有可用知识库。"

    if len(knowledge_bases) == 1:
        return [
            KnowledgeBaseCandidate(
                knowledge_base=knowledge_bases[0],
                score=1.0,
                reason="当前只有一个知识库，系统已自动选中。",
            )
        ], "当前只有一个知识库，系统已自动选中。"

    scored_candidates: list[KnowledgeBaseCandidate] = []
    for item in knowledge_bases:
        semantic_score, keyword_score = _score_knowledge_base(db, question, item)
        total_score = semantic_score + keyword_score
        scored_candidates.append(
            KnowledgeBaseCandidate(
                knowledge_base=item,
                score=total_score,
                reason=f"语义得分 {semantic_score:.3f}，关键词得分 {keyword_score:.3f}。",
            )
        )

    scored_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return scored_candidates[:limit], "系统根据问题内容自动选择了最相关的知识库候选。"


def _score_knowledge_base(
    db: Session,
    question: str,
    knowledge_base: KnowledgeBase,
) -> tuple[float, float]:
    kb_text = _build_knowledge_base_text(db, knowledge_base)
    semantic_score = _cosine_similarity(generate_embedding(question), generate_embedding(kb_text))
    keyword_score = _keyword_overlap_score(question, kb_text)
    return semantic_score, keyword_score


def _build_knowledge_base_text(db: Session, knowledge_base: KnowledgeBase) -> str:
    documents = list(
        db.scalars(
            select(Document).where(Document.knowledge_base_id == knowledge_base.id).order_by(Document.created_at.desc())
        )
    )
    filenames = " ".join(document.filename for document in documents[:20])
    parts = [
        knowledge_base.name or "",
        knowledge_base.description or "",
        filenames,
    ]
    return " ".join(part for part in parts if part).strip()


def _keyword_overlap_score(question: str, kb_text: str) -> float:
    question_tokens = set(_extract_keywords(question))
    kb_tokens = set(_extract_keywords(kb_text))
    if not question_tokens or not kb_tokens:
        return 0.0
    overlap = len(question_tokens & kb_tokens)
    return overlap / max(len(question_tokens), 1)


def _extract_keywords(text: str) -> list[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    return [token for token in normalized.split() if len(token) >= 2]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
