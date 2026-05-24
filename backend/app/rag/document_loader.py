from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


class DocumentParseError(ValueError):
    pass


def extract_upload_text(filename: str, content_type: str | None, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf" or raw.startswith(b"%PDF"):
        return _extract_pdf_text(raw)
    return _extract_plain_text(raw)


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
