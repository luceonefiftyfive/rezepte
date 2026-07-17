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
from app.routers.users import require_admin_or_super_admin
from app.services.image_service import ImageService
from app.services.recipe_service import RecipeService
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/recipes", tags=["recipes"])
settings = Settings()


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
) -> list[RecipeOut]:
    return await RecipeService(db).list_recipes()


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
) -> RecipeOut:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe: RecipeCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> RecipeOut:
    return await RecipeService(db).create_recipe(recipe)


@router.put("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: str,
    recipe: RecipeUpdate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> RecipeOut:
    service = RecipeService(db)
    existing = await service.get_recipe(recipe_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
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
) -> dict[str, object]:
    if not await RecipeService(db).delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"ok": True, "deleted_id": recipe_id}


@router.post("/{recipe_id}/images/upload")
async def upload_recipe_image(
    recipe_id: str,
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    file: UploadFile = File(...),
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

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
    file: UploadFile = File(...),
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
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
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
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
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
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
