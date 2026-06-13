from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import os
import requests
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

# Read Keycloak settings from environment to avoid circular imports
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE")

# Optional values for login flow
KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")

security = HTTPBearer(auto_error=False)

router = APIRouter()


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


# --- Login / callback flow routes ---


def _auth_server_base() -> Optional[str]:
    if KEYCLOAK_BASE_URL and KEYCLOAK_REALM:
        return f"{KEYCLOAK_BASE_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}"
    return None


def _authorization_endpoint() -> Optional[str]:
    base = _auth_server_base()
    if base:
        return f"{base}/protocol/openid-connect/auth"
    return None


def _token_endpoint() -> Optional[str]:
    base = _auth_server_base()
    if base:
        return f"{base}/protocol/openid-connect/token"
    return None


@router.get("/login")
def login_redirect():
    auth_url = _authorization_endpoint()
    if not auth_url or not KEYCLOAK_CLIENT_ID or not BACKEND_BASE_URL or not FRONTEND_BASE_URL:
        raise HTTPException(status_code=500, detail="Keycloak login is not configured on the server")

    redirect_uri = f"{BACKEND_BASE_URL.rstrip('/')}/auth/callback"
    params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect_uri,
    }

    # build query string
    q = "&".join(f"{k}={requests.utils.requote_uri(v)}" for k, v in params.items())
    full = f"{auth_url}?{q}"
    return RedirectResponse(full)


@router.get("/auth/callback")
def auth_callback(code: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    token_url = _token_endpoint()
    if not token_url or not KEYCLOAK_CLIENT_ID or not BACKEND_BASE_URL or not FRONTEND_BASE_URL:
        raise HTTPException(status_code=500, detail="Keycloak token endpoint not configured")

    redirect_uri = f"{BACKEND_BASE_URL.rstrip('/')}/auth/callback"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": KEYCLOAK_CLIENT_ID,
    }

    auth = None
    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET

    r = requests.post(token_url, data=data, timeout=10)
    try:
        r.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to exchange code: {exc}") from exc

    tokens = r.json()
    access_token = tokens.get("access_token")
    id_token = tokens.get("id_token")

    # Redirect to frontend with tokens in fragment so frontend can read them
    redirect_to = FRONTEND_BASE_URL.rstrip("/")
    fragment = []
    if access_token:
        fragment.append(f"access_token={access_token}")
    if id_token:
        fragment.append(f"id_token={id_token}")

    frag = "&".join(fragment)
    url = f"{redirect_to}/#{frag}" if frag else redirect_to
    return RedirectResponse(url)
