
import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import httpx
import secrets
import os
import logging

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "rezepte")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "frontend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "change-me-frontend-secret")

log = logging.getLogger(__name__)

SESSIONS = {}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    rezepte_test: bool = Field(default=False, alias="REZEPTE_TEST")
    app_base_url: str = Field(default="http://localhost:8080", alias="APP_BASE_URL")

    app_name: str = "Familienrezepte API"

    mongodb_uri: str = Field(
        default="mongodb://rezepte:change-me@mongodb:27017/rezepte?authSource=admin",
        alias="MONGODB_URI",
    )
    mongodb_database: str = Field(default="rezepte", alias="MONGODB_DATABASE")

    s3_endpoint_url: str = Field(default="http://minio:9000", alias="S3_ENDPOINT_URL")
    s3_bucket: str = Field(default="familienrezepte-images", alias="S3_BUCKET")
    s3_access_key: str = Field(default="rezepte-minio", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="change-me-minio-password", alias="S3_SECRET_KEY")

    @property
    def mode(self) -> str:
        return "test" if self.rezepte_test else "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.rezepte_test:
            return ["*"]

        return [self.app_base_url]


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
    app.state.mongo_client = AsyncMongoClient(settings.mongodb_uri)
    app.state.db = app.state.mongo_client[settings.mongodb_database]
    app.state.s3_client = create_s3_client()

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


class RecipeIn(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class RecipeOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: str

class LoginRequest(BaseModel):
    username: str
    password: str



@app.get("/")
async def root() -> dict[str, Any]:
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
async def system_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {
        "api": {"ok": True},
        "mongodb": {"ok": False},
        "s3": {"ok": False},
    }

    try:
        await app.state.db.command("ping")
        checks["mongodb"] = {"ok": True}
    except PyMongoError as exc:
        checks["mongodb"] = {"ok": False, "error": str(exc)}
    except Exception as exc:
        checks["mongodb"] = {"ok": False, "error": str(exc)}

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

    checks["ok"] = all(
        checks[name]["ok"]
        for name in ["api", "mongodb", "s3"]
    )

    return checks


@app.get("/recipes", response_model=list[RecipeOut])
async def list_recipes() -> list[RecipeOut]:
    cursor = (
        app.state.db.recipes
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .limit(100)
    )

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
async def delete_recipe(recipe_id: str) -> dict[str, Any]:
    result = await app.state.db.recipes.delete_one({"id": recipe_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return {
        "ok": True,
        "deleted_id": recipe_id,
    }


@app.post("/images/test-upload")
async def upload_test_image(file: UploadFile = File(...)) -> dict[str, Any]:
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

@app.post("/auth/login")
async def login(data: LoginRequest):
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    log.error(f"Attempting login for user '{data.username}' against Keycloak at {token_url}")

    async with httpx.AsyncClient() as client:
        data_content = {
                "grant_type": "password",
                "client_id": KEYCLOAK_CLIENT_ID,
                "client_secret": KEYCLOAK_CLIENT_SECRET,
                "username": data.username,
                "password": data.password,
                "scope": "openid profile email",
            } 
        log.error(f"Sending token request to Keycloak with data: {data_content}")
        r = await client.post(
            token_url,
            data=data_content,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if r.status_code != 200:
        log.error("Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tokens = r.json()
    session_id = secrets.token_urlsafe(32)

    SESSIONS[session_id] = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "id_token": tokens.get("id_token"),
    }

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response

@app.get("/auth/me")
def me(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"authenticated": True}

@app.post("/auth/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")

    session = SESSIONS.pop(session_id, None) if session_id else None

    if session and session.get("refresh_token"):
        logout_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"

        async with httpx.AsyncClient() as client:
            await client.post(
                logout_url,
                data={
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": session["refresh_token"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    response = JSONResponse({"ok": True})
    response.delete_cookie("session_id", path="/")
    return response


@app.get("/testapp")
async def test_app(request: Request) :

    REALM = "rezepte"
    CLIENT_ID = "backend-web"
    USERNAME = "joergu"
    PASSWORD = "joergu"
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    async with httpx.AsyncClient() as client:
        data = {
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": USERNAME,
                "password": PASSWORD,
            }
        log.error(f"Testing Keycloak token endpoint at {token_url} with user '{USERNAME}'")
        log.error(f"data...{data}")
        res= await client.post(
            token_url,
            data=data,
        )

        return {
            "status_code": httpx.codes.OK,
            "response": f"{res.status_code} -> {res.text}",
        }

