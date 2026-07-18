import pytest
from httpx2 import AsyncClient


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str) -> str:
    response = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_user(
    client: AsyncClient,
    token: str,
    *,
    username: str,
    email: str,
    groups: list[dict[str, str]],
) -> dict:
    response = await client.post(
        "/users",
        headers=auth_header(token),
        json={
            "username": username,
            "password": "very-secret",
            "first_name": username.capitalize(),
            "last_name": "Tester",
            "email": email,
            "groups": groups,
            "is_super_admin": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_group(
    client: AsyncClient, token: str, group_id: str, name: str
) -> dict:
    response = await client.post(
        "/groups",
        headers=auth_header(token),
        json={"id": group_id, "name": name, "description": None},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_recipe(
    client: AsyncClient,
    token: str,
    *,
    title: str,
    group_ids: list[str],
) -> dict:
    payload = {
        "title": title,
        "description": None,
        "group_ids": group_ids,
        "tags": [],
        "time": {
            "preparation_minutes": 10,
            "cooking_minutes": 20,
            "resting_minutes": 0,
        },
        "yield": {"amount": "2", "unit": "Portionen"},
        "ingredient_sections": [
            {
                "id": "main",
                "name": "Basis",
                "ingredients": [
                    {
                        "name": "Zutat",
                        "amount": "1",
                        "unit": "piece",
                        "optional": False,
                        "scaling": "linear",
                    }
                ],
            }
        ],
        "instructions": [{"id": "step-1", "text": "Mischen."}],
        "remarks": None,
    }
    response = await client.post("/recipes", headers=auth_header(token), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_super_admin_group_crud_and_delete_cleanup(client):
    admin_token = await login(client, "admin", "admin-password")

    created = await create_group(client, admin_token, "book-1", "Buch 1")
    assert created["id"] == "book-1"

    updated = await client.put(
        "/groups/book-1",
        headers=auth_header(admin_token),
        json={"name": "Buch Eins", "description": "Familienbuch"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Buch Eins"

    await create_group(client, admin_token, "book-2", "Buch 2")

    user = await create_user(
        client,
        admin_token,
        username="editor",
        email="editor@example.com",
        groups=[
            {"group_id": "book-1", "role": "author"},
            {"group_id": "book-2", "role": "reader"},
        ],
    )

    await create_recipe(client, admin_token, title="R1", group_ids=["book-1"])
    recipe_mixed = await create_recipe(
        client,
        admin_token,
        title="R2",
        group_ids=["book-1", "book-2"],
    )

    delete = await client.delete("/groups/book-1", headers=auth_header(admin_token))
    assert delete.status_code == 200
    body = delete.json()
    assert body["users_updated"] >= 1
    assert body["recipes_updated"] >= 1
    assert body["recipes_deleted"] == 1

    recipes = await client.get("/recipes", headers=auth_header(admin_token))
    assert recipes.status_code == 200
    assert [recipe["id"] for recipe in recipes.json()] == [recipe_mixed["id"]]
    assert recipes.json()[0]["group_ids"] == ["book-2"]

    user_after = await client.get(
        f"/users/{user['id']}", headers=auth_header(admin_token)
    )
    assert user_after.status_code == 200
    assert user_after.json()["groups"] == [{"group_id": "book-2", "role": "reader"}]


@pytest.mark.anyio
async def test_only_super_admin_can_manage_groups(client):
    admin_token = await login(client, "admin", "admin-password")
    await create_group(client, admin_token, "book-a", "Buch A")

    await create_user(
        client,
        admin_token,
        username="groupadmin",
        email="groupadmin@example.com",
        groups=[{"group_id": "book-a", "role": "admin"}],
    )

    group_admin_token = await login(client, "groupadmin", "very-secret")

    list_groups = await client.get("/groups", headers=auth_header(group_admin_token))
    assert list_groups.status_code == 200
    assert [group["id"] for group in list_groups.json()] == ["book-a"]

    create = await client.post(
        "/groups",
        headers=auth_header(group_admin_token),
        json={"id": "book-b", "name": "Buch B", "description": None},
    )
    assert create.status_code == 403

    update = await client.put(
        "/groups/book-a",
        headers=auth_header(group_admin_token),
        json={"name": "Neu"},
    )
    assert update.status_code == 403

    delete = await client.delete(
        "/groups/book-a", headers=auth_header(group_admin_token)
    )
    assert delete.status_code == 403


@pytest.mark.anyio
async def test_recipe_visibility_and_group_selection_by_permissions(client):
    admin_token = await login(client, "admin", "admin-password")
    await create_group(client, admin_token, "g1", "Gruppe 1")
    await create_group(client, admin_token, "g2", "Gruppe 2")

    await create_user(
        client,
        admin_token,
        username="usera",
        email="usera@example.com",
        groups=[{"group_id": "g1", "role": "author"}],
    )
    await create_user(
        client,
        admin_token,
        username="userb",
        email="userb@example.com",
        groups=[
            {"group_id": "g1", "role": "author"},
            {"group_id": "g2", "role": "author"},
        ],
    )

    token_a = await login(client, "usera", "very-secret")
    token_b = await login(client, "userb", "very-secret")

    recipe_g1 = await create_recipe(client, token_b, title="Nur G1", group_ids=["g1"])
    recipe_g2 = await create_recipe(client, token_b, title="Nur G2", group_ids=["g2"])

    list_a = await client.get("/recipes", headers=auth_header(token_a))
    assert list_a.status_code == 200
    assert [recipe["id"] for recipe in list_a.json()] == [recipe_g1["id"]]

    invalid_filter = await client.get(
        "/recipes?group_ids=g2",
        headers=auth_header(token_a),
    )
    assert invalid_filter.status_code == 403

    filter_b = await client.get("/recipes?group_ids=g2", headers=auth_header(token_b))
    assert filter_b.status_code == 200
    assert [recipe["id"] for recipe in filter_b.json()] == [recipe_g2["id"]]

    no_groups = await client.post(
        "/recipes",
        headers=auth_header(token_a),
        json={
            "title": "Fehlt",
            "description": None,
            "group_ids": [],
            "tags": [],
            "time": {
                "preparation_minutes": 1,
                "cooking_minutes": 1,
                "resting_minutes": 0,
            },
            "yield": {"amount": "1", "unit": "Portion"},
            "ingredient_sections": [],
            "instructions": [{"id": "s1", "text": "x"}],
            "remarks": None,
        },
    )
    assert no_groups.status_code == 422

    forbidden_group = await client.post(
        "/recipes",
        headers=auth_header(token_a),
        json={
            "title": "Unzulaessig",
            "description": None,
            "group_ids": ["g2"],
            "tags": [],
            "time": {
                "preparation_minutes": 1,
                "cooking_minutes": 1,
                "resting_minutes": 0,
            },
            "yield": {"amount": "1", "unit": "Portion"},
            "ingredient_sections": [],
            "instructions": [{"id": "s1", "text": "x"}],
            "remarks": None,
        },
    )
    assert forbidden_group.status_code == 403

    manageable_a = await client.get(
        "/groups?manageable_only=true",
        headers=auth_header(token_a),
    )
    assert manageable_a.status_code == 200
    assert [group["id"] for group in manageable_a.json()] == ["g1"]

    manageable_b = await client.get(
        "/groups?manageable_only=true",
        headers=auth_header(token_b),
    )
    assert manageable_b.status_code == 200
    assert [group["id"] for group in manageable_b.json()] == ["g1", "g2"]
