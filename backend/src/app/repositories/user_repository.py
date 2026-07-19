from typing import Any, Optional

from app.repositories.base_repository import MongoRepository
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

UserDocument = dict[str, Any]


class UserRepository(MongoRepository[UserDocument]):
    collection_name = "users"

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        index_info = await self.collection.index_information()

        # Migrate legacy global unique indexes so soft-deleted users do not block reuse.
        for legacy_name in ("username_1", "email_1"):
            if legacy_name in index_info:
                await self.collection.drop_index(legacy_name)

        await self.collection.create_index(
            "username",
            unique=True,
            partialFilterExpression={"is_active": True},
            name="uniq_active_username",
        )
        await self.collection.create_index(
            "email",
            unique=True,
            partialFilterExpression={"is_active": True},
            name="uniq_active_email",
        )

    async def find_by_username(
        self, username: str, *, active_only: bool = False
    ) -> Optional[UserDocument]:
        query: dict[str, Any] = {"username": username}
        if active_only:
            query["is_active"] = True
        return await self.find_one(query)

    async def find_by_email(
        self, email: str, *, active_only: bool = False
    ) -> Optional[UserDocument]:
        query: dict[str, Any] = {"email": email}
        if active_only:
            query["is_active"] = True
        return await self.find_one(query)

    async def find_active_super_admin(self) -> Optional[UserDocument]:
        return await self.find_one({"is_super_admin": True, "is_active": True})

    async def count_active_super_admins(self) -> int:
        return await self.count({"is_super_admin": True, "is_active": True})

    async def list_users(
        self,
        group_id: Optional[str] = None,
        role: Optional[str] = None,
        email_verified: Optional[bool] = None,
    ) -> list[UserDocument]:
        query: dict[str, Any] = {"is_active": True}
        if group_id:
            query["groups.group_id"] = group_id
        if role:
            query["groups.role"] = role
        if email_verified is not None:
            query["email_verified"] = email_verified

        return await self.list(query)

    async def update_by_object_id(
        self, object_id: ObjectId, update: dict[str, Any]
    ) -> Optional[UserDocument]:
        return await self.update_by_id(object_id, update)

    async def email_exists_for_other_user(
        self, email: str, user_object_id: ObjectId
    ) -> bool:
        return await self.exists(
            {
                "email": email,
                "_id": {"$ne": user_object_id},
                "is_active": True,
            }
        )

    async def remove_group_references(self, group_id: str) -> int:
        result = await self.collection.update_many(
            {},
            {"$pull": {"groups": {"group_id": group_id}}},
        )
        return result.modified_count
