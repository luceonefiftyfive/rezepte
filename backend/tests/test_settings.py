from app.core.settings import Settings


def test_settings_accepts_mongodb_uri_env_var(monkeypatch):
    monkeypatch.setenv(
        "MONGODB_URI",
        "mongodb://rezepte:secret@mongodb:27017/rezepte?authSource=admin",
    )
    monkeypatch.delenv("MONGODB_URL", raising=False)

    settings = Settings()

    assert (
        settings.mongodb_url
        == "mongodb://rezepte:secret@mongodb:27017/rezepte?authSource=admin"
    )
