from typing import Any, Literal

from pydantic import BaseModel, Field


class HttpToolConfig(BaseModel):
    url: str = Field(min_length=1)
    method: Literal["GET", "POST"] = "GET"
    trigger_keywords: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=20, ge=1, le=120)


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: Literal["http"] = "http"
    description: str = ""
    config: HttpToolConfig
    enabled: bool = True


class ToolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    type: Literal["http"] | None = None
    description: str | None = None
    config: HttpToolConfig | None = None
    enabled: bool | None = None


class ToolRead(BaseModel):
    id: str
    name: str
    type: str
    description: str
    config: dict
    enabled: bool


class ToolTestRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ToolTestResult(BaseModel):
    ok: bool
    status_code: int | None = None
    elapsed_ms: int = 0
    output: Any = None
    error: str = ""
