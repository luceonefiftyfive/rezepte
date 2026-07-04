from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Rezepte API"
    mode: str = "development"
    cors_origins: list[str] = ["*"]
    rezepte_test: bool = False

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "rezepte"

    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    superuser_username: str = "admin"
    superuser_password: str = "admin-password"
    superuser_email: EmailStr = "admin@example.com"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rezepte"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
