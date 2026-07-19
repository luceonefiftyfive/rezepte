import typing as ty

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.settings import settings
from app.models.user import (
    GroupsUpdate,
    LoginRequest,
    OwnProfileUpdate,
    Role,
    SuperAdminUpdate,
    TokenResponse,
    UserCreate,
    UserPublic,
    user_to_public,
)
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_service(
    db: ty.Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> UserService:
    return UserService(db)


async def get_current_user(
    token: ty.Annotated[str, Depends(oauth2_scheme)],
    service: ty.Annotated[UserService, Depends(get_user_service)],
) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = await service.get_user_or_404(user_id)
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is inactive")
    return user


def require_super_admin(
    current_user: ty.Annotated[dict, Depends(get_current_user)],
) -> dict:
    if not current_user.get("is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super-admin required")
    return current_user


def require_admin_or_super_admin(
    current_user: ty.Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user.get("is_super_admin", False):
        return current_user
    if any(
        group["role"] == Role.admin.value for group in current_user.get("groups", [])
    ):
        return current_user
    raise HTTPException(status_code=403, detail="Admin required")


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    service: ty.Annotated[UserService, Depends(get_user_service)],
):
    user = await service.authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])), user=user_to_public(user)
    )


@router.get("/auth/me", response_model=UserPublic)
async def identify_current_user(
    current_user: ty.Annotated[dict, Depends(get_current_user)],
):
    return user_to_public(current_user)


@router.post("/users", response_model=UserPublic, status_code=201)
async def create_user(
    data: UserCreate,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
):
    created = await service.create_user(data, current_user)
    return user_to_public(created)


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    db: ty.Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
    group_id: ty.Optional[str] = Query(default=None),
    role: ty.Optional[Role] = Query(default=None),
    email_verified: ty.Optional[bool] = Query(default=None),
):
    repository = UserRepository(db)
    users = await repository.list_users(
        group_id=group_id,
        role=role.value if role else None,
        email_verified=email_verified,
    )
    return [user_to_public(user) for user in users]


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
):
    return user_to_public(await service.get_user_or_404(user_id))


@router.patch("/users/me", response_model=UserPublic)
async def update_own_profile(
    data: OwnProfileUpdate,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(get_current_user)],
):
    updated = await service.update_own_profile(
        current_user, data.first_name, data.last_name, data.email
    )
    return user_to_public(updated)


@router.patch("/users/{user_id}/groups", response_model=UserPublic)
async def update_user_groups(
    user_id: str,
    data: GroupsUpdate,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
):
    updated = await service.update_user_groups(user_id, data.groups, current_user)
    return user_to_public(updated)


@router.patch("/users/{user_id}/super-admin", response_model=UserPublic)
async def update_super_admin_status(
    user_id: str,
    data: SuperAdminUpdate,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(require_super_admin)],
):
    updated = await service.update_super_admin_status(
        user_id, data.is_super_admin, current_user
    )
    return user_to_public(updated)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    service: ty.Annotated[UserService, Depends(get_user_service)],
    current_user: ty.Annotated[dict, Depends(require_super_admin)],
):
    await service.soft_delete_user(user_id, current_user)
    return {"deleted": True}


@router.get("/users/check-username/{username}")
async def check_username(
    username: str, db: ty.Annotated[AsyncIOMotorDatabase, Depends(get_db)]
):
    repository = UserRepository(db)
    return {
        "username": username,
        "available": await repository.find_by_username(username, active_only=True)
        is None,
    }


@router.get("/users/check-email/{email}")
async def check_email(
    email: str, db: ty.Annotated[AsyncIOMotorDatabase, Depends(get_db)]
):
    repository = UserRepository(db)
    return {
        "email": email,
        "available": await repository.find_by_email(email, active_only=True) is None,
    }
