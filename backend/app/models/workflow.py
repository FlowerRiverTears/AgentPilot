import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Workflow(Base, TimestampMixin):
    """工作流定义"""
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    nodes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # nodes 格式: [{"id": "node-1", "type": "start", "label": "开始", "config": {}}, ...]
    # agent 节点 config: {"agent_id": "xxx"}
    # tool 节点 config: {"tool_id": "xxx"}
    # knowledge 节点 config: {"knowledge_base_id": "xxx", "top_k": 3}
    # condition 节点 config: {"rules": [{"keyword": "xxx", "target_node": "node-2"}], "default_target": "node-3"}
    edges: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # edges 格式: [{"source": "node-1", "target": "node-2"}, ...]
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)  # draft/published


class WorkflowRun(Base, TimestampMixin):
    """工作流执行记录"""
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
    node_results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # node_results: [{"node_id": "node-1", "node_type": "agent", "status": "completed", "output": "...", "duration_ms": 123}]
    duration_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
