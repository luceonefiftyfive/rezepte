from typing import Any

from app.repositories.base_repository import MongoRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

GroupDocument = dict[str, Any]


class GroupRepository(MongoRepository[GroupDocument]):
    collection_name = "groups"

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("id", unique=True)

    async def find_by_group_id(self, group_id: str) -> GroupDocument | None:
        return await self.find_one({"id": group_id})

    async def list_groups(
        self, group_ids: set[str] | None = None
    ) -> list[GroupDocument]:
        query: dict[str, Any] = {}
        if group_ids is not None:
            query["id"] = {"$in": sorted(group_ids)}
        return await self.list(query=query, sort=[("name", 1), ("id", 1)])

    async def update_by_group_id(
        self, group_id: str, values: dict[str, Any]
    ) -> GroupDocument | None:
        return await self.update_one({"id": group_id}, values)

    async def delete_by_group_id(self, group_id: str) -> bool:
        result = await self.collection.delete_one({"id": group_id})
        return result.deleted_count == 1
