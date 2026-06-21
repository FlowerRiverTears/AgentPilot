from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog


async def log_audit(
    username: str,
    action: str,
    resource: str,
    user_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    """记录审计日志。"""
    try:
        async with AsyncSessionLocal() as session:
            log_entry = AuditLog(
                username=username,
                user_id=user_id,
                action=action,
                resource=resource,
                detail=detail,
                ip_address=ip_address,
            )
            session.add(log_entry)
            await session.commit()
    except Exception:
        pass  # 审计日志写入失败不影响主流程