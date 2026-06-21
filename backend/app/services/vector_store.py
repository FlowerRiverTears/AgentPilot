"""向量存储抽象层，支持 pgvector 和 Qdrant 切换。"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _vector_to_str(vector: list[float]) -> str:
    """将向量列表转换为 pgvector 接受的字符串格式：[0.1, 0.2, ...]"""
    return "[" + ",".join(str(x) for x in vector) + "]"


class VectorStoreBackend(ABC):
    """向量存储后端抽象接口"""

    @abstractmethod
    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        """插入或更新向量"""
        pass

    @abstractmethod
    async def search(
        self, collection: str, query_vector: list[float], top_k: int = 5, score_threshold: float = 0.0
    ) -> list[dict]:
        """向量检索，返回 [{"id": "...", "score": 0.95, "payload": {...}}]"""
        pass

    @abstractmethod
    async def delete(self, collection: str, point_id: str) -> None:
        """删除向量"""
        pass

    @abstractmethod
    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """确保集合存在"""
        pass


class PgVectorBackend(VectorStoreBackend):
    """pgvector 后端（使用现有的 PostgreSQL + pgvector）。

    collection 参数语义为知识库 ID（knowledge_base_id），用于过滤 document_chunks。
    point_id 参数语义为 document_chunks 记录的主键 ID。
    """

    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        """更新 document_chunks 表的 embedding 字段。

        Args:
            collection: 知识库 ID（pgvector 后端中不直接使用，元数据已存储在表中）
            point_id: document_chunks 记录的主键 ID
            vector: 向量数据
            payload: 附加载荷（pgvector 后端忽略，元数据已存储在表中）
        """
        vector_str = _vector_to_str(vector)
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("UPDATE document_chunks SET embedding = :vector WHERE id = :point_id"),
                {"vector": vector_str, "point_id": point_id},
            )
            await session.commit()

    async def search(
        self, collection: str, query_vector: list[float], top_k: int = 5, score_threshold: float = 0.0
    ) -> list[dict]:
        """使用 pgvector 余弦距离进行向量检索。

        Args:
            collection: 知识库 ID，用于过滤 document_chunks（通过 JOIN documents 表）
            query_vector: 查询向量
            top_k: 返回结果数量上限
            score_threshold: 相似度分数下限（score = 1 - cosine_distance）

        Returns:
            [{"id": "...", "score": 0.95, "payload": {"content": "..."}}]
        """
        vector_str = _vector_to_str(query_vector)
        # embedding <=> 是 pgvector 的余弦距离运算符，score = 1 - distance
        # document_chunks 没有 knowledge_base_id 字段，需 JOIN documents 表（参考 memory.py）
        sql = text(
            """
            SELECT dc.id, dc.content, 1 - (dc.embedding <=> :query_vector) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.knowledge_base_id = :kb_id
              AND 1 - (dc.embedding <=> :query_vector) >= :score_threshold
            ORDER BY dc.embedding <=> :query_vector
            LIMIT :top_k
            """
        )
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                sql,
                {
                    "query_vector": vector_str,
                    "kb_id": collection,
                    "score_threshold": score_threshold,
                    "top_k": top_k,
                },
            )
            results: list[dict] = []
            for row in rows.all():
                results.append(
                    {
                        "id": str(row.id),
                        "score": float(row.score),
                        "payload": {"content": row.content},
                    }
                )
            return results

    async def delete(self, collection: str, point_id: str) -> None:
        """pgvector 后端无需单独删除向量，document_chunks 删除时自动清理。"""
        pass

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """pgvector 后端的 document_chunks 表已存在，无需创建集合。"""
        pass


class QdrantBackend(VectorStoreBackend):
    """Qdrant 向量数据库后端，通过 REST API 操作。"""

    def __init__(self, url: str = "http://localhost:6333") -> None:
        self._url = url.rstrip("/")

    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        """插入或更新 Qdrant 中的向量点。"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{self._url}/collections/{collection}/points",
                json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            )
            response.raise_for_status()

    async def search(
        self, collection: str, query_vector: list[float], top_k: int = 5, score_threshold: float = 0.0
    ) -> list[dict]:
        """在 Qdrant 集合中进行向量检索。"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._url}/collections/{collection}/points/search",
                json={"vector": query_vector, "limit": top_k, "score_threshold": score_threshold},
            )
            response.raise_for_status()
            data = response.json()
            results: list[dict] = []
            for item in data.get("result", []):
                results.append(
                    {
                        "id": str(item.get("id")),
                        "score": float(item.get("score", 0.0)),
                        "payload": item.get("payload", {}) or {},
                    }
                )
            return results

    async def delete(self, collection: str, point_id: str) -> None:
        """删除 Qdrant 集合中的指定向量点。"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._url}/collections/{collection}/points/delete",
                json={"points": [point_id]},
            )
            response.raise_for_status()

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """确保 Qdrant 集合存在，不存在则创建（使用余弦距离）。"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{self._url}/collections/{collection}",
                json={"vectors": {"size": vector_size, "distance": "Cosine"}},
            )
            response.raise_for_status()


class VectorStoreFactory:
    """向量存储工厂，根据配置创建后端"""

    @staticmethod
    def create(backend: str = "pgvector", **kwargs) -> VectorStoreBackend:
        if backend == "qdrant":
            return QdrantBackend(url=kwargs.get("url", "http://localhost:6333"))
        return PgVectorBackend()


# 全局实例（默认 pgvector）
# 后续可通过配置切换
vector_store = VectorStoreFactory.create("pgvector")
