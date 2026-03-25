from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.schemas.retrieval import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalSearchResultItem,
)
from app.services.embedding_service import generate_embedding


def search_chunks(db: Session, payload: RetrievalSearchRequest) -> RetrievalSearchResponse:
    # 检索层只负责向量查询与结果包装，不处理任务路由和回答生成。
    query_embedding = generate_embedding(payload.query)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    stmt: Select[tuple[DocumentChunk, Document, KnowledgeBase, float]] = (
        select(DocumentChunk, Document, KnowledgeBase, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .where(DocumentChunk.embedding.is_not(None))
    )

    knowledge_base_ids = _normalize_knowledge_base_ids(payload)
    if knowledge_base_ids:
        stmt = stmt.where(Document.knowledge_base_id.in_(knowledge_base_ids))

    stmt = stmt.order_by(distance.asc()).limit(payload.limit)
    rows = db.execute(stmt).all()

    items = [
        RetrievalSearchResultItem(
            chunk_id=chunk.id,
            document_id=document.id,
            filename=document.filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=max(0.0, 1.0 - float(raw_distance)),
            knowledge_base_id=knowledge_base.id,
            knowledge_base_name=knowledge_base.name,
            metadata_json=chunk.metadata_json,
        )
        for chunk, document, knowledge_base, raw_distance in rows
    ]

    return RetrievalSearchResponse(
        query=payload.query,
        total=len(items),
        items=items,
    )


def retrieve_relevant_chunks(
    db: Session,
    query: str,
    knowledge_base_id: int | None = None,
    knowledge_base_ids: list[int] | None = None,
    limit: int = 4,
) -> list[RetrievalSearchResultItem]:
    # 给上层工作流和工具层复用的轻量封装。
    response = search_chunks(
        db,
        RetrievalSearchRequest(
            query=query,
            knowledge_base_id=knowledge_base_id,
            knowledge_base_ids=knowledge_base_ids,
            limit=limit,
        ),
    )
    return response.items


def _normalize_knowledge_base_ids(payload: RetrievalSearchRequest) -> list[int]:
    if payload.knowledge_base_ids:
        return list(dict.fromkeys(payload.knowledge_base_ids))
    if payload.knowledge_base_id is not None:
        return [payload.knowledge_base_id]
    return []
