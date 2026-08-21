
from app.core.settings import settings
from litestar.datastructures import State
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global mongo_client
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    return mongo_client


def get_db(state: State) -> AsyncIOMotorDatabase:
    db = getattr(state, "db", None)
    if db is not None:
        return db

    return get_mongo_client()[settings.mongodb_database]
