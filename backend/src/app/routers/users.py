import typing as ty

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
from jose import JWTError, jwt
from litestar import Request, Router, delete, get, patch, post
from litestar.di import NamedDependency
from litestar.exceptions import HTTPException
from litestar.params import FromPath, FromQuery
from motor.motor_asyncio import AsyncIOMotorDatabase

Db = ty.Annotated[AsyncIOMotorDatabase, NamedDependency[AsyncIOMotorDatabase]]
CurrentUser = ty.Annotated[dict, NamedDependency[dict]]


async def get_current_user(request: Request, db: Db) -> dict:
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise credentials_error
    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_error
    except JWTError:
        raise credentials_error

    service = UserService(db)
    user = await service.get_user_or_404(user_id)
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is inactive")
    return user


def require_super_admin(current_user: CurrentUser) -> dict:
    if not current_user.get("is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super-admin required")
    return current_user


def require_admin_or_super_admin(current_user: CurrentUser) -> dict:
    if current_user.get("is_super_admin", False):
        return current_user
    if any(
        group["role"] == Role.admin.value for group in current_user.get("groups", [])
    ):
        return current_user
    raise HTTPException(status_code=403, detail="Admin required")


@post("/auth/login", status_code=200)
async def login(data: LoginRequest, db: Db) -> TokenResponse:
    service = UserService(db)
    user = await service.authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])), user=user_to_public(user)
    )


@get("/auth/me")
async def identify_current_user(current_user: CurrentUser) -> UserPublic:
    return user_to_public(current_user)


@post("/users", status_code=201)
async def create_user(
    data: UserCreate,
    db: Db,
    admin_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    created = await service.create_user(data, admin_user)
    return user_to_public(created)


@get("/users")
async def list_users(
    db: Db,
    admin_user: CurrentUser,
    group_id: FromQuery[str | None] = None,
    role: FromQuery[Role | None] = None,
    email_verified: FromQuery[bool | None] = None,
) -> list[UserPublic]:
    repository = UserRepository(db)
    users = await repository.list_users(
        group_id=group_id,
        role=role.value if role else None,
        email_verified=email_verified,
    )
    return [user_to_public(user) for user in users]


@get("/users/{user_id:str}")
async def get_user(
    user_id: FromPath[str], db: Db, admin_user: CurrentUser
) -> UserPublic:
    service = UserService(db)
    return user_to_public(await service.get_user_or_404(user_id))


@patch("/users/me")
async def update_own_profile(
    data: OwnProfileUpdate,
    db: Db,
    current_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    updated = await service.update_own_profile(
        current_user, data.first_name, data.last_name, data.email
    )
    return user_to_public(updated)


@patch("/users/{user_id:str}/groups")
async def update_user_groups(
    user_id: FromPath[str],
    data: GroupsUpdate,
    db: Db,
    admin_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    updated = await service.update_user_groups(user_id, data.groups, admin_user)
    return user_to_public(updated)


@patch("/users/{user_id:str}/super-admin")
async def update_super_admin_status(
    user_id: FromPath[str],
    data: SuperAdminUpdate,
    db: Db,
    super_admin_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    updated = await service.update_super_admin_status(
        user_id, data.is_super_admin, super_admin_user
    )
    return user_to_public(updated)


@delete("/users/{user_id:str}", status_code=200)
async def delete_user(
    user_id: FromPath[str], db: Db, super_admin_user: CurrentUser
) -> dict:
    service = UserService(db)
    await service.soft_delete_user(user_id, super_admin_user)
    return {"deleted": True}


@get("/users/check-username/{username:str}")
async def check_username(username: FromPath[str], db: Db) -> dict:
    repository = UserRepository(db)
    return {
        "username": username,
        "available": await repository.find_by_username(username, active_only=True)
        is None,
    }


@get("/users/check-email/{email:str}")
async def check_email(email: FromPath[str], db: Db) -> dict:
    repository = UserRepository(db)
    return {
        "email": email,
        "available": await repository.find_by_email(email, active_only=True) is None,
    }


router = Router(
    path="",
    route_handlers=[
        login,
        identify_current_user,
        create_user,
        list_users,
        get_user,
        update_own_profile,
        update_user_groups,
        update_super_admin_status,
        delete_user,
        check_username,
        check_email,
    ],
)
