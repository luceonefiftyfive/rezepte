import logging

from app.core.security import hash_password, now_utc, verify_password
from app.core.settings import settings
from app.models.user import GroupRole, Role, UserCreate
from app.repositories.user_repository import UserRepository
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repository = UserRepository(db)

    async def bootstrap_superuser(self) -> None:
        await self.repository.ensure_indexes()
        existing = await self.repository.find_active_super_admin()
        if existing:
            log.info("Superuser already exists, skipping bootstrap")
            return

        user = UserCreate(
            username=settings.superuser_username,
            password=settings.superuser_password,
            first_name="System",
            last_name="Administrator",
            email=settings.superuser_email,
            groups=[],
            is_super_admin=True,
        )
        doc = self.create_user_document(user)
        doc["email_verified"] = True
        await self.repository.insert(doc)
        log.info(
            "Bootstrapped superuser with username '%s'", settings.superuser_username
        )

    def create_user_document(self, data: UserCreate) -> dict:
        timestamp = now_utc()
        return {
            "username": data.username,
            "password_hash": hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": str(data.email),
            "email_verified": False,
            "groups": [group.model_dump() for group in data.groups],
            "is_super_admin": data.is_super_admin,
            "is_active": True,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    async def get_user_or_404(self, user_id: str) -> dict:
        user = await self.repository.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def authenticate_user(self, username: str, password: str) -> dict | None:
        log.info("Authenticating user '%s'", username)
        user = await self.repository.find_by_username(username, active_only=True)
        if not user:
            log.info(
                "Authentication failed for user '%s': user not found or inactive",
                username,
            )
            return None
        if not verify_password(password, user["password_hash"]):
            log.info("Authentication failed for user '%s': invalid password", username)
            return None
        log.info("User '%s' authenticated successfully", username)
        return user

    async def ensure_username_and_email_unique(self, username: str, email: str) -> None:
        if await self.repository.find_by_username(username, active_only=True):
            raise HTTPException(status_code=409, detail="Username already exists")
        if await self.repository.find_by_email(email, active_only=True):
            raise HTTPException(status_code=409, detail="Email already exists")

    def assert_may_manage_groups(
        self, current_user: dict, new_groups: list[GroupRole]
    ) -> None:
        if current_user.get("is_super_admin", False):
            return

        admin_group_ids = {
            group["group_id"]
            for group in current_user.get("groups", [])
            if group["role"] == Role.admin.value
        }
        requested_group_ids = {group.group_id for group in new_groups}

        if not requested_group_ids.issubset(admin_group_ids):
            raise HTTPException(
                status_code=403,
                detail="You may only manage groups where you are admin",
            )

    async def create_user(self, data: UserCreate, current_user: dict) -> dict:
        if data.is_super_admin and not current_user.get("is_super_admin", False):
            raise HTTPException(
                status_code=403, detail="Only super-admin may create super-admin users"
            )

        self.assert_may_manage_groups(current_user, data.groups)
        await self.ensure_username_and_email_unique(data.username, str(data.email))
        return await self.repository.insert(self.create_user_document(data))

    async def update_own_profile(
        self, current_user: dict, first_name=None, last_name=None, email=None
    ) -> dict:
        update: dict = {}
        if first_name is not None:
            update["first_name"] = first_name
        if last_name is not None:
            update["last_name"] = last_name
        if email is not None:
            new_email = str(email)
            if await self.repository.email_exists_for_other_user(
                new_email, current_user["_id"]
            ):
                raise HTTPException(status_code=409, detail="Email already exists")
            update["email"] = new_email
            update["email_verified"] = False

        if not update:
            return current_user

        update["updated_at"] = now_utc()
        return await self.repository.update_by_object_id(current_user["_id"], update)

    async def update_user_groups(
        self, user_id: str, groups: list[GroupRole], current_user: dict
    ) -> dict:
        self.assert_may_manage_groups(current_user, groups)
        target = await self.get_user_or_404(user_id)
        return await self.repository.update_by_object_id(
            target["_id"],
            {
                "groups": [group.model_dump() for group in groups],
                "updated_at": now_utc(),
            },
        )

    async def update_super_admin_status(
        self, user_id: str, is_super_admin: bool, current_user: dict
    ) -> dict:
        target = await self.get_user_or_404(user_id)
        if target["_id"] == current_user["_id"] and not is_super_admin:
            if await self.repository.count_active_super_admins() <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="At least one active super-admin must remain",
                )
        return await self.repository.update_by_object_id(
            target["_id"],
            {"is_super_admin": is_super_admin, "updated_at": now_utc()},
        )

    async def soft_delete_user(self, user_id: str, current_user: dict) -> None:
        target = await self.get_user_or_404(user_id)
        if target["_id"] == current_user["_id"]:
            if await self.repository.count_active_super_admins() <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="At least one active super-admin must remain",
                )

        target_id = str(target["_id"])
        await self.repository.update_by_object_id(
            target["_id"],
            {
                "is_active": False,
                "deleted_username": target.get("username"),
                "deleted_email": target.get("email"),
                "username": f"deleted-{target_id}-username",
                "email": f"deleted-{target_id}@deleted.local",
                "updated_at": now_utc(),
            },
        )
