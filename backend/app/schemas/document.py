from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: int
    knowledge_base_id: int
    filename: str
    file_type: str
    storage_path: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentProcessResult(BaseModel):
    document_id: int
    status: str
    chunk_count: int
    message: str
