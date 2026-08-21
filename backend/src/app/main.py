import asyncio
import logging
import os
import subprocess
import typing as ty
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import boto3
from app.core.database import get_db, get_mongo_client
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
from litestar import Litestar, Request, Response, get, post
from litestar.config.cors import CORSConfig
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency, Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException, ValidationException
from litestar.params import Body
from litestar.plugins.pydantic import PydanticPlugin
from pymongo.errors import PyMongoError
from yaml import YAMLError, safe_load

log = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


configure_logging()


def _find_version_file() -> Path | None:
    """Search for version.yaml from cwd and source tree parents."""
    roots: list[Path] = [Path.cwd(), *Path(__file__).resolve().parents]
    seen: set[Path] = set()
    for root in roots:
        candidate = (root / "version.yaml").resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def _read_configured_version() -> str:
    version_file = _find_version_file()
    if not version_file:
        return "unknown"

    try:
        payload = safe_load(version_file.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return "unknown"

    if not isinstance(payload, dict):
        return "unknown"

    version = payload.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return "unknown"


def _read_git_hash() -> str:
    env_hash = os.getenv("REZEPTE_GIT_HASH", "").strip()
    if env_hash:
        return env_hash

    version_file = _find_version_file()
    search_root = version_file.parent if version_file else Path.cwd()

    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=search_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return output.strip() or "unknown"


def get_system_version() -> dict[str, str]:
    return {
        "version": _read_configured_version(),
        "git_hash": _read_git_hash(),
    }


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
async def lifespan(app: Litestar):
    app.state.mongo_client = get_mongo_client()
    app.state.db = app.state.mongo_client[settings.mongodb_database]
    app.state.s3_client = create_s3_client()

    # Bootstrap superuser if not exists
    await UserService(app.state.db).bootstrap_superuser()
    await GroupRepository(app.state.db).ensure_indexes()

    yield

    await app.state.mongo_client.close()


def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    return Response(
        content={"detail": exc.detail},
        status_code=exc.status_code,
        headers=exc.headers,
    )


def validation_exception_handler(
    request: Request, exc: ValidationException
) -> Response:
    return Response(content={"detail": exc.detail}, status_code=422)


settings = Settings()

cors_config = CORSConfig(
    allow_origins=settings.cors_origins,
    allow_credentials=not settings.rezepte_test,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = Litestar(
    route_handlers=[users_router, recipes_router, groups_router],
    lifespan=[lifespan],
    cors_config=cors_config,
    dependencies={
        "db": Provide(get_db, sync_to_thread=False),
        "current_user": Provide(get_current_user),
        "admin_user": Provide(require_admin_or_super_admin, sync_to_thread=False),
        "super_admin_user": Provide(require_super_admin, sync_to_thread=False),
    },
    exception_handlers={
        HTTPException: http_exception_handler,
        ValidationException: validation_exception_handler,
    },
    plugins=[
        PydanticPlugin(prefer_alias=True),
    ],
)


@get("/")
async def root() -> dict[str, ty.Any]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "message": "Litestar backend is reachable.",
        "python": "3.13",
        "package_manager": "uv",
    }


@get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "mode": settings.mode,
    }


@get("/system/checks")
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


@get("/system/version")
async def system_version() -> dict[str, str]:
    return get_system_version()


@post("/images/test-upload", status_code=200, request_max_body_size=30 * 1024 * 1024)
async def upload_test_image(
    request: Request,
    data: ty.Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, ty.Any]:
    if not data.content_type or not data.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    content = await data.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is larger than 25 MB")

    safe_filename = data.filename or "upload"
    object_key = f"test-uploads/{uuid.uuid4()}-{safe_filename}"

    try:
        await asyncio.to_thread(
            request.app.state.s3_client.put_object,
            Bucket=settings.s3_bucket,
            Key=object_key,
            Body=content,
            ContentType=data.content_type,
        )

    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": object_key,
        "size": len(content),
        "content_type": data.content_type,
    }


app.register(root)
app.register(health)
app.register(system_checks)
app.register(system_version)
app.register(upload_test_image)


@get("/test-access", sync_to_thread=False)
def test_access(current_user: ty.Annotated[dict, NamedDependency[dict]]) -> dict:
    return {
        "message": "You are authenticated",
        "username": current_user["username"],
    }


@get("/test-admin-access", sync_to_thread=False)
def test_admin_access(admin_user: ty.Annotated[dict, NamedDependency[dict]]) -> dict:
    return {
        "message": "You are admin or super-admin",
        "username": admin_user["username"],
    }


@get("/test-super-admin-access", sync_to_thread=False)
def test_super_admin_access(
    super_admin_user: ty.Annotated[dict, NamedDependency[dict]],
) -> dict:
    return {
        "message": "You are super-admin",
        "username": super_admin_user["username"],
    }


app.register(test_access)
app.register(test_admin_access)
app.register(test_super_admin_access)
