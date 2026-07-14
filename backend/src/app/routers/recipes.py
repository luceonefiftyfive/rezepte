from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.models.recipes import RecipeCreate, RecipeOut, RecipeUpdate
from app.services.recipe_service import RecipeService

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeOut])
async def list_recipes(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> list[RecipeOut]:
    return await RecipeService(db).list_recipes()


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
