"""Health check endpoints with dependency verification."""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check."""
    return {"app": settings.app_name, "version": settings.app_version, "status": "ok"}


@router.get("/health/stats")
async def health_stats():
    """Detailed health stats with dependency checks."""
    from app.db.session import AsyncSessionLocal
    from app.core.config import settings as s

    checks = {}

    # Check database connectivity
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Check MinIO connectivity
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"http://{s.minio_endpoint}/minio/health/live")
            checks["minio"] = "ok" if resp.status_code == 200 else f"error: HTTP {resp.status_code}"
    except Exception as e:
        checks["minio"] = f"error: {str(e)[:100]}"

    # Check embedding service
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{s.embedding_base_url}/health")
            checks["embedding"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        checks["embedding"] = "unreachable"

    # Gather stats
    stats = {
        "app": s.app_name,
        "version": s.app_version,
        "environment": s.environment,
        "auth_enabled": s.auth_enabled,
        "ocr_enabled": s.ocr_enabled,
        "status": "ok" if all(v == "ok" for v in checks.values()) else "degraded",
        "checks": checks,
    }

    # Try to get counts
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            for table, label in [
                ("agents", "agents_total"),
                ("agents", "agents_published"),
                ("agent_runs", "runs_total"),
                ("knowledge_bases", "knowledge_bases"),
                ("documents", "documents"),
                ("tools", "tools"),
                ("tool_calls", "tool_calls"),
                ("conversations", "conversations"),
                ("feedbacks", "feedback_likes"),
                ("feedbacks", "feedback_dislikes"),
            ]:
                if label == "agents_published":
                    result = await session.execute(text("SELECT COUNT(*) FROM agents WHERE status='published'"))
                elif label == "feedback_likes":
                    result = await session.execute(text("SELECT COUNT(*) FROM feedbacks WHERE rating='like'"))
                elif label == "feedback_dislikes":
                    result = await session.execute(text("SELECT COUNT(*) FROM feedbacks WHERE rating='dislike'"))
                else:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[label] = result.scalar()
    except Exception:
        pass

    return stats
