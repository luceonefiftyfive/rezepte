import asyncio
import logging
import typing as ty
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import boto3
from app.core.database import get_mongo_client
from app.core.settings import Settings
from app.models.recipes import RecipeIn, RecipeOut
from app.routers.users import (
    get_current_user,
    require_admin_or_super_admin,
    require_super_admin,
)
from app.routers.users import router as users_router
from app.services.user_service import UserService
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

log = logging.getLogger(__name__)

SESSIONS = {}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


configure_logging()


def create_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="eu-central-1",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.mongo_client = get_mongo_client()
    app.state.db = app.state.mongo_client[settings.mongodb_database]
    app.state.s3_client = create_s3_client()

    # Bootstrap superuser if not exists
    await UserService(app.state.db).bootstrap_superuser()

    yield

    await app.state.mongo_client.close()


settings = Settings()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=not settings.rezepte_test,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)


@app.get("/")
async def root() -> dict[str, ty.Any]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "message": "FastAPI backend is reachable.",
        "python": "3.13",
        "package_manager": "uv",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "mode": settings.mode,
    }


@app.get("/system/checks")
async def system_checks() -> dict[str, ty.Any]:
    checks: dict[str, ty.Any] = {
        "api": {"ok": True},
        "mongo_db": {"ok": False},
        "s3": {"ok": False},
    }

    try:
        await app.state.db.command("ping")
        checks["mongo_db"] = {"ok": True}
    except PyMongoError as exc:
        checks["mongo_db"] = {"ok": False, "error": str(exc)}
    except Exception as exc:
        checks["mongo_db"] = {"ok": False, "error": str(exc)}

    try:
        await asyncio.to_thread(
            app.state.s3_client.head_bucket,
            Bucket=settings.s3_bucket,
        )
        checks["s3"] = {
            "ok": True,
            "endpoint": settings.s3_endpoint_url,
            "bucket": settings.s3_bucket,
        }
    except Exception as exc:
        checks["s3"] = {
            "ok": False,
            "endpoint": settings.s3_endpoint_url,
            "bucket": settings.s3_bucket,
            "error": str(exc),
        }

    checks["ok"] = all(checks[name]["ok"] for name in ["api", "mongo_db", "s3"])

    return checks


@app.get("/recipes", response_model=list[RecipeOut])
async def list_recipes() -> list[RecipeOut]:
    cursor = app.state.db.recipes.find({}, {"_id": 0}).sort("created_at", -1).limit(100)

    recipes = [RecipeOut(**document) async for document in cursor]
    return recipes


@app.post("/recipes", response_model=RecipeOut)
async def create_recipe(recipe: RecipeIn) -> RecipeOut:
    now = datetime.now(timezone.utc).isoformat()

    document = {
        "id": str(uuid.uuid4()),
        "title": recipe.title,
        "description": recipe.description,
        "tags": recipe.tags,
        "created_at": now,
    }

    await app.state.db.recipes.insert_one(document)

    return RecipeOut(**document)


@app.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str) -> dict[str, ty.Any]:
    result = await app.state.db.recipes.delete_one({"id": recipe_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return {
        "ok": True,
        "deleted_id": recipe_id,
    }


@app.post("/images/test-upload")
async def upload_test_image(file: UploadFile = File(...)) -> dict[str, ty.Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is larger than 25 MB")

    safe_filename = file.filename or "upload"
    object_key = f"test-uploads/{uuid.uuid4()}-{safe_filename}"

    try:
        await asyncio.to_thread(
            app.state.s3_client.put_object,
            Bucket=settings.s3_bucket,
            Key=object_key,
            Body=content,
            ContentType=file.content_type,
        )

    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": object_key,
        "size": len(content),
        "content_type": file.content_type,
    }


@app.get("/test-access")
def test_access(
    current_user: ty.Annotated[dict, Depends(get_current_user)],
):
    return {
        "message": "You are authenticated",
        "username": current_user["username"],
    }


@app.get("/test-admin-access")
def test_admin_access(
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
):
    return {
        "message": "You are admin or super-admin",
        "username": current_user["username"],
    }


@app.get("/test-super-admin-access")
def test_super_admin_access(
    current_user: ty.Annotated[dict, Depends(require_super_admin)],
):
    return {
        "message": "You are super-admin",
        "username": current_user["username"],
    }


@app.get("/test-access")
async def test_access(current_user: ty.Annotated[dict, Depends(get_current_user)]):
    return {"message": "You are authenticated", "username": current_user["username"]}


@app.get("/test-admin-access")
async def test_admin_access(
    current_user: ty.Annotated[dict, Depends(require_admin_or_super_admin)],
):
    return {
        "message": "You are admin or super-admin",
        "username": current_user["username"],
    }


@app.get("/test-super-admin-access")
async def test_super_admin_access(
    current_user: ty.Annotated[dict, Depends(require_super_admin)],
):
    return {"message": "You are super-admin", "username": current_user["username"]}
