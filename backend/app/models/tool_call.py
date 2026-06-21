import uuid

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ToolCall(Base, TimestampMixin):
    """工具调用日志表，记录每次工具调用的输入、输出、状态和耗时。"""

    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    tool_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tools.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    input: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="success", nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
