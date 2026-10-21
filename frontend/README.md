# Family Recipes - Frontend

React/Vite frontend for the current Litestar backend.

## Features

- Sign in through `/auth/login` and load the current user through `/auth/me`
- Store the access token in the browser
- View the status of the API, MongoDB, and S3
- Tests for authenticated users, administrators, and super administrators
- Create, list, search, and delete recipes
- Upload images to the existing S3 test endpoint
- Create users, manage group roles, grant super administrator status, and deactivate users
- German-language user interface

## Development

```bash
npm install
npm run dev
```

By default, Vite forwards `/api` requests to `http://localhost:8000` and removes the `/api` prefix.
To use a different backend, set:

```bash
VITE_DEV_API_TARGET=http://backend:8000 npm run dev
```

## Production Build

```bash
npm run build
```

The build output is written to `dist/`.

## Configuration

See `.env.example`:

```env
VITE_API_BASE_URL=/api
VITE_DEV_API_TARGET=http://localhost:8000
```

In production, the reverse proxy should forward `/api/*` requests to Litestar.

## Recipe editor V2

The recipe editor supports structured ingredient sections, ingredients with normalized units,
custom units, preparation notes, optional ingredients, ordered instruction steps, yield,
preparation/cooking/resting times, tags, recipe-book IDs, editing and deletion.

Run tests and build:

```bash
npm install
npm test
npm run build
```
