from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.chat_service import ask_with_rag, stream_ask_with_rag

router = APIRouter(prefix="/chat")


@router.post("/ask", response_model=ChatAskResponse)
def ask_endpoint(
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
) -> ChatAskResponse:
    return ask_with_rag(db, payload)


@router.post("/ask/stream")
def ask_stream_endpoint(
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        stream_ask_with_rag(db, payload),
        media_type="text/event-stream",
    )
