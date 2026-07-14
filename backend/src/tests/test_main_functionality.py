from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from botocore.exceptions import ClientError

from app.main import app, settings


class FakeS3Client:
    def __init__(self) -> None:
        self.head_bucket = Mock(return_value={})
        self.put_object = Mock(return_value={"ETag": "test-etag"})


@pytest.fixture(autouse=True)
def configure_app_state(db):
    app.state.db = db
    app.state.s3_client = FakeS3Client()
    yield
    if hasattr(app.state, "db"):
        del app.state.db
    if hasattr(app.state, "s3_client"):
        del app.state.s3_client


@pytest.mark.anyio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": settings.app_name,
        "status": "ok",
        "message": "FastAPI backend is reachable.",
        "python": "3.13",
        "package_manager": "uv",
    }


@pytest.mark.anyio
async def test_system_checks_reports_success(client):
    response = await client.get("/system/checks")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == {"ok": True}
    assert data["mongo_db"] == {"ok": True}
    assert data["s3"]["ok"] is True
    assert data["s3"]["bucket"] == settings.s3_bucket
    assert data["ok"] is True
    app.state.s3_client.head_bucket.assert_called_once_with(Bucket=settings.s3_bucket)


@pytest.mark.anyio
async def test_system_checks_reports_dependency_failures(client, monkeypatch):
    async def failed_command(*args, **kwargs):
        raise RuntimeError("mongo unavailable")

    monkeypatch.setattr(app.state.db, "command", failed_command)
    app.state.s3_client.head_bucket.side_effect = RuntimeError("s3 unavailable")

    response = await client.get("/system/checks")
    assert response.status_code == 200
    data = response.json()
    assert data["mongo_db"] == {"ok": False, "error": "mongo unavailable"}
    assert data["s3"]["ok"] is False
    assert data["s3"]["error"] == "s3 unavailable"
    assert data["ok"] is False


@pytest.mark.anyio
async def test_recipe_create_get_list_update_and_delete(client):
    payload = {
        "title": "Kartoffelsuppe",
        "description": "Ein Familienrezept",
        "group_ids": ["family"],
        "tags": ["vegetarisch", "Suppe"],
        "time": {
            "preparation_minutes": 20,
            "cooking_minutes": 40,
            "resting_minutes": 0,
        },
        "yield": {"amount": "4", "unit": "Portionen"},
        "ingredient_sections": [
            {
                "id": "main",
                "name": "Für die Suppe",
                "ingredients": [
                    {
                        "name": "Kartoffeln",
                        "amount": "1000",
                        "unit": "g",
                        "preparation": "geschält und gewürfelt",
                        "optional": False,
                        "scaling": "linear",
                    },
                    {
                        "name": "Salz",
                        "amount": None,
                        "unit": "as_needed",
                        "remarks": "nach Geschmack",
                        "optional": False,
                        "scaling": "manual",
                    },
                ],
            }
        ],
        "instructions": [
            {"id": "step-1", "text": "Gemüse vorbereiten."},
            {"id": "step-2", "text": "Alles 30 Minuten kochen."},
        ],
        "remarks": "Am nächsten Tag besonders gut.",
    }

    created_response = await client.post("/recipes", json=payload)
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["title"] == "Kartoffelsuppe"
    assert created["yield"] == {"amount": "4", "unit": "Portionen"}
    assert len(created["ingredient_sections"][0]["ingredients"]) == 2
    assert created["instructions"][1]["text"].startswith("Alles")
    assert created["version"] == 1

    get_response = await client.get(f"/recipes/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created

    list_response = await client.get("/recipes")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    update_response = await client.put(
        f"/recipes/{created['id']}",
        json={
            "title": "Cremige Kartoffelsuppe",
            "instructions": created["instructions"]
            + [{"id": "step-3", "text": "Suppe pürieren."}],
            "version": 1,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Cremige Kartoffelsuppe"
    assert len(updated["instructions"]) == 3
    assert updated["version"] == 2

    conflict = await client.put(
        f"/recipes/{created['id']}",
        json={"title": "Veraltete Änderung", "version": 1},
    )
    assert conflict.status_code == 409

    deleted = await client.delete(f"/recipes/{created['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "deleted_id": created["id"]}
    assert (await client.get(f"/recipes/{created['id']}")).status_code == 404


@pytest.mark.anyio
async def test_recipe_validation(client):
    base = {
        "title": "Test",
        "yield": {"amount": "2", "unit": "Portionen"},
        "ingredient_sections": [],
        "instructions": [],
    }

    empty_title = await client.post("/recipes", json=base | {"title": ""})
    assert empty_title.status_code == 422

    missing_custom_unit = await client.post(
        "/recipes",
        json=base
        | {
            "ingredient_sections": [
                {
                    "id": "main",
                    "ingredients": [{"name": "Dose Bohnen", "unit": "custom"}],
                }
            ]
        },
    )
    assert missing_custom_unit.status_code == 422

    duplicate_steps = await client.post(
        "/recipes",
        json=base
        | {
            "instructions": [
                {"id": "same", "text": "Erster Schritt"},
                {"id": "same", "text": "Zweiter Schritt"},
            ]
        },
    )
    assert duplicate_steps.status_code == 422


@pytest.mark.anyio
async def test_image_upload_success(client):
    response = await client.post(
        "/images/test-upload",
        files={"file": ("dish.png", b"png-content", "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["bucket"] == settings.s3_bucket
    assert data["key"].startswith("test-uploads/")
    assert data["key"].endswith("-dish.png")
    assert data["size"] == len(b"png-content")
    assert data["content_type"] == "image/png"
    app.state.s3_client.put_object.assert_called_once()
    call = app.state.s3_client.put_object.call_args.kwargs
    assert call["Bucket"] == settings.s3_bucket
    assert call["Body"] == b"png-content"
    assert call["ContentType"] == "image/png"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "content", "content_type", "status_code", "detail"),
    [
        ("notes.txt", b"text", "text/plain", 400, "Only image files are allowed"),
        ("empty.png", b"", "image/png", 400, "Uploaded file is empty"),
        (
            "large.png",
            b"x" * (25 * 1024 * 1024 + 1),
            "image/png",
            413,
            "Image is larger than 25 MB",
        ),
    ],
)
async def test_image_upload_validation(
    client, filename, content, content_type, status_code, detail
):
    response = await client.post(
        "/images/test-upload", files={"file": (filename, content, content_type)}
    )
    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    app.state.s3_client.put_object.assert_not_called()


@pytest.mark.anyio
async def test_image_upload_maps_s3_client_error_to_http_500(client):
    app.state.s3_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "upload failed"}},
        "PutObject",
    )
    response = await client.post(
        "/images/test-upload",
        files={"file": ("dish.jpg", b"jpeg-content", "image/jpeg")},
    )
    assert response.status_code == 500
    assert "upload failed" in response.json()["detail"]
