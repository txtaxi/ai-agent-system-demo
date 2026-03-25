from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead
from app.services.knowledge_base_service import create_knowledge_base, list_knowledge_bases

router = APIRouter(prefix="/knowledge-bases")


@router.post("", response_model=KnowledgeBaseRead)
def create_knowledge_base_endpoint(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    return create_knowledge_base(db, payload)


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases_endpoint(
    db: Session = Depends(get_db),
) -> list[KnowledgeBaseRead]:
    return list_knowledge_bases(db)
