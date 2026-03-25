from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.retrieval import RetrievalSearchRequest, RetrievalSearchResponse
from app.services.retrieval_service import search_chunks

router = APIRouter(prefix="/retrieval")


@router.post("/search", response_model=RetrievalSearchResponse)
def search_chunks_endpoint(
    payload: RetrievalSearchRequest,
    db: Session = Depends(get_db),
) -> RetrievalSearchResponse:
    return search_chunks(db, payload)
