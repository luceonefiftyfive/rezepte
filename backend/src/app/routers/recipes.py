import typing as ty

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
from app.routers.users import CurrentUser, Db
from app.services.image_service import ImageService
from app.services.recipe_service import RecipeListSort, RecipeService
from litestar import Request, Response, Router, delete, get, post, put
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body, FromPath, FromQuery
from litestar.status_codes import HTTP_201_CREATED

settings = Settings()

FileUpload = ty.Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]


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


def _recipe_image_url(key: str) -> str:
    image_key = key.lstrip("/")
    return f"/api/recipes/images/{image_key}"


async def _read_recipe_import_payload(
    request: Request,
) -> bytes:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a ZIP archive using multipart/form-data",
        )

    form = await request.form()
    raw_format = form.get("format")
    if raw_format not in {None, RecipeExportFormat.ZIP.value}:
        raise HTTPException(status_code=400, detail="Only ZIP format is supported")

    archive = form.get("archive")
    if archive is None or not hasattr(archive, "read"):
        raise HTTPException(status_code=400, detail="Please select a ZIP archive")
    archive_content = await archive.read()
    if not archive_content:
        raise HTTPException(status_code=400, detail="Uploaded ZIP archive is empty")
    return archive_content


@get("")
async def list_recipes(
    db: Db,
    current_user: CurrentUser,
    group_ids: FromQuery[str | None] = None,
    sort: FromQuery[RecipeListSort] = RecipeListSort.CREATED_DESC,
) -> list[RecipeOut]:
    selected_group_ids = _parse_group_ids(group_ids)
    if current_user.get("is_super_admin", False):
        return await RecipeService(db).list_recipes(
            group_ids=sorted(selected_group_ids) if selected_group_ids else None,
            sort=sort,
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
    return await RecipeService(db).list_recipes(
        group_ids=sorted(effective_group_ids),
        sort=sort,
    )


@get("/admin/export")
async def export_recipes(
    db: Db,
    request: Request,
    admin_user: CurrentUser,
    group_id: FromQuery[str | None] = None,
) -> Response:
    service = RecipeService(db, request.app.state.s3_client, settings)
    exported = await service.export_recipes(group_id=group_id)
    return Response(
        content=exported,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="rezepte-export.zip"'},
    )


@delete("/admin/purge", status_code=200)
async def purge_recipes(
    db: Db,
    admin_user: CurrentUser,
    group_id: FromQuery[str | None] = None,
) -> dict[str, object]:
    deleted_count = await RecipeService(db).purge_recipes(group_id=group_id)
    return {"ok": True, "group_id": group_id, "deleted_count": deleted_count}


@post("/admin/import/preview", status_code=200)
async def preview_import_recipes(
    db: Db,
    request: Request,
    admin_user: CurrentUser,
) -> RecipeImportPreviewResult:
    try:
        archive_content = await _read_recipe_import_payload(request)
        return await RecipeService(
            db, request.app.state.s3_client, settings
        ).preview_import_recipes(archive_content=archive_content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@post("/admin/import", status_code=200)
async def import_recipes(
    db: Db,
    request: Request,
    admin_user: CurrentUser,
) -> RecipeImportResult:
    try:
        archive_content = await _read_recipe_import_payload(request)
        return await RecipeService(
            db, request.app.state.s3_client, settings
        ).import_recipes(archive_content=archive_content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@get("/images/{key:path}", name="stream_recipe_image")
async def stream_recipe_image(
    key: FromPath[str],
    request: Request,
) -> Response:
    downloaded = await ImageService(
        request.app.state.s3_client,
        settings,
    ).download_image(key.lstrip("/"))

    return Response(
        content=downloaded.content,
        media_type=downloaded.content_type,
    )


@get("/{recipe_id:str}")
async def get_recipe(
    recipe_id: FromPath[str],
    db: Db,
    current_user: CurrentUser,
) -> RecipeOut:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not current_user.get("is_super_admin", False):
        if not set(recipe.group_ids).intersection(_assigned_group_ids(current_user)):
            raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@post("", status_code=HTTP_201_CREATED)
async def create_recipe(
    data: RecipeCreate,
    db: Db,
    current_user: CurrentUser,
) -> RecipeOut:
    recipe = data
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


@put("/{recipe_id:str}")
async def update_recipe(
    recipe_id: FromPath[str],
    data: RecipeUpdate,
    db: Db,
    current_user: CurrentUser,
) -> RecipeOut:
    recipe = data
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


@delete("/{recipe_id:str}", status_code=200)
async def delete_recipe(
    recipe_id: FromPath[str],
    db: Db,
    current_user: CurrentUser,
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


@post("/{recipe_id:str}/images/upload", status_code=200)
async def upload_recipe_image(
    recipe_id: FromPath[str],
    request: Request,
    db: Db,
    current_user: CurrentUser,
    data: FileUpload,
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
        file=data,
        key_prefix=f"recipes/{recipe_id}/cover",
    )
    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": uploaded.key,
        "size": uploaded.size,
        "content_type": uploaded.content_type,
        "view_url": _recipe_image_url(uploaded.key),
    }


@post("/{recipe_id:str}/instructions/{step_id:str}/image/upload", status_code=200)
async def upload_instruction_image(
    recipe_id: FromPath[str],
    step_id: FromPath[str],
    request: Request,
    db: Db,
    current_user: CurrentUser,
    data: FileUpload,
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
        file=data,
        key_prefix=f"recipes/{recipe_id}/steps/{step_id}",
    )
    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": uploaded.key,
        "size": uploaded.size,
        "content_type": uploaded.content_type,
        "view_url": _recipe_image_url(uploaded.key),
    }


@get("/{recipe_id:str}/image-url")
async def get_recipe_image_url(
    recipe_id: FromPath[str],
    request: Request,
    db: Db,
    current_user: CurrentUser,
) -> dict[str, object]:
    recipe = await RecipeService(db).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not current_user.get("is_super_admin", False):
        if not set(recipe.group_ids).intersection(_assigned_group_ids(current_user)):
            raise HTTPException(status_code=404, detail="Recipe not found")
    if not recipe.recipe_image_key:
        raise HTTPException(status_code=404, detail="Recipe image not found")

    view_url = _recipe_image_url(recipe.recipe_image_key)
    return {
        "ok": True,
        "key": recipe.recipe_image_key,
        "view_url": view_url,
    }


@get("/{recipe_id:str}/instructions/{step_id:str}/image-url")
async def get_instruction_image_url(
    recipe_id: FromPath[str],
    step_id: FromPath[str],
    request: Request,
    db: Db,
    current_user: CurrentUser,
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

    view_url = _recipe_image_url(step.image_key)
    return {
        "ok": True,
        "key": step.image_key,
        "view_url": view_url,
    }


router = Router(
    path="/recipes",
    route_handlers=[
        list_recipes,
        export_recipes,
        purge_recipes,
        preview_import_recipes,
        import_recipes,
        stream_recipe_image,
        get_recipe,
        create_recipe,
        update_recipe,
        delete_recipe,
        upload_recipe_image,
        upload_instruction_image,
        get_recipe_image_url,
        get_instruction_image_url,
    ],
)
