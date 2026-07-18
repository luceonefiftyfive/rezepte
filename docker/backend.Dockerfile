FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ARG REZEPTE_GIT_HASH=unknown

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV REZEPTE_GIT_HASH=${REZEPTE_GIT_HASH}

COPY backend/pyproject.toml ./
COPY version.yaml ./version.yaml
RUN uv sync --no-dev --no-install-project

COPY backend/src/app ./app
RUN uv sync --no-dev

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
