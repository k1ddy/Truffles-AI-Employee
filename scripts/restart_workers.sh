#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-truffles-api_truffles-api}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-0}"
ENV_FILE="${ENV_FILE:-/home/zhan/truffles-main/truffles-api/.env}"
NETWORK="${NETWORK:-truffles_internal-net}"
OUTBOX_WORKER_ENABLED="${OUTBOX_WORKER_ENABLED:-1}"
SENTINEL_ENABLED="${SENTINEL_ENABLED:-1}"
OUTBOX_OTEL_SERVICE_NAME="${OUTBOX_OTEL_SERVICE_NAME:-truffles-outbox}"
SENTINEL_OTEL_SERVICE_NAME="${SENTINEL_OTEL_SERVICE_NAME:-truffles-sentinel}"

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

run_worker() {
  local name="$1"
  local cmd="$2"
  shift 2

  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" \
    --env-file "$ENV_FILE" \
    --network "$NETWORK" \
    --restart unless-stopped \
    "$@" \
    "$IMAGE_NAME" \
    $cmd
}

run_worker "truffles-outbox" "python -m app.workers.outbox" \
  -e OUTBOX_WORKER_ENABLED="$OUTBOX_WORKER_ENABLED" \
  -e OTEL_SERVICE_NAME="$OUTBOX_OTEL_SERVICE_NAME"
run_worker "truffles-sentinel" "python -m app.workers.sentinel" \
  -e SENTINEL_ENABLED="$SENTINEL_ENABLED" \
  -e OTEL_SERVICE_NAME="$SENTINEL_OTEL_SERVICE_NAME"

echo "Workers restarted: truffles-outbox, truffles-sentinel"
