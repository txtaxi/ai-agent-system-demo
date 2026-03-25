from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate


def create_knowledge_base(db: Session, payload: KnowledgeBaseCreate) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        name=payload.name,
        description=payload.description,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def list_knowledge_bases(db: Session) -> list[KnowledgeBase]:
    return list(db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())))
