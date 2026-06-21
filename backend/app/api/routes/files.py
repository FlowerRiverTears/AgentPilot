from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.deps import get_optional_user
from app.rag.document_loader import DocumentParseError, extract_upload_text
from app.schemas.files import FileUploadResult

router = APIRouter()

# 支持的文件扩展名
TEXT_EXTENSIONS = {".txt", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=FileUploadResult)
async def upload_file(file: UploadFile = File(...), _user=Depends(get_optional_user)) -> FileUploadResult:
    """前台文件上传：解析文件内容，返回文本供对话上下文注入使用（无需鉴权）。"""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(raw) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

    filename = file.filename or "uploaded-file"
    suffix = Path(filename).suffix.lower()

    # 图片文件：不提取文本
    if suffix in IMAGE_EXTENSIONS:
        return FileUploadResult(
            file_id=uuid4().hex,
            filename=filename,
            content_type="image",
            text_content="",
            char_count=0,
        )

    # 文本类文件（PDF/TXT/MD）：使用 document_loader 解析
    if suffix in PDF_EXTENSIONS or suffix in TEXT_EXTENSIONS:
        try:
            text_content = extract_upload_text(filename, file.content_type, raw)
        except DocumentParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # 截断到 8000 字符避免上下文过长
        truncated = text_content[:settings.max_text_length]
        content_type = "pdf" if suffix in PDF_EXTENSIONS else "text"
        return FileUploadResult(
            file_id=uuid4().hex,
            filename=filename,
            content_type=content_type,
            text_content=truncated,
            char_count=len(truncated),
        )

    raise HTTPException(status_code=400, detail=f"不支持的文件类型：{suffix}")
