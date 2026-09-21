import pytest
from test_user_management import auth_header, create_normal_user, login


async def create_recipe(client, token: str) -> dict:
    response = await client.post(
        "/recipes",
        headers=auth_header(token),
        json={
            "title": "Bewertetes Rezept",
            "group_ids": ["recipes"],
            "yield": {"amount": "2", "unit": "Portionen"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_recipe_rating_can_be_updated_and_lists_chronological_comments(client):
    admin_token = await login(client)
    recipe = await create_recipe(client, admin_token)
    await create_normal_user(
        client, admin_token, username="anna", email="anna@example.com"
    )
    anna_token = await login(client, "anna", "very-secret")

    first_rating = await client.put(
        f"/recipes/{recipe['id']}/rating",
        headers=auth_header(admin_token),
        json={"score": 5, "comment": "Spitzenrezept"},
    )
    assert first_rating.status_code == 200, first_rating.text

    second_rating = await client.put(
        f"/recipes/{recipe['id']}/rating",
        headers=auth_header(anna_token),
        json={"score": 3, "comment": "Gut, aber zu salzig"},
    )
    assert second_rating.status_code == 200, second_rating.text

    updated_rating = await client.put(
        f"/recipes/{recipe['id']}/rating",
        headers=auth_header(admin_token),
        json={"score": 4, "comment": "Auch aufgewärmt sehr gut"},
    )
    assert updated_rating.status_code == 200, updated_rating.text

    ratings = await client.get(
        f"/recipes/{recipe['id']}/ratings", headers=auth_header(admin_token)
    )
    assert ratings.status_code == 200, ratings.text
    data = ratings.json()
    assert data["rating_count"] == 2
    assert data["average_score"] == 3.5
    assert data["own_rating"]["score"] == 4
    assert [comment["username"] for comment in data["comments"]] == ["admin", "anna"]
    assert data["comments"][0]["comment"] == "Auch aufgewärmt sehr gut"

    invalid_rating = await client.put(
        f"/recipes/{recipe['id']}/rating",
        headers=auth_header(admin_token),
        json={"score": 6, "comment": "zu viele Punkte"},
    )
    assert invalid_rating.status_code == 422
