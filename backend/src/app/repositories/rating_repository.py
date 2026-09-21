from datetime import datetime
from typing import Any

from app.repositories.base_repository import MongoRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

RatingDocument = dict[str, Any]


class RatingRepository(MongoRepository[RatingDocument]):
    collection_name = "recipe_ratings"

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("recipe_id", 1), ("user_id", 1)], unique=True
        )

    async def upsert_rating(
        self,
        recipe_id: str,
        user_id: str,
        username: str,
        score: int,
        comment: str,
        now: datetime,
    ) -> RatingDocument:
        return await self.collection.find_one_and_update(
            {"recipe_id": recipe_id, "user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "score": score,
                    "comment": comment,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "recipe_id": recipe_id,
                    "user_id": user_id,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def list_for_recipe(self, recipe_id: str) -> list[RatingDocument]:
        return await self.list(query={"recipe_id": recipe_id}, sort=[("created_at", 1)])
