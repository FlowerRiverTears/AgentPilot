from pydantic import BaseModel


class FileUploadResult(BaseModel):
    file_id: str
    filename: str
    content_type: str  # text/image/pdf
    text_content: str  # 提取的文本内容（图片为空）
    char_count: int
    message: str = "文件解析成功"
