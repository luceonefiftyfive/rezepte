import asyncio
import logging
import typing as ty
import uuid
from contextlib import asynccontextmanager

import boto3
from app.core.database import get_mongo_client
from app.core.settings import Settings
from app.repositories.group_repository import GroupRepository
from app.routers.groups import router as groups_router
from app.routers.recipes import router as recipes_router
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
    await GroupRepository(app.state.db).ensure_indexes()

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
app.include_router(recipes_router)
app.include_router(groups_router)


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
