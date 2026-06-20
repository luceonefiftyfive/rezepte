# Prinziple authenthication

Used login flow:

```
frontend @ React Login-Dialog
  -> POST /api/auth/login { username, password }

backend FastAPI
  -> POST Keycloak /token with grant_type=password
  -> retieves access_token + refresh_token
  -> saves tokens on server side
  -> set HttpOnly session_id cookie

frontend @ React
  -> checks /api/auth/me
```

Used logout flow:

```
React
  -> POST /api/auth/logout

FastAPI
  -> deletes local session
  -> optional: revert keycloak refresh token
  -> deletes session_id cookie

user is logged out
```
