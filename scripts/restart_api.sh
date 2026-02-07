#!/bin/bash
set -euo pipefail

IMAGE_NAME="${1:-${IMAGE_NAME:-ghcr.io/k1ddy/truffles-ai-employee:main}}"
PULL_IMAGE="${PULL_IMAGE:-0}"
REQUIRE_GHCR="${REQUIRE_GHCR:-1}"
VERIFY_VERSION="${VERIFY_VERSION:-0}"
VERIFY_URL="${VERIFY_URL:-http://localhost:8000/admin/version}"
VERIFY_RETRIES="${VERIFY_RETRIES:-30}"
VERIFY_SLEEP_SECONDS="${VERIFY_SLEEP_SECONDS:-1}"
EXPECTED_GIT_COMMIT="${EXPECTED_GIT_COMMIT:-}"
EXPECTED_VERSION="${EXPECTED_VERSION:-}"

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-/app/migrations}"
MIGRATION_RUNNER="${MIGRATION_RUNNER:-/app/scripts/apply_sql_migrations.py}"
MIGRATION_NETWORK="${MIGRATION_NETWORK:-truffles_internal-net}"

API_WORKDIR="${API_WORKDIR:-/home/zhan/truffles-main/truffles-api}"
API_ENV_FILE="${API_ENV_FILE:-${API_WORKDIR}/.env}"

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
    python "$MIGRATION_RUNNER" --migrations-dir "$MIGRATIONS_DIR"
fi

docker rm -f truffles-api >/dev/null 2>&1 || true
cd "$API_WORKDIR"
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
  "$IMAGE_NAME"

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
