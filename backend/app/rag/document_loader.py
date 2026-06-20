from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.services.ocr import get_ocr_language, is_scanned_pdf, ocr_pdf

logger = logging.getLogger(__name__)


class DocumentParseError(ValueError):
    pass


@dataclass
class ExtractedImage:
    page_number: int
    image_index: int
    image_bytes: bytes
    content_type: str = "image/png"


@dataclass
class ParsedDocument:
    text: str
    images: list[ExtractedImage]
    ocr_used: bool = False


def extract_upload_text(filename: str, content_type: str | None, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf" or raw.startswith(b"%PDF"):
        return _extract_pdf_text(raw)
    return _extract_plain_text(raw)


def extract_upload(filename: str, content_type: str | None, raw: bytes) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf" or raw.startswith(b"%PDF"):
        return _extract_pdf(raw)
    return ParsedDocument(text=_extract_plain_text(raw), images=[])


def _extract_pdf(raw: bytes) -> ParsedDocument:
    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as exc:
        raise DocumentParseError("PDF 文件无法解析") from exc

    pages: list[str] = []
    all_images: list[ExtractedImage] = []

    for page_index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        cleaned = _clean_text(page_text)
        if cleaned:
            pages.append(f"第 {page_index} 页\n{cleaned}")

        try:
            all_images.extend(_extract_page_images(page, page_index))
        except Exception:
            pass

    text = "\n\n".join(pages)
    page_count = len(reader.pages)

    ocr_used = False
    if is_scanned_pdf(text, page_count):
        logger.info("检测到扫描件 PDF（每页平均文字少于阈值），启用 OCR 提取")
        ocr_text = ocr_pdf(raw, language=get_ocr_language())
        if ocr_text:
            text = f"{text}\n\n{ocr_text}" if text.strip() else ocr_text
            ocr_used = True
            logger.info("OCR 提取完成，已合并文字")
        else:
            logger.warning("OCR 未提取到文字")

    if not text.strip() and not all_images:
        raise DocumentParseError("PDF 文件没有可提取的文本或图片，可能是扫描件或图片型 PDF")
    return ParsedDocument(text=text, images=all_images, ocr_used=ocr_used)


def _extract_page_images(page, page_number: int) -> list[ExtractedImage]:
    images: list[ExtractedImage] = []
    if not hasattr(page, "images"):
        return images

    for img_index, img in enumerate(page.images):
        try:
            image_bytes = img.data
            if len(image_bytes) < 1024:
                continue
            content_type = "image/png"
            if hasattr(img, "name") and img.name:
                ext = Path(img.name).suffix.lower()
                if ext in (".jpg", ".jpeg"):
                    content_type = "image/jpeg"
            images.append(
                ExtractedImage(
                    page_number=page_number,
                    image_index=img_index,
                    image_bytes=image_bytes,
                    content_type=content_type,
                )
            )
        except Exception:
            continue
    return images


def _extract_pdf_text(raw: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as exc:
        raise DocumentParseError("PDF 文件无法解析") from exc

    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        cleaned = _clean_text(page_text)
        if cleaned:
            pages.append(f"第 {index} 页\n{cleaned}")

    text = "\n\n".join(pages)
    page_count = len(reader.pages)

    if is_scanned_pdf(text, page_count):
        logger.info("检测到扫描件 PDF（每页平均文字少于阈值），启用 OCR 提取")
        ocr_text = ocr_pdf(raw, language=get_ocr_language())
        if ocr_text:
            text = f"{text}\n\n{ocr_text}" if text.strip() else ocr_text
            logger.info("OCR 提取完成，已合并文字")
        else:
            logger.warning("OCR 未提取到文字")

    if not text.strip():
        raise DocumentParseError("PDF 文件没有可提取的文本，可能是扫描件或图片型 PDF")
    return text


def _extract_plain_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return _clean_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _clean_text(raw.decode("utf-8", errors="ignore"))


def _clean_text(text: str) -> str:
    cleaned = "".join(
        char
        for char in text
        if char in "\n\r\t" or (ord(char) >= 32 and char != "\x00")
    )
    lines = [line.strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line)
