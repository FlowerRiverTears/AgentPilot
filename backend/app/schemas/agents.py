from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    system_prompt: str = "You are a useful enterprise AI agent."
    model: str | None = None
    model_config_id: str | None = None
    knowledge_base_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)


class AgentUpdate(AgentCreate):
    pass


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


class AgentRunSummary(BaseModel):
    run_id: str
    agent_id: str
    agent_name: str = "未知智能体"
    status: str
    input: str
    model: str = ""
    trace_id: str | None = None
    created_at: str


class AgentRunDetail(AgentRunSummary):
    answer: str
    citations: list[dict] = Field(default_factory=list)
    steps: list[dict[str, str]] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
