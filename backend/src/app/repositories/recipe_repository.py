from typing import Any

from app.repositories.base_repository import MongoRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

RecipeDocument = dict[str, Any]


class RecipeRepository(MongoRepository[RecipeDocument]):
    collection_name = "recipes"

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)

    async def find_by_public_id(self, recipe_id: str) -> RecipeDocument | None:
        return await self.find_one({"id": recipe_id})

    async def list_by_group(
        self,
        group_id: str | None = None,
        group_ids: list[str] | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[RecipeDocument]:
        query: dict[str, Any] = {}
        if group_ids:
            query["group_ids"] = {"$in": group_ids}
        elif group_id:
            query["group_ids"] = group_id
        return await self.list(query=query, sort=sort)

    async def update_with_version(
        self, recipe_id: str, version: int, values: dict[str, Any]
    ) -> RecipeDocument | None:
        return await self.collection.find_one_and_update(
            {"id": recipe_id, "version": version},
            {"$set": values, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def delete_by_public_id(self, recipe_id: str) -> bool:
        result = await self.collection.delete_one({"id": recipe_id})
        return result.deleted_count == 1

    async def purge_all(self) -> int:
        result = await self.collection.delete_many({})
        return result.deleted_count

    async def purge_by_group(self, group_id: str) -> int:
        result = await self.collection.delete_many({"group_ids": group_id})
        return result.deleted_count

    async def remove_group_references(self, group_id: str) -> tuple[int, int]:
        updated = await self.collection.update_many(
            {"group_ids": group_id},
            {"$pull": {"group_ids": group_id}},
        )
        deleted = await self.collection.delete_many({"group_ids": {"$size": 0}})
        return updated.modified_count, deleted.deleted_count

    async def upsert_by_public_id(
        self, recipe_id: str, values: dict[str, Any]
    ) -> tuple[RecipeDocument, bool]:
        existing = await self.find_by_public_id(recipe_id)
        if existing is None:
            created = await self.insert(values)
            return created, True

        await self.collection.replace_one({"id": recipe_id}, values)
        updated = await self.find_by_public_id(recipe_id)
        if updated is None:
            raise RuntimeError("Recipe disappeared during upsert")
        return updated, False
