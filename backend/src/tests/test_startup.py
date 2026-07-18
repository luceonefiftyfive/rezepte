from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.main import lifespan
from fastapi import FastAPI


@pytest.mark.anyio
async def test_lifespan_bootstraps_superuser(monkeypatch):
    class FakeCollection:
        async def create_index(self, *args, **kwargs):
            return None

    class FakeDatabase:
        def __getitem__(self, name):
            return FakeCollection()

    class FakeMongoClient:
        def __init__(self, db):
            self.db = db

        def __getitem__(self, name):
            return self.db

        async def close(self):
            return None

    fake_db = FakeDatabase()
    fake_client = FakeMongoClient(fake_db)
    bootstrap_superuser = AsyncMock()

    monkeypatch.setattr("app.main.get_mongo_client", lambda: fake_client)
    monkeypatch.setattr("app.main.create_s3_client", lambda: object())
    monkeypatch.setattr(
        "app.main.UserService",
        lambda db: SimpleNamespace(bootstrap_superuser=bootstrap_superuser),
    )

    app = FastAPI()
    async with lifespan(app):
        assert app.state.db is fake_db
        bootstrap_superuser.assert_awaited_once()
