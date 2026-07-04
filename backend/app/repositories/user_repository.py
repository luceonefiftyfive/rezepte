from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("username", unique=True)
        await self.collection.create_index("email", unique=True)

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        if not ObjectId.is_valid(user_id):
            return None
        return await self.collection.find_one({"_id": ObjectId(user_id)})

    async def find_by_username(self, username: str) -> Optional[dict]:
        return await self.collection.find_one({"username": username})

    async def find_by_email(self, email: str) -> Optional[dict]:
        return await self.collection.find_one({"email": email})

    async def find_active_super_admin(self) -> Optional[dict]:
        return await self.collection.find_one({"is_super_admin": True, "is_active": True})

    async def count_active_super_admins(self) -> int:
        return await self.collection.count_documents({"is_super_admin": True, "is_active": True})

    async def insert(self, document: dict) -> dict:
        result = await self.collection.insert_one(document)
        return await self.collection.find_one({"_id": result.inserted_id})

    async def list_users(
        self,
        group_id: Optional[str] = None,
        role: Optional[str] = None,
        email_verified: Optional[bool] = None,
    ) -> list[dict]:
        query: dict = {"is_active": True}
        if group_id:
            query["groups.group_id"] = group_id
        if role:
            query["groups.role"] = role
        if email_verified is not None:
            query["email_verified"] = email_verified

        cursor = self.collection.find(query)
        return await cursor.to_list(length=None)

    async def update_by_id(self, user_id: str, update: dict) -> Optional[dict]:
        if not ObjectId.is_valid(user_id):
            return None
        object_id = ObjectId(user_id)
        await self.collection.update_one({"_id": object_id}, {"$set": update})
        return await self.collection.find_one({"_id": object_id})

    async def update_by_object_id(self, object_id: ObjectId, update: dict) -> Optional[dict]:
        await self.collection.update_one({"_id": object_id}, {"$set": update})
        return await self.collection.find_one({"_id": object_id})

    async def email_exists_for_other_user(self, email: str, user_object_id: ObjectId) -> bool:
        existing = await self.collection.find_one({"email": email, "_id": {"$ne": user_object_id}})
        return existing is not None
