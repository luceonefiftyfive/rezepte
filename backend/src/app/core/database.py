from typing import Optional

from app.core.settings import settings
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

mongo_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> AsyncIOMotorClient:
    global mongo_client
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    return mongo_client


def get_db(request: Request) -> AsyncIOMotorDatabase:
    app_state = getattr(request.app, "state", None)
    db = getattr(app_state, "db", None)
    if db is not None:
        return db

    return get_mongo_client()[settings.mongodb_database]
