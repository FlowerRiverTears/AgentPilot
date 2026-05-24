import logging
import math

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    dimensions: int = 1024

    def __init__(self) -> None:
        self._base_url = settings.embedding_base_url or settings.llm_base_url
        self._api_key = settings.embedding_api_key or settings.llm_api_key
        self._model = settings.embedding_model

    async def embed_text(self, text: str) -> list[float]:
        if self._model and self._base_url:
            return await self._remote_embed(text)
        return self._local_embed(text)

    async def _remote_embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self._base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self._model, "input": text},
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self.dimensions = len(embedding)
                return embedding
        except Exception:
            logger.warning("Remote embedding failed, falling back to local stub", exc_info=True)
            return self._local_embed(text)

    def _local_embed(self, text: str) -> list[float]:
        import hashlib

        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode("utf-8")).digest()
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


embedding_service = EmbeddingService()
