#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/booking_quality_matrix_resumable.sh [options]

Runs resumable LLM-quality matrix for booking flows.
If <output>/summary.json already exists for a step, the step is skipped.

Options:
  --run-stamp <id>           Run prefix for /tmp/booking_quality paths.
                             Default: <UTC-date>-<worktree>-<hash>
  --run-nonce <id>           Extra run token for unique JIDs/output run_id.
                             Default: <UTC-hhmmss>-<pid>
  --output-root <path>       Artifact root.
                             Default: /tmp/booking_quality/<worktree>-<hash>
  --base-url <url>           API base URL. Default: http://localhost:8000
  --spawn-local-api          Start local uvicorn from ./truffles-api on a dedicated localhost port.
  --api-port <n>             Local API port when --spawn-local-api is enabled (default: auto-pick).
  --api-start-timeout <n>    Seconds to wait for local API readiness. Default: 60
  --keep-local-api           Keep spawned API process after matrix exits (debug).
  --client-slug <slug>       Client slug. Default: demo_salon
  --branches <csv>           Branch slugs. Default: main,branch_b
  --seeds <csv>              Seeds for generate/replay. Default: 42,1337,2026,9001
  --baseline-count <n>       Baseline dialog count. Default: 5
  --count <n>                Generate/replay dialog count. Default: 10
  --min-turns <n>            Min turns for generate runs. Default: 10
  --max-turns <n>            Max turns for generate runs. Default: 20
  --scenario-coverage <csv>  Coverage tags. Default: booking,info,interrupt,handoff
  --profile <fast|strict>    Runtime profile. Default: fast
  --jid-mode <mode>          JID mode for llm-quality. Default: unique
  --judge-mode <mode>        Judge mode (off/sample/all/critical). Default: sample
  --judge-sample <n>         Judge sample ratio for sample mode. Default: 0.35
  --baseline-summary <path>  Canonical baseline summary for non-replay runs.
                             Default: latest valid /tmp/booking_quality/*/summary.json
  --baseline-regression-tolerance <n>
                             Regression tolerance for baseline/generate runs. Default: 1.0
  --allowlist-jids <csv>     Optional JID allowlist override.
  --max-failures <n>         Stop after N failed turns (0 disables). Default: 20
  --retry-attempts <n>       Retries per failed step. Default: 3
  --retry-sleep <sec>        Base retry sleep (linear backoff). Default: 5
  --workdir <path>           Repo workdir. Default: current directory
  --help                     Show this help.

Examples:
  # Resume existing run without touching completed artifacts
  scripts/booking_quality_matrix_resumable.sh --run-stamp 20260207-stress

  # Start a new run stamp
  scripts/booking_quality_matrix_resumable.sh --run-stamp 20260208-stress
EOF
}

WORKTREE_KEY="$(basename "${PWD}")"
WORKTREE_HASH="$(printf '%s' "${PWD}" | sha1sum | cut -c1-6)"
RUN_STAMP="$(date -u +%Y%m%d)-${WORKTREE_KEY}-${WORKTREE_HASH}"
RUN_NONCE="$(date -u +%H%M%S)-$$"
OUTPUT_ROOT="/tmp/booking_quality/${WORKTREE_KEY}-${WORKTREE_HASH}"
BASE_URL="http://localhost:8000"
CLIENT_SLUG="demo_salon"
BRANCHES_CSV="main,branch_b"
SEEDS_CSV="42,1337,2026,9001"
BASELINE_COUNT=5
RUN_COUNT=10
MIN_TURNS=10
MAX_TURNS=20
SCENARIO_COVERAGE="booking,info,interrupt,handoff"
PROFILE="fast"
JID_MODE="unique"
JUDGE_MODE="sample"
JUDGE_SAMPLE="0.35"
BASELINE_SUMMARY=""
CANONICAL_BASELINE_SUMMARY=""
BASELINE_REGRESSION_TOLERANCE="1.0"
ALLOWLIST_JIDS=""
MAX_FAILURES=20
RETRY_ATTEMPTS=3
RETRY_SLEEP=5
WORKDIR="${PWD}"
SPAWN_LOCAL_API=0
API_PORT=""
API_START_TIMEOUT=60
KEEP_LOCAL_API=0
API_PID=""
API_LOG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-stamp) RUN_STAMP="$2"; shift 2 ;;
    --run-nonce) RUN_NONCE="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --spawn-local-api) SPAWN_LOCAL_API=1; shift ;;
    --api-port) API_PORT="$2"; shift 2 ;;
    --api-start-timeout) API_START_TIMEOUT="$2"; shift 2 ;;
    --keep-local-api) KEEP_LOCAL_API=1; shift ;;
    --client-slug) CLIENT_SLUG="$2"; shift 2 ;;
    --branches) BRANCHES_CSV="$2"; shift 2 ;;
    --seeds) SEEDS_CSV="$2"; shift 2 ;;
    --baseline-count) BASELINE_COUNT="$2"; shift 2 ;;
    --count) RUN_COUNT="$2"; shift 2 ;;
    --min-turns) MIN_TURNS="$2"; shift 2 ;;
    --max-turns) MAX_TURNS="$2"; shift 2 ;;
    --scenario-coverage) SCENARIO_COVERAGE="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --jid-mode) JID_MODE="$2"; shift 2 ;;
    --judge-mode) JUDGE_MODE="$2"; shift 2 ;;
    --judge-sample) JUDGE_SAMPLE="$2"; shift 2 ;;
    --baseline-summary) BASELINE_SUMMARY="$2"; shift 2 ;;
    --baseline-regression-tolerance) BASELINE_REGRESSION_TOLERANCE="$2"; shift 2 ;;
    --allowlist-jids) ALLOWLIST_JIDS="$2"; shift 2 ;;
    --max-failures) MAX_FAILURES="$2"; shift 2 ;;
    --retry-attempts) RETRY_ATTEMPTS="$2"; shift 2 ;;
    --retry-sleep) RETRY_SLEEP="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *)
      echo "[fatal] unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

cd "$WORKDIR"

REPORT="${OUTPUT_ROOT}/${RUN_STAMP}-matrix-report.tsv"
STATE_FILE="${OUTPUT_ROOT}/${RUN_STAMP}-state.json"
mkdir -p "$OUTPUT_ROOT"
LOCK_FILE="${OUTPUT_ROOT}/${RUN_STAMP}.lock"
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "[fatal] run already in progress for run-stamp=${RUN_STAMP} (lock=${LOCK_FILE})" >&2
    exit 1
  fi
fi

IFS=',' read -r -a BRANCHES <<< "$BRANCHES_CSV"
IFS=',' read -r -a SEEDS <<< "$SEEDS_CSV"
ALLOWLIST_ARGS=()
if [[ -n "$ALLOWLIST_JIDS" ]]; then
  ALLOWLIST_ARGS=(--allowlist-jids "$ALLOWLIST_JIDS")
fi

if [[ "$PROFILE" != "fast" && "$PROFILE" != "strict" ]]; then
  echo "[fatal] unsupported profile: $PROFILE" >&2
  exit 1
fi

if [[ "$JUDGE_MODE" != "off" && "$JUDGE_MODE" != "sample" && "$JUDGE_MODE" != "all" && "$JUDGE_MODE" != "critical" ]]; then
  echo "[fatal] unsupported judge-mode: $JUDGE_MODE" >&2
  exit 1
fi

if [[ "$PROFILE" == "fast" ]]; then
  LLM_TIMEOUT=10
  POLL_TIMEOUT=10
  TRACE_TIMEOUT=10
  POLL_INTERVAL=0.25
  TRACE_INTERVAL=0.25
  MIN_WAIT=0.05
  MAX_WAIT=0.12
  RETRY_COUNT=3
  RETRY_BACKOFF=0.2
  BATCH_SIZE=1
else
  LLM_TIMEOUT=12
  POLL_TIMEOUT=8
  TRACE_TIMEOUT=8
  POLL_INTERVAL=0.6
  TRACE_INTERVAL=0.6
  MIN_WAIT=0.2
  MAX_WAIT=0.5
  RETRY_COUNT=6
  RETRY_BACKOFF=0.6
  BATCH_SIZE=1
fi

JUDGE_ARGS=(--judge-mode "$JUDGE_MODE")
if [[ "$JUDGE_MODE" == "sample" ]]; then
  JUDGE_ARGS+=(--judge-sample "$JUDGE_SAMPLE")
fi

log() {
  printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"
}

pick_free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

cleanup_local_api() {
  if [[ -n "${API_PID:-}" && "${KEEP_LOCAL_API}" != "1" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi
}

start_local_api_if_needed() {
  if [[ "${SPAWN_LOCAL_API}" != "1" ]]; then
    return 0
  fi
  local env_file=""
  for candidate in \
    "truffles-api/.env" \
    "/home/zhan/truffles-main/truffles-api/.env"; do
    if [[ -f "${candidate}" ]]; then
      env_file="${candidate}"
      break
    fi
  done
  if [[ -z "${env_file}" ]]; then
    echo "[fatal] --spawn-local-api requires truffles-api/.env (worktree or canonical repo)" >&2
    exit 1
  fi
  if [[ -z "$API_PORT" ]]; then
    API_PORT="$(pick_free_port)"
  fi
  API_LOG="${OUTPUT_ROOT}/${RUN_STAMP}-api.log"
  set -a
  # shellcheck disable=SC1091
  source "${env_file}"
  set +a
  (
    cd truffles-api
    python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}" >"${API_LOG}" 2>&1
  ) &
  API_PID=$!
  BASE_URL="http://127.0.0.1:${API_PORT}"
  local i
  for ((i = 0; i < API_START_TIMEOUT; i++)); do
    if curl -fsS -m 2 "${BASE_URL}/admin/health" >/dev/null; then
      log "local API ready: base_url=${BASE_URL} pid=${API_PID}"
      trap cleanup_local_api EXIT
      return 0
    fi
    sleep 1
  done
  echo "[fatal] local API failed to start in ${API_START_TIMEOUT}s (base_url=${BASE_URL}, log=${API_LOG})" >&2
  cleanup_local_api
  exit 1
}

write_state() {
  local status="$1"
  local branch="${2:-}"
  local seed="${3:-}"
  local mode="${4:-}"
  local output="${5:-}"
  cat > "$STATE_FILE" <<EOF
{
  "status": "$status",
  "run_stamp": "$RUN_STAMP",
  "branch": "$branch",
  "seed": "$seed",
  "mode": "$mode",
  "output_dir": "$output",
  "updated_at": "$(date -u +%FT%TZ)"
}
EOF
}

ensure_openai_key() {
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "[fatal] docker not available and OPENAI_API_KEY is empty" >&2
    exit 1
  fi
  local key
  key="$(docker exec -i truffles-api /bin/sh -lc 'printf %s "${OPENAI_API_KEY:-}"' 2>/dev/null || true)"
  if [[ -z "$key" ]]; then
    echo "[fatal] missing OPENAI_API_KEY (env and truffles-api container)" >&2
    exit 1
  fi
  export OPENAI_API_KEY="$key"
}

assert_canonical_baseline() {
  local summary="$1"
  local infra semantic judge_enabled
  infra="$(jq -r '.infra_valid // false' "$summary")"
  semantic="$(jq -r '.semantic_valid // false' "$summary")"
  judge_enabled="$(jq -r '.judge.enabled // false' "$summary")"
  if [[ "$infra" != "true" || "$semantic" != "true" || "$judge_enabled" != "true" ]]; then
    echo "[fatal] baseline is not canonical: ${summary}" >&2
    jq -c '{infra_valid, semantic_valid, judge_enabled:(.judge.enabled // false), quality_status}' "$summary" >&2 || true
    exit 1
  fi
}

resolve_canonical_baseline_summary() {
  local candidate="${BASELINE_SUMMARY}"
  if [[ -z "$candidate" ]]; then
    candidate="$(python3 - <<'PY'
import glob
import json
import os

best_path = ""
best_mtime = -1.0
for path in glob.glob("/tmp/booking_quality/*/summary.json"):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        continue
    judge = payload.get("judge") if isinstance(payload.get("judge"), dict) else {}
    if (
        payload.get("infra_valid") is True
        and payload.get("semantic_valid") is True
        and judge.get("enabled") is True
    ):
        mtime = os.path.getmtime(path)
        if mtime > best_mtime:
            best_mtime = mtime
            best_path = path
print(best_path)
PY
)"
  fi
  if [[ -z "$candidate" ]]; then
    echo "[fatal] canonical baseline summary not found; pass --baseline-summary <path>" >&2
    exit 1
  fi
  if [[ ! -f "$candidate" ]]; then
    echo "[fatal] baseline summary not found: $candidate" >&2
    exit 1
  fi
  assert_canonical_baseline "$candidate"
  CANONICAL_BASELINE_SUMMARY="$(realpath "$candidate")"
  log "canonical baseline summary: ${CANONICAL_BASELINE_SUMMARY}"
}

append_report_row() {
  local branch="$1"
  local seed="$2"
  local mode="$3"
  local output="$4"
  local summary="${output}/summary.json"

  local pass unknown meta info_mismatch webhook infra
  pass="$(jq -r '.metrics.rates.pass_rate // "null"' "$summary")"
  unknown="$(jq -r '.metrics.rates.unknown_state_rate // "null"' "$summary")"
  meta="$(jq -r '.metrics.rates.decision_meta_coverage // "null"' "$summary")"
  info_mismatch="$(jq -r '.metrics.counts.info_mismatch // "null"' "$summary")"
  webhook="$(jq -r '.metrics.counts.webhook_errors // -1' "$summary")"
  infra="$(jq -r '.metrics.counts.infra_errors // -1' "$summary")"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$branch" "$seed" "$mode" "$output" "$pass" "$unknown" "$meta" "$info_mismatch" "$webhook" "$infra" >> "$REPORT"

  if [[ "$webhook" -gt 0 || "$infra" -gt 0 ]]; then
    log "stop-the-line: webhook_errors=${webhook} infra_errors=${infra} summary=${summary}"
    write_state "stopped" "$branch" "$seed" "$mode" "$output"
    exit 2
  fi
}

run_step() {
  local branch="$1"
  local seed="$2"
  local mode="$3"
  local output="$4"
  shift 4

  local summary="${output}/summary.json"
  local run_id
  run_id="$(printf '%s-%s-%s-%s-%s' "$RUN_STAMP" "$RUN_NONCE" "$branch" "$seed" "$mode" | tr ' /' '__')"
  if [[ -f "$summary" ]]; then
    log "skip completed step: branch=${branch} seed=${seed} mode=${mode} output=${output}"
    append_report_row "$branch" "$seed" "$mode" "$output"
    return 0
  fi

  write_state "running" "$branch" "$seed" "$mode" "$output"
  log "start step: branch=${branch} seed=${seed} mode=${mode} output=${output}"

  local attempt=1
  while [[ "$attempt" -le "$RETRY_ATTEMPTS" ]]; do
    rm -rf "$output"
    mkdir -p "$output"

    set +e
    TEST_MODE=1 python3 ops/diagnose.py llm-quality "$@" --run-id "$run_id" --output-dir "$output"
    local rc=$?
    set -e

    if [[ "$rc" -eq 0 && -f "$summary" ]]; then
      log "done step: branch=${branch} seed=${seed} mode=${mode}"
      append_report_row "$branch" "$seed" "$mode" "$output"
      return 0
    fi

    log "retry step: branch=${branch} seed=${seed} mode=${mode} attempt=${attempt}/${RETRY_ATTEMPTS} rc=${rc}"
    if [[ "$attempt" -ge "$RETRY_ATTEMPTS" ]]; then
      write_state "failed" "$branch" "$seed" "$mode" "$output"
      echo "[fatal] step failed after retries: branch=${branch} seed=${seed} mode=${mode}" >&2
      exit 1
    fi
    sleep $(( RETRY_SLEEP * attempt ))
    attempt=$(( attempt + 1 ))
  done
}

printf 'branch\tseed\tmode\toutput\tpass_rate\tunknown_state_rate\tdecision_meta_coverage\tinfo_mismatch\twebhook_errors\tinfra_errors\n' > "$REPORT"
write_state "starting"

ensure_openai_key
start_local_api_if_needed
resolve_canonical_baseline_summary

for branch in "${BRANCHES[@]}"; do
  baseline_out="${OUTPUT_ROOT}/${RUN_STAMP}-${branch}-baseline-c${BASELINE_COUNT}"
  run_step "$branch" "baseline" "baseline" "$baseline_out" \
    --mode llm \
    --base-url "$BASE_URL" \
    --client-slug "$CLIENT_SLUG" \
    --branch-slug "$branch" \
    --count "$BASELINE_COUNT" \
    --seed 777 \
    --min-turns "$MIN_TURNS" \
    --max-turns "$MAX_TURNS" \
    --include-media \
    --scenario-coverage "$SCENARIO_COVERAGE" \
    --baseline-summary "${CANONICAL_BASELINE_SUMMARY}" \
    --regression-tolerance "${BASELINE_REGRESSION_TOLERANCE}" \
    --tool-hooks auto \
    --reset-before-dialog \
    --jid-mode "$JID_MODE" \
    --max-failures "$MAX_FAILURES" \
    --batch-size "$BATCH_SIZE" \
    --retry-count "$RETRY_COUNT" \
    --retry-backoff "$RETRY_BACKOFF" \
    --timeout "$LLM_TIMEOUT" \
    --poll-timeout "$POLL_TIMEOUT" \
    --poll-interval "$POLL_INTERVAL" \
    --trace-timeout "$TRACE_TIMEOUT" \
    --trace-interval "$TRACE_INTERVAL" \
    --min-wait "$MIN_WAIT" \
    --max-wait "$MAX_WAIT" \
    "${JUDGE_ARGS[@]}" \
    "${ALLOWLIST_ARGS[@]}"
  assert_canonical_baseline "${baseline_out}/summary.json"

  for seed in "${SEEDS[@]}"; do
    gen_out="${OUTPUT_ROOT}/${RUN_STAMP}-${branch}-seed-${seed}-gen"
    run_step "$branch" "$seed" "generate" "$gen_out" \
      --mode llm \
      --base-url "$BASE_URL" \
      --client-slug "$CLIENT_SLUG" \
      --branch-slug "$branch" \
      --count "$RUN_COUNT" \
      --seed "$seed" \
      --min-turns "$MIN_TURNS" \
      --max-turns "$MAX_TURNS" \
      --include-media \
      --scenario-coverage "$SCENARIO_COVERAGE" \
      --baseline-summary "${CANONICAL_BASELINE_SUMMARY}" \
      --regression-tolerance "${BASELINE_REGRESSION_TOLERANCE}" \
      --tool-hooks auto \
      --reset-before-dialog \
      --jid-mode "$JID_MODE" \
      --max-failures "$MAX_FAILURES" \
      --batch-size "$BATCH_SIZE" \
      --retry-count "$RETRY_COUNT" \
      --retry-backoff "$RETRY_BACKOFF" \
      --timeout "$LLM_TIMEOUT" \
      --poll-timeout "$POLL_TIMEOUT" \
      --poll-interval "$POLL_INTERVAL" \
      --trace-timeout "$TRACE_TIMEOUT" \
      --trace-interval "$TRACE_INTERVAL" \
      --min-wait "$MIN_WAIT" \
      --max-wait "$MAX_WAIT" \
      "${JUDGE_ARGS[@]}" \
      "${ALLOWLIST_ARGS[@]}"

    replay_out="${OUTPUT_ROOT}/${RUN_STAMP}-${branch}-seed-${seed}-replay"
    run_step "$branch" "$seed" "replay" "$replay_out" \
      --base-url "$BASE_URL" \
      --client-slug "$CLIENT_SLUG" \
      --branch-slug "$branch" \
      --scenarios-file "${gen_out}/scenarios.json" \
      --baseline-summary "${baseline_out}/summary.json" \
      --count "$RUN_COUNT" \
      --tool-hooks auto \
      --reset-before-dialog \
      --jid-mode "$JID_MODE" \
      --max-failures "$MAX_FAILURES" \
      --batch-size "$BATCH_SIZE" \
      --retry-count "$RETRY_COUNT" \
      --retry-backoff "$RETRY_BACKOFF" \
      --timeout "$LLM_TIMEOUT" \
      --poll-timeout "$POLL_TIMEOUT" \
      --poll-interval "$POLL_INTERVAL" \
      --trace-timeout "$TRACE_TIMEOUT" \
      --trace-interval "$TRACE_INTERVAL" \
      --min-wait "$MIN_WAIT" \
      --max-wait "$MAX_WAIT" \
      "${JUDGE_ARGS[@]}" \
      "${ALLOWLIST_ARGS[@]}"
  done
done

write_state "done"
log "matrix done. report=${REPORT}"
