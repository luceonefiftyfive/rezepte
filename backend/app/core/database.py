from app.core.settings import settings
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

mongo_client = AsyncIOMotorClient(settings.mongodb_url)


def get_db() -> AsyncIOMotorDatabase:
    return mongo_client[settings.mongodb_database]
