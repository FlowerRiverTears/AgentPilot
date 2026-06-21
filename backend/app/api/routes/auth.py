from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.config import settings
from app.core.audit import log_audit
from app.core.deps import get_current_admin, get_current_user
from app.core.rate_limit import login_limiter
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.core.token_blacklist import token_blacklist
from app.db.session import AsyncSessionLocal
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    UpdateUserRequest,
    UserInfo,
    UserListItem,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    if login_limiter.is_limited(client_ip):
        remaining = login_limiter.get_remaining_time(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录尝试过于频繁，请 {remaining} 秒后再试",
        )
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == payload.username))
        user = result.scalars().first()
        if not user or not user.is_active:
            login_limiter.record(client_ip)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        if not verify_password(payload.password, user.password_hash):
            login_limiter.record(client_ip)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        token = create_access_token({"sub": user.username, "role": user.role})
        return LoginResponse(access_token=token, username=user.username, role=user.role)


@router.post("/logout")
async def logout(current: UserInfo = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> dict:
    """将当前 token 加入黑名单，使其失效。"""
    payload = decode_access_token(credentials.credentials)
    if payload:
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            token_blacklist.add(jti, exp)
    return {"ok": True}


@router.get("/me", response_model=UserInfo)
async def me(current: UserInfo = Depends(get_current_user)) -> UserInfo:
    return current


# ========== 用户管理（仅管理员）==========

@router.get("/users", response_model=list[UserListItem])
async def list_users(_admin: UserInfo = Depends(get_current_admin)) -> list[UserListItem]:
    """获取所有用户列表（管理员）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return [
            UserListItem(
                id=str(u.id),
                username=u.username,
                role=u.role,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]


@router.post("/users", response_model=UserListItem)
async def create_user(payload: CreateUserRequest, request: Request, _admin: UserInfo = Depends(get_current_admin)) -> UserListItem:
    """创建新用户（管理员）。"""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.username == payload.username))
        if existing.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        await log_audit(
            username=_admin.username,
            user_id=_admin.id,
            action="create_user",
            resource=f"user/{user.id}",
            detail=f"创建用户 {payload.username}，角色 {payload.role}",
            ip_address=request.client.host if request.client else None,
        )
        return UserListItem(
            id=str(user.id),
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


@router.put("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    request: Request,
    _admin: UserInfo = Depends(get_current_admin),
) -> UserListItem:
    """更新用户信息（管理员）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        if payload.role is not None:
            user.role = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)
        await session.commit()
        await session.refresh(user)
        await log_audit(
            username=_admin.username,
            user_id=_admin.id,
            action="update_user",
            resource=f"user/{user_id}",
            detail=f"更新用户 {user.username}",
            ip_address=request.client.host if request.client else None,
        )
        return UserListItem(
            id=str(user.id),
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request, _admin: UserInfo = Depends(get_current_admin)) -> dict:
    """删除用户（管理员）。不允许删除自己。"""
    if user_id == _admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        await session.delete(user)
        await session.commit()
        await log_audit(
            username=_admin.username,
            user_id=_admin.id,
            action="delete_user",
            resource=f"user/{user_id}",
            detail=f"删除用户 {user.username}",
            ip_address=request.client.host if request.client else None,
        )
        return {"ok": True}


# ========== 密码修改 ==========

@router.put("/me/password")
async def change_password(
    payload: ChangePasswordRequest,
    current: UserInfo = Depends(get_current_user),
) -> dict:
    """修改当前用户密码。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == current.id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        if not verify_password(payload.old_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
        user.password_hash = hash_password(payload.new_password)
        await session.commit()
        return {"ok": True}


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
