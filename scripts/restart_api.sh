#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
EXPECTED_IMAGE="${EXPECTED_IMAGE:-}"
VERIFY_VERSION="${VERIFY_VERSION:-0}"
VERIFY_URL="${VERIFY_URL:-http://localhost:8000/admin/version}"
VERIFY_RETRIES="${VERIFY_RETRIES:-30}"
VERIFY_SLEEP_SECONDS="${VERIFY_SLEEP_SECONDS:-1}"
EXPECTED_GIT_COMMIT="${EXPECTED_GIT_COMMIT:-}"
EXPECTED_VERSION="${EXPECTED_VERSION:-}"
OUTBOX_WORKER_MODE_OVERRIDE="${OUTBOX_WORKER_MODE_OVERRIDE:-}"
DATABASE_LOCAL_CIDRS="${DATABASE_LOCAL_CIDRS:-}"
WEBHOOK_ENQUEUE_ONLY_OVERRIDE="${WEBHOOK_ENQUEUE_ONLY_OVERRIDE:-}"

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-/app/migrations}"
MIGRATION_RUNNER="${MIGRATION_RUNNER:-/app/scripts/apply_sql_migrations.py}"
MIGRATION_NETWORK="${MIGRATION_NETWORK:-truffles_internal-net}"
MIGRATION_BOOTSTRAP_MODE="${MIGRATION_BOOTSTRAP_MODE:-auto}"

API_WORKDIR="${API_WORKDIR:-/home/zhan/truffles-main/truffles-api}"
API_ENV_FILE="${API_ENV_FILE:-${API_WORKDIR}/.env}"

is_ghcr_image_ref() {
  local image_ref="$1"
  case "$image_ref" in
    ghcr.io/k1ddy/truffles-ai-employee:*|ghcr.io/k1ddy/truffles-ai-employee@sha256:*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ "$REQUIRE_GHCR" = "1" ]; then
  if ! is_ghcr_image_ref "$IMAGE_NAME"; then
    echo "ERROR: REQUIRE_GHCR=1 but IMAGE_NAME='$IMAGE_NAME' is not a GHCR image ref." >&2
    exit 1
  fi
fi

if [ "$PULL_IMAGE" = "1" ]; then
  docker pull "$IMAGE_NAME"
fi

if [ "$VERIFY_VERSION" != "1" ] && { [ -n "$EXPECTED_GIT_COMMIT" ] || [ -n "$EXPECTED_VERSION" ]; }; then
  echo "VERIFY_VERSION=0 but expected runtime fingerprint was provided; forcing VERIFY_VERSION=1." >&2
  VERIFY_VERSION=1
fi

if [ "$RUN_MIGRATIONS" = "1" ]; then
  if [ ! -f "$API_ENV_FILE" ]; then
    echo "ERROR: API env file not found: $API_ENV_FILE" >&2
    exit 1
  fi

  echo "Running DB migrations from image before container switch..."
  docker run --rm \
    --env-file "$API_ENV_FILE" \
    --network "$MIGRATION_NETWORK" \
    "$IMAGE_NAME" \
    python "$MIGRATION_RUNNER" --migrations-dir "$MIGRATIONS_DIR" --bootstrap "$MIGRATION_BOOTSTRAP_MODE"
fi

docker rm -f truffles-api >/dev/null 2>&1 || true
cd "$API_WORKDIR"
extra_env_args=()
if [ -n "$OUTBOX_WORKER_MODE_OVERRIDE" ]; then
  extra_env_args+=(-e "OUTBOX_WORKER_MODE=$OUTBOX_WORKER_MODE_OVERRIDE")
fi
if [ -n "$DATABASE_LOCAL_CIDRS" ]; then
  extra_env_args+=(-e "DATABASE_LOCAL_CIDRS=$DATABASE_LOCAL_CIDRS")
fi
if [ -n "$WEBHOOK_ENQUEUE_ONLY_OVERRIDE" ]; then
  extra_env_args+=(-e "WEBHOOK_ENQUEUE_ONLY=$WEBHOOK_ENQUEUE_ONLY_OVERRIDE")
fi
docker run -d --name truffles-api \
  --env-file .env \
  --network truffles_internal-net \
  --network proxy-net \
  -p 8000:8000 \
  --restart unless-stopped \
  -l traefik.enable=true \
  -l 'traefik.http.routers.truffles-api.rule=Host(`api.truffles.kz`)' \
  -l traefik.http.routers.truffles-api.entrypoints=websecure \
  -l traefik.http.routers.truffles-api.tls.certresolver=myresolver \
  -l traefik.http.services.truffles-api.loadbalancer.server.port=8000 \
  -l traefik.docker.network=proxy-net \
  --add-host auth.truffles.kz:172.20.0.2 \
  -e CONSOLE_OIDC_JWKS_URL=https://auth.truffles.kz/realms/truffles/protocol/openid-connect/certs \
  -e CONSOLE_OIDC_ISSUER=https://auth.truffles.kz/realms/truffles \
  "${extra_env_args[@]}" \
  "$IMAGE_NAME"

expected_ref="${EXPECTED_IMAGE:-$IMAGE_NAME}"
expected_image_id="$(docker image inspect --format '{{.Id}}' "$expected_ref" 2>/dev/null || true)"
if [ -z "$expected_image_id" ]; then
  echo "ERROR: deploy verify failed (cannot inspect expected image: $expected_ref)." >&2
  exit 1
fi
actual_image_id="$(docker inspect --format '{{.Image}}' truffles-api 2>/dev/null || true)"
if [ -z "$actual_image_id" ]; then
  echo "ERROR: deploy verify failed (cannot inspect truffles-api image)." >&2
  exit 1
fi
if [ "$actual_image_id" != "$expected_image_id" ]; then
  echo "ERROR: deploy verify failed (API image mismatch)." >&2
  echo "expected=$expected_image_id" >&2
  echo "actual=$actual_image_id" >&2
  exit 1
fi
echo "Deploy image verify OK: truffles-api image id $actual_image_id"

if [ "$VERIFY_VERSION" = "1" ]; then
  resp=""
  for _ in $(seq 1 "$VERIFY_RETRIES"); do
    resp="$(curl -fsS "$VERIFY_URL" 2>/dev/null || true)"
    if [ -n "$resp" ]; then
      break
    fi
    sleep "$VERIFY_SLEEP_SECONDS"
  done
  if [ -z "$resp" ]; then
    echo "ERROR: deploy verify failed (no response from $VERIFY_URL)." >&2
    exit 1
  fi
  RESP="$resp" EXPECTED_GIT_COMMIT="$EXPECTED_GIT_COMMIT" EXPECTED_VERSION="$EXPECTED_VERSION" python3 - <<'PY'
import json
import os
import sys

resp = os.environ.get("RESP", "")
expected_commit = os.environ.get("EXPECTED_GIT_COMMIT", "")
expected_version = os.environ.get("EXPECTED_VERSION", "")

try:
    data = json.loads(resp)
except Exception as exc:
    print(f"ERROR: deploy verify failed (invalid JSON): {exc}", file=sys.stderr)
    sys.exit(1)

version = data.get("version") or ""
git_commit = data.get("git_commit") or ""

if not version or version == "unknown":
    print("ERROR: deploy verify failed (version unknown).", file=sys.stderr)
    sys.exit(1)

if expected_commit and git_commit != expected_commit:
    print(
        f"ERROR: deploy verify failed (git_commit mismatch: expected {expected_commit}, got {git_commit}).",
        file=sys.stderr,
    )
    sys.exit(1)

if expected_version and version != expected_version:
    print(
        f"ERROR: deploy verify failed (version mismatch: expected {expected_version}, got {version}).",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"Deploy verify OK: version={version} git_commit={git_commit}")
PY
fi
