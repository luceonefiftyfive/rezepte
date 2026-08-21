from app.core.security import now_utc
from app.models.group import GroupCreate, GroupOut, GroupUpdate
from app.repositories.group_repository import GroupRepository
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.user_repository import UserRepository
from litestar.exceptions import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


class GroupService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.group_repository = GroupRepository(db)
        self.user_repository = UserRepository(db)
        self.recipe_repository = RecipeRepository(db)

    @staticmethod
    def _to_output(document: dict) -> GroupOut:
        return GroupOut.model_validate(
            {key: value for key, value in document.items() if key != "_id"}
        )

    async def list_groups(self, group_ids: set[str] | None = None) -> list[GroupOut]:
        groups = await self.group_repository.list_groups(group_ids=group_ids)
        return [self._to_output(group) for group in groups]

    async def get_group_or_404(self, group_id: str) -> GroupOut:
        group = await self.group_repository.find_by_group_id(group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        return self._to_output(group)

    async def create_group(self, data: GroupCreate) -> GroupOut:
        if await self.group_repository.find_by_group_id(data.id):
            raise HTTPException(status_code=409, detail="Group ID already exists")
        timestamp = now_utc()
        created = await self.group_repository.insert(
            data.model_dump(mode="json")
            | {"created_at": timestamp, "updated_at": timestamp}
        )
        return self._to_output(created)

    async def update_group(self, group_id: str, data: GroupUpdate) -> GroupOut:
        values = data.model_dump(mode="json", exclude_none=True)
        if not values:
            return await self.get_group_or_404(group_id)
        values["updated_at"] = now_utc()
        updated = await self.group_repository.update_by_group_id(group_id, values)
        if updated is None:
            raise HTTPException(status_code=404, detail="Group not found")
        return self._to_output(updated)

    async def delete_group(self, group_id: str) -> dict[str, int | str | bool]:
        existing = await self.group_repository.find_by_group_id(group_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Group not found")

        await self.group_repository.delete_by_group_id(group_id)
        users_updated = await self.user_repository.remove_group_references(group_id)
        recipes_updated, recipes_deleted = (
            await self.recipe_repository.remove_group_references(group_id)
        )

        return {
            "ok": True,
            "deleted_group_id": group_id,
            "users_updated": users_updated,
            "recipes_updated": recipes_updated,
            "recipes_deleted": recipes_deleted,
        }
