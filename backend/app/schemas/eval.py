import uuid

from pydantic import BaseModel, Field, field_validator


class EvalCaseCreate(BaseModel):
    """评测用例创建模型"""

    question: str = Field(min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)


class EvalDatasetCreate(BaseModel):
    """评测数据集创建模型"""

    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    agent_id: str
    cases: list[EvalCaseCreate] = Field(default_factory=list)

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("agent_id must be a valid UUID")
        return v


class EvalDatasetRead(BaseModel):
    """评测数据集读取模型"""

    id: str
    name: str
    description: str
    agent_id: str
    cases: list[dict]
    created_at: str


class EvalResultRead(BaseModel):
    """评测结果详情读取模型"""

    id: str
    dataset_id: str
    agent_id: str
    status: str
    total_cases: int
    passed_cases: int
    accuracy: float
    avg_duration_ms: int
    details: list[dict]
    created_at: str


class EvalResultSummary(BaseModel):
    """评测结果摘要读取模型"""

    id: str
    dataset_id: str
    agent_id: str
    status: str
    total_cases: int
    passed_cases: int
    accuracy: float
    avg_duration_ms: int
    created_at: str
