import uuid as uuid_lib

from pydantic import BaseModel, Field, field_validator


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    system_prompt: str = "You are a useful enterprise AI agent."
    model: str | None = None
    model_config_id: str | None = None
    knowledge_base_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    sub_agent_ids: list[str] = Field(default_factory=list)
    tool_chain: list[dict] = Field(default_factory=list)

    @field_validator('model_config_id')
    @classmethod
    def validate_uuid(cls, v):
        if v:
            try:
                uuid_lib.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid UUID format')
        return v

    @field_validator('tool_chain')
    @classmethod
    def validate_tool_chain(cls, v):
        if v and len(v) > 10:
            raise ValueError('Tool chain cannot exceed 10 steps')
        return v


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    model_config_id: str | None = None
    knowledge_base_ids: list[str] | None = None
    tool_ids: list[str] | None = None
    sub_agent_ids: list[str] | None = None
    tool_chain: list[dict] | None = None


class AgentRead(AgentCreate):
    id: str
    status: str = "draft"


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentRunCreate(BaseModel):
    agent_id: str
    input: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list)
    file_content: str = ""
    file_name: str = ""

    @field_validator('agent_id')
    @classmethod
    def validate_uuid(cls, v):
        if v:
            try:
                uuid_lib.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid UUID format')
        return v


class AgentRunSummary(BaseModel):
    run_id: str
    agent_id: str
    agent_name: str = "未知智能体"
    status: str
    input: str
    model: str = ""
    duration_ms: int | None = None
    trace_id: str | None = None
    created_at: str


class AgentRunDetail(AgentRunSummary):
    answer: str
    citations: list[dict] = Field(default_factory=list)
    steps: list[dict[str, str]] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
    tool_results: list[dict[str, str]] = Field(default_factory=list)
