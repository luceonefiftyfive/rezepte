from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, TypeVar, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument

DocumentT = TypeVar("DocumentT", bound=dict[str, Any])


class MongoRepository(Generic[DocumentT]):
    """Generic asynchronous MongoDB repository for document collections.

    Domain repositories inherit from this class and add entity-specific indexes
    and queries. Public string IDs are converted to MongoDB ObjectIds here so
    services do not need to repeat validation and conversion logic.
    """

    collection_name: str

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str | None = None):
        resolved_name = collection_name or getattr(self, "collection_name", None)
        if not resolved_name:
            raise ValueError("A MongoDB collection name must be configured")
        self.collection: AsyncIOMotorCollection = db[resolved_name]

    @staticmethod
    def to_object_id(value: str | ObjectId) -> ObjectId | None:
        if isinstance(value, ObjectId):
            return value
        if not ObjectId.is_valid(value):
            return None
        return ObjectId(value)

    async def find_by_id(self, entity_id: str | ObjectId) -> DocumentT | None:
        object_id = self.to_object_id(entity_id)
        if object_id is None:
            return None
        document = await self.collection.find_one({"_id": object_id})
        return cast(DocumentT | None, document)

    async def find_one(self, query: Mapping[str, Any]) -> DocumentT | None:
        document = await self.collection.find_one(dict(query))
        return cast(DocumentT | None, document)

    async def exists(self, query: Mapping[str, Any]) -> bool:
        return await self.collection.count_documents(dict(query), limit=1) > 0

    async def count(self, query: Mapping[str, Any] | None = None) -> int:
        return await self.collection.count_documents(dict(query or {}))

    async def insert(self, document: DocumentT) -> DocumentT:
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        if created is None:
            raise RuntimeError("Inserted document could not be retrieved")
        return cast(DocumentT, created)

    async def list(
        self,
        query: Mapping[str, Any] | None = None,
        *,
        skip: int = 0,
        limit: int | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[DocumentT]:
        if skip < 0:
            raise ValueError("skip must not be negative")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than zero")

        cursor = self.collection.find(dict(query or {}))
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)

        documents = await cursor.to_list(length=limit)
        return cast(list[DocumentT], documents)

    async def update_by_id(
        self,
        entity_id: str | ObjectId,
        update: Mapping[str, Any],
    ) -> DocumentT | None:
        object_id = self.to_object_id(entity_id)
        if object_id is None:
            return None
        return await self.update_one({"_id": object_id}, update)

    async def update_one(
        self,
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> DocumentT | None:
        if not update:
            return await self.find_one(query)

        document = await self.collection.find_one_and_update(
            dict(query),
            {"$set": dict(update)},
            return_document=ReturnDocument.AFTER,
        )
        return cast(DocumentT | None, document)

    async def delete_by_id(self, entity_id: str | ObjectId) -> bool:
        object_id = self.to_object_id(entity_id)
        if object_id is None:
            return False
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1
