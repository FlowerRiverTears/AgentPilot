import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EvalDataset(Base, TimestampMixin):
    """评测数据集"""

    __tablename__ = "eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    # 用例列表：[{"question": "...", "expected_keywords": ["关键词1", "关键词2"]}]
    cases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class EvalResult(Base, TimestampMixin):
    """评测结果"""

    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    # running / completed / failed
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 每条用例的详细结果
    details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_eval_result_status",
        ),
    )
