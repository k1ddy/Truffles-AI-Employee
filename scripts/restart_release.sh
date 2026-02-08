#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-1}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
MIGRATION_BOOTSTRAP_MODE="${MIGRATION_BOOTSTRAP_MODE:-auto}"
VERIFY_VERSION="${VERIFY_VERSION:-1}"
EXPECTED_GIT_COMMIT="${EXPECTED_GIT_COMMIT:-}"
EXPECTED_VERSION="${EXPECTED_VERSION:-}"
API_SCRIPT="${API_SCRIPT:-${SCRIPT_DIR}/restart_api.sh}"
WORKERS_SCRIPT="${WORKERS_SCRIPT:-${SCRIPT_DIR}/restart_workers.sh}"
API_CONTAINER="${API_CONTAINER:-truffles-api}"
WORKER_CONTAINERS="${WORKER_CONTAINERS:-truffles-outbox truffles-sentinel}"

is_ghcr_image_ref() {
  local image_ref="$1"
  case "$image_ref" in
    ghcr.io/k1ddy/truffles-ai-employee:*|ghcr.io/k1ddy/truffles-ai-employee@sha256:*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_digest_ref() {
  local image_ref="$1"

  if [[ "$image_ref" == *"@sha256:"* ]]; then
    echo "$image_ref"
    return 0
  fi

  local digests
  digests="$(docker image inspect --format '{{join .RepoDigests "\n"}}' "$image_ref" 2>/dev/null || true)"
  local digest_ref
  digest_ref="$(printf '%s\n' "$digests" | grep -m1 '^ghcr.io/k1ddy/truffles-ai-employee@sha256:' || true)"

  if [ -n "$digest_ref" ]; then
    echo "$digest_ref"
    return 0
  fi

  if [ "$REQUIRE_GHCR" = "1" ]; then
    echo "ERROR: cannot resolve digest for image '$image_ref'." >&2
    return 1
  fi

  echo "$image_ref"
}

if [ ! -f "$API_SCRIPT" ]; then
  echo "ERROR: API restart script not found: $API_SCRIPT" >&2
  exit 1
fi

if [ ! -f "$WORKERS_SCRIPT" ]; then
  echo "ERROR: workers restart script not found: $WORKERS_SCRIPT" >&2
  exit 1
fi

if [ "$REQUIRE_GHCR" = "1" ] && ! is_ghcr_image_ref "$IMAGE_NAME"; then
  echo "ERROR: REQUIRE_GHCR=1 but IMAGE_NAME='$IMAGE_NAME' is not a GHCR image ref." >&2
  exit 1
fi

if [ "$PULL_IMAGE" = "1" ]; then
  docker pull "$IMAGE_NAME"
fi

IMAGE_REF="$(resolve_digest_ref "$IMAGE_NAME")"
echo "Release image ref: $IMAGE_REF"

IMAGE_NAME="$IMAGE_REF" \
PULL_IMAGE=0 \
REQUIRE_GHCR="$REQUIRE_GHCR" \
EXPECTED_IMAGE="$IMAGE_REF" \
RUN_MIGRATIONS="$RUN_MIGRATIONS" \
MIGRATION_BOOTSTRAP_MODE="$MIGRATION_BOOTSTRAP_MODE" \
VERIFY_VERSION="$VERIFY_VERSION" \
EXPECTED_GIT_COMMIT="$EXPECTED_GIT_COMMIT" \
EXPECTED_VERSION="$EXPECTED_VERSION" \
bash "$API_SCRIPT"

IMAGE_NAME="$IMAGE_REF" \
PULL_IMAGE=0 \
REQUIRE_GHCR="$REQUIRE_GHCR" \
EXPECTED_IMAGE="$IMAGE_REF" \
bash "$WORKERS_SCRIPT"

api_image_id="$(docker inspect --format '{{.Image}}' "$API_CONTAINER" 2>/dev/null || true)"
if [ -z "$api_image_id" ]; then
  echo "ERROR: release parity check failed (cannot inspect $API_CONTAINER)." >&2
  exit 1
fi

for worker in $WORKER_CONTAINERS; do
  worker_image_id="$(docker inspect --format '{{.Image}}' "$worker" 2>/dev/null || true)"
  if [ -z "$worker_image_id" ]; then
    echo "ERROR: release parity check failed (cannot inspect $worker)." >&2
    exit 1
  fi
  if [ "$worker_image_id" != "$api_image_id" ]; then
    echo "ERROR: release parity check failed ($worker image differs from $API_CONTAINER)." >&2
    echo "$API_CONTAINER=$api_image_id" >&2
    echo "$worker=$worker_image_id" >&2
    exit 1
  fi
done

echo "Release parity OK: API and workers share image id $api_image_id"
