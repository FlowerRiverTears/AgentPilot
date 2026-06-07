import base64
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

        self._mm_base_url = settings.multimodal_embedding_base_url
        self._mm_api_key = settings.multimodal_embedding_api_key
        self._mm_model = settings.multimodal_embedding_model
        self._mm_dimensions = settings.multimodal_embedding_dimensions

    @property
    def multimodal_available(self) -> bool:
        return bool(self._mm_model and self._mm_base_url)

    async def embed_text(self, text: str) -> list[float]:
        if self._model and self._base_url:
            return await self._remote_embed(text)
        return self._local_embed(text)

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        if not self.multimodal_available:
            logger.warning("Multimodal embedding not configured, falling back to local stub")
            return self._local_image_embed(image_bytes)
        return await self._remote_multimodal_embed(image_bytes)

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
        except Exception as exc:
            logger.warning("Remote embedding failed, falling back to local stub: %s", exc)
            return self._local_embed(text)

    async def _remote_multimodal_embed(self, image_bytes: bytes) -> list[float]:
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            async with httpx.AsyncClient(timeout=120) as client:
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
                self._mm_dimensions = len(embedding)
                return embedding
        except Exception as exc:
            logger.warning("Remote multimodal embedding failed, falling back to local stub: %s", exc)
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

        vector = [0.0] * self._mm_dimensions
        for i in range(0, min(len(image_bytes), 8192), 4):
            chunk = image_bytes[i : i + 4]
            digest = hashlib.sha256(chunk).digest()
            index = int.from_bytes(digest[:4], "big") % self._mm_dimensions
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
