from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import AsyncSessionLocal
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == payload.username))
        user = result.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        token = create_access_token({"sub": user.username, "role": user.role})
        return LoginResponse(access_token=token, username=user.username, role=user.role)


@router.post("/logout")
async def logout() -> dict:
    """前端清除本地 token 即可，后端无状态。"""
    return {"ok": True}


@router.get("/me", response_model=UserInfo)
async def me(current: UserInfo = Depends(get_current_user)) -> UserInfo:
    return current


async def seed_admin_user() -> None:
    """初始化默认管理员账号。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == settings.admin_username))
        if result.scalars().first():
            return
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
