from datetime import datetime

from pydantic import BaseModel, Field


class AgentRunStepRead(BaseModel):
    node: str
    detail: str
    meta: dict | None = None


class AgentRunSummaryRead(BaseModel):
    route_type: str | None = None
    route_reason: str | None = None
    rewritten_query: str | None = None
    rewrite_reason: str | None = None
    rewrite_accepted: bool | None = None
    rewrite_assessment_reason: str | None = None
    selected_tool: str | None = None
    selected_tool_reason: str | None = None
    retrieval_quality: str | None = None
    retrieval_quality_reason: str | None = None
    retrieval_queries: list[str] = Field(default_factory=list)
    rerank_applied: bool | None = None
    rerank_reason: str | None = None
    human_review_required: bool | None = None
    human_review_reason: str | None = None
    review_status: str | None = None
    review_comment: str | None = None
    need_more_context: bool | None = None
    need_more_context_reason: str | None = None
    search_round: int = 1
    selected_knowledge_bases: list[dict] = Field(default_factory=list)
    context_count: int = 0


class AgentRunRead(BaseModel):
    id: int
    conversation_id: int | None
    user_query: str
    route: str | None
    status: str
    trace_json: dict | None
    started_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True


class AgentRunTraceRead(BaseModel):
    id: int
    conversation_id: int | None
    user_query: str
    route: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary: AgentRunSummaryRead
    steps: list[AgentRunStepRead]


class AgentRunReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: str | None = Field(default=None, max_length=1000)
