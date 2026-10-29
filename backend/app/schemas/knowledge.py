from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import KnowledgeDocumentStatus


class KnowledgeDocumentResponse(BaseModel):
    id: int
    product_id: int | None
    filename: str
    title: str
    source_type: str
    status: KnowledgeDocumentStatus
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeUploadResponse(BaseModel):
    document: KnowledgeDocumentResponse
    chunk_count: int
    duplicate: bool = False
