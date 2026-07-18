import base64
import io
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

import yaml
from app.models.recipes import (
    RecipeCreate,
    RecipeExportFormat,
    RecipeExportImage,
    RecipeExportPayload,
    RecipeImportPreviewResult,
    RecipeImportResult,
    RecipeOut,
    RecipeUpdate,
)
from app.repositories.recipe_repository import RecipeRepository
from app.services.image_service import DownloadedImage, ImageService
from motor.motor_asyncio import AsyncIOMotorDatabase


class RecipeService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        s3_client: Any | None = None,
        settings: Any | None = None,
    ):
        self.repository = RecipeRepository(db)
        self.s3_client = s3_client
        self.settings = settings

    @staticmethod
    def _to_output(document: dict[str, Any]) -> RecipeOut:
        document = {key: value for key, value in document.items() if key != "_id"}
        return RecipeOut.model_validate(document)

    async def list_recipes(self, group_ids: list[str] | None = None) -> list[RecipeOut]:
        if group_ids is None:
            documents = await self.repository.list(sort=[("updated_at", -1)], limit=100)
        else:
            documents = await self.repository.list_by_group(
                group_ids=group_ids,
                sort=[("updated_at", -1)],
            )
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
        self,
        group_id: str | None = None,
        include_image_data: bool = True,
    ) -> RecipeExportPayload:
        documents = await self.repository.list_by_group(
            group_id=group_id,
            sort=[("updated_at", -1)],
        )
        recipes = [self._to_output(document) for document in documents]
        images = await self._build_export_images(
            recipes,
            include_image_data=include_image_data,
        )
        return RecipeExportPayload(
            export_schema="rezepte.recipes.export.v1",
            exported_at=datetime.now(timezone.utc),
            count=len(recipes),
            filters={"group_id": group_id},
            recipes=recipes,
            images=images,
        )

    async def export_recipes(
        self,
        export_format: RecipeExportFormat,
        group_id: str | None = None,
    ) -> str | bytes:
        if export_format == RecipeExportFormat.ZIP:
            return await self._build_export_archive(group_id=group_id)

        include_image_data = export_format != RecipeExportFormat.ZIP
        payload = await self.build_export_payload(
            group_id=group_id,
            include_image_data=include_image_data,
        )
        payload_yaml = self._dump_export_payload_yaml(payload)

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
        content: str | None,
        import_format: RecipeExportFormat,
        archive_content: bytes | None = None,
    ) -> RecipeImportResult:
        parsed_payload = self._parse_import_payload(
            content=content,
            import_format=import_format,
            archive_content=archive_content,
        )
        await self._restore_import_images(
            parsed_payload,
            import_format=import_format,
            archive_content=archive_content,
        )
        documents = self._collect_import_documents(parsed_payload)
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
        content: str | None,
        import_format: RecipeExportFormat,
        archive_content: bytes | None = None,
    ) -> RecipeImportPreviewResult:
        parsed_payload = self._parse_import_payload(
            content=content,
            import_format=import_format,
            archive_content=archive_content,
        )
        documents = self._collect_import_documents(parsed_payload)
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
        self,
        content: str | None,
        import_format: RecipeExportFormat,
        archive_content: bytes | None = None,
    ) -> dict[str, Any]:
        if import_format == RecipeExportFormat.ZIP:
            if archive_content is None:
                raise ValueError("ZIP import requires archive content")
            with zipfile.ZipFile(io.BytesIO(archive_content)) as archive:
                try:
                    yaml_content = archive.read("manifest.yaml").decode("utf-8")
                except KeyError as exc:
                    raise ValueError("ZIP archive must contain manifest.yaml") from exc
                parsed = yaml.safe_load(yaml_content)
                if not isinstance(parsed, dict):
                    raise ValueError(
                        "Import content must describe an object at top level"
                    )
                return parsed

        if content is None:
            raise ValueError("Import content is required")

        yaml_content = (
            self._extract_yaml_from_markdown(content)
            if import_format == RecipeExportFormat.MARKDOWN
            else content
        )
        parsed = yaml.safe_load(yaml_content)
        if not isinstance(parsed, dict):
            raise ValueError("Import content must describe an object at top level")
        return parsed

    def _require_image_service(self) -> ImageService:
        if self.s3_client is None or self.settings is None:
            raise RuntimeError("Image export/import requires S3 dependencies")
        return ImageService(self.s3_client, self.settings)

    async def _build_export_images(
        self,
        recipes: list[RecipeOut],
        include_image_data: bool = True,
    ) -> dict[str, RecipeExportImage]:
        image_keys: set[str] = set()
        for recipe in recipes:
            if recipe.recipe_image_key:
                image_keys.add(recipe.recipe_image_key)
            for step in recipe.instructions:
                if step.image_key:
                    image_keys.add(step.image_key)

        if not image_keys:
            return {}

        image_service = self._require_image_service()
        images: dict[str, RecipeExportImage] = {}
        for key in sorted(image_keys):
            downloaded = await image_service.download_image(key)
            images[key] = RecipeExportImage(
                content_type=downloaded.content_type,
                data=(
                    base64.b64encode(downloaded.content).decode("ascii")
                    if include_image_data
                    else None
                ),
                path=None if include_image_data else f"images/{key}",
            )
        return images

    def _dump_export_payload_yaml(self, payload: RecipeExportPayload) -> str:
        return yaml.safe_dump(
            payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            sort_keys=False,
            allow_unicode=False,
        )

    async def _build_export_archive(self, group_id: str | None = None) -> bytes:
        documents = await self.repository.list_by_group(
            group_id=group_id,
            sort=[("updated_at", -1)],
        )
        recipes = [self._to_output(document) for document in documents]
        downloaded_images = await self._download_export_images(recipes)
        payload = RecipeExportPayload(
            export_schema="rezepte.recipes.export.v1",
            exported_at=datetime.now(timezone.utc),
            count=len(recipes),
            filters={"group_id": group_id},
            recipes=recipes,
            images={
                key: RecipeExportImage(
                    content_type=image.content_type, path=f"images/{key}"
                )
                for key, image in downloaded_images.items()
            },
        )

        archive_buffer = io.BytesIO()
        manifest_yaml = self._dump_export_payload_yaml(payload)

        with zipfile.ZipFile(
            archive_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr("manifest.yaml", manifest_yaml)
            for key, downloaded in downloaded_images.items():
                archive.writestr(f"images/{key}", downloaded.content)

        return archive_buffer.getvalue()

    async def _download_export_images(
        self,
        recipes: list[RecipeOut],
    ) -> dict[str, DownloadedImage]:
        image_keys: set[str] = set()
        for recipe in recipes:
            if recipe.recipe_image_key:
                image_keys.add(recipe.recipe_image_key)
            for step in recipe.instructions:
                if step.image_key:
                    image_keys.add(step.image_key)

        if not image_keys:
            return {}

        image_service = self._require_image_service()
        images: dict[str, DownloadedImage] = {}
        for key in sorted(image_keys):
            images[key] = await image_service.download_image(key)
        return images

    async def _restore_import_images(
        self,
        parsed_payload: dict[str, Any],
        import_format: RecipeExportFormat,
        archive_content: bytes | None = None,
    ) -> None:
        raw_images = parsed_payload.get("images", {})
        if raw_images is None:
            return
        if not isinstance(raw_images, dict):
            raise ValueError("Import content contains invalid 'images' data")
        if not raw_images:
            return

        image_service = self._require_image_service()
        archive = None
        if import_format == RecipeExportFormat.ZIP:
            if archive_content is None:
                raise ValueError("ZIP import requires archive content")
            archive = zipfile.ZipFile(io.BytesIO(archive_content))

        try:
            for key, raw_image in raw_images.items():
                if not isinstance(key, str) or not isinstance(raw_image, dict):
                    raise ValueError(
                        "Each exported image must be an object keyed by its storage key"
                    )
                content_type = raw_image.get("content_type")
                data = raw_image.get("data")
                path = raw_image.get("path")
                if not isinstance(content_type, str) or not content_type:
                    raise ValueError(
                        f"Exported image {key} is missing a valid content_type"
                    )

                if isinstance(data, str) and data:
                    try:
                        content = base64.b64decode(data, validate=True)
                    except ValueError as exc:
                        raise ValueError(
                            f"Exported image {key} is not valid base64 data"
                        ) from exc
                else:
                    if archive is None:
                        raise ValueError(
                            f"Exported image {key} does not contain inline data"
                        )
                    image_path = (
                        path if isinstance(path, str) and path else f"images/{key}"
                    )
                    try:
                        content = archive.read(image_path)
                    except KeyError as exc:
                        raise ValueError(
                            f"Exported image {key} is missing from the ZIP archive"
                        ) from exc

                await image_service.restore_image(
                    key=key, content=content, content_type=content_type
                )
        finally:
            if archive is not None:
                archive.close()

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
        parsed_payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        recipes = parsed_payload.get("recipes")

        if not isinstance(recipes, list):
            raise ValueError("Import content does not contain a valid 'recipes' list")

        documents: list[dict[str, Any]] = []
        for raw_recipe in recipes:
            if not isinstance(raw_recipe, dict):
                raise ValueError("Each recipe in import content must be an object")
            documents.append(self._normalize_import_recipe(raw_recipe))

        return documents
