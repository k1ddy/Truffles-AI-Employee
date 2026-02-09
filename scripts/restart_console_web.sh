#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
compose_file="${repo_root}/truffles-api/docker-compose.yml"

if [[ ! -f "$compose_file" ]]; then
  echo "ERROR: docker-compose file not found: ${compose_file}" >&2
  exit 1
fi

EXPECTED_GIT_COMMIT=${EXPECTED_GIT_COMMIT:-${GIT_COMMIT:-$(git -C "$repo_root" rev-parse HEAD)}}
BUILD_TIME=${BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}
VERIFY_CONSOLE_BUILD=${VERIFY_CONSOLE_BUILD:-1}

export GIT_COMMIT="${EXPECTED_GIT_COMMIT}" BUILD_TIME

docker compose -f "$compose_file" build console-web
docker compose -f "$compose_file" up -d console-web

if [[ "$VERIFY_CONSOLE_BUILD" == "1" ]]; then
  actual_commit="$(docker exec truffles-console-web /bin/sh -lc 'printf "%s" "${NEXT_PUBLIC_BUILD_SHA:-unknown}"')"
  actual_time="$(docker exec truffles-console-web /bin/sh -lc 'printf "%s" "${NEXT_PUBLIC_BUILD_TIME:-unknown}"')"
  if [[ "$actual_commit" != "$EXPECTED_GIT_COMMIT" ]]; then
    echo "ERROR: console build SHA mismatch: expected=${EXPECTED_GIT_COMMIT} got=${actual_commit}" >&2
    exit 1
  fi
  echo "Console web verify OK: SHA=${actual_commit} BUILD_TIME=${actual_time}"
else
  echo "Console web restarted with GIT_COMMIT=${EXPECTED_GIT_COMMIT} BUILD_TIME=${BUILD_TIME}"
fi
