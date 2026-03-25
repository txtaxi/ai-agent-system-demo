from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackRead,
    FeedbackStatsRead,
    NegativeFeedbackSampleRead,
)
from app.services.feedback_service import (
    create_or_update_feedback,
    get_feedback_stats,
    list_negative_feedback_samples,
)

router = APIRouter(prefix="/feedback")


@router.post("", response_model=FeedbackRead)
def create_feedback_endpoint(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackRead:
    try:
        return create_or_update_feedback(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stats", response_model=FeedbackStatsRead)
def get_feedback_stats_endpoint(
    db: Session = Depends(get_db),
) -> FeedbackStatsRead:
    return get_feedback_stats(db)


@router.get("/negative-samples", response_model=list[NegativeFeedbackSampleRead])
def list_negative_feedback_samples_endpoint(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[NegativeFeedbackSampleRead]:
    return list_negative_feedback_samples(db, limit=limit)
