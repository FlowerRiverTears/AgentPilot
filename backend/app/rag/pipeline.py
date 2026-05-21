from uuid import uuid4

from app.schemas.knowledge import RetrievedChunk
from app.vector.embeddings import embedding_service


class RAGPipeline:
    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
        clean_text = " ".join(text.split())
        if not clean_text:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(clean_text):
            end = min(start + chunk_size, len(clean_text))
            chunks.append(clean_text[start:end])
            if end == len(clean_text):
                break
            start = max(end - overlap, start + 1)
        return chunks

    def build_chunks(self, source: str, text: str) -> list[RetrievedChunk]:
        chunks = []
        for chunk in self.chunk_text(text):
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(uuid4()),
                    content=chunk,
                    score=0.0,
                    source=source,
                )
            )
        return chunks

    def retrieve(self, query: str, chunks: list[RetrievedChunk], top_k: int = 5) -> list[RetrievedChunk]:
        query_vector = embedding_service.embed_text(query)
        ranked: list[RetrievedChunk] = []

        for chunk in chunks:
            chunk_vector = embedding_service.embed_text(chunk.content)
            score = embedding_service.similarity(query_vector, chunk_vector)
            ranked.append(chunk.model_copy(update={"score": score}))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]


rag_pipeline = RAGPipeline()
