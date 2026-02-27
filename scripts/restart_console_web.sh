#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${REPO_ROOT:-}" ]]; then
  repo_root="${REPO_ROOT}"
elif repo_root_candidate="$(git -C "${script_dir}" rev-parse --show-toplevel 2>/dev/null)"; then
  repo_root="${repo_root_candidate}"
else
  # Fallback for environments where .git is unavailable but scripts live under <repo>/scripts.
  repo_root="$(cd "${script_dir}/.." && pwd)"
fi

compose_file="${repo_root}/truffles-api/docker-compose.yml"

if [[ ! -f "$compose_file" ]]; then
  echo "ERROR: docker-compose file not found: ${compose_file}" >&2
  exit 1
fi

if [[ -z "${EXPECTED_GIT_COMMIT:-}" ]]; then
  if [[ -n "${GIT_COMMIT:-}" ]]; then
    EXPECTED_GIT_COMMIT="${GIT_COMMIT}"
  elif git -C "$repo_root" rev-parse HEAD >/dev/null 2>&1; then
    EXPECTED_GIT_COMMIT="$(git -C "$repo_root" rev-parse HEAD)"
  else
    EXPECTED_GIT_COMMIT="unknown"
  fi
fi
BUILD_TIME=${BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}
VERIFY_CONSOLE_BUILD=${VERIFY_CONSOLE_BUILD:-1}
CONSOLE_BUILD_MAX_ATTEMPTS=${CONSOLE_BUILD_MAX_ATTEMPTS:-3}
CONSOLE_BUILD_RETRY_DELAY_SECONDS=${CONSOLE_BUILD_RETRY_DELAY_SECONDS:-5}

if ! [[ "${CONSOLE_BUILD_MAX_ATTEMPTS}" =~ ^[0-9]+$ ]] || (( CONSOLE_BUILD_MAX_ATTEMPTS < 1 )); then
  echo "ERROR: CONSOLE_BUILD_MAX_ATTEMPTS must be integer >= 1, got '${CONSOLE_BUILD_MAX_ATTEMPTS}'" >&2
  exit 1
fi

if ! [[ "${CONSOLE_BUILD_RETRY_DELAY_SECONDS}" =~ ^[0-9]+$ ]] || (( CONSOLE_BUILD_RETRY_DELAY_SECONDS < 1 )); then
  echo "ERROR: CONSOLE_BUILD_RETRY_DELAY_SECONDS must be integer >= 1, got '${CONSOLE_BUILD_RETRY_DELAY_SECONDS}'" >&2
  exit 1
fi

export GIT_COMMIT="${EXPECTED_GIT_COMMIT}" BUILD_TIME

attempt=1
while true; do
  echo "Console web restart attempt ${attempt}/${CONSOLE_BUILD_MAX_ATTEMPTS}..."
  build_ok=0

  if docker compose -f "$compose_file" build console-web; then
    if docker compose -f "$compose_file" up -d console-web; then
      build_ok=1
    fi
  fi

  if (( build_ok == 1 )); then
    break
  fi

  if (( attempt >= CONSOLE_BUILD_MAX_ATTEMPTS )); then
    echo "ERROR: console-web restart failed after ${CONSOLE_BUILD_MAX_ATTEMPTS} attempts" >&2
    exit 1
  fi

  sleep_seconds=$((CONSOLE_BUILD_RETRY_DELAY_SECONDS * attempt))
  echo "WARN: console-web restart attempt ${attempt} failed; retrying in ${sleep_seconds}s..." >&2
  attempt=$((attempt + 1))
  sleep "${sleep_seconds}"
done

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
