from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import os

# Read Keycloak settings from environment to avoid circular imports
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE")

security = HTTPBearer(auto_error=False)


class JWKSClient:
    def __init__(self, jwks_url: str, ttl: int = 300):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._jwks: Optional[Dict[str, Any]] = None
        self._expires_at = 0

    def get_jwks(self) -> Dict[str, Any]:
        now = time.time()
        if not self._jwks or now >= self._expires_at:
            r = requests.get(self.jwks_url, timeout=5)
            r.raise_for_status()
            self._jwks = r.json()
            self._expires_at = now + self.ttl

        return self._jwks


_jwks_client: Optional[JWKSClient] = None


def get_jwks_client() -> JWKSClient:
    global _jwks_client
    if _jwks_client is None:
        if not KEYCLOAK_JWKS_URL:
            raise RuntimeError("KEYCLOAK_JWKS_URL is not configured")
        _jwks_client = JWKSClient(KEYCLOAK_JWKS_URL)
    return _jwks_client


def verify_jwt_token(token: str) -> Dict[str, Any]:
    jwks = get_jwks_client().get_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    key = None
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") == kid:
            key = jwk
            break

    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token kid")

    algorithms = [key.get("alg", "RS256")]

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=KEYCLOAK_AUDIENCE or None,
            issuer=KEYCLOAK_ISSUER or None,
        )
    except Exception as exc:  # jose raises JWTError and others
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return payload


def get_token_credentials(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
    return credentials.credentials


def require_authenticated(token: str = Depends(get_token_credentials)) -> Dict[str, Any]:
    return verify_jwt_token(token)


def require_groups(*allowed_groups: str):
    def _dependency(payload: Dict[str, Any] = Depends(require_authenticated)) -> Dict[str, Any]:
        # Keycloak may put groups under `groups` claim or roles under `realm_access.roles`
        groups: List[str] = []
        if isinstance(payload.get("groups"), list):
            groups = payload.get("groups")
        elif isinstance(payload.get("realm_access"), dict):
            groups = payload.get("realm_access", {}).get("roles", [])

        # If user has no groups, that's acceptable per requirements ("no group")
        if not allowed_groups:
            return payload

        for g in allowed_groups:
            if g in groups:
                return payload

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient group membership")

    return _dependency
