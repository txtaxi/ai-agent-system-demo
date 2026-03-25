from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.chat import ConversationRead, MessageRead
from app.services.conversation_service import list_conversations, list_messages

router = APIRouter(prefix="/conversations")


@router.get("", response_model=list[ConversationRead])
def list_conversations_endpoint(
    db: Session = Depends(get_db),
) -> list[ConversationRead]:
    return list_conversations(db)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def list_messages_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> list[MessageRead]:
    try:
        return list_messages(db, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
