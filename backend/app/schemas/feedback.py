from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    agent_run_id: int
    conversation_id: int | None = None
    rating: str = Field(pattern="^(positive|negative)$")
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackRead(BaseModel):
    id: int
    agent_run_id: int
    conversation_id: int | None
    rating: str
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackBucketStatRead(BaseModel):
    label: str
    total: int
    positive: int
    negative: int


class FeedbackStatsRead(BaseModel):
    total: int
    positive: int
    negative: int
    positive_rate: float
    negative_rate: float
    by_route: list[FeedbackBucketStatRead]
    by_tool: list[FeedbackBucketStatRead]
    by_retrieval_quality: list[FeedbackBucketStatRead]
    by_human_review: list[FeedbackBucketStatRead]
    by_knowledge_base: list[FeedbackBucketStatRead]


class NegativeFeedbackSampleRead(BaseModel):
    feedback_id: int
    agent_run_id: int
    conversation_id: int | None
    rating: str
    comment: str | None
    created_at: datetime
    user_query: str
    route: str
    selected_tool: str
    retrieval_quality: str
    human_review_required: bool | None
    knowledge_base_names: list[str]
