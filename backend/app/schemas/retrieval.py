from pydantic import BaseModel, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    knowledge_base_id: int | None = None
    knowledge_base_ids: list[int] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class RetrievalSearchResultItem(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    content: str
    score: float
    knowledge_base_id: int
    knowledge_base_name: str
    metadata_json: dict | None


class RetrievalSearchResponse(BaseModel):
    query: str
    total: int
    items: list[RetrievalSearchResultItem]
