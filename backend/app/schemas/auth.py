from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str = "admin"


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UpdateUserRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|user)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class UserListItem(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime | None = None
