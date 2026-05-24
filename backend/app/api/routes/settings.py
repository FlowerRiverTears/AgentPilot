from fastapi import APIRouter, HTTPException

from app.llm.gateway import llm_gateway
from app.schemas.settings import (
    ModelConfigCreate,
    ModelConfigRead,
    ModelConfigTestResult,
    ModelConfigUpdate,
)

router = APIRouter()


@router.get("/model", response_model=ModelConfigRead)
async def get_model_config() -> ModelConfigRead:
    return await llm_gateway.get_config()


@router.put("/model", response_model=ModelConfigRead)
async def update_model_config(payload: ModelConfigUpdate) -> ModelConfigRead:
    configs = await llm_gateway.list_configs()
    default_config = next((config for config in configs if config.is_default), None)
    if not default_config:
        create_data = {
            "name": payload.name or "default",
            "base_url": payload.base_url or "",
            "api_key": payload.api_key or "",
            "default_model": payload.default_model or "",
            "is_default": True,
        }
        return await llm_gateway.create_config(ModelConfigCreate(**create_data))
    return await llm_gateway.update_config(default_config.id, payload)


@router.get("/models", response_model=list[ModelConfigRead])
async def list_model_configs() -> list[ModelConfigRead]:
    await llm_gateway.ensure_defaults()
    return await llm_gateway.list_configs()


@router.post("/models", response_model=ModelConfigRead, status_code=201)
async def create_model_config(payload: ModelConfigCreate) -> ModelConfigRead:
    return await llm_gateway.create_config(payload)


@router.put("/models/{config_id}", response_model=ModelConfigRead)
async def update_named_model_config(config_id: str, payload: ModelConfigUpdate) -> ModelConfigRead:
    try:
        return await llm_gateway.update_config(config_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Model config not found") from None


@router.post("/models/{config_id}/default", response_model=ModelConfigRead)
async def set_default_model_config(config_id: str) -> ModelConfigRead:
    try:
        return await llm_gateway.set_default(config_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Model config not found") from None


@router.post("/models/{config_id}/test", response_model=ModelConfigTestResult)
async def test_model_config(config_id: str) -> ModelConfigTestResult:
    try:
        return await llm_gateway.test_config(config_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Model config not found") from None


@router.delete("/models/{config_id}", status_code=204)
async def delete_model_config(config_id: str) -> None:
    deleted = await llm_gateway.delete_config(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model config not found")
