from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core.deps import get_current_admin
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.schemas.auth import UserInfo

router = APIRouter()


@router.get("/audit-logs")
async def list_audit_logs(
    request: Request,
    _admin: UserInfo = Depends(get_current_admin),
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """获取审计日志列表（管理员）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource": log.resource,
                "detail": log.detail,
                "ip_address": log.ip_address,
            }
            for log in logs
        ]