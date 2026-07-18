from typing import Annotated

from app.core.database import get_db
from app.core.settings import Settings
from app.models.recipes import (
    RecipeCreate,
    RecipeExportFormat,
    RecipeImportPreviewResult,
    RecipeImportResult,
    RecipeOut,
    RecipeUpdate,
)
from app.models.user import Role
from app.routers.users import get_current_user, require_admin_or_super_admin
from app.services.image_service import ImageService
from app.services.recipe_service import RecipeService
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/recipes", tags=["recipes"])
settings = Settings()


def _assigned_group_ids(current_user: dict) -> set[str]:
    return {group["group_id"] for group in current_user.get("groups", [])}


def _manageable_group_ids(current_user: dict) -> set[str] | None:
    if current_user.get("is_super_admin", False):
        return None
    return {
        group["group_id"]
        for group in current_user.get("groups", [])
        if group["role"] in {Role.admin.value, Role.author.value}
    }


def _parse_group_ids(value: str | None) -> set[str] | None:
    if value is None:
        return None
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed


def _recipe_image_url(request: Request, key: str) -> str:
    base_url = settings.app_base_url.rstrip("/")
    image_key = key.lstrip("/")
    return f"{base_url}/api/recipes/images/{image_key}"


async def _read_recipe_import_payload(
    request: Request,
) -> tuple[RecipeExportFormat, str | None, bytes | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_format = form.get("format")
        if not isinstance(raw_format, str) or not raw_format:
            raise HTTPException(status_code=400, detail="Import format is required")
        try:
            import_format = RecipeExportFormat(raw_format)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid import format"
            ) from exc

        content = form.get("content")
        archive = form.get("archive")
        archive_content = None
        if archive is not None:
            if not hasattr(archive, "read"):
                raise HTTPException(status_code=400, detail="Invalid archive upload")
            archive_content = await archive.read()

        if import_format == RecipeExportFormat.ZIP:
            if archive_content is None:
                raise HTTPException(
                    status_code=400, detail="Please select a ZIP archive"
                )
            return import_format, None, archive_content

        if not isinstance(content, str):
            raise HTTPException(status_code=400, detail="Import content is required")
        return import_format, content, None

    payload = await request.json()
    raw_format = payload.get("format", RecipeExportFormat.YAML)
    try:
        import_format = RecipeExportFormat(raw_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid import format") from exc

    content = payload.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="Import content is required")
    return import_format, content, None


@router.get("", response_model=list[RecipeOut])
async def list_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    group_ids: str | None = None,
) -> list[RecipeOut]:
    selected_group_ids = _parse_group_ids(group_ids)
    if current_user.get("is_super_admin", False):
        return await RecipeService(db).list_recipes(
            group_ids=sorted(selected_group_ids) if selected_group_ids else None
        )

    assigned_group_ids = _assigned_group_ids(current_user)
    if not assigned_group_ids:
        return []
    if selected_group_ids is not None and not selected_group_ids.issubset(
        assigned_group_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="You may only filter recipes by groups assigned to you",
        )

    effective_group_ids = selected_group_ids or assigned_group_ids
    return await RecipeService(db).list_recipes(group_ids=sorted(effective_group_ids))


@router.get("/admin/export", response_model=None)
async def export_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    request: Request,
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
    format: RecipeExportFormat = RecipeExportFormat.YAML,
    group_id: str | None = None,
) -> str | Response:
    service = RecipeService(db, request.app.state.s3_client, settings)
    exported = await service.export_recipes(export_format=format, group_id=group_id)
    if format == RecipeExportFormat.ZIP:
        assert isinstance(exported, bytes)
        return Response(
            content=exported,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="rezepte-export.zip"'
            },
        )
    assert isinstance(exported, str)
    return PlainTextResponse(exported)


@router.delete("/admin/purge")
async def purge_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
    group_id: str | None = None,
) -> dict[str, object]:
    deleted_count = await RecipeService(db).purge_recipes(group_id=group_id)
    return {"ok": True, "group_id": group_id, "deleted_count": deleted_count}


@router.post("/admin/import/preview", response_model=RecipeImportPreviewResult)
async def preview_import_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    request: Request,
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
) -> RecipeImportPreviewResult:
    try:
        import_format, content, archive_content = await _read_recipe_import_payload(
            request
        )
        return await RecipeService(
            db, request.app.state.s3_client, settings
        ).preview_import_recipes(
            content=content,
            import_format=import_format,
            archive_content=archive_content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/import", response_model=RecipeImportResult)
async def import_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    request: Request,
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
) -> RecipeImportResult:
    try:
        import_format, content, archive_content = await _read_recipe_import_payload(
            request
        )
        return await RecipeService(
            db, request.app.state.s3_client, settings
        ).import_recipes(
            content=content,
            import_format=import_format,
            archive_content=archive_content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> RecipeOut:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not current_user.get("is_super_admin", False):
        if not set(recipe.group_ids).intersection(_assigned_group_ids(current_user)):
            raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe: RecipeCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> RecipeOut:
    if not recipe.group_ids:
        raise HTTPException(
            status_code=422, detail="A recipe must be assigned to at least one group"
        )

    manageable_group_ids = _manageable_group_ids(current_user)
    requested_group_ids = set(recipe.group_ids)
    if manageable_group_ids is not None:
        if not manageable_group_ids:
            raise HTTPException(status_code=403, detail="Author role required")
        if not requested_group_ids.issubset(manageable_group_ids):
            raise HTTPException(
                status_code=403,
                detail="You may only create recipes in groups where you are author or admin",
            )
    return await RecipeService(db).create_recipe(recipe)


@router.put("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: str,
    recipe: RecipeUpdate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> RecipeOut:
    service = RecipeService(db)
    existing = await service.get_recipe(recipe_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    manageable_group_ids = _manageable_group_ids(current_user)
    if manageable_group_ids is not None:
        if not manageable_group_ids:
            raise HTTPException(status_code=403, detail="Author role required")
        if not set(existing.group_ids).intersection(manageable_group_ids):
            raise HTTPException(status_code=403, detail="You may not edit this recipe")

        requested_group_ids = (
            set(recipe.group_ids)
            if recipe.group_ids is not None
            else set(existing.group_ids)
        )
        if not requested_group_ids:
            raise HTTPException(
                status_code=422,
                detail="A recipe must be assigned to at least one group",
            )
        if not requested_group_ids.issubset(manageable_group_ids):
            raise HTTPException(
                status_code=403,
                detail="You may only assign groups where you are author or admin",
            )
    elif recipe.group_ids is not None and not recipe.group_ids:
        raise HTTPException(
            status_code=422,
            detail="A recipe must be assigned to at least one group",
        )

    updated = await service.update_recipe(recipe_id, recipe)
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Recipe was changed by another user. Reload and try again.",
        )
    return updated


@router.delete("/{recipe_id}")
async def delete_recipe(
    recipe_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, object]:
    service = RecipeService(db)
    existing = await service.get_recipe(recipe_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    manageable_group_ids = _manageable_group_ids(current_user)
    if manageable_group_ids is not None:
        if not manageable_group_ids:
            raise HTTPException(status_code=403, detail="Author role required")
        if not set(existing.group_ids).intersection(manageable_group_ids):
            raise HTTPException(
                status_code=403, detail="You may not delete this recipe"
            )

    if not await service.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"ok": True, "deleted_id": recipe_id}


@router.post("/{recipe_id}/images/upload")
async def upload_recipe_image(
    recipe_id: str,
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    manageable_group_ids = _manageable_group_ids(current_user)
    if manageable_group_ids is not None:
        if not manageable_group_ids:
            raise HTTPException(status_code=403, detail="Author role required")
        if not set(recipe.group_ids).intersection(manageable_group_ids):
            raise HTTPException(status_code=403, detail="You may not edit this recipe")

    image_service = ImageService(request.app.state.s3_client, settings)
    uploaded = await image_service.upload_image(
        file=file,
        key_prefix=f"recipes/{recipe_id}/cover",
    )
    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": uploaded.key,
        "size": uploaded.size,
        "content_type": uploaded.content_type,
        "view_url": _recipe_image_url(request, uploaded.key),
    }


@router.post("/{recipe_id}/instructions/{step_id}/image/upload")
async def upload_instruction_image(
    recipe_id: str,
    step_id: str,
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    manageable_group_ids = _manageable_group_ids(current_user)
    if manageable_group_ids is not None:
        if not manageable_group_ids:
            raise HTTPException(status_code=403, detail="Author role required")
        if not set(recipe.group_ids).intersection(manageable_group_ids):
            raise HTTPException(status_code=403, detail="You may not edit this recipe")
    if not any(step.id == step_id for step in recipe.instructions):
        raise HTTPException(status_code=404, detail="Instruction step not found")

    image_service = ImageService(request.app.state.s3_client, settings)
    uploaded = await image_service.upload_image(
        file=file,
        key_prefix=f"recipes/{recipe_id}/steps/{step_id}",
    )
    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": uploaded.key,
        "size": uploaded.size,
        "content_type": uploaded.content_type,
        "view_url": _recipe_image_url(request, uploaded.key),
    }


@router.get("/images/{key:path}", name="stream_recipe_image")
async def stream_recipe_image(
    key: str,
    request: Request,
) -> Response:
    downloaded = await ImageService(
        request.app.state.s3_client, settings
    ).download_image(key)
    return Response(content=downloaded.content, media_type=downloaded.content_type)


@router.get("/{recipe_id}/image-url")
async def get_recipe_image_url(
    recipe_id: str,
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not current_user.get("is_super_admin", False):
        if not set(recipe.group_ids).intersection(_assigned_group_ids(current_user)):
            raise HTTPException(status_code=404, detail="Recipe not found")
    if not recipe.recipe_image_key:
        raise HTTPException(status_code=404, detail="Recipe image not found")

    view_url = _recipe_image_url(request, recipe.recipe_image_key)
    return {
        "ok": True,
        "key": recipe.recipe_image_key,
        "view_url": view_url,
    }


@router.get("/{recipe_id}/instructions/{step_id}/image-url")
async def get_instruction_image_url(
    recipe_id: str,
    step_id: str,
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not current_user.get("is_super_admin", False):
        if not set(recipe.group_ids).intersection(_assigned_group_ids(current_user)):
            raise HTTPException(status_code=404, detail="Recipe not found")

    step = next((item for item in recipe.instructions if item.id == step_id), None)
    if step is None:
        raise HTTPException(status_code=404, detail="Instruction step not found")
    if not step.image_key:
        raise HTTPException(status_code=404, detail="Instruction image not found")

    view_url = _recipe_image_url(request, step.image_key)
    return {
        "ok": True,
        "key": step.image_key,
        "view_url": view_url,
    }
