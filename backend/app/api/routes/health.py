from fastapi import APIRouter, Request

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "trace_id": request.state.trace_id,
    }
