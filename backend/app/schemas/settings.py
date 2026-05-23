from pydantic import BaseModel, Field


class ModelConfigRead(BaseModel):
    id: str = "default"
    name: str = "default"
    base_url: str
    api_key_set: bool
    default_model: str
    is_default: bool = True


class ModelConfigUpdate(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=80)
    base_url: str = Field(min_length=1)
    api_key: str = ""
    default_model: str = Field(min_length=1)
    is_default: bool = True


class ModelConfigCreate(ModelConfigUpdate):
    pass


class ModelConfigTestResult(BaseModel):
    ok: bool
    message: str
