from typing import Annotated

from app.core.database import get_db
from app.models.recipes import (
    RecipeCreate,
    RecipeExportFormat,
    RecipeImportPreviewResult,
    RecipeImportRequest,
    RecipeImportResult,
    RecipeOut,
    RecipeUpdate,
)
from app.routers.users import require_admin_or_super_admin
from app.services.recipe_service import RecipeService
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeOut])
async def list_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> list[RecipeOut]:
    return await RecipeService(db).list_recipes()


@router.get("/admin/export", response_class=PlainTextResponse)
async def export_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
    format: RecipeExportFormat = RecipeExportFormat.YAML,
    group_id: str | None = None,
) -> str:
    service = RecipeService(db)
    return await service.export_recipes(export_format=format, group_id=group_id)


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
    payload: RecipeImportRequest,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
) -> RecipeImportPreviewResult:
    try:
        return await RecipeService(db).preview_import_recipes(
            content=payload.content,
            import_format=payload.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/import", response_model=RecipeImportResult)
async def import_recipes(
    payload: RecipeImportRequest,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin_or_super_admin)],
) -> RecipeImportResult:
    try:
        return await RecipeService(db).import_recipes(
            content=payload.content,
            import_format=payload.format,
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
