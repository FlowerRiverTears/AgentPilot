import uuid

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(80), nullable=False)  # 前端生成的会话ID
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    messages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # 完整消息列表
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 上下文压缩摘要
    summary_to_turn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 摘要覆盖到第几轮
