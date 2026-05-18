#!/usr/bin/env bash
set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DOCKER_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${REZEPTE_TEST:-}" ]; then
  MODE="test"
  ENV_FILE="$DOCKER_DIR/.env.test"
  SECRETS_FILE="$DOCKER_DIR/.env.test.secrets"
  OVERRIDE_FILE="$DOCKER_DIR/docker-compose.test.yml"
else
  MODE="prod"
  ENV_FILE="$DOCKER_DIR/.env.prod"
  SECRETS_FILE="$DOCKER_DIR/.env.prod.secrets"
  OVERRIDE_FILE="$DOCKER_DIR/docker-compose.prod.yml"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE" >&2
  echo "Create it from the matching *.example file in docker/." >&2
  exit 1
fi

if [ ! -f "$SECRETS_FILE" ]; then
  echo "Missing secrets file: $SECRETS_FILE" >&2
  echo "Create it from the matching *.secrets.example file in docker/." >&2
  exit 1
fi

export REZEPTE_ENV_FILE="$ENV_FILE"
export REZEPTE_SECRETS_FILE="$SECRETS_FILE"

echo "Familienrezepte mode: $MODE"
echo "Env file: $ENV_FILE"
echo "Secrets file: $SECRETS_FILE"
echo "Compose override: $OVERRIDE_FILE"

exec docker compose \
  --env-file "$ENV_FILE" \
  --env-file "$SECRETS_FILE" \
  -f "$DOCKER_DIR/docker-compose.yml" \
  -f "$OVERRIDE_FILE" \
  "$@"
