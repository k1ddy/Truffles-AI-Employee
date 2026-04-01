#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose-bge.yml"
PROJECT_NAME="truffles-bge"
SERVICE_NAME="bge-m3"
LOG_TAIL="${BGE_LOG_TAIL:-120}"

usage() {
  cat <<'EOF' >&2
Usage: start_bge_m3.sh [up|recreate|logs|ps|stop|down|config]

Canonical entrypoint for the BGE-M3 runtime.
Runs Docker Compose with an explicit project name so ownership does not depend on cwd.
EOF
  exit 64
}

compose() {
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
}

ensure_singleton_container_slot() {
  if docker ps -a --format '{{.Names}}' | grep -qx "${SERVICE_NAME}"; then
    docker rm -f "${SERVICE_NAME}" >/dev/null
  fi
}

command_name="${1:-up}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "${command_name}" in
  up|start|recreate|restart)
    ensure_singleton_container_slot
    compose up -d --force-recreate "$@" "${SERVICE_NAME}"
    ;;
  logs)
    compose logs --tail "${LOG_TAIL}" "$@" "${SERVICE_NAME}"
    ;;
  ps)
    compose ps "$@" "${SERVICE_NAME}"
    ;;
  stop)
    compose stop "$@" "${SERVICE_NAME}"
    ;;
  down)
    compose down "$@"
    ;;
  config)
    compose config "$@"
    ;;
  *)
    usage
    ;;
esac
