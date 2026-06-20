"""OCR 服务：支持扫描件 PDF 文字提取。"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 扫描件判定阈值：每页平均文字少于该值则视为扫描件
SCANNED_PDF_AVG_CHARS_THRESHOLD = 50


def is_scanned_pdf(text: str, page_count: int) -> bool:
    """判断是否为扫描件 PDF：每页平均文字少于阈值。

    Args:
        text: pypdf 已提取的文字内容
        page_count: PDF 总页数

    Returns:
        True 表示判定为扫描件 PDF，需要启用 OCR
    """
    if page_count <= 0:
        return False
    avg_chars = len(text.strip()) / page_count
    return avg_chars < SCANNED_PDF_AVG_CHARS_THRESHOLD


def get_ocr_language() -> str:
    """读取 OCR 语言配置，未配置时返回默认值。"""
    try:
        from app.core.config import settings

        return getattr(settings, "ocr_language", "chi_sim+eng")
    except Exception:
        return "chi_sim+eng"


def ocr_pdf(file_bytes: bytes, language: str = "chi_sim+eng") -> str:
    """对 PDF 执行 OCR，返回提取的文字。

    Args:
        file_bytes: PDF 文件的二进制内容
        language: Tesseract 语言代码，默认中文简体+英文

    Returns:
        提取的文字内容；OCR 依赖缺失或处理失败时返回空字符串
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except ImportError:
        logger.warning("OCR 依赖未安装（pytesseract/pdf2image），跳过 OCR")
        return ""

    try:
        images = convert_from_bytes(file_bytes, dpi=200)
        texts: list[str] = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang=language)
            if text.strip():
                texts.append(f"--- 第 {i + 1} 页（OCR）---\n{text.strip()}")
        return "\n\n".join(texts)
    except Exception as exc:
        logger.error("OCR 处理失败: %s", exc)
        return ""
