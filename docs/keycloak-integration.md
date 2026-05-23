Keycloak integration
--------------------

This backend verifies Keycloak-issued JWT access tokens using the realm JWKS.

Environment variables
- `KEYCLOAK_JWKS_URL` (required): URL to the realm JWKS, e.g. `https://<keycloak-host>/realms/<realm>/protocol/openid-connect/certs`.
- `KEYCLOAK_ISSUER` (optional): issuer URL to validate the `iss` claim.
- `KEYCLOAK_AUDIENCE` (optional): audience to validate the `aud` claim.

Endpoints protection
- `POST /recipes` — requires authentication (any valid token). Users may belong to no group or groups `admin`/`viewer`.
- `DELETE /recipes/{id}` — requires membership in the `admin` group (checked against `groups` claim or `realm_access.roles`).

Notes
- The implementation fetches JWKS and caches it for 5 minutes.
- The code uses `python-jose[cryptography]` and `requests` to validate tokens.
