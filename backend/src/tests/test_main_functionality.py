import io
import zipfile
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from app import main as main_module
from app.main import app, settings
from botocore.exceptions import ClientError


class _FakeS3Body:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class FakeS3Client:
    def __init__(self) -> None:
        self.head_bucket = Mock(return_value={})
        self.objects: dict[str, dict[str, object]] = {}
        self.put_object = Mock(side_effect=self._put_object)
        self.get_object = Mock(side_effect=self._get_object)

    def _put_object(self, *, Bucket, Key, Body, ContentType):
        self.objects[Key] = {"Body": Body, "ContentType": ContentType, "Bucket": Bucket}
        return {"ETag": "test-etag"}

    def _get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}
            raise ClientError(error_response, "GetObject")
        stored = self.objects[Key]
        return {
            "Body": _FakeS3Body(stored["Body"]),
            "ContentType": stored["ContentType"],
        }


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
async def test_system_version_returns_configured_values(client, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_system_version",
        lambda: {"version": "1.2.3", "git_hash": "abc1234"},
    )

    response = await client.get("/system/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.2.3", "git_hash": "abc1234"}


@pytest.mark.anyio
async def test_read_git_hash_prefers_env(monkeypatch):
    monkeypatch.setenv("REZEPTE_GIT_HASH", "from-env-hash")
    assert main_module._read_git_hash() == "from-env-hash"


@pytest.mark.anyio
async def test_recipe_create_get_list_update_and_delete(client):
    admin_token = await _login_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}
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

    created_response = await client.post("/recipes", json=payload, headers=headers)
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["title"] == "Kartoffelsuppe"
    assert created["yield"] == {"amount": "4", "unit": "Portionen"}
    assert len(created["ingredient_sections"][0]["ingredients"]) == 2
    assert created["instructions"][1]["text"].startswith("Alles")
    assert created["version"] == 1

    get_response = await client.get(f"/recipes/{created['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json() == created

    list_response = await client.get("/recipes", headers=headers)
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
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Cremige Kartoffelsuppe"
    assert len(updated["instructions"]) == 3
    assert updated["version"] == 2

    conflict = await client.put(
        f"/recipes/{created['id']}",
        json={"title": "Veraltete Änderung", "version": 1},
        headers=headers,
    )
    assert conflict.status_code == 409

    deleted = await client.delete(f"/recipes/{created['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "deleted_id": created["id"]}
    assert (
        await client.get(f"/recipes/{created['id']}", headers=headers)
    ).status_code == 404


@pytest.mark.anyio
async def test_recipe_list_supports_title_and_creation_sorting(client):
    admin_token = await _login_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    early_response = await client.post(
        "/recipes",
        json={
            "title": "Zwiebelkuchen",
            "group_ids": ["family"],
            "yield": {"amount": "1", "unit": "Blech"},
            "ingredient_sections": [],
            "instructions": [],
        },
        headers=headers,
    )
    assert early_response.status_code == 201

    later_response = await client.post(
        "/recipes",
        json={
            "title": "Apfelmus",
            "group_ids": ["family"],
            "yield": {"amount": "2", "unit": "Gläser"},
            "ingredient_sections": [],
            "instructions": [],
        },
        headers=headers,
    )
    assert later_response.status_code == 201

    created_sorted = await client.get("/recipes?sort=created_desc", headers=headers)
    assert created_sorted.status_code == 200
    assert [item["title"] for item in created_sorted.json()][:2] == [
        "Apfelmus",
        "Zwiebelkuchen",
    ]

    title_sorted = await client.get("/recipes?sort=title_asc", headers=headers)
    assert title_sorted.status_code == 200
    assert [item["title"] for item in title_sorted.json()][:2] == [
        "Apfelmus",
        "Zwiebelkuchen",
    ]


@pytest.mark.anyio
async def test_recipe_validation(client):
    admin_token = await _login_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}
    base = {
        "title": "Test",
        "yield": {"amount": "2", "unit": "Portionen"},
        "group_ids": ["recipes"],
        "ingredient_sections": [],
        "instructions": [],
    }

    empty_title = await client.post(
        "/recipes", json=base | {"title": ""}, headers=headers
    )
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
        headers=headers,
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
        headers=headers,
    )
    assert duplicate_steps.status_code == 422


async def _login_token(client, username="admin", password="admin-password") -> str:
    response = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.anyio
async def test_recipe_admin_export_import_and_purge(client):
    admin_token = await _login_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    cover_key = "recipes/export-test/cover.jpg"
    step_key = "recipes/export-test/steps/step-1/detail.png"
    app.state.s3_client.put_object(
        Bucket=settings.s3_bucket,
        Key=cover_key,
        Body=b"cover-bytes",
        ContentType="image/jpeg",
    )
    app.state.s3_client.put_object(
        Bucket=settings.s3_bucket,
        Key=step_key,
        Body=b"step-bytes",
        ContentType="image/png",
    )

    payload = {
        "title": "Kartoffelsuppe",
        "description": "Ein Familienrezept",
        "group_ids": ["family"],
        "tags": ["Suppe"],
        "time": {
            "preparation_minutes": 20,
            "cooking_minutes": 40,
            "resting_minutes": 0,
        },
        "yield": {"amount": "4", "unit": "Portionen"},
        "recipe_image_key": cover_key,
        "ingredient_sections": [
            {
                "id": "main",
                "name": "Für die Suppe",
                "ingredients": [
                    {
                        "name": "Kartoffeln",
                        "amount": "1000",
                        "unit": "g",
                        "optional": False,
                        "scaling": "linear",
                    }
                ],
            }
        ],
        "instructions": [
            {"id": "step-1", "text": "Alles kochen.", "image_key": step_key}
        ],
        "remarks": None,
    }

    created = await client.post("/recipes", json=payload, headers=headers)
    assert created.status_code == 201

    yaml_export = await client.get(
        "/recipes/admin/export?format=yaml&group_id=family",
        headers=headers,
    )
    assert yaml_export.status_code == 200
    assert "recipes:" in yaml_export.text
    assert "Kartoffelsuppe" in yaml_export.text
    assert "images:" in yaml_export.text
    assert cover_key in yaml_export.text
    assert step_key in yaml_export.text

    app.state.s3_client.objects.clear()

    purge_group = await client.delete(
        "/recipes/admin/purge?group_id=family",
        headers=headers,
    )
    assert purge_group.status_code == 200
    assert purge_group.json()["deleted_count"] == 1

    preview_yaml = await client.post(
        "/recipes/admin/import/preview",
        headers=headers,
        json={"format": "yaml", "content": yaml_export.text},
    )
    assert preview_yaml.status_code == 200
    assert preview_yaml.json() == {
        "imported": 1,
        "would_create": 1,
        "would_update": 0,
    }

    import_yaml = await client.post(
        "/recipes/admin/import",
        headers=headers,
        json={"format": "yaml", "content": yaml_export.text},
    )
    assert import_yaml.status_code == 200
    assert import_yaml.json()["imported"] == 1
    assert cover_key in app.state.s3_client.objects
    assert step_key in app.state.s3_client.objects

    zip_export = await client.get(
        "/recipes/admin/export?format=zip&group_id=family",
        headers=headers,
    )
    assert zip_export.status_code == 200
    assert zip_export.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(zip_export.content)) as archive:
        manifest = archive.read("manifest.yaml").decode("utf-8")
        assert "recipes:" in manifest
        assert archive.read(f"images/{cover_key}") == b"cover-bytes"
        assert archive.read(f"images/{step_key}") == b"step-bytes"

    app.state.s3_client.objects.clear()

    preview_zip = await client.post(
        "/recipes/admin/import/preview",
        headers=headers,
        files={
            "format": (None, "zip"),
            "archive": ("rezepte-export.zip", zip_export.content, "application/zip"),
        },
    )
    assert preview_zip.status_code == 200
    assert preview_zip.json() == {
        "imported": 1,
        "would_create": 0,
        "would_update": 1,
    }

    import_zip = await client.post(
        "/recipes/admin/import",
        headers=headers,
        files={
            "format": (None, "zip"),
            "archive": ("rezepte-export.zip", zip_export.content, "application/zip"),
        },
    )
    assert import_zip.status_code == 200
    assert import_zip.json()["imported"] == 1
    assert cover_key in app.state.s3_client.objects
    assert step_key in app.state.s3_client.objects

    markdown_export = await client.get(
        "/recipes/admin/export?format=markdown",
        headers=headers,
    )
    assert markdown_export.status_code == 200
    assert markdown_export.text.startswith("# Rezepte Export")

    purge_all = await client.delete("/recipes/admin/purge", headers=headers)
    assert purge_all.status_code == 200
    assert purge_all.json()["deleted_count"] == 1

    preview_markdown = await client.post(
        "/recipes/admin/import/preview",
        headers=headers,
        json={"format": "markdown", "content": markdown_export.text},
    )
    assert preview_markdown.status_code == 200
    assert preview_markdown.json() == {
        "imported": 1,
        "would_create": 1,
        "would_update": 0,
    }

    import_markdown = await client.post(
        "/recipes/admin/import",
        headers=headers,
        json={"format": "markdown", "content": markdown_export.text},
    )
    assert import_markdown.status_code == 200
    assert import_markdown.json()["imported"] == 1

    listed = await client.get("/recipes", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.anyio
async def test_non_admin_cannot_use_recipe_admin_tools(client):
    admin_token = await _login_token(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_user = await client.post(
        "/users",
        headers=admin_headers,
        json={
            "username": "reader",
            "password": "very-secret",
            "first_name": "Read",
            "last_name": "Only",
            "email": "reader@example.com",
            "groups": [{"group_id": "recipes", "role": "reader"}],
            "is_super_admin": False,
        },
    )
    assert create_user.status_code == 201

    reader_token = await _login_token(client, username="reader", password="very-secret")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    export_response = await client.get("/recipes/admin/export", headers=reader_headers)
    assert export_response.status_code == 403

    purge_response = await client.delete("/recipes/admin/purge", headers=reader_headers)
    assert purge_response.status_code == 403

    import_response = await client.post(
        "/recipes/admin/import",
        headers=reader_headers,
        json={"format": "yaml", "content": "recipes: []"},
    )
    assert import_response.status_code == 403

    preview_response = await client.post(
        "/recipes/admin/import/preview",
        headers=reader_headers,
        json={"format": "yaml", "content": "recipes: []"},
    )
    assert preview_response.status_code == 403


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


@pytest.mark.anyio
async def test_recipe_scoped_image_upload_and_view_url(client):
    admin_token = await _login_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_payload = {
        "title": "Bildtest",
        "description": None,
        "group_ids": ["recipes"],
        "tags": [],
        "time": {
            "preparation_minutes": 1,
            "cooking_minutes": 2,
            "resting_minutes": 3,
        },
        "yield": {"amount": "2", "unit": "Portionen"},
        "ingredient_sections": [],
        "instructions": [{"id": "step-1", "text": "Teig kneten."}],
        "remarks": None,
    }
    created = await client.post("/recipes", json=create_payload, headers=headers)
    assert created.status_code == 201
    recipe = created.json()

    upload_cover = await client.post(
        f"/recipes/{recipe['id']}/images/upload",
        files={"file": ("cover.jpg", b"jpeg-content", "image/jpeg")},
        headers=headers,
    )
    assert upload_cover.status_code == 200
    cover = upload_cover.json()
    assert cover["key"].startswith(f"recipes/{recipe['id']}/cover/")
    assert "view_url" in cover
    assert cover["view_url"].startswith(f"{settings.app_base_url}/api/recipes/images/")
    assert "minio:9000" not in cover["view_url"]

    upload_step = await client.post(
        f"/recipes/{recipe['id']}/instructions/step-1/image/upload",
        files={"file": ("step.jpg", b"jpeg-content", "image/jpeg")},
        headers=headers,
    )
    assert upload_step.status_code == 200
    step = upload_step.json()
    assert step["key"].startswith(f"recipes/{recipe['id']}/steps/step-1/")
    assert "view_url" in step
    assert step["view_url"].startswith(f"{settings.app_base_url}/api/recipes/images/")
    assert "minio:9000" not in step["view_url"]

    update = await client.put(
        f"/recipes/{recipe['id']}",
        json={
            "recipe_image_key": cover["key"],
            "instructions": [
                {"id": "step-1", "text": "Teig kneten.", "image_key": step["key"]}
            ],
            "version": recipe["version"],
        },
        headers=headers,
    )
    assert update.status_code == 200

    cover_url = await client.get(f"/recipes/{recipe['id']}/image-url", headers=headers)
    assert cover_url.status_code == 200
    assert cover_url.json()["key"] == cover["key"]
    assert cover_url.json()["view_url"] == cover["view_url"]

    streamed_cover = await client.get(
        urlsplit(cover["view_url"]).path.removeprefix("/api")
    )
    assert streamed_cover.status_code == 200
    assert streamed_cover.headers["content-type"] == "image/jpeg"
    assert streamed_cover.content == b"jpeg-content"

    step_url = await client.get(
        f"/recipes/{recipe['id']}/instructions/step-1/image-url",
        headers=headers,
    )
    assert step_url.status_code == 200
    assert step_url.json()["key"] == step["key"]
    assert step_url.json()["view_url"] == step["view_url"]
