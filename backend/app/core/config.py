import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AgentPilot"
    app_version: str = "3.0.0"
    api_prefix: str = "/api"
    environment: str = "local"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+asyncpg://agentpilot:agentpilot@localhost:5432/agentpilot"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:19000"

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_default_model: str = "qwen2.5:7b"
    llm_request_timeout_seconds: int = 120

    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = 1024

    multimodal_embedding_base_url: str = ""
    multimodal_embedding_api_key: str = ""
    multimodal_embedding_model: str = ""
    multimodal_embedding_dimensions: int = 768

    minio_access_key: str = "agentpilot"
    minio_secret_key: str = "agentpilot123"
    minio_bucket: str = "agentpilot-images"
    minio_secure: bool = False

    retrieval_min_score: float = 0.3
    retrieval_min_lexical_score: float = 0.3

    # 鉴权配置
    jwt_secret_key: str = "agentpilot-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24小时
    auth_enabled: bool = True  # 是否启用鉴权，方便开发时关闭
    admin_username: str = "admin"
    admin_password: str = "admin123"  # 初始管理员密码

    # 安全配置
    encryption_key: str = "agentpilot-encryption-key-change-in-production"  # For API key encryption
    rate_limit_enabled: bool = True
    login_rate_limit: str = "5/minute"  # Rate limit string for login

    # 上下文压缩配置
    context_token_threshold: int = 6000  # Token 估算超过此值时触发压缩
    recent_turns: int = 6  # 压缩时保留最近几轮对话原文

    # OCR 配置
    ocr_enabled: bool = True  # 是否启用扫描件 PDF 的 OCR
    ocr_language: str = "chi_sim+eng"  # Tesseract 语言代码
    ocr_dpi: int = 200  # PDF 转图片的 DPI

    # 向量数据库配置
    vector_db_backend: str = "pgvector"  # pgvector / qdrant
    qdrant_url: str = "http://localhost:6333"  # Qdrant 服务地址

    # RAG Pipeline
    chunk_size: int = 800
    chunk_overlap: int = 120

    # File upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_text_length: int = 8000

    # OCR
    ocr_scanned_threshold: int = 50  # Average chars per page threshold

    # Embedding
    embedding_timeout: int = 60
    embedding_batch_timeout: int = 120

    def validate_security(self) -> None:
        """Validate security-critical settings at startup."""
        if self.jwt_secret_key == "agentpilot-dev-secret-change-in-production":
            if self.environment == "production":
                raise RuntimeError(
                    "JWT secret key must be changed in production! Set JWT_SECRET_KEY environment variable."
                )
            logger.warning(
                "JWT secret key is using the default value. "
                "Set JWT_SECRET_KEY environment variable for production."
            )
        if self.admin_password == "admin123":
            logger.warning(
                "Default admin password is in use. Please change ADMIN_PASSWORD for production."
            )


settings = Settings()
