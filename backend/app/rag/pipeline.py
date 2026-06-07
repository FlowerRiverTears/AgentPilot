from __future__ import annotations

import re
from uuid import uuid4

from app.rag.document_loader import ExtractedImage
from app.rag.text_quality import is_readable_text
from app.schemas.knowledge import RetrievedChunk


PAGE_MARKER_RE = re.compile(r"^第\s*(\d+)\s*页\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


class RAGPipeline:
    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
        clean_text = self._normalize_text(text)
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

    def build_image_chunk_id(self, image: ExtractedImage) -> str:
        return f"image:p{image.page_number}:i{image.image_index}"

    def image_description(self, image: ExtractedImage) -> str:
        return f"第 {image.page_number} 页第 {image.image_index + 1} 张图片"

    def build_chunks(self, source: str, text: str) -> list[RetrievedChunk]:
        chunks = []
        for index, chunk in enumerate(self.chunk_text(text), start=1):
            if is_readable_text(chunk):
                chunks.append(
                    RetrievedChunk(
                        chunk_id=str(uuid4()),
                        content=chunk,
                        score=0.0,
                        source=source,
                        source_uri=source,
                        section_path=self._extract_section_path(chunk),
                        page_number=self._extract_page_number(chunk),
                        token_count=self._estimate_tokens(chunk),
                        content_type="text",
                        image_url="",
                        metadata={
                            "chunk_index": index,
                            "chunking_method": "recursive-character",
                            "chunk_size": 800,
                            "overlap": 120,
                        },
                    )
                )
        return chunks

    def build_image_chunks(self, source: str, images: list[ExtractedImage]) -> list[RetrievedChunk]:
        chunks = []
        for img in images:
            description = self.image_description(img)
            chunks.append(
                RetrievedChunk(
                    chunk_id=self.build_image_chunk_id(img),
                    content=description,
                    score=0.0,
                    source=source,
                    source_uri=source,
                    section_path=f"第 {img.page_number} 页",
                    page_number=img.page_number,
                    token_count=self._estimate_tokens(description),
                    content_type="image",
                    image_url="",
                    metadata={
                        "image_index": img.image_index,
                        "content_type": img.content_type,
                        "chunking_method": "pdf-image-extraction",
                    },
                )
            )
        return chunks

    def _extract_page_number(self, text: str) -> int | None:
        for line in text.splitlines()[:3]:
            match = PAGE_MARKER_RE.match(line.strip())
            if match:
                return int(match.group(1))
        return None

    def _extract_section_path(self, text: str) -> str:
        headings = []
        for line in text.splitlines():
            match = HEADING_RE.match(line.strip())
            if match:
                headings.append(match.group(2).strip())
        return " > ".join(headings[:3])

    def _estimate_tokens(self, text: str) -> int:
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        other_terms = re.findall(r"[A-Za-z0-9_]+", text)
        return chinese_chars + len(other_terms)

    def _normalize_text(self, text: str) -> str:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        paragraphs = []
        current: list[str] = []
        for line in lines:
            if line:
                current.append(line)
            elif current:
                paragraphs.append("\n".join(current))
                current = []
        if current:
            paragraphs.append("\n".join(current))
        return "\n\n".join(paragraphs)


rag_pipeline = RAGPipeline()
