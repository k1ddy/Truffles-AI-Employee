#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
compose_file="${repo_root}/truffles-api/docker-compose.yml"

if [[ ! -f "$compose_file" ]]; then
  echo "ERROR: docker-compose file not found: ${compose_file}" >&2
  exit 1
fi

GIT_COMMIT=${GIT_COMMIT:-$(git -C "$repo_root" rev-parse HEAD)}
BUILD_TIME=${BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}

export GIT_COMMIT BUILD_TIME

docker compose -f "$compose_file" build console-web
docker compose -f "$compose_file" up -d console-web

echo "Console web restarted with GIT_COMMIT=${GIT_COMMIT} BUILD_TIME=${BUILD_TIME}"
