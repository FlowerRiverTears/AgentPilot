from fastapi import APIRouter

from app.llm.gateway import llm_gateway
from app.schemas.settings import ModelConfigRead, ModelConfigUpdate

router = APIRouter()


@router.get("/model", response_model=ModelConfigRead)
async def get_model_config() -> ModelConfigRead:
    return llm_gateway.get_config()


@router.put("/model", response_model=ModelConfigRead)
async def update_model_config(payload: ModelConfigUpdate) -> ModelConfigRead:
    return llm_gateway.update_config(payload)
