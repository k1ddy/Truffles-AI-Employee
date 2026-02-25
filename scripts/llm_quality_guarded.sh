#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/llm_quality_guarded.sh \
    --mode <lock|replay|full> \
    --run-id <id> \
    [--owner-file <path>]... \
    [--quick-check <cmd>]... \
    [--allow-repeat-fingerprint] \
    [--allow-no-owner-delta] \
    -- \
    <llm-quality args>

Example:
  scripts/llm_quality_guarded.sh \
    --mode replay \
    --run-id booking-replay-20260225-a1 \
    --owner-file ops/diagnose.py \
    --quick-check "pytest -q truffles-api/tests/test_booking_quality_status_gate.py" \
    -- \
    --base-url http://127.0.0.1:18100 \
    --client-slug demo_salon \
    --scenarios-file /tmp/booking_quality/booking-lock/scenarios.json \
    --baseline-summary /tmp/booking_quality/booking-lock/summary.json \
    --count 10 \
    --tool-hooks auto \
    --reset-before-dialog \
    --jid-mode unique \
    --judge-mode all \
    --fail-on-thresholds \
    --fail-on-regression \
    --run-economy-gate block
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 2
}

trim() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

owner_match_found() {
  local owner="$1"
  local path
  for path in "${CHANGED_PATHS[@]}"; do
    if [[ "$path" == "$owner" || "$path" == "$owner/"* ]]; then
      return 0
    fi
  done
  return 1
}

MODE=""
RUN_ID=""
ALLOW_REPEAT_FINGERPRINT=0
ALLOW_NO_OWNER_DELTA=0
declare -a OWNER_FILES=()
declare -a QUICK_CHECKS=()
declare -a QUALITY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$(trim "${2:-}")"
      shift 2
      ;;
    --run-id)
      RUN_ID="$(trim "${2:-}")"
      shift 2
      ;;
    --owner-file)
      OWNER_FILES+=("$(trim "${2:-}")")
      shift 2
      ;;
    --quick-check)
      QUICK_CHECKS+=("$(trim "${2:-}")")
      shift 2
      ;;
    --allow-repeat-fingerprint)
      ALLOW_REPEAT_FINGERPRINT=1
      shift
      ;;
    --allow-no-owner-delta)
      ALLOW_NO_OWNER_DELTA=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      QUALITY_ARGS=("$@")
      break
      ;;
    *)
      die "unknown argument: $1 (use --help)"
      ;;
  esac
done

[[ -n "$MODE" ]] || die "--mode is required"
[[ "$MODE" =~ ^(lock|replay|full)$ ]] || die "--mode must be one of: lock|replay|full"
[[ -n "$RUN_ID" ]] || die "--run-id is required"
[[ ${#QUALITY_ARGS[@]} -gt 0 ]] || die "llm-quality args are required after --"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

declare -a CHANGED_PATHS=()
while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  CHANGED_PATHS+=("$path")
done < <({ git diff --name-only; git diff --name-only --cached; } | sort -u)

if [[ ${#OWNER_FILES[@]} -gt 0 && "$ALLOW_NO_OWNER_DELTA" -ne 1 ]]; then
  OWNER_DELTA=0
  for owner in "${OWNER_FILES[@]}"; do
    [[ -n "$owner" ]] || continue
    if owner_match_found "$owner"; then
      OWNER_DELTA=1
      break
    fi
  done
  if [[ "$OWNER_DELTA" -ne 1 ]]; then
    die "no owner-file delta detected; changed paths do not match owner scope"
  fi
fi

BASE_SHA="$(git rev-parse HEAD)"
STATUS_LINES="$(git status --porcelain=v1)"
FILE_DIGEST_LINES=""
if [[ ${#CHANGED_PATHS[@]} -gt 0 ]]; then
  for path in "${CHANGED_PATHS[@]}"; do
    if [[ -f "$path" ]]; then
      digest="$(sha256sum "$path" | awk '{print $1}')"
      FILE_DIGEST_LINES+="${path}:${digest}"$'\n'
    else
      FILE_DIGEST_LINES+="${path}:deleted"$'\n'
    fi
  done
fi
FINGERPRINT="$(
  {
    printf '%s\n' "$BASE_SHA"
    printf '%s\n' "$STATUS_LINES"
    printf '%s' "$FILE_DIGEST_LINES"
  } | sha256sum | awk '{print $1}'
)"

LEDGER_DIR="/tmp/booking_quality/_run_guard"
LEDGER_FILE="$LEDGER_DIR/ledger.tsv"
mkdir -p "$LEDGER_DIR"
touch "$LEDGER_FILE"

if [[ "$ALLOW_REPEAT_FINGERPRINT" -ne 1 ]]; then
  last_match="$(awk -F'\t' -v m="$MODE" -v f="$FINGERPRINT" '$2==m && $4==f {line=$0} END{print line}' "$LEDGER_FILE")"
  if [[ -n "$last_match" ]]; then
    IFS=$'\t' read -r ts _ lm_run_id _ status summary <<<"$last_match"
    die "repeat fingerprint blocked (mode=$MODE run_id=$lm_run_id status=$status at $ts summary=$summary). Use --allow-repeat-fingerprint only with explicit reason."
  fi
fi

for cmd in "${QUICK_CHECKS[@]}"; do
  [[ -n "$cmd" ]] || continue
  echo "[guard] quick-check: $cmd"
  bash -lc "$cmd"
done

OUTPUT_DIR="/tmp/booking_quality/${RUN_ID}"
has_run_id_arg=0
has_output_dir_arg=0
for idx in "${!QUALITY_ARGS[@]}"; do
  arg="${QUALITY_ARGS[$idx]}"
  if [[ "$arg" == "--run-id" ]]; then
    has_run_id_arg=1
  fi
  if [[ "$arg" == "--output-dir" ]]; then
    has_output_dir_arg=1
    next_idx=$((idx + 1))
    if [[ $next_idx -lt ${#QUALITY_ARGS[@]} ]]; then
      OUTPUT_DIR="${QUALITY_ARGS[$next_idx]}"
    fi
  fi
done

declare -a CMD=(python3 ops/diagnose.py llm-quality)
CMD+=("${QUALITY_ARGS[@]}")
if [[ "$has_run_id_arg" -ne 1 ]]; then
  CMD+=(--run-id "$RUN_ID")
fi
if [[ "$has_output_dir_arg" -ne 1 ]]; then
  CMD+=(--output-dir "$OUTPUT_DIR")
fi

START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$START_TS" "$MODE" "$RUN_ID" "$FINGERPRINT" "started" "-" >> "$LEDGER_FILE"

echo "[guard] mode=$MODE run_id=$RUN_ID fingerprint=$FINGERPRINT"
set +e
"${CMD[@]}"
EXIT_CODE=$?
set -e

SUMMARY_PATH="${OUTPUT_DIR%/}/summary.json"
STATUS_LABEL="failed"
if [[ "$EXIT_CODE" -eq 0 ]]; then
  STATUS_LABEL="completed"
fi

if [[ -f "$SUMMARY_PATH" ]]; then
  INFRA_VALID="$(jq -r '.quality_status.infra_valid // .infra_valid // false' "$SUMMARY_PATH" 2>/dev/null || echo false)"
  SEMANTIC_VALID="$(jq -r '.quality_status.semantic_valid // .semantic_valid // false' "$SUMMARY_PATH" 2>/dev/null || echo false)"
  echo "[guard] summary=$SUMMARY_PATH infra_valid=$INFRA_VALID semantic_valid=$SEMANTIC_VALID"
  if [[ "$EXIT_CODE" -eq 0 && ( "$INFRA_VALID" != "true" || "$SEMANTIC_VALID" != "true" ) ]]; then
    EXIT_CODE=3
    STATUS_LABEL="invalid_quality"
  fi
fi

END_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$END_TS" "$MODE" "$RUN_ID" "$FINGERPRINT" "$STATUS_LABEL" "$SUMMARY_PATH" >> "$LEDGER_FILE"

exit "$EXIT_CODE"
