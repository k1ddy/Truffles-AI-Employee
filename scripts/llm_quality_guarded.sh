#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/llm_quality_guarded.sh \
    --mode <lock|replay|canary|full> \
    --run-id <id> \
    [--pg-checklist <path>] \
    [--owner-file <path>]... \
    [--quick-check <cmd>]... \
    [--allow-repeat-fingerprint] \
    [--allow-no-owner-delta] \
    [--allow-pending-previous] \
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

Reference:
  docs/runbooks/BOOKING_CONFIRM_VERIFY.md
  section: "Guarded llm-quality quickstart (single entrypoint)"
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
PG_CHECKLIST_PATH=""
ALLOW_REPEAT_FINGERPRINT=0
ALLOW_NO_OWNER_DELTA=0
ALLOW_PENDING_PREVIOUS=0
declare -a OWNER_FILES=()
declare -a QUICK_CHECKS=()
declare -a QUALITY_ARGS=()
HAS_RESUME=0
QUALITY_LANE_REQUESTED="auto"
FAIL_ON_THRESHOLDS=0
FAIL_ON_REGRESSION=0
UPDATE_BASELINE=0

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
    --pg-checklist)
      PG_CHECKLIST_PATH="$(trim "${2:-}")"
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
    --allow-pending-previous)
      ALLOW_PENDING_PREVIOUS=1
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
[[ "$MODE" =~ ^(lock|replay|canary|full)$ ]] || die "--mode must be one of: lock|replay|canary|full"
[[ -n "$RUN_ID" ]] || die "--run-id is required"
[[ ${#QUALITY_ARGS[@]} -gt 0 ]] || die "llm-quality args are required after --"

OUTPUT_DIR="/tmp/booking_quality/${RUN_ID}"
has_run_id_arg=0
has_output_dir_arg=0
has_chain_id_arg=0
has_chain_step_arg=0
has_chain_token_arg=0
for idx in "${!QUALITY_ARGS[@]}"; do
  arg="${QUALITY_ARGS[$idx]}"
  case "$arg" in
    --resume)
      HAS_RESUME=1
      ;;
    --run-id)
      has_run_id_arg=1
      ;;
    --output-dir)
      has_output_dir_arg=1
      next_idx=$((idx + 1))
      if [[ $next_idx -lt ${#QUALITY_ARGS[@]} ]]; then
        OUTPUT_DIR="${QUALITY_ARGS[$next_idx]}"
      fi
      ;;
    --quality-lane)
      next_idx=$((idx + 1))
      if [[ $next_idx -lt ${#QUALITY_ARGS[@]} ]]; then
        QUALITY_LANE_REQUESTED="$(trim "${QUALITY_ARGS[$next_idx]}")"
      fi
      ;;
    --fail-on-thresholds)
      FAIL_ON_THRESHOLDS=1
      ;;
    --fail-on-regression)
      FAIL_ON_REGRESSION=1
      ;;
    --update-baseline)
      UPDATE_BASELINE=1
      ;;
    --chain-id)
      has_chain_id_arg=1
      ;;
    --chain-step)
      has_chain_step_arg=1
      ;;
    --chain-token)
      has_chain_token_arg=1
      ;;
  esac
done

QUALITY_LANE_EFFECTIVE="$(printf '%s' "$QUALITY_LANE_REQUESTED" | tr '[:upper:]' '[:lower:]')"
if [[ "$QUALITY_LANE_EFFECTIVE" != "dev" && "$QUALITY_LANE_EFFECTIVE" != "acceptance" && "$QUALITY_LANE_EFFECTIVE" != "auto" ]]; then
  QUALITY_LANE_EFFECTIVE="auto"
fi
if [[ "$QUALITY_LANE_EFFECTIVE" == "auto" ]]; then
  if [[ "$FAIL_ON_THRESHOLDS" -eq 1 || "$FAIL_ON_REGRESSION" -eq 1 || "$UPDATE_BASELINE" -eq 1 ]]; then
    QUALITY_LANE_EFFECTIVE="acceptance"
  else
    QUALITY_LANE_EFFECTIVE="dev"
  fi
fi

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

LEDGER_DIR="${LLM_QUALITY_GUARD_LEDGER_DIR:-/tmp/booking_quality/_run_guard}"
LEDGER_FILE="$LEDGER_DIR/ledger.tsv"
mkdir -p "$LEDGER_DIR"
touch "$LEDGER_FILE"

if [[ "$ALLOW_REPEAT_FINGERPRINT" -ne 1 && "$HAS_RESUME" -ne 1 ]]; then
  last_match="$(awk -F'\t' -v m="$MODE" -v f="$FINGERPRINT" '$2==m && $4==f {line=$0} END{print line}' "$LEDGER_FILE")"
  if [[ -n "$last_match" ]]; then
    IFS=$'\t' read -r ts _ lm_run_id _ status summary <<<"$last_match"
    die "repeat fingerprint blocked (mode=$MODE run_id=$lm_run_id status=$status at $ts summary=$summary). Use --allow-repeat-fingerprint only with explicit reason."
  fi
fi

INDEX_ROOT="${LLM_QUALITY_INDEX_ROOT:-/tmp/booking_quality/_index}"
if [[ "$ALLOW_PENDING_PREVIOUS" -ne 1 && "$HAS_RESUME" -ne 1 ]]; then
  latest_mode_file="$INDEX_ROOT/latest_by_mode/${MODE}.json"
  if [[ -f "$latest_mode_file" ]]; then
    read -r last_run_id last_status last_audit last_artifacts <<EOF
$(python3 - "$latest_mode_file" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
print(
    (data.get("run_id") or ""),
    (data.get("status") or ""),
    (data.get("manual_audit_status") or ""),
    str(data.get("artifact_integrity_valid") or ""),
)
PY
)
EOF
    if [[ "$last_run_id" != "" ]]; then
      if [[ "$last_status" == "incomplete" || "$last_status" == "invalid" || "$last_status" == "failed" ]]; then
        die "previous run not canonical (mode=$MODE run_id=$last_run_id status=$last_status). Resolve artifacts/manual audit before new run or pass --allow-pending-previous."
      fi
      if [[ "$last_audit" != "" && "$last_audit" != "done" ]]; then
        die "previous run manual audit pending (mode=$MODE run_id=$last_run_id audit=$last_audit). Resolve before new run or pass --allow-pending-previous."
      fi
      if [[ "$last_artifacts" == "False" || "$last_artifacts" == "false" ]]; then
        die "previous run artifacts incomplete (mode=$MODE run_id=$last_run_id). Resolve before new run or pass --allow-pending-previous."
      fi
    fi
  fi
fi

if [[ -f "$INDEX_ROOT/by_mode/${MODE}/${RUN_ID}.json" && "$HAS_RESUME" -ne 1 ]]; then
  die "run_id already exists in index (mode=$MODE run_id=$RUN_ID). Choose a new run-id."
fi
if [[ "$HAS_RESUME" -eq 1 && ! -f "$INDEX_ROOT/by_mode/${MODE}/${RUN_ID}.json" ]]; then
  echo "[guard] resume requested but indexed run_id not found; continuing anyway" >&2
fi

for cmd in "${QUICK_CHECKS[@]}"; do
  [[ -n "$cmd" ]] || continue
  echo "[guard] quick-check: $cmd"
  bash -lc "$cmd"
done

CHAIN_CONTROLLER_BIN="${LLM_QUALITY_CHAIN_CONTROLLER_BIN:-scripts/quality_chain_controller.sh}"
DIAGNOSE_BIN="${LLM_QUALITY_DIAGNOSE_BIN:-python3}"
DIAGNOSE_SCRIPT="${LLM_QUALITY_DIAGNOSE_SCRIPT:-ops/diagnose.py}"
CHAIN_CONTROLLER_ACTIVE=0
CHAIN_ID=""
CHAIN_STEP=""
CHAIN_TOKEN=""

if [[ "$QUALITY_LANE_EFFECTIVE" == "acceptance" && "${LLM_QUALITY_CHAIN_CONTROLLER_INTERNAL:-0}" != "1" ]]; then
  if [[ "$has_chain_id_arg" -eq 1 || "$has_chain_step_arg" -eq 1 || "$has_chain_token_arg" -eq 1 ]]; then
    die "chain args are managed by quality_chain_controller; remove --chain-id/--chain-step/--chain-token from manual guarded runs"
  fi
  PG_CHECKLIST_EFFECTIVE="$PG_CHECKLIST_PATH"
  if [[ -z "$PG_CHECKLIST_EFFECTIVE" ]]; then
    PG_CHECKLIST_EFFECTIVE="${LLM_QUALITY_PG_CHECKLIST:-}"
  fi
  PG_CHECKLIST_EFFECTIVE="$(trim "$PG_CHECKLIST_EFFECTIVE")"
  if [[ "$MODE" == "lock" && "$HAS_RESUME" -ne 1 && -z "$PG_CHECKLIST_EFFECTIVE" ]]; then
    die "go-to-full gate requires --pg-checklist for acceptance lock run"
  fi
  if [[ ! -x "$CHAIN_CONTROLLER_BIN" ]]; then
    die "quality chain controller not executable: $CHAIN_CONTROLLER_BIN"
  fi
  declare -a PREPARE_CMD=("$CHAIN_CONTROLLER_BIN" "prepare" "--mode" "$MODE" "--run-id" "$RUN_ID" "--output-dir" "$OUTPUT_DIR")
  if [[ -n "$PG_CHECKLIST_EFFECTIVE" ]]; then
    PREPARE_CMD+=("--pg-checklist" "$PG_CHECKLIST_EFFECTIVE")
  fi
  if [[ "$HAS_RESUME" -eq 1 ]]; then
    PREPARE_CMD+=("--resume")
  fi
  PREPARE_OUTPUT="$("${PREPARE_CMD[@]}")" || die "chain controller prepare failed"
  IFS=$'\t' read -r CHAIN_ID CHAIN_STEP CHAIN_TOKEN <<<"$PREPARE_OUTPUT"
  [[ -n "$CHAIN_ID" && -n "$CHAIN_STEP" && -n "$CHAIN_TOKEN" ]] || die "chain controller prepare returned invalid tokens"
  CHAIN_CONTROLLER_ACTIVE=1
  echo "[guard] chain-controller active chain_id=$CHAIN_ID step=$CHAIN_STEP"
fi

declare -a CMD=("$DIAGNOSE_BIN" "$DIAGNOSE_SCRIPT" "llm-quality")
CMD+=("${QUALITY_ARGS[@]}")
if [[ "$has_run_id_arg" -ne 1 ]]; then
  CMD+=(--run-id "$RUN_ID")
fi
if [[ "$has_output_dir_arg" -ne 1 ]]; then
  CMD+=(--output-dir "$OUTPUT_DIR")
fi
if [[ "$CHAIN_CONTROLLER_ACTIVE" -eq 1 ]]; then
  CMD+=(--chain-id "$CHAIN_ID" --chain-step "$CHAIN_STEP" --chain-token "$CHAIN_TOKEN")
fi
CMD_STRING="$(printf '%q ' "${CMD[@]}")"

START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$START_TS" "$MODE" "$RUN_ID" "$FINGERPRINT" "started" "-" "$OUTPUT_DIR" "$CMD_STRING" >> "$LEDGER_FILE"

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

if [[ "$CHAIN_CONTROLLER_ACTIVE" -eq 1 ]]; then
  if ! "$CHAIN_CONTROLLER_BIN" finalize --mode "$MODE" --run-id "$RUN_ID" --output-dir "$OUTPUT_DIR" --summary-path "$SUMMARY_PATH" --exit-code "$EXIT_CODE" >/dev/null; then
    echo "[guard] chain-controller finalize failed for run_id=$RUN_ID" >&2
    if [[ "$EXIT_CODE" -eq 0 ]]; then
      EXIT_CODE=4
      STATUS_LABEL="chain_finalize_failed"
    fi
  fi
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
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$END_TS" "$MODE" "$RUN_ID" "$FINGERPRINT" "$STATUS_LABEL" "$SUMMARY_PATH" "$OUTPUT_DIR" "$CMD_STRING" >> "$LEDGER_FILE"

exit "$EXIT_CODE"
