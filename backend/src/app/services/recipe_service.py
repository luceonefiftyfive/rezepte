from datetime import datetime, timezone
from typing import Any
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.recipes import RecipeCreate, RecipeOut, RecipeUpdate
from app.repositories.recipe_repository import RecipeRepository


class RecipeService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repository = RecipeRepository(db)

    @staticmethod
    def _to_output(document: dict[str, Any]) -> RecipeOut:
        document = {key: value for key, value in document.items() if key != "_id"}
        return RecipeOut.model_validate(document)

    async def list_recipes(self) -> list[RecipeOut]:
        documents = await self.repository.list(sort=[("updated_at", -1)], limit=100)
        return [self._to_output(document) for document in documents]

    async def get_recipe(self, recipe_id: str) -> RecipeOut | None:
        document = await self.repository.find_by_public_id(recipe_id)
        return self._to_output(document) if document else None

    async def create_recipe(self, recipe: RecipeCreate) -> RecipeOut:
        now = datetime.now(timezone.utc)
        document = recipe.model_dump(by_alias=True, mode="json") | {
            "id": str(uuid.uuid4()),
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }
        created = await self.repository.insert(document)
        return self._to_output(created)

    async def update_recipe(
        self, recipe_id: str, recipe: RecipeUpdate
    ) -> RecipeOut | None:
        values = recipe.model_dump(
            by_alias=True, mode="json", exclude_none=True, exclude={"version"}
        )
        values["updated_at"] = datetime.now(timezone.utc)
        updated = await self.repository.update_with_version(
            recipe_id, recipe.version, values
        )
        return self._to_output(updated) if updated else None

    async def delete_recipe(self, recipe_id: str) -> bool:
        return await self.repository.delete_by_public_id(recipe_id)
