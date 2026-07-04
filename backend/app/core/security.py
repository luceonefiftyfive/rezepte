import hashlib
import os
from datetime import datetime, timedelta, timezone

from app.core.settings import settings
from jose import jwt


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA256 (built-in, no external dependencies)"""
    salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"pbkdf2_sha256${100000}${salt.hex()}${pwd_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        algorithm, iterations, salt_hex, hash_hex = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)

        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return pwd_hash == stored_hash
    except (ValueError, AttributeError):
        return False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str) -> str:
    expires_at = now_utc() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
