from pydantic import BaseModel, Field


class ModelConfigRead(BaseModel):
    base_url: str
    api_key_set: bool
    default_model: str


class ModelConfigUpdate(BaseModel):
    base_url: str = Field(min_length=1)
    api_key: str = ""
    default_model: str = Field(min_length=1)
