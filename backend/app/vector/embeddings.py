import base64
import logging
import math
import threading

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._base_url = settings.embedding_base_url or settings.llm_base_url
        self._api_key = settings.embedding_api_key or settings.llm_api_key
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

        self._mm_base_url = settings.multimodal_embedding_base_url
        self._mm_api_key = settings.multimodal_embedding_api_key
        self._mm_model = settings.multimodal_embedding_model
        self._mm_dimensions = settings.multimodal_embedding_dimensions

        self._dim_lock = threading.Lock()

    def _set_dimensions(self, value: int):
        """Thread-safe dimension setting."""
        with self._dim_lock:
            if self._dimensions is None:
                self._dimensions = value

    def _set_mm_dimensions(self, value: int):
        """Thread-safe multimodal dimension setting."""
        with self._dim_lock:
            if self._mm_dimensions is None:
                self._mm_dimensions = value

    @property
    def multimodal_available(self) -> bool:
        return bool(self._mm_model and self._mm_base_url)

    @property
    def dimensions(self) -> int:
        """当前生效的向量维度。多模态启用时统一使用多模态维度。"""
        if self.multimodal_available:
            return self._mm_dimensions
        return self._dimensions

    async def embed_text(self, text: str) -> list[float]:
        # 多模态可用时，文本也用多模态模型编码，确保和图片在同一向量空间
        if self.multimodal_available:
            return await self._remote_multimodal_text_embed(text)
        if self._model and self._base_url:
            return await self._remote_embed(text)
        return self._local_embed(text)

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        if not self.multimodal_available:
            logger.warning("Multimodal embedding not configured, falling back to local stub")
            return self._local_image_embed(image_bytes)
        return await self._remote_multimodal_image_embed(image_bytes)

    async def _remote_embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=settings.embedding_timeout) as client:
                response = await client.post(
                    f"{self._base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self._model, "input": text},
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._set_dimensions(len(embedding))
                return embedding
        except Exception as exc:
            logger.warning("Remote embedding failed, falling back to local stub: %s", exc)
            return self._local_embed(text)

    async def _remote_multimodal_text_embed(self, text: str) -> list[float]:
        """使用多模态模型的文本编码器，输出与图片在同一向量空间。"""
        try:
            async with httpx.AsyncClient(timeout=settings.embedding_timeout) as client:
                response = await client.post(
                    f"{self._mm_base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {self._mm_api_key}"},
                    json={
                        "model": self._mm_model,
                        "input": [{"type": "text", "text": text}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._set_mm_dimensions(len(embedding))
                return embedding
        except Exception as exc:
            logger.warning("Remote multimodal text embedding failed, falling back to local stub: %s", exc)
            return self._local_embed(text)

    async def _remote_multimodal_image_embed(self, image_bytes: bytes) -> list[float]:
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            async with httpx.AsyncClient(timeout=settings.embedding_batch_timeout) as client:
                response = await client.post(
                    f"{self._mm_base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {self._mm_api_key}"},
                    json={
                        "model": self._mm_model,
                        "input": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._set_mm_dimensions(len(embedding))
                return embedding
        except Exception as exc:
            logger.warning("Remote multimodal image embedding failed, falling back to local stub: %s", exc)
            return self._local_image_embed(image_bytes)

    def _local_embed(self, text: str) -> list[float]:
        import hashlib

        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        return self._normalize(vector)

    def _local_image_embed(self, image_bytes: bytes) -> list[float]:
        import hashlib

        vector = [0.0] * self.dimensions
        for i in range(0, min(len(image_bytes), 8192), 4):
            chunk = image_bytes[i : i + 4]
            digest = hashlib.sha256(chunk).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        return self._normalize(vector)

    def similarity(self, left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


_embedding_service = None


def get_embedding_service() -> "EmbeddingService":
    """Lazy-initialized embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
