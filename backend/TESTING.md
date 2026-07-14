# Backend test suite

Run all tests from the backend directory:

```bash
uv run pytest
```

Run with concise output:

```bash
uv run pytest -q
```

The suite covers:

- generic MongoDB repository CRUD, sorting, pagination and invalid IDs;
- settings and database dependency behaviour;
- application startup and superuser bootstrap;
- root and health endpoints;
- MongoDB and S3 system checks, including failure reporting;
- user login, current-user lookup and role-protected endpoints;
- user creation, listing, updates, group assignment and soft deletion;
- basic recipe creation, listing, deletion and input validation;
- image upload validation, S3 upload calls and S3 error handling.

External MongoDB and S3 services are not required. Tests use `mongomock-motor` and a mocked S3 client.
