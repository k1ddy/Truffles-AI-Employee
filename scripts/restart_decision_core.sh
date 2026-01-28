#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
ENV_FILE="${ENV_FILE:-/home/zhan/truffles-main/truffles-api/.env}"
NETWORK="${NETWORK:-truffles_internal-net}"
PORT="${PORT:-8013}"
CONTAINER_NAME="${CONTAINER_NAME:-truffles-decision-core}"
OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-truffles-decision-core}"
DECISION_CORE_ENABLED="${DECISION_CORE_ENABLED:-0}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

if [ "$REQUIRE_GHCR" = "1" ]; then
  case "$IMAGE_NAME" in
    ghcr.io/k1ddy/truffles-ai-employee:*) ;;
    *)
      echo "ERROR: REQUIRE_GHCR=1 but IMAGE_NAME='$IMAGE_NAME' is not a GHCR image." >&2
      exit 1
      ;;
  esac
fi

if [ "$PULL_IMAGE" = "1" ]; then
  docker pull "$IMAGE_NAME"
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d --name "$CONTAINER_NAME" \
  --env-file "$ENV_FILE" \
  --network "$NETWORK" \
  -p "127.0.0.1:${PORT}:8000" \
  --restart unless-stopped \
  -e OTEL_SERVICE_NAME="$OTEL_SERVICE_NAME" \
  -e DECISION_CORE_ENABLED="$DECISION_CORE_ENABLED" \
  "$IMAGE_NAME" \
  uvicorn app.decision_core_app:app --host 0.0.0.0 --port 8000

echo "Decision Core restarted: $CONTAINER_NAME (port $PORT)"
