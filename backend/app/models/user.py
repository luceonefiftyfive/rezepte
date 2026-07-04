from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    admin = "admin"
    author = "author"
    reader = "reader"


class GroupRole(BaseModel):
    group_id: str = Field(min_length=1)
    role: Role


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    groups: list[GroupRole] = []
    is_super_admin: bool = False


class UserPublic(BaseModel):
    id: str
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    email_verified: bool
    groups: list[GroupRole]
    is_super_admin: bool
    is_active: bool


class OwnProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1)
    last_name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[EmailStr] = None


class GroupsUpdate(BaseModel):
    groups: list[GroupRole]


class SuperAdminUpdate(BaseModel):
    is_super_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


def user_to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        username=user["username"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        email_verified=user.get("email_verified", False),
        groups=user.get("groups", []),
        is_super_admin=user.get("is_super_admin", False),
        is_active=user.get("is_active", True),
    )
