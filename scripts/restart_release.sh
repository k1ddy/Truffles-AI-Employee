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
RELEASE_ENV_FILE="${RELEASE_ENV_FILE:-/home/zhan/truffles-main/truffles-api/.env}"
RELEASE_RUNTIME_NETWORK="${RELEASE_RUNTIME_NETWORK:-truffles_internal-net}"
API_SCRIPT="${API_SCRIPT:-${SCRIPT_DIR}/restart_api.sh}"
WORKERS_SCRIPT="${WORKERS_SCRIPT:-${SCRIPT_DIR}/restart_workers.sh}"
CONSOLE_SCRIPT="${CONSOLE_SCRIPT:-${SCRIPT_DIR}/restart_console_web.sh}"
KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT="${KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT:-${SCRIPT_DIR}/restart_knowledge_activation_service.sh}"
RESTART_KNOWLEDGE_ACTIVATION_SERVICE="${RESTART_KNOWLEDGE_ACTIVATION_SERVICE:-0}"
RESTART_CONSOLE_WEB="${RESTART_CONSOLE_WEB:-1}"
KNOWLEDGE_ACTIVATION_SERVICE_ENABLED="${KNOWLEDGE_ACTIVATION_SERVICE_ENABLED:-1}"
RUN_KNOWLEDGE_ACTIVATION_CANARY="${RUN_KNOWLEDGE_ACTIVATION_CANARY:-0}"
KNOWLEDGE_ACTIVATION_CANARY_SCRIPT="${KNOWLEDGE_ACTIVATION_CANARY_SCRIPT:-${SCRIPT_DIR}/../truffles-api/scripts/knowledge_activation_release_guard.py}"
KNOWLEDGE_ACTIVATION_CANARY_OUTPUT="${KNOWLEDGE_ACTIVATION_CANARY_OUTPUT:-/tmp/knowledge_activation_release_guard.json}"
ACTIVATION_GUARD_PYTHON="${ACTIVATION_GUARD_PYTHON:-python3}"
RUN_RELEASE_TOPOLOGY_TRUTH="${RUN_RELEASE_TOPOLOGY_TRUTH:-1}"
RELEASE_TOPOLOGY_TRUTH_SCRIPT="${RELEASE_TOPOLOGY_TRUTH_SCRIPT:-${SCRIPT_DIR}/release_topology_truth.py}"
RELEASE_TOPOLOGY_TRUTH_OUTPUT="${RELEASE_TOPOLOGY_TRUTH_OUTPUT:-/tmp/release_topology_truth.json}"
TOPOLOGY_TRUTH_PYTHON="${TOPOLOGY_TRUTH_PYTHON:-python3}"
TOPOLOGY_TRUTH_BASE_URL="${TOPOLOGY_TRUTH_BASE_URL:-http://localhost:8000}"
FAIL_ON_ACTIVE_SHADOW="${FAIL_ON_ACTIVE_SHADOW:-0}"
RUNTIME_PROFILE_SCRIPT="${RUNTIME_PROFILE_SCRIPT:-${SCRIPT_DIR}/release_runtime_profile.py}"
RUNTIME_PROFILE_PYTHON="${RUNTIME_PROFILE_PYTHON:-python3}"
RUNTIME_PROFILE_OUTPUT="${RUNTIME_PROFILE_OUTPUT:-/tmp/release_runtime_profile.json}"
API_CONTAINER="${API_CONTAINER:-truffles-api}"
WORKER_CONTAINERS="${WORKER_CONTAINERS:-truffles-outbox truffles-knowledge-activation truffles-sentinel}"
KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER="${KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER:-truffles-knowledge-activation-service}"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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

if [ "$RESTART_CONSOLE_WEB" = "1" ] && [ ! -f "$CONSOLE_SCRIPT" ]; then
  echo "ERROR: console web restart script not found: $CONSOLE_SCRIPT" >&2
  exit 1
fi

if [ "$RESTART_KNOWLEDGE_ACTIVATION_SERVICE" = "1" ] && [ ! -f "$KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT" ]; then
  echo "ERROR: knowledge activation service restart script not found: $KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT" >&2
  exit 1
fi

if [ "$RUN_KNOWLEDGE_ACTIVATION_CANARY" = "1" ] && [ ! -f "$KNOWLEDGE_ACTIVATION_CANARY_SCRIPT" ]; then
  echo "ERROR: knowledge activation canary script not found: $KNOWLEDGE_ACTIVATION_CANARY_SCRIPT" >&2
  exit 1
fi

if [ "$RUN_RELEASE_TOPOLOGY_TRUTH" = "1" ] && [ ! -f "$RELEASE_TOPOLOGY_TRUTH_SCRIPT" ]; then
  echo "ERROR: release topology truth script not found: $RELEASE_TOPOLOGY_TRUTH_SCRIPT" >&2
  exit 1
fi

if [ ! -f "$RELEASE_ENV_FILE" ]; then
  echo "ERROR: release env file not found: $RELEASE_ENV_FILE" >&2
  exit 1
fi

if [ ! -f "$RUNTIME_PROFILE_SCRIPT" ]; then
  echo "ERROR: runtime profile script not found: $RUNTIME_PROFILE_SCRIPT" >&2
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

"$RUNTIME_PROFILE_PYTHON" "$RUNTIME_PROFILE_SCRIPT" \
  --env-file "$RELEASE_ENV_FILE" \
  --network "$RELEASE_RUNTIME_NETWORK" \
  --output "$RUNTIME_PROFILE_OUTPUT" >/dev/null

readarray -t runtime_profile_values < <(
  "$RUNTIME_PROFILE_PYTHON" - <<'PY' "$RUNTIME_PROFILE_OUTPUT"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("outbox_worker_mode_override") or "")
print(",".join(payload.get("database_local_cidrs") or []))
print(payload.get("webhook_enqueue_only_override") or "")
for item in payload.get("warnings") or []:
    print(f"WARN:{item}")
PY
)

OUTBOX_WORKER_MODE_OVERRIDE="${runtime_profile_values[0]:-}"
DATABASE_LOCAL_CIDRS="${runtime_profile_values[1]:-}"
WEBHOOK_ENQUEUE_ONLY_OVERRIDE="${runtime_profile_values[2]:-}"
for value in "${runtime_profile_values[@]:3}"; do
  if [[ "$value" == WARN:* ]]; then
    echo "Runtime profile warning: ${value#WARN:}" >&2
  fi
done

IMAGE_NAME="$IMAGE_REF" \
PULL_IMAGE=0 \
REQUIRE_GHCR="$REQUIRE_GHCR" \
EXPECTED_IMAGE="$IMAGE_REF" \
RUN_MIGRATIONS="$RUN_MIGRATIONS" \
MIGRATION_BOOTSTRAP_MODE="$MIGRATION_BOOTSTRAP_MODE" \
VERIFY_VERSION="$VERIFY_VERSION" \
EXPECTED_GIT_COMMIT="$EXPECTED_GIT_COMMIT" \
EXPECTED_VERSION="$EXPECTED_VERSION" \
OUTBOX_WORKER_MODE_OVERRIDE="$OUTBOX_WORKER_MODE_OVERRIDE" \
DATABASE_LOCAL_CIDRS="$DATABASE_LOCAL_CIDRS" \
WEBHOOK_ENQUEUE_ONLY_OVERRIDE="$WEBHOOK_ENQUEUE_ONLY_OVERRIDE" \
bash "$API_SCRIPT"

IMAGE_NAME="$IMAGE_REF" \
PULL_IMAGE=0 \
REQUIRE_GHCR="$REQUIRE_GHCR" \
EXPECTED_IMAGE="$IMAGE_REF" \
OUTBOX_WORKER_MODE_OVERRIDE="$OUTBOX_WORKER_MODE_OVERRIDE" \
DATABASE_LOCAL_CIDRS="$DATABASE_LOCAL_CIDRS" \
bash "$WORKERS_SCRIPT"

if [ "$RESTART_KNOWLEDGE_ACTIVATION_SERVICE" = "1" ]; then
  IMAGE_NAME="$IMAGE_REF" \
  PULL_IMAGE=0 \
  REQUIRE_GHCR="$REQUIRE_GHCR" \
  EXPECTED_IMAGE="$IMAGE_REF" \
  KNOWLEDGE_ACTIVATION_SERVICE_ENABLED="$KNOWLEDGE_ACTIVATION_SERVICE_ENABLED" \
  VERIFY_HEALTH=1 \
  bash "$KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT"
fi

if [ "$RESTART_CONSOLE_WEB" = "1" ]; then
  EXPECTED_GIT_COMMIT="$EXPECTED_GIT_COMMIT" \
  BUILD_TIME="${BUILD_TIME:-}" \
  VERIFY_CONSOLE_BUILD=1 \
  bash "$CONSOLE_SCRIPT"
fi

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

if [ "$RESTART_KNOWLEDGE_ACTIVATION_SERVICE" = "1" ]; then
  activation_image_id="$(docker inspect --format '{{.Image}}' "$KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER" 2>/dev/null || true)"
  if [ -z "$activation_image_id" ]; then
    echo "ERROR: release parity check failed (cannot inspect $KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER)." >&2
    exit 1
  fi
  if [ "$activation_image_id" != "$api_image_id" ]; then
    echo "ERROR: release parity check failed ($KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER image differs from $API_CONTAINER)." >&2
    echo "$API_CONTAINER=$api_image_id" >&2
    echo "$KNOWLEDGE_ACTIVATION_SERVICE_CONTAINER=$activation_image_id" >&2
    exit 1
  fi
fi

if [ "$RESTART_KNOWLEDGE_ACTIVATION_SERVICE" = "1" ] && [ "$RESTART_CONSOLE_WEB" = "1" ]; then
  echo "Release parity OK: API, workers, knowledge activation service, and console web were verified"
elif [ "$RESTART_KNOWLEDGE_ACTIVATION_SERVICE" = "1" ]; then
  echo "Release parity OK: API, workers, and knowledge activation service share image id $api_image_id"
elif [ "$RESTART_CONSOLE_WEB" = "1" ]; then
  echo "Release parity OK: API, workers, and console web were verified"
else
  echo "Release parity OK: API and workers share image id $api_image_id"
fi

if [ "$RUN_KNOWLEDGE_ACTIVATION_CANARY" = "1" ]; then
  "$ACTIVATION_GUARD_PYTHON" "$KNOWLEDGE_ACTIVATION_CANARY_SCRIPT" \
    --output "$KNOWLEDGE_ACTIVATION_CANARY_OUTPUT" \
    --pretty
  echo "Knowledge activation canary artifact: $KNOWLEDGE_ACTIVATION_CANARY_OUTPUT"
fi

if [ "$RUN_RELEASE_TOPOLOGY_TRUTH" = "1" ]; then
  topology_truth_cmd=(
    "$TOPOLOGY_TRUTH_PYTHON"
    "$RELEASE_TOPOLOGY_TRUTH_SCRIPT"
    --repo-root "$REPO_ROOT"
    --base-url "$TOPOLOGY_TRUTH_BASE_URL"
    --output "$RELEASE_TOPOLOGY_TRUTH_OUTPUT"
  )
  if [ -n "$EXPECTED_GIT_COMMIT" ]; then
    topology_truth_cmd+=(--expected-commit "$EXPECTED_GIT_COMMIT")
  fi
  if [ "$FAIL_ON_ACTIVE_SHADOW" = "1" ]; then
    topology_truth_cmd+=(--fail-on-active-shadow)
  fi
  "${topology_truth_cmd[@]}"
  echo "Release topology truth artifact: $RELEASE_TOPOLOGY_TRUTH_OUTPUT"
fi
