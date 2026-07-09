# User Management API

Base URL: `http://<server>/api`

Authentication uses JWT bearer tokens. Protected endpoints require:

```http
Authorization: Bearer <ACCESS_TOKEN>
```

## Roles

### Group roles

| Role     | Meaning                                                     |
| -------- | ----------------------------------------------------------- |
| `admin`  | May manage users/groups for groups they administer          |
| `author` | May create/edit application content, depending on app logic |
| `reader` | May read application content, depending on app logic        |

### Global role

| Role          | Meaning                             |
| ------------- | ----------------------------------- |
| `super-admin` | Global administrator for all groups |

In the API model, global super-admin status is represented by:

```json
{
  "is_super_admin": true
}
```

---

## Data Models

### GroupRole

```json
{
  "group_id": "recipes",
  "role": "admin"
}
```

Allowed `role` values:

```text
admin
author
reader
```

### UserCreate

```json
{
  "username": "jdoe",
  "password": "very-secret",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false
}
```

Validation:

| Field            | Rule                     |
| ---------------- | ------------------------ |
| `username`       | minimum 3 characters     |
| `password`       | minimum 8 characters     |
| `first_name`     | minimum 1 character      |
| `last_name`      | minimum 1 character      |
| `email`          | valid email address      |
| `groups`         | list of `GroupRole`      |
| `is_super_admin` | boolean, default `false` |

### UserPublic

Returned by most user endpoints.

```json
{
  "id": "64f1...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

Passwords and password hashes are never returned.

---

## Public Endpoints

### Health Check

```http
GET /health
```

#### Response `200 OK`\*

```json
{
  "ok": true
}
```

---

### Login

```http
POST /auth/login
```

Content type: `application/x-www-form-urlencoded`

#### Request Body

```text
username=admin&password=admin-password
```

#### Response `200 OK`

```json
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "user": {
    "id": "64f1...",
    "username": "admin",
    "first_name": "System",
    "last_name": "Administrator",
    "email": "admin@example.com",
    "email_verified": true,
    "groups": [],
    "is_super_admin": true,
    "is_active": true
  }
}
```

#### Error Responses

| Status | Meaning                      |
| ------ | ---------------------------- |
| `401`  | Invalid username or password |

---

### Check Username Availability

```http
GET /users/check-username/{username}
```

Example:

```http
GET /users/check-username/admin
```

#### Response `200 OK`

```json
{
  "username": "admin",
  "available": false
}
```

---

### Check Email Availability

```http
GET /users/check-email/{email}
```

Example:

```http
GET /users/check-email/john@example.com
```

#### Response `200 OK`

```json
{
  "email": "john@example.com",
  "available": true
}
```

---

### Authenticated User Endpoints

#### Get Current User

```http
GET /auth/me
```

Requires: authenticated user.

#### Response `200 OK`

```json
{
  "id": "64f1...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                  |
| ------ | ------------------------ |
| `401`  | Missing or invalid token |
| `403`  | User is inactive         |

---

### Update Own Profile

```http
PATCH /users/me
```

Requires: authenticated user.

A user may update their own `first_name`, `last_name`, and `email`.

If the email changes, `email_verified` is reset to `false`.

#### Request Body

All fields are optional.

```json
{
  "first_name": "John",
  "last_name": "Changed",
  "email": "new-john@example.com"
}
```

#### Response `200 OK`

```json
{
  "id": "64f1...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Changed",
  "email": "new-john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                  |
| ------ | ------------------------ |
| `401`  | Missing or invalid token |
| `409`  | Email already exists     |

---

## Admin / Super-Admin Endpoints

The following endpoints require either:

- `is_super_admin = true`, or
- at least one group role with `role = admin`

### Create User

```http
POST /users
```

Requires: admin or super-admin.

Only a super-admin may create another super-admin.

A normal admin may only assign groups they administer.

#### Request Body

```json
{
  "username": "jdoe",
  "password": "very-secret",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false
}
```

#### Response `201 Created`

```json
{
  "id": "64f1...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                                             |
| ------ | --------------------------------------------------- |
| `401`  | Missing or invalid token                            |
| `403`  | Admin rights required, or insufficient group rights |
| `409`  | Username or email already exists                    |
| `422`  | Validation error                                    |

---

### List Users

```http
GET /users
```

Requires: admin or super-admin.

#### Query Parameters

| Parameter        |    Type | Required | Description                                                            |
| ---------------- | ------: | -------: | ---------------------------------------------------------------------- |
| `group_id`       |  string |       no | Return only users assigned to this group                               |
| `role`           |  string |       no | Return only users with this role. Allowed: `admin`, `author`, `reader` |
| `email_verified` | boolean |       no | Filter by email verification status                                    |

Examples:

```http
GET /users
GET /users?group_id=recipes
GET /users?role=author
GET /users?email_verified=false
```

#### Response `200 OK`

```json
[
  {
    "id": "64f1...",
    "username": "admin",
    "first_name": "System",
    "last_name": "Administrator",
    "email": "admin@example.com",
    "email_verified": true,
    "groups": [],
    "is_super_admin": true,
    "is_active": true
  },
  {
    "id": "64f2...",
    "username": "jdoe",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "email_verified": false,
    "groups": [
      {
        "group_id": "recipes",
        "role": "reader"
      }
    ],
    "is_super_admin": false,
    "is_active": true
  }
]
```

---

### Get User By ID

```http
GET /users/{user_id}
```

Requires: admin or super-admin.

#### Response `200 OK`

```json
{
  "id": "64f2...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "reader"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                  |
| ------ | ------------------------ |
| `401`  | Missing or invalid token |
| `403`  | Admin rights required    |
| `404`  | User not found           |

---

### Update User Groups

```http
PATCH /users/{user_id}/groups
```

Requires: admin or super-admin.

A super-admin may update any user groups.

A normal admin may only manage groups where they are admin.

#### Request Body

```json
{
  "groups": [
    {
      "group_id": "recipes",
      "role": "admin"
    },
    {
      "group_id": "family",
      "role": "author"
    }
  ]
}
```

#### Response `200 OK`\*

```json
{
  "id": "64f2...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [
    {
      "group_id": "recipes",
      "role": "admin"
    },
    {
      "group_id": "family",
      "role": "author"
    }
  ],
  "is_super_admin": false,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                                            |
| ------ | -------------------------------------------------- |
| `401`  | Missing or invalid token                           |
| `403`  | Admin rights required or insufficient group rights |
| `404`  | User not found                                     |
| `422`  | Validation error                                   |

---

## Super-Admin Only Endpoints

### Set Super-Admin Status

```http
PATCH /users/{user_id}/super-admin
```

Requires: super-admin.

The implementation prevents removing the last active super-admin.

#### Request Body

```json
{
  "is_super_admin": true
}
```

#### Response `200 OK`

```json
{
  "id": "64f2...",
  "username": "jdoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "email_verified": false,
  "groups": [],
  "is_super_admin": true,
  "is_active": true
}
```

#### Error Responses

| Status | Meaning                                   |
| ------ | ----------------------------------------- |
| `401`  | Missing or invalid token                  |
| `403`  | Super-admin required                      |
| `404`  | User not found                            |
| `400`  | Cannot remove the last active super-admin |

---

### Delete User

```http
DELETE /users/{user_id}
```

Requires: super-admin.

The implementation uses soft delete by setting `is_active = false`.

The implementation prevents deleting the last active super-admin.

#### Response `200 OK`

```json
{
  "deleted": true
}
```

#### Error Responses

| Status | Meaning                                   |
| ------ | ----------------------------------------- |
| `401`  | Missing or invalid token                  |
| `403`  | Super-admin required                      |
| `404`  | User not found                            |
| `400`  | Cannot delete the last active super-admin |

---

## Test Access Endpoints

These endpoints are included to demonstrate access protection.

### Authenticated Access Test

```http
GET /test-access
```

Requires: authenticated user.

#### Response `200 OK`

```json
{
  "message": "You are authenticated",
  "username": "jdoe"
}
```

---

### Admin Access Test

```http
GET /test-admin-access
```

Requires: admin or super-admin.

#### Response `200 OK`

```json
{
  "message": "You are admin or super-admin",
  "username": "admin"
}
```

---

### Super-Admin Access Test

```http
GET /test-super-admin-access
```

Requires: super-admin.

#### Response `200 OK`

```json
{
  "message": "You are super-admin",
  "username": "admin"
}
```

---

### Superuser Bootstrap

At application startup, the backend creates a default super-admin if no active
super-admin exists.

Environment variables:

```env
SUPERUSER_USERNAME=admin
SUPERUSER_PASSWORD=admin-password
SUPERUSER_EMAIL=admin@example.com
```

The created bootstrap user has:

```json
{
  "username": "admin",
  "first_name": "System",
  "last_name": "Administrator",
  "email_verified": true,
  "groups": [],
  "is_super_admin": true,
  "is_active": true
}
```

The password is stored as a hash, not as plain text.

---

## Example cURL Flow

### 1. Login

```bash
TOKEN=$(curl -s -X POST "http://<server>/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin-password" \
  | jq -r '.access_token')
```

### 2. Call Protected Endpoint

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://<server>/api/test-access"
```

### 3. Create User

```bash
curl -X POST "http://<server>/api/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jdoe",
    "password": "very-secret",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "groups": [
      {
        "group_id": "recipes",
        "role": "reader"
      }
    ],
    "is_super_admin": false
  }'
```
