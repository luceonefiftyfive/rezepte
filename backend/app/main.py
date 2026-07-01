import asyncio
import logging
import typing as ty
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

log = logging.getLogger(__name__)

SESSIONS = {}


class User(BaseModel):
    username: str
    email: str | None = None
    first_name: str
    last_name: str


class Login(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Hash:
    def bcrypt(password: str):
        return pwd_context.hash(password)

    def verify(password: str, hashed_password: str):
        return pwd_context.verify(password, hashed_password)


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
    mongodb_recipe_database: str = Field(
        default="rezepte", alias="MONGODB_RECIPES_DATABASE"
    )
    mongodb_user_database: str = Field(default="user", alias="MONGODB_USER_DATABASE")

    s3_endpoint_url: str = Field(default="http://minio:9000", alias="S3_ENDPOINT_URL")
    s3_bucket: str = Field(default="familienrezepte-images", alias="S3_BUCKET")
    s3_access_key: str = Field(default="rezepte-minio", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(
        default="change-me-minio-password", alias="S3_SECRET_KEY"
    )

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
    app.state.recipes_db = app.state.mongo_client[settings.mongodb_recipes_database]
    app.state.user_db = app.state.mongo_client[settings.mongodb_user_database]
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
        "mongo_recipes_db": {"ok": False},
        "mongo_user_db": {"ok": False},
        "s3": {"ok": False},
    }

    try:
        await app.state.recipes_db.command("ping")
        checks["mongo_recipes_db"] = {"ok": True}
    except PyMongoError as exc:
        checks["mongo_recipes_db"] = {"ok": False, "error": str(exc)}
    except Exception as exc:
        checks["mongo_recipes_db"] = {"ok": False, "error": str(exc)}

    try:
        await app.state.user_db.command("ping")
        checks["mongo_user_db"] = {"ok": True}
    except PyMongoError as exc:
        checks["mongo_user_db"] = {"ok": False, "error": str(exc)}
    except Exception as exc:
        checks["mongo_user_db"] = {"ok": False, "error": str(exc)}

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
        for name in ["api", "mongo_recipes_db", "mongo_user_db", "s3"]
    )

    return checks


@app.get("/recipes", response_model=list[RecipeOut])
async def list_recipes() -> list[RecipeOut]:
    cursor = (
        app.state.recipes_db.recipes.find({}, {"_id": 0})
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
async def delete_recipe(recipe_id: str) -> dict[str, ty.Any]:
    result = await app.state.recipes_db.recipes.delete_one({"id": recipe_id})

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


@app.post("/register")
def create_user(user: User):
    hashed_pass = Hash.bcrypt(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_pass
    user_id = app.state.user_db.insert_one(user_dict).inserted_id
    return {"result": "User created", "user_id": str(user_id)}


@app.post("/login")
def login_user(login: OAuth2PasswordRequestForm = Depends()):
    user = app.state.user_db.users.find_one({"username": login.username})
