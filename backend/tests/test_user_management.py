import pytest
from httpx import AsyncClient


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def login(
    client: AsyncClient, username="admin", password="admin-password"
) -> str:
    response = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_normal_user(
    client: AsyncClient, token: str, username="jdoe", email="john@example.com"
) -> dict:
    response = await client.post(
        "/users",
        headers=auth_header(token),
        json={
            "username": username,
            "password": "very-secret",
            "first_name": "John",
            "last_name": "Doe",
            "email": email,
            "groups": [{"group_id": "recipes", "role": "reader"}],
            "is_super_admin": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_login_and_me(client):
    token = await login(client)
    response = await client.get("/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["is_super_admin"] is True


@pytest.mark.anyio
async def test_test_access_is_protected(client):
    response = await client.get("/test-access")
    assert response.status_code == 401
    token = await login(client)
    response = await client.get("/test-access", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["message"] == "You are authenticated"


@pytest.mark.anyio
async def test_create_user(client):
    token = await login(client)
    user = await create_normal_user(client, token)
    assert user["username"] == "jdoe"
    assert user["email_verified"] is False
    assert user["groups"][0]["role"] == "reader"
    assert "password_hash" not in user


@pytest.mark.anyio
async def test_list_and_get_users(client):
    token = await login(client)
    user = await create_normal_user(client, token)
    response = await client.get("/users", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 2
    response = await client.get(f"/users/{user['id']}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["username"] == "jdoe"


@pytest.mark.anyio
async def test_update_own_profile(client):
    token = await login(client)
    response = await client.patch(
        "/users/me",
        headers=auth_header(token),
        json={
            "first_name": "Admin",
            "last_name": "Changed",
            "email": "new-admin@example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Admin"
    assert data["last_name"] == "Changed"
    assert data["email"] == "new-admin@example.com"
    assert data["email_verified"] is False


@pytest.mark.anyio
async def test_update_user_groups(client):
    token = await login(client)
    user = await create_normal_user(client, token)
    response = await client.patch(
        f"/users/{user['id']}/groups",
        headers=auth_header(token),
        json={
            "groups": [
                {"group_id": "recipes", "role": "admin"},
                {"group_id": "family", "role": "author"},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["groups"][0]["role"] == "admin"
    assert response.json()["groups"][1]["role"] == "author"


@pytest.mark.anyio
async def test_set_super_admin(client):
    token = await login(client)
    user = await create_normal_user(client, token)
    response = await client.patch(
        f"/users/{user['id']}/super-admin",
        headers=auth_header(token),
        json={"is_super_admin": True},
    )
    assert response.status_code == 200
    assert response.json()["is_super_admin"] is True


@pytest.mark.anyio
async def test_delete_user_soft_delete(client):
    token = await login(client)
    user = await create_normal_user(client, token)
    response = await client.delete(f"/users/{user['id']}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.anyio
async def test_check_username_and_email(client):
    response = await client.get("/users/check-username/admin")
    assert response.status_code == 200
    assert response.json()["available"] is False
    response = await client.get("/users/check-email/free@example.com")
    assert response.status_code == 200
    assert response.json()["available"] is True


@pytest.mark.anyio
async def test_non_admin_cannot_list_users(client):
    admin_token = await login(client)
    await create_normal_user(client, admin_token)
    user_token = await login(client, username="jdoe", password="very-secret")
    response = await client.get("/users", headers=auth_header(user_token))
    assert response.status_code == 403


@pytest.mark.anyio
async def test_super_admin_access(client):
    token = await login(client)
    response = await client.get("/test-super-admin-access", headers=auth_header(token))
    assert response.status_code == 200


@pytest.mark.anyio
async def test_admin_access(client):
    token = await login(client)
    response = await client.get("/test-admin-access", headers=auth_header(token))
    assert response.status_code == 200
