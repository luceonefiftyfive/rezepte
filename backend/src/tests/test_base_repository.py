import pytest
from bson import ObjectId

from app.repositories.base_repository import MongoRepository


class SampleRepository(MongoRepository[dict]):
    collection_name = "test_entities"


@pytest.mark.anyio
async def test_generic_repository_crud(db):
    repository = SampleRepository(db)

    created = await repository.insert({"name": "First", "active": True})
    assert isinstance(created["_id"], ObjectId)

    found = await repository.find_by_id(str(created["_id"]))
    assert found is not None
    assert found["name"] == "First"

    updated = await repository.update_by_id(created["_id"], {"name": "Updated"})
    assert updated is not None
    assert updated["name"] == "Updated"

    assert await repository.exists({"active": True}) is True
    assert await repository.count({"active": True}) == 1

    deleted = await repository.delete_by_id(str(created["_id"]))
    assert deleted is True
    assert await repository.find_by_id(created["_id"]) is None


@pytest.mark.anyio
async def test_generic_repository_list_pagination_and_sort(db):
    repository = SampleRepository(db)
    await repository.insert({"name": "B"})
    await repository.insert({"name": "A"})
    await repository.insert({"name": "C"})

    documents = await repository.list(skip=1, limit=1, sort=[("name", 1)])
    assert [document["name"] for document in documents] == ["B"]


@pytest.mark.anyio
async def test_generic_repository_rejects_invalid_public_id(db):
    repository = SampleRepository(db)

    assert await repository.find_by_id("not-an-object-id") is None
    assert await repository.update_by_id("not-an-object-id", {"name": "X"}) is None
    assert await repository.delete_by_id("not-an-object-id") is False
