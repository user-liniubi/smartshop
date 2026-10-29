from pydantic import BaseModel, Field


class RagAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    product_id: int | None = Field(default=None, gt=0)
    top_k: int | None = Field(default=None, ge=1, le=10)


class CitationResponse(BaseModel):
    document_id: int
    chunk_id: str
    filename: str
    title: str
    page: int | None = None
    heading: str | None = None
    excerpt: str
    similarity: float


class RagAskResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[CitationResponse]
    model: str
