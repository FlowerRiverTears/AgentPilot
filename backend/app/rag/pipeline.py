from uuid import uuid4

from app.rag.text_quality import is_readable_text
from app.schemas.knowledge import RetrievedChunk


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
            if is_readable_text(chunk):
                chunks.append(
                    RetrievedChunk(
                        chunk_id=str(uuid4()),
                        content=chunk,
                        score=0.0,
                        source=source,
                    )
                )
        return chunks


rag_pipeline = RAGPipeline()
