#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="${API_DIR:-$ROOT_DIR/truffles-api}"
PROJECT_NAME="${PROJECT_NAME:-truffles-api-test}"
PYTEST_ARGS="${PYTEST_ARGS:-/app/tests/test_message_endpoint.py}"

COMPOSE_BASE="$API_DIR/docker-compose.yml"
COMPOSE_TEST="$API_DIR/docker-compose.test.yml"

if [ ! -f "$COMPOSE_BASE" ]; then
  echo "ERROR: compose file not found: $COMPOSE_BASE" >&2
  exit 1
fi

if [ ! -f "$COMPOSE_TEST" ]; then
  echo "ERROR: compose test file not found: $COMPOSE_TEST" >&2
  exit 1
fi

compose() {
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_BASE" -f "$COMPOSE_TEST" "$@"
}

compose up -d --build truffles-api truffles-outbox truffles-sentinel

compose exec -T truffles-api env -i \
  PATH=/usr/local/bin:/usr/bin:/bin \
  PYTHONPATH=/app \
  pytest -q $PYTEST_ARGS
