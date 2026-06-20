from fastapi import APIRouter, Request

from app.core.config import settings
from app.repositories.memory import store

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "trace_id": request.state.trace_id,
    }


@router.get("/health/stats")
async def stats() -> dict:
    """总览统计数据，供前端总览页展示。"""
    counts = await store.get_stats()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "auth_enabled": settings.auth_enabled,
        "ocr_enabled": settings.ocr_enabled,
        "status": "ok",
        **counts,
    }
