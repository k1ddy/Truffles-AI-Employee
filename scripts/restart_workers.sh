#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
EXPECTED_IMAGE="${EXPECTED_IMAGE:-}"
ENV_FILE="${ENV_FILE:-/home/zhan/truffles-main/truffles-api/.env}"
NETWORK="${NETWORK:-truffles_internal-net}"
OUTBOX_WORKER_ENABLED="${OUTBOX_WORKER_ENABLED:-1}"
KNOWLEDGE_ACTIVATION_WORKER_ENABLED="${KNOWLEDGE_ACTIVATION_WORKER_ENABLED:-1}"
SENTINEL_ENABLED="${SENTINEL_ENABLED:-1}"
OUTBOX_OTEL_SERVICE_NAME="${OUTBOX_OTEL_SERVICE_NAME:-truffles-outbox}"
KNOWLEDGE_ACTIVATION_OTEL_SERVICE_NAME="${KNOWLEDGE_ACTIVATION_OTEL_SERVICE_NAME:-truffles-knowledge-activation}"
SENTINEL_OTEL_SERVICE_NAME="${SENTINEL_OTEL_SERVICE_NAME:-truffles-sentinel}"
OUTBOX_WORKER_MODE_OVERRIDE="${OUTBOX_WORKER_MODE_OVERRIDE:-}"
DATABASE_LOCAL_CIDRS="${DATABASE_LOCAL_CIDRS:-}"

is_ghcr_image_ref() {
  local image_ref="$1"
  case "$image_ref" in
    ghcr.io/k1ddy/truffles-ai-employee:*|ghcr.io/k1ddy/truffles-ai-employee@sha256:*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

if [ "$REQUIRE_GHCR" = "1" ]; then
  if ! is_ghcr_image_ref "$IMAGE_NAME"; then
    echo "ERROR: REQUIRE_GHCR=1 but IMAGE_NAME='$IMAGE_NAME' is not a GHCR image ref." >&2
    exit 1
  fi
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

outbox_extra_args=()
if [ -n "$OUTBOX_WORKER_MODE_OVERRIDE" ]; then
  outbox_extra_args+=(-e "OUTBOX_WORKER_MODE=$OUTBOX_WORKER_MODE_OVERRIDE")
fi
if [ -n "$DATABASE_LOCAL_CIDRS" ]; then
  outbox_extra_args+=(-e "DATABASE_LOCAL_CIDRS=$DATABASE_LOCAL_CIDRS")
fi

common_runtime_args=()
if [ -n "$DATABASE_LOCAL_CIDRS" ]; then
  common_runtime_args+=(-e "DATABASE_LOCAL_CIDRS=$DATABASE_LOCAL_CIDRS")
fi

run_worker "truffles-outbox" "python -m app.workers.outbox" \
  -e OUTBOX_WORKER_ENABLED="$OUTBOX_WORKER_ENABLED" \
  "${outbox_extra_args[@]}" \
  -e OTEL_SERVICE_NAME="$OUTBOX_OTEL_SERVICE_NAME"
run_worker "truffles-knowledge-activation" "python -m app.workers.knowledge_activation" \
  -e KNOWLEDGE_ACTIVATION_WORKER_ENABLED="$KNOWLEDGE_ACTIVATION_WORKER_ENABLED" \
  "${common_runtime_args[@]}" \
  -e OTEL_SERVICE_NAME="$KNOWLEDGE_ACTIVATION_OTEL_SERVICE_NAME"
run_worker "truffles-sentinel" "python -m app.workers.sentinel" \
  -e SENTINEL_ENABLED="$SENTINEL_ENABLED" \
  "${common_runtime_args[@]}" \
  -e OTEL_SERVICE_NAME="$SENTINEL_OTEL_SERVICE_NAME"

expected_ref="${EXPECTED_IMAGE:-$IMAGE_NAME}"
expected_image_id="$(docker image inspect --format '{{.Id}}' "$expected_ref" 2>/dev/null || true)"
if [ -z "$expected_image_id" ]; then
  echo "ERROR: worker verify failed (cannot inspect expected image: $expected_ref)." >&2
  exit 1
fi

for worker in truffles-outbox truffles-knowledge-activation truffles-sentinel; do
  actual_image_id="$(docker inspect --format '{{.Image}}' "$worker" 2>/dev/null || true)"
  if [ -z "$actual_image_id" ]; then
    echo "ERROR: worker verify failed (cannot inspect container: $worker)." >&2
    exit 1
  fi
  if [ "$actual_image_id" != "$expected_image_id" ]; then
    echo "ERROR: worker verify failed ($worker image mismatch)." >&2
    echo "expected=$expected_image_id" >&2
    echo "actual=$actual_image_id" >&2
    exit 1
  fi
done

echo "Workers restarted: truffles-outbox, truffles-knowledge-activation, truffles-sentinel"
