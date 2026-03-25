from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentChunkRead, DocumentProcessResult, DocumentRead
from app.services.document_service import (
    list_document_chunks,
    list_documents,
    process_document,
    save_uploaded_document,
)

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=DocumentRead)
def upload_document(
    knowledge_base_id: int = Query(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        return save_uploaded_document(db, knowledge_base_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[DocumentRead])
def list_documents_endpoint(
    knowledge_base_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    return list_documents(db, knowledge_base_id)


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def list_document_chunks_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> list[DocumentChunkRead]:
    try:
        return list_document_chunks(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/process", response_model=DocumentProcessResult)
def process_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentProcessResult:
    try:
        return process_document(db, document_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "不存在" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
