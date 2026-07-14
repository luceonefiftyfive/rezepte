from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.repositories.base_repository import MongoRepository

RecipeDocument = dict[str, Any]


class RecipeRepository(MongoRepository[RecipeDocument]):
    collection_name = "recipes"

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)

    async def find_by_public_id(self, recipe_id: str) -> RecipeDocument | None:
        return await self.find_one({"id": recipe_id})

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
