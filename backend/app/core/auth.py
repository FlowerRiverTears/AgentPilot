from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """后台管理接口需要的鉴权依赖。auth_enabled=False 时跳过鉴权。"""
    if not settings.auth_enabled:
        return {"sub": "anonymous", "role": "admin"}
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return payload
