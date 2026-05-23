from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AgentPilot"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    environment: str = "local"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+asyncpg://agentpilot:agentpilot@localhost:5432/agentpilot"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_default_model: str = "qwen2.5:7b"
    llm_request_timeout_seconds: int = 120
    embedding_model: str = "bge-m3"


settings = Settings()
