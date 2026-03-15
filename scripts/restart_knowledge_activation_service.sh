#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
EXPECTED_IMAGE="${EXPECTED_IMAGE:-}"
ENV_FILE="${ENV_FILE:-/home/zhan/truffles-main/truffles-api/.env}"
NETWORK="${NETWORK:-truffles_internal-net}"
PORT="${PORT:-8015}"
CONTAINER_NAME="${CONTAINER_NAME:-truffles-knowledge-activation-service}"
OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-truffles-knowledge-activation-service}"
KNOWLEDGE_ACTIVATION_SERVICE_ENABLED="${KNOWLEDGE_ACTIVATION_SERVICE_ENABLED:-0}"
VERIFY_HEALTH="${VERIFY_HEALTH:-0}"
VERIFY_URL="${VERIFY_URL:-http://127.0.0.1:${PORT}/health}"
VERIFY_RETRIES="${VERIFY_RETRIES:-30}"
VERIFY_SLEEP_SECONDS="${VERIFY_SLEEP_SECONDS:-1}"

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
  -e KNOWLEDGE_ACTIVATION_SERVICE_ENABLED="$KNOWLEDGE_ACTIVATION_SERVICE_ENABLED" \
  "$IMAGE_NAME" \
  uvicorn app.knowledge_activation_service_app:app --host 0.0.0.0 --port 8000

expected_ref="${EXPECTED_IMAGE:-$IMAGE_NAME}"
expected_image_id="$(docker image inspect --format '{{.Id}}' "$expected_ref" 2>/dev/null || true)"
if [ -z "$expected_image_id" ]; then
  echo "ERROR: activation service verify failed (cannot inspect expected image: $expected_ref)." >&2
  exit 1
fi
actual_image_id="$(docker inspect --format '{{.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
if [ -z "$actual_image_id" ]; then
  echo "ERROR: activation service verify failed (cannot inspect container image: $CONTAINER_NAME)." >&2
  exit 1
fi
if [ "$actual_image_id" != "$expected_image_id" ]; then
  echo "ERROR: activation service verify failed (image mismatch)." >&2
  echo "expected=$expected_image_id" >&2
  echo "actual=$actual_image_id" >&2
  exit 1
fi

if [ "$VERIFY_HEALTH" = "1" ]; then
  resp=""
  for _ in $(seq 1 "$VERIFY_RETRIES"); do
    resp="$(curl -fsS "$VERIFY_URL" 2>/dev/null || true)"
    if [ -n "$resp" ]; then
      break
    fi
    sleep "$VERIFY_SLEEP_SECONDS"
  done
  if [ -z "$resp" ]; then
    echo "ERROR: activation service verify failed (no response from $VERIFY_URL)." >&2
    exit 1
  fi
fi

echo "Knowledge Activation Service restarted: $CONTAINER_NAME (port $PORT)"
