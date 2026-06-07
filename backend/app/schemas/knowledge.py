from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""


class KnowledgeBaseRead(KnowledgeBaseCreate):
    id: str
    document_count: int = 0


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunk(BaseModel):
    chunk_id: str
    content: str
    score: float
    source: str
    content_type: str = "text"
    image_url: str = ""
    document_id: str = ""
    source_uri: str = ""
    section_path: str = ""
    page_number: int | None = None
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    vector_score: float = 0.0
    lexical_score: float = 0.0
