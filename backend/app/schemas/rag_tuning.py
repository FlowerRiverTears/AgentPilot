from pydantic import BaseModel, Field

class RagConfigUpdate(BaseModel):
    chunk_size: int | None = Field(default=None, ge=100, le=2000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_weight_vector: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_weight_lexical: float | None = Field(default=None, ge=0.0, le=1.0)

class RagConfigRead(BaseModel):
    knowledge_base_id: str
    knowledge_base_name: str = ""
    chunk_size: int
    chunk_overlap: int
    top_k: int
    score_threshold: float
    retrieval_weight_vector: float
    retrieval_weight_lexical: float

class RetrievalTestRequest(BaseModel):
    knowledge_base_id: str
    query: str = Field(min_length=1)
    top_k: int | None = None
    score_threshold: float | None = None

class RetrievalTestResult(BaseModel):
    query: str
    chunks: list[dict]  # 检索到的文档切片
    total: int
