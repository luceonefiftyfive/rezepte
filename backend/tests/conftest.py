import pytest
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def db():
    client = AsyncMongoMockClient()
    test_db = client["test_rezepte"]
    await test_db.users.create_index("username", unique=True)
    await test_db.users.create_index("email", unique=True)
    await test_db.users.insert_one(
        {
            "username": "admin",
            "password_hash": hash_password("admin-password"),
            "first_name": "System",
            "last_name": "Administrator",
            "email": "admin@example.com",
            "email_verified": True,
            "groups": [],
            "is_super_admin": True,
            "is_active": True,
        }
    )
    return test_db


@pytest.fixture()
async def client(db):
    app.dependency_overrides[get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
