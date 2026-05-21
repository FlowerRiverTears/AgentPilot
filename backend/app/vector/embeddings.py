import hashlib
import math


class EmbeddingService:
    """Deterministic local embedding stub.

    It keeps the MVP runnable without an external embedding model. Replace this
    with a provider adapter when wiring real embeddings.
    """

    dimensions = 64

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = digest[0] % self.dimensions
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
