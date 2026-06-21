import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    rating: Mapped[str] = mapped_column(String(20), nullable=False)  # "like" or "dislike"
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
