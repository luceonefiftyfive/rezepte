import re
import uuid
from datetime import datetime, timezone
from typing import Any

import yaml
from app.models.recipes import (
    RecipeCreate,
    RecipeExportFormat,
    RecipeExportPayload,
    RecipeImportPreviewResult,
    RecipeImportResult,
    RecipeOut,
    RecipeUpdate,
)
from app.repositories.recipe_repository import RecipeRepository
from motor.motor_asyncio import AsyncIOMotorDatabase


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

    async def build_export_payload(
        self, group_id: str | None = None
    ) -> RecipeExportPayload:
        documents = await self.repository.list_by_group(
            group_id=group_id,
            sort=[("updated_at", -1)],
        )
        recipes = [self._to_output(document) for document in documents]
        return RecipeExportPayload(
            export_schema="rezepte.recipes.export.v1",
            exported_at=datetime.now(timezone.utc),
            count=len(recipes),
            filters={"group_id": group_id},
            recipes=recipes,
        )

    async def export_recipes(
        self,
        export_format: RecipeExportFormat,
        group_id: str | None = None,
    ) -> str:
        payload = await self.build_export_payload(group_id=group_id)
        payload_yaml = yaml.safe_dump(
            payload.model_dump(mode="json", by_alias=True),
            sort_keys=False,
            allow_unicode=False,
        )

        if export_format == RecipeExportFormat.YAML:
            return payload_yaml

        filter_group = group_id or "alle"
        return (
            "# Rezepte Export\n\n"
            f"- Schema: `{payload.export_schema}`\n"
            f"- Exportiert am: `{payload.exported_at.isoformat()}`\n"
            f"- Anzahl Rezepte: `{payload.count}`\n"
            f"- Filter Gruppe: `{filter_group}`\n\n"
            "```yaml\n"
            f"{payload_yaml}"
            "```\n"
        )

    async def purge_recipes(self, group_id: str | None = None) -> int:
        if group_id:
            return await self.repository.purge_by_group(group_id)
        return await self.repository.purge_all()

    async def import_recipes(
        self,
        content: str,
        import_format: RecipeExportFormat,
    ) -> RecipeImportResult:
        documents = self._collect_import_documents(content, import_format)
        created = 0
        updated = 0

        for document in documents:
            _, was_created = await self.repository.upsert_by_public_id(
                document["id"], document
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return RecipeImportResult(
            imported=len(documents), created=created, updated=updated
        )

    async def preview_import_recipes(
        self,
        content: str,
        import_format: RecipeExportFormat,
    ) -> RecipeImportPreviewResult:
        documents = self._collect_import_documents(content, import_format)
        simulated_existing_ids: set[str] = set()
        would_create = 0
        would_update = 0

        for document in documents:
            recipe_id = document["id"]
            if recipe_id in simulated_existing_ids:
                would_update += 1
                continue

            if await self.repository.find_by_public_id(recipe_id):
                simulated_existing_ids.add(recipe_id)
                would_update += 1
                continue

            simulated_existing_ids.add(recipe_id)
            would_create += 1

        return RecipeImportPreviewResult(
            imported=len(documents),
            would_create=would_create,
            would_update=would_update,
        )

    @staticmethod
    def _extract_yaml_from_markdown(content: str) -> str:
        code_fence_match = re.search(
            r"```(?:yaml|yml|json)?\s*\n(.*?)```",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return code_fence_match.group(1).strip() if code_fence_match else content

    def _parse_import_payload(
        self, content: str, import_format: RecipeExportFormat
    ) -> dict[str, Any]:
        yaml_content = (
            self._extract_yaml_from_markdown(content)
            if import_format == RecipeExportFormat.MARKDOWN
            else content
        )
        parsed = yaml.safe_load(yaml_content)
        if not isinstance(parsed, dict):
            raise ValueError("Import content must describe an object at top level")
        return parsed

    def _normalize_import_recipe(self, raw_recipe: dict[str, Any]) -> dict[str, Any]:
        if "id" in raw_recipe:
            parsed = RecipeOut.model_validate(raw_recipe)
            normalized = parsed.model_dump(mode="json", by_alias=True)
            normalized["created_at"] = parsed.created_at
            normalized["updated_at"] = parsed.updated_at
            return normalized

        parsed_create = RecipeCreate.model_validate(raw_recipe)
        now = datetime.now(timezone.utc)
        return parsed_create.model_dump(mode="json", by_alias=True) | {
            "id": str(uuid.uuid4()),
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }

    def _collect_import_documents(
        self,
        content: str,
        import_format: RecipeExportFormat,
    ) -> list[dict[str, Any]]:
        parsed_payload = self._parse_import_payload(content, import_format)
        recipes = parsed_payload.get("recipes")

        if not isinstance(recipes, list):
            raise ValueError("Import content does not contain a valid 'recipes' list")

        documents: list[dict[str, Any]] = []
        for raw_recipe in recipes:
            if not isinstance(raw_recipe, dict):
                raise ValueError("Each recipe in import content must be an object")
            documents.append(self._normalize_import_recipe(raw_recipe))

        return documents
