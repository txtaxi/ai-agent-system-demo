from datetime import datetime

from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    score: float
    knowledge_base_id: int
    knowledge_base_name: str


class KnowledgeBaseSelection(BaseModel):
    id: int
    name: str
    description: str | None = None
    selection_reason: str
    score: float


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    knowledge_base_id: int | None = None
    conversation_id: int | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class ChatAskResponse(BaseModel):
    conversation_id: int
    agent_run_id: int
    question: str
    answer: str
    citations: list[CitationItem]
    context_count: int
    route_type: str
    route_reason: str
    selected_tool: str
    selected_tool_reason: str
    human_review_required: bool
    human_review_reason: str
    awaiting_human_review: bool = False
    review_status: str = "completed"
    selected_knowledge_bases: list[KnowledgeBaseSelection]


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations_json: list[dict] | None
    agent_run_id: int | None = None
    route_type: str | None = None
    route_reason: str | None = None
    selected_tool: str | None = None
    selected_tool_reason: str | None = None
    human_review_required: bool | None = None
    human_review_reason: str | None = None
    awaiting_human_review: bool = False
    review_status: str | None = None
    selected_knowledge_bases: list[dict] = Field(default_factory=list)
    feedback_rating: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationRead(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
