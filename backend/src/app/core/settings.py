import os

from pydantic import EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Rezepte API"
    mode: str = "development"
    app_base_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["*"]
    rezepte_test: bool = False

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "rezepte"

    @model_validator(mode="after")
    def _set_mongodb_url_from_uri(self):
        mongodb_uri = os.getenv("MONGODB_URI")
        if mongodb_uri:
            self.mongodb_url = mongodb_uri
        else:
            mongodb_url = os.getenv("MONGODB_URL")
            if mongodb_url and self.mongodb_url in ("", "mongodb://localhost:27017"):
                self.mongodb_url = mongodb_url
        return self

    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "UnbenetRezepte"
    webauthn_origin: str = "http://localhost:5173"
    webauthn_require_user_verification: bool = True

    superuser_username: str = "admin"
    superuser_password: str = "admin-password"
    superuser_email: EmailStr = "admin@example.com"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rezepte"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
