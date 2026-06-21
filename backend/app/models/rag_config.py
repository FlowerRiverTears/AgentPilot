import uuid
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class RagConfig(Base, TimestampMixin):
    """RAG 检索调优配置（按知识库维度）"""
    __tablename__ = "rag_configs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=False, unique=True)
    chunk_size: Mapped[int] = mapped_column(Integer, default=500, nullable=False)  # 切块大小（字符数）
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 切块重叠（字符数）
    top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 检索返回数量
    score_threshold: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)  # 相似度阈值
    retrieval_weight_vector: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)  # 向量检索权重
    retrieval_weight_lexical: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)  # 关键词检索权重
