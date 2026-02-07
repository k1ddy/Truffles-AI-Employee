#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/booking_quality_matrix_resumable.sh [options]

Runs resumable LLM-quality matrix for booking flows.
If <output>/summary.json already exists for a step, the step is skipped.

Options:
  --run-stamp <id>           Run prefix for /tmp/booking_quality paths.
                             Default: 20260207-stress
  --base-url <url>           API base URL. Default: http://localhost:8000
  --client-slug <slug>       Client slug. Default: demo_salon
  --branches <csv>           Branch slugs. Default: main,branch_b
  --seeds <csv>              Seeds for generate/replay. Default: 42,1337,2026,9001
  --baseline-count <n>       Baseline dialog count. Default: 5
  --count <n>                Generate/replay dialog count. Default: 10
  --min-turns <n>            Min turns for generate runs. Default: 10
  --max-turns <n>            Max turns for generate runs. Default: 20
  --scenario-coverage <csv>  Coverage tags. Default: booking,info,interrupt,handoff
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

RUN_STAMP="20260207-stress"
BASE_URL="http://localhost:8000"
CLIENT_SLUG="demo_salon"
BRANCHES_CSV="main,branch_b"
SEEDS_CSV="42,1337,2026,9001"
BASELINE_COUNT=5
RUN_COUNT=10
MIN_TURNS=10
MAX_TURNS=20
SCENARIO_COVERAGE="booking,info,interrupt,handoff"
ALLOWLIST_JIDS=""
MAX_FAILURES=20
RETRY_ATTEMPTS=3
RETRY_SLEEP=5
WORKDIR="${PWD}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-stamp) RUN_STAMP="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --client-slug) CLIENT_SLUG="$2"; shift 2 ;;
    --branches) BRANCHES_CSV="$2"; shift 2 ;;
    --seeds) SEEDS_CSV="$2"; shift 2 ;;
    --baseline-count) BASELINE_COUNT="$2"; shift 2 ;;
    --count) RUN_COUNT="$2"; shift 2 ;;
    --min-turns) MIN_TURNS="$2"; shift 2 ;;
    --max-turns) MAX_TURNS="$2"; shift 2 ;;
    --scenario-coverage) SCENARIO_COVERAGE="$2"; shift 2 ;;
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

REPORT="/tmp/booking_quality/${RUN_STAMP}-matrix-report.tsv"
STATE_FILE="/tmp/booking_quality/${RUN_STAMP}-state.json"
mkdir -p /tmp/booking_quality

IFS=',' read -r -a BRANCHES <<< "$BRANCHES_CSV"
IFS=',' read -r -a SEEDS <<< "$SEEDS_CSV"
ALLOWLIST_ARGS=()
if [[ -n "$ALLOWLIST_JIDS" ]]; then
  ALLOWLIST_ARGS=(--allowlist-jids "$ALLOWLIST_JIDS")
fi

log() {
  printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"
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
    TEST_MODE=1 python3 ops/diagnose.py llm-quality "$@" --output-dir "$output"
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

for branch in "${BRANCHES[@]}"; do
  baseline_out="/tmp/booking_quality/${RUN_STAMP}-${branch}-baseline-c${BASELINE_COUNT}"
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
    --tool-hooks auto \
    --reset-before-dialog \
    --max-failures "$MAX_FAILURES" \
    --batch-size 1 \
    --retry-count 6 \
    --judge-mode off \
    --timeout 12 \
    --poll-timeout 8 \
    --trace-timeout 8 \
    --min-wait 0.2 \
    --max-wait 0.5 \
    "${ALLOWLIST_ARGS[@]}"

  for seed in "${SEEDS[@]}"; do
    gen_out="/tmp/booking_quality/${RUN_STAMP}-${branch}-seed-${seed}-gen"
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
      --tool-hooks auto \
      --reset-before-dialog \
      --max-failures "$MAX_FAILURES" \
      --batch-size 1 \
      --retry-count 6 \
      --judge-mode off \
      --timeout 12 \
      --poll-timeout 8 \
      --trace-timeout 8 \
      --min-wait 0.2 \
      --max-wait 0.5 \
      "${ALLOWLIST_ARGS[@]}"

    replay_out="/tmp/booking_quality/${RUN_STAMP}-${branch}-seed-${seed}-replay"
    run_step "$branch" "$seed" "replay" "$replay_out" \
      --base-url "$BASE_URL" \
      --client-slug "$CLIENT_SLUG" \
      --branch-slug "$branch" \
      --scenarios-file "${gen_out}/scenarios.json" \
      --baseline-summary "${baseline_out}/summary.json" \
      --count "$RUN_COUNT" \
      --tool-hooks auto \
      --reset-before-dialog \
      --max-failures "$MAX_FAILURES" \
      --batch-size 1 \
      --retry-count 6 \
      --judge-mode off \
      --timeout 12 \
      --poll-timeout 8 \
      --trace-timeout 8 \
      --min-wait 0.2 \
      --max-wait 0.5 \
      "${ALLOWLIST_ARGS[@]}"
  done
done

write_state "done"
log "matrix done. report=${REPORT}"
