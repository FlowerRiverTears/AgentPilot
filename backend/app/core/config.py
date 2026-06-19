from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AgentPilot"
    app_version: str = "0.2.0"
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


settings = Settings()
