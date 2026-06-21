from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    id: str
    type: str  # start/agent/tool/knowledge/condition/end
    label: str = ""
    config: dict = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None
    status: str | None = None


class WorkflowRead(BaseModel):
    id: str
    name: str
    description: str
    nodes: list[dict]
    edges: list[dict]
    status: str
    created_at: str


class WorkflowRunCreate(BaseModel):
    workflow_id: str
    input: str = Field(min_length=1)


class WorkflowRunRead(BaseModel):
    id: str
    workflow_id: str
    status: str
    input: str
    output: str | None
    node_results: list[dict]
    duration_ms: int
    error: str | None
    created_at: str
