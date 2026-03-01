#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/quality_chain_controller.sh prepare --mode <lock|replay|full> --run-id <id> [--output-dir <dir>] [--chain-id <id>] [--resume] [--pg-checklist <path>]
  scripts/quality_chain_controller.sh finalize --mode <lock|replay|full> --run-id <id> [--output-dir <dir>] [--summary-path <path>] [--exit-code <n>] [--chain-id <id>]
  scripts/quality_chain_controller.sh status --chain-id <id>
  scripts/quality_chain_controller.sh close --chain-id <id>
  scripts/quality_chain_controller.sh abort --chain-id <id> [--reason <text>]

Aliases:
  start   -> prepare --mode lock
  resume  -> prepare --resume
  advance -> prepare
USAGE
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

COMMAND="${1:-}"
if [[ -z "$COMMAND" ]]; then
  usage
  exit 2
fi
shift || true

case "$COMMAND" in
  start)
    COMMAND="prepare"
    set -- --mode lock "$@"
    ;;
  resume)
    COMMAND="prepare"
    set -- --resume "$@"
    ;;
  advance)
    COMMAND="prepare"
    ;;
  prepare|finalize|status|close|abort)
    ;;
  --help|-h|help)
    usage
    exit 0
    ;;
  *)
    die "unknown command: $COMMAND"
    ;;
esac

MODE=""
RUN_ID=""
OUTPUT_DIR=""
CHAIN_ID=""
SUMMARY_PATH=""
EXIT_CODE="0"
RESUME_FLAG=0
ABORT_REASON=""
PG_CHECKLIST_PATH=""

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
    --output-dir)
      OUTPUT_DIR="$(trim "${2:-}")"
      shift 2
      ;;
    --chain-id)
      CHAIN_ID="$(trim "${2:-}")"
      shift 2
      ;;
    --summary-path)
      SUMMARY_PATH="$(trim "${2:-}")"
      shift 2
      ;;
    --exit-code)
      EXIT_CODE="$(trim "${2:-}")"
      shift 2
      ;;
    --resume)
      RESUME_FLAG=1
      shift
      ;;
    --pg-checklist)
      PG_CHECKLIST_PATH="$(trim "${2:-}")"
      shift 2
      ;;
    --reason)
      ABORT_REASON="$(trim "${2:-}")"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

CHAIN_ROOT="${LLM_QUALITY_CHAIN_ROOT:-/tmp/booking_quality/_chain}"

if [[ "$COMMAND" == "prepare" || "$COMMAND" == "finalize" ]]; then
  [[ -n "$MODE" ]] || die "--mode is required for $COMMAND"
  [[ "$MODE" =~ ^(lock|replay|full)$ ]] || die "--mode must be one of: lock|replay|full"
  [[ -n "$RUN_ID" ]] || die "--run-id is required for $COMMAND"
fi
if [[ "$COMMAND" == "status" || "$COMMAND" == "close" || "$COMMAND" == "abort" ]]; then
  [[ -n "$CHAIN_ID" ]] || die "--chain-id is required for $COMMAND"
fi
if [[ "$COMMAND" == "prepare" || "$COMMAND" == "finalize" ]]; then
  if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="/tmp/booking_quality/${RUN_ID}"
  fi
fi
if [[ "$COMMAND" == "finalize" && -z "$SUMMARY_PATH" ]]; then
  SUMMARY_PATH="${OUTPUT_DIR%/}/summary.json"
fi

python3 - "$COMMAND" "$CHAIN_ROOT" "$MODE" "$RUN_ID" "$OUTPUT_DIR" "$CHAIN_ID" "$SUMMARY_PATH" "$EXIT_CODE" "$RESUME_FLAG" "$ABORT_REASON" "$PG_CHECKLIST_PATH" <<'PY'
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

COMMAND = sys.argv[1]
CHAIN_ROOT = os.path.abspath(os.path.expanduser(sys.argv[2]))
MODE = (sys.argv[3] or "").strip().lower()
RUN_ID = (sys.argv[4] or "").strip()
OUTPUT_DIR = os.path.abspath(os.path.expanduser((sys.argv[5] or "").strip() or "."))
CHAIN_ID_ARG = (sys.argv[6] or "").strip()
SUMMARY_PATH = os.path.abspath(os.path.expanduser((sys.argv[7] or "").strip() or ""))
try:
    EXIT_CODE = int((sys.argv[8] or "0").strip() or 0)
except Exception:
    EXIT_CODE = 1
RESUME_FLAG = str(sys.argv[9] or "0").strip() == "1"
ABORT_REASON = (sys.argv[10] or "").strip() or "manual_abort"
PG_CHECKLIST_PATH = (sys.argv[11] or "").strip()

STEPS = ("lock", "replay", "full")
BLOCKERS = ("wrong_action", "handoff_miss", "booking_flow_break", "run_completion_gap")
GO_TO_FULL_KEYS = ("PG0", "PG1", "PG2", "PG3", "PG4", "PG5", "PG6")
DEFECT_MAPPING_KEYS = ("defect_class", "target_test", "gate", "owner")
VALID_DONE_AUDIT_STATES = {"done", "completed", "pass", "passed"}
DEFAULT_EVIDENCE_FRESHNESS_HOURS = 24.0
REPO_ROOT = os.path.abspath(
    os.path.expanduser(str(os.environ.get("LLM_QUALITY_REPO_ROOT") or os.getcwd()))
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def eprint(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def sanitize_chain_id(token: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", token or "").strip("-._")
    return safe


def derive_chain_id(run_id: str, explicit: str) -> str:
    if explicit:
        return sanitize_chain_id(explicit)
    matched = re.match(r"^booking-(lock|replay|full)-(.+)$", run_id, flags=re.IGNORECASE)
    if matched:
        return sanitize_chain_id(matched.group(2))
    return sanitize_chain_id(run_id)


def state_path(chain_id: str) -> str:
    return os.path.join(CHAIN_ROOT, f"{chain_id}.json")


def lock_path(path: str) -> str:
    return f"{path}.lock"


def load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_pg_entry(entry) -> bool:
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, (int, float)):
        return bool(entry)
    if isinstance(entry, str):
        token = entry.strip().casefold()
        return token in {"pass", "passed", "true", "ok", "done", "green"}
    if isinstance(entry, dict):
        if "pass" in entry:
            return bool(entry.get("pass"))
        status = str(entry.get("status") or "").strip().casefold()
        if status:
            return status in {"pass", "passed", "ok", "done", "green", "true"}
    return False


def parse_status_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in {"true", "1", "yes", "ok", "pass", "passed", "green"}:
            return True
        if token in {"false", "0", "no", "fail", "failed", "red"}:
            return False
    return None


def parse_datetime_utc(raw_value):
    token = str(raw_value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_evidence_freshness_hours(payload: dict, source: dict):
    raw_value = (
        source.get("evidence_freshness_hours")
        if isinstance(source, dict)
        else None
    )
    if raw_value in (None, "") and isinstance(payload, dict):
        raw_value = payload.get("evidence_freshness_hours")
    if raw_value in (None, ""):
        return DEFAULT_EVIDENCE_FRESHNESS_HOURS, None
    try:
        parsed = float(raw_value)
    except Exception:
        return None, "go_to_full_evidence_freshness_invalid"
    if parsed <= 0:
        return None, "go_to_full_evidence_freshness_invalid"
    return parsed, None


def validate_evidence_freshness(
    *,
    token,
    freshness_hours,
    primary_ts=None,
    fallback_ts=None,
):
    observed = parse_datetime_utc(primary_ts) or parse_datetime_utc(fallback_ts)
    if observed is None:
        return None, f"{token}_timestamp_missing"
    age_seconds = (datetime.now(timezone.utc) - observed).total_seconds()
    limit_seconds = float(freshness_hours) * 3600.0
    if age_seconds < 0:
        age_seconds = 0.0
    if age_seconds > limit_seconds:
        age_hours = age_seconds / 3600.0
        return None, f"{token}_stale:{age_hours:.2f}:{freshness_hours:.2f}"
    return observed.isoformat(), None


def normalize_path_token(path_value: str):
    token = str(path_value or "").replace("\\", "/").strip()
    while token.startswith("./"):
        token = token[2:]
    return token


def target_symbol_from_reference(target_ref: str):
    test_part = str(target_ref or "").split("::", 1)[1]
    return test_part.split("[", 1)[0].strip()


def pytest_entry_matches_target(entry: dict, target_path: str, target_symbol: str):
    if str(entry.get("status") or "").strip().casefold() != "passed":
        return False
    case_name = str(entry.get("name") or "").strip()
    if not case_name:
        return False
    case_symbol = case_name.split("[", 1)[0].strip()
    if case_symbol != target_symbol:
        return False

    target_norm = normalize_path_token(target_path)
    target_abs = os.path.abspath(os.path.join(REPO_ROOT, target_norm))
    file_attr = normalize_path_token(entry.get("file") or "")
    if file_attr:
        file_abs = os.path.abspath(file_attr)
        if os.path.isabs(file_attr):
            return file_abs == target_abs
        return file_attr.endswith(target_norm) or file_abs == target_abs

    class_attr = str(entry.get("classname") or "").strip()
    if class_attr:
        class_path = normalize_path_token(class_attr.replace(".", "/"))
        target_no_ext = target_norm[:-3] if target_norm.endswith(".py") else target_norm
        if class_path.endswith(target_no_ext):
            return True
    return False


def parse_pytest_junit(path: str):
    try:
        tree = ET.parse(path)
    except Exception:
        return None, "go_to_full_l1_report_unreadable"
    root = tree.getroot()
    testsuite = root
    if root.tag == "testsuites":
        testsuite = root.find("testsuite")
    if testsuite is None:
        return None, "go_to_full_l1_report_unreadable"
    entries = []
    for testcase in testsuite.iter("testcase"):
        status = "passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            status = "failed"
        elif testcase.find("skipped") is not None:
            status = "skipped"
        entries.append(
            {
                "name": testcase.attrib.get("name"),
                "classname": testcase.attrib.get("classname"),
                "file": testcase.attrib.get("file"),
                "status": status,
            }
        )
    return {
        "entries": entries,
        "timestamp": testsuite.attrib.get("timestamp"),
    }, None


def load_pg_checklist(path: str):
    token = str(path or "").strip()
    if not token:
        token = str(os.environ.get("LLM_QUALITY_PG_CHECKLIST") or "").strip()
    if not token:
        return None, "go_to_full_gate_required:missing_pg_checklist"
    normalized = os.path.abspath(os.path.expanduser(token))
    payload = load_json(normalized)
    if not isinstance(payload, dict):
        return None, f"go_to_full_gate_invalid:unreadable:{normalized}"

    gate_payload = payload.get("go_to_full")
    if isinstance(gate_payload, dict):
        source = gate_payload
    else:
        source = payload

    missing = []
    failed = []
    statuses = {}
    for key in GO_TO_FULL_KEYS:
        if key not in source:
            missing.append(key)
            continue
        passed = parse_pg_entry(source.get(key))
        statuses[key] = passed
        if not passed:
            failed.append(key)

    if missing:
        return None, "go_to_full_gate_missing:" + ",".join(missing)
    if failed:
        return None, "go_to_full_gate_failed:" + ",".join(failed)

    root_cause_statement = str(
        source.get("root_cause_statement")
        or payload.get("root_cause_statement")
        or ""
    ).strip()
    if not root_cause_statement:
        return None, "go_to_full_root_cause_missing"

    mapping = source.get("defect_mapping")
    if not isinstance(mapping, list):
        mapping = payload.get("defect_mapping")
    if not isinstance(mapping, list) or not mapping:
        return None, "go_to_full_mapping_missing"

    invalid_rows = []
    for index, row in enumerate(mapping):
        if not isinstance(row, dict):
            invalid_rows.append(f"{index}:not_object")
            continue
        missing_row_fields = []
        for field in DEFECT_MAPPING_KEYS:
            value = str(row.get(field) or "").strip()
            if not value:
                missing_row_fields.append(field)
        gate_value = str(row.get("gate") or "").strip()
        if gate_value and gate_value not in GO_TO_FULL_KEYS:
            missing_row_fields.append("gate_invalid")
        target_ref = str(row.get("target_test") or "").strip()
        target_valid, target_reason = validate_target_test_reference(target_ref)
        if not target_valid:
            missing_row_fields.append(target_reason or "target_test_invalid")
        if missing_row_fields:
            invalid_rows.append(f"{index}:{','.join(missing_row_fields)}")
    if invalid_rows:
        return None, "go_to_full_mapping_invalid:" + ";".join(invalid_rows)

    freshness_hours, freshness_error = resolve_evidence_freshness_hours(payload, source)
    if freshness_error:
        return None, freshness_error

    target_tests = [
        str(row.get("target_test") or "").strip()
        for row in mapping
        if isinstance(row, dict) and str(row.get("target_test") or "").strip()
    ]
    l1_evidence, l1_error = validate_l1_evidence(
        payload,
        source,
        target_tests=target_tests,
        freshness_hours=freshness_hours,
    )
    if l1_error:
        return None, l1_error

    l2_evidence, l2_error = validate_l2_evidence(
        payload,
        source,
        freshness_hours=freshness_hours,
    )
    if l2_error:
        return None, l2_error

    result = {
        "path": normalized,
        "keys": list(GO_TO_FULL_KEYS),
        "status": {key: bool(statuses.get(key)) for key in GO_TO_FULL_KEYS},
        "root_cause_statement": root_cause_statement,
        "defect_mapping_count": len(mapping),
        "evidence_freshness_hours": freshness_hours,
        "l1_evidence": l1_evidence,
        "l2_evidence": l2_evidence,
    }
    return result, None


def validate_target_test_reference(target_ref: str):
    token = str(target_ref or "").strip()
    if not token:
        return False, "target_test_missing"
    if "::" not in token:
        return False, "target_test_format_invalid"
    path_part, test_part = token.split("::", 1)
    path_part = path_part.strip()
    test_part = test_part.strip()
    if not path_part or not test_part:
        return False, "target_test_format_invalid"

    resolved_path = path_part
    if not os.path.isabs(resolved_path):
        resolved_path = os.path.join(REPO_ROOT, resolved_path)
    resolved_path = os.path.abspath(os.path.expanduser(resolved_path))
    if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
        return False, "target_test_path_missing"

    # Keep this check lightweight and deterministic: ensure test symbol exists in file text.
    test_symbol = test_part.split("[", 1)[0].strip()
    if not test_symbol:
        return False, "target_test_symbol_missing"
    try:
        with open(resolved_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except Exception:
        return False, "target_test_file_unreadable"
    if test_symbol not in content:
        return False, "target_test_symbol_missing"
    return True, None


def validate_l1_evidence(payload: dict, source: dict, *, target_tests, freshness_hours):
    evidence = source.get("l1_evidence")
    if not isinstance(evidence, dict):
        evidence = payload.get("l1_evidence")
    if not isinstance(evidence, dict):
        return None, "go_to_full_l1_evidence_missing"

    junit_path_token = str(
        evidence.get("junit_xml_path")
        or evidence.get("report_path")
        or ""
    ).strip()
    if not junit_path_token:
        return None, "go_to_full_l1_report_path_missing"
    junit_path = os.path.abspath(os.path.expanduser(junit_path_token))
    if not os.path.exists(junit_path) or not os.path.isfile(junit_path):
        return None, f"go_to_full_l1_report_missing:{junit_path}"
    parsed_report, report_error = parse_pytest_junit(junit_path)
    if report_error:
        return None, report_error
    report_entries = parsed_report.get("entries") if isinstance(parsed_report, dict) else []
    if not isinstance(report_entries, list):
        report_entries = []

    missing_targets = []
    for target_ref in target_tests:
        if "::" not in target_ref:
            missing_targets.append(target_ref)
            continue
        path_part, _ = target_ref.split("::", 1)
        symbol = target_symbol_from_reference(target_ref)
        matched = any(
            pytest_entry_matches_target(entry, path_part, symbol)
            for entry in report_entries
            if isinstance(entry, dict)
        )
        if not matched:
            missing_targets.append(target_ref)
    if missing_targets:
        return None, "go_to_full_l1_target_not_passed:" + ",".join(missing_targets)

    report_mtime_iso = datetime.fromtimestamp(
        os.path.getmtime(junit_path),
        tz=timezone.utc,
    ).isoformat()
    freshness_timestamp, freshness_error = validate_evidence_freshness(
        token="go_to_full_l1_evidence",
        freshness_hours=freshness_hours,
        primary_ts=evidence.get("recorded_at") or (parsed_report or {}).get("timestamp"),
        fallback_ts=report_mtime_iso,
    )
    if freshness_error:
        return None, freshness_error

    return {
        "junit_xml_path": junit_path,
        "target_tests": list(target_tests),
        "recorded_at": freshness_timestamp,
    }, None


def validate_l2_evidence(payload: dict, source: dict, *, freshness_hours):
    evidence = source.get("l2_evidence")
    if not isinstance(evidence, dict):
        evidence = payload.get("l2_evidence")
    if not isinstance(evidence, dict):
        return None, "go_to_full_l2_evidence_missing"

    summary_path_token = str(evidence.get("summary_path") or "").strip()
    if not summary_path_token:
        return None, "go_to_full_l2_summary_path_missing"
    summary_path = os.path.abspath(os.path.expanduser(summary_path_token))
    if not os.path.exists(summary_path) or not os.path.isfile(summary_path):
        return None, f"go_to_full_l2_summary_missing:{summary_path}"
    summary = load_json(summary_path)
    if not isinstance(summary, dict):
        return None, "go_to_full_l2_summary_unreadable"

    quality_status = summary.get("quality_status")
    if not isinstance(quality_status, dict):
        quality_status = {}
    infra_valid = parse_status_bool(quality_status.get("infra_valid"))
    if infra_valid is None:
        infra_valid = parse_status_bool(summary.get("infra_valid"))
    semantic_valid = parse_status_bool(quality_status.get("semantic_valid"))
    if semantic_valid is None:
        semantic_valid = parse_status_bool(summary.get("semantic_valid"))
    run_integrity_valid = parse_status_bool(quality_status.get("run_integrity_valid"))
    if run_integrity_valid is None:
        run_integrity_valid = parse_status_bool(summary.get("run_integrity_valid"))
    if infra_valid is not True or semantic_valid is not True or run_integrity_valid is not True:
        return None, "go_to_full_l2_not_green"

    manual_audit_status = str(
        quality_status.get("manual_audit_status")
        or summary.get("manual_audit_status")
        or ""
    ).strip().casefold()
    if manual_audit_status and manual_audit_status not in VALID_DONE_AUDIT_STATES:
        return None, f"go_to_full_l2_manual_audit_incomplete:{manual_audit_status}"

    config = summary.get("config")
    if not isinstance(config, dict):
        config = {}
    lane_token = str(
        quality_status.get("quality_lane_effective")
        or config.get("quality_lane_effective")
        or config.get("quality_lane")
        or summary.get("quality_lane_effective")
        or summary.get("quality_lane")
        or ""
    ).strip().casefold()
    if lane_token == "acceptance":
        return None, "go_to_full_l2_lane_invalid:acceptance"

    expected_run_id = str(evidence.get("run_id") or "").strip()
    observed_run_id = str(summary.get("run_id") or "").strip()
    if expected_run_id and observed_run_id and expected_run_id != observed_run_id:
        return None, f"go_to_full_l2_run_id_mismatch:{expected_run_id}:{observed_run_id}"

    summary_mtime_iso = datetime.fromtimestamp(
        os.path.getmtime(summary_path),
        tz=timezone.utc,
    ).isoformat()
    freshness_timestamp, freshness_error = validate_evidence_freshness(
        token="go_to_full_l2_evidence",
        freshness_hours=freshness_hours,
        primary_ts=evidence.get("recorded_at") or summary.get("finished_at"),
        fallback_ts=summary_mtime_iso,
    )
    if freshness_error:
        return None, freshness_error

    return {
        "summary_path": summary_path,
        "run_id": observed_run_id or expected_run_id or None,
        "infra_valid": True,
        "semantic_valid": True,
        "run_integrity_valid": True,
        "manual_audit_status": manual_audit_status or None,
        "lane_effective": lane_token or None,
        "recorded_at": freshness_timestamp,
    }, None


def write_json_atomic(path: str, payload: dict) -> None:
    tmp_path = f"{path}.tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def run_id_mode_ok(run_id: str, mode: str):
    token = (run_id or "").strip().lower()
    if token.startswith("booking-"):
        expected = f"booking-{mode}-"
        if not token.startswith(expected):
            observed = token.split("-", 3)
            observed_mode = observed[1] if len(observed) > 1 else "unknown"
            return False, f"run_id_mode_mismatch:{mode}:{observed_mode}"
    return True, None


def step_next(mode: str):
    if mode == "lock":
        return "replay"
    if mode == "replay":
        return "full"
    return None


def infer_step_status(summary: dict | None, manifest: dict | None, exit_code: int) -> str:
    summary = summary if isinstance(summary, dict) else {}
    manifest = manifest if isinstance(manifest, dict) else {}
    quality = summary.get("quality_status") if isinstance(summary.get("quality_status"), dict) else {}
    infra_valid = summary.get("infra_valid")
    if infra_valid is None:
        infra_valid = quality.get("infra_valid")
    semantic_valid = summary.get("semantic_valid")
    if semantic_valid is None:
        semantic_valid = quality.get("semantic_valid")
    run_integrity_valid = quality.get("run_integrity_valid")
    if run_integrity_valid is None:
        run_integrity_valid = summary.get("run_integrity_valid")
    if infra_valid is True and semantic_valid is True and run_integrity_valid is True:
        return "canonical"

    manifest_status = str(manifest.get("status") or "").strip().lower()
    stop_reason = str(summary.get("stop_reason") or manifest.get("stop_reason") or "").strip().lower()
    if manifest_status == "incomplete" or stop_reason in {
        "in_progress",
        "signal_2",
        "signal_15",
        "system_exit",
        "keyboard_interrupt",
    }:
        return "incomplete"
    if exit_code == 0:
        return "invalid"
    return "failed"


def derive_target_blocker_total(summary: dict | None) -> tuple[int, int]:
    summary = summary if isinstance(summary, dict) else {}
    blocking = summary.get("blocking_reasons") if isinstance(summary.get("blocking_reasons"), dict) else {}
    reason_counts = blocking.get("reasons") if isinstance(blocking.get("reasons"), dict) else {}
    total = 0
    for key in BLOCKERS:
        try:
            total += int(reason_counts.get(key) or 0)
        except Exception:
            continue
    judge = summary.get("judge") if isinstance(summary.get("judge"), dict) else {}
    judge_counts = judge.get("counts") if isinstance(judge.get("counts"), dict) else {}
    try:
        judged = int(judge_counts.get("judged") or 0)
    except Exception:
        judged = 0
    return total, judged


def replace_mode_in_run_id(run_id: str, next_mode: str) -> str:
    match = re.match(r"^booking-(lock|replay|full)-(.+)$", run_id)
    if match:
        return f"booking-{next_mode}-{match.group(2)}"
    return f"booking-{next_mode}-{run_id}"


def build_next_command(state: dict, *, mode: str, run_id: str, output_dir: str, step_status: str) -> str | None:
    steps = state.get("steps") if isinstance(state.get("steps"), dict) else {}
    if state.get("status") == "blocked":
        return None
    if step_status == "incomplete":
        return (
            f"scripts/llm_quality_guarded.sh --mode {mode} --run-id {run_id} -- "
            f"--resume --output-dir {output_dir} --quality-lane acceptance"
        )
    if step_status != "canonical":
        return (
            f"scripts/llm_quality_guarded.sh --mode {mode} --run-id {run_id} -- "
            f"--quality-lane acceptance"
        )

    next_mode = step_next(mode)
    if not next_mode:
        return None
    next_run_id = replace_mode_in_run_id(run_id, next_mode)

    lock_output_dir = ""
    lock_entry = steps.get("lock") if isinstance(steps.get("lock"), dict) else {}
    if isinstance(lock_entry.get("output_dir"), str) and lock_entry.get("output_dir"):
        lock_output_dir = lock_entry.get("output_dir")

    if next_mode == "replay":
        if lock_output_dir:
            return (
                f"scripts/llm_quality_guarded.sh --mode replay --run-id {next_run_id} -- "
                f"--scenarios-file {lock_output_dir}/scenarios.json --baseline-summary {lock_output_dir}/summary.json "
                "--reset-before-dialog --quality-lane acceptance"
            )
        return (
            f"scripts/llm_quality_guarded.sh --mode replay --run-id {next_run_id} -- "
            "--scenarios-file <lock_output_dir>/scenarios.json --baseline-summary <lock_output_dir>/summary.json "
            "--reset-before-dialog --quality-lane acceptance"
        )
    if next_mode == "full":
        if lock_output_dir:
            return (
                f"scripts/llm_quality_guarded.sh --mode full --run-id {next_run_id} -- "
                f"--baseline-summary {lock_output_dir}/summary.json --quality-lane acceptance"
            )
        return (
            f"scripts/llm_quality_guarded.sh --mode full --run-id {next_run_id} -- "
            "--baseline-summary <lock_output_dir>/summary.json --quality-lane acceptance"
        )
    return None


def write_brief(state: dict, *, chain_id: str, output_dir: str, mode: str, run_id: str, step_status: str, next_command: str | None):
    status = str(state.get("status") or "active")
    blocked_reason = str(state.get("blocked_reason") or "").strip()
    lines = [
        f"# Chain Brief: {chain_id}",
        "",
        f"- status: `{status}`",
        f"- current_step: `{state.get('current_step')}`",
        f"- last_mode: `{mode}`",
        f"- last_run_id: `{run_id}`",
        f"- last_step_status: `{step_status}`",
    ]
    if blocked_reason:
        lines.append(f"- blocked_reason: `{blocked_reason}`")
    roi = state.get("roi") if isinstance(state.get("roi"), dict) else {}
    lines.append(
        f"- roi_consecutive_no_improve: `{int(roi.get('consecutive_no_improve') or 0)}`"
    )
    lines.append("")
    lines.append("## Next")
    if next_command:
        lines.append(f"- command: `{next_command}`")
    else:
        lines.append("- command: n/a")

    brief_text = "\n".join(lines) + "\n"
    brief_paths = []
    if output_dir:
        brief_paths.append(os.path.join(output_dir, "brief_for_next_agent.md"))
    brief_paths.append(os.path.join(CHAIN_ROOT, f"{chain_id}-brief_for_next_agent.md"))
    for path in brief_paths:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(brief_text)
        except Exception:
            continue


def with_lock(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lock_fp = open(lock_path(path), "a+", encoding="utf-8")
    if fcntl is not None:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
    return lock_fp


def ensure_state_defaults(state: dict, chain_id: str) -> dict:
    state = state if isinstance(state, dict) else {}
    steps = state.get("steps") if isinstance(state.get("steps"), dict) else {}
    for step in STEPS:
        entry = steps.get(step)
        if not isinstance(entry, dict):
            entry = {"status": "idle", "run_id": None, "output_dir": None, "updated_at": None}
            steps[step] = entry
    state["steps"] = steps
    state.setdefault("chain_id", chain_id)
    state.setdefault("lane", "acceptance")
    state.setdefault("status", "active")
    state.setdefault("current_step", "lock")
    active = state.get("active") if isinstance(state.get("active"), dict) else {}
    state["active"] = {
        "step": active.get("step") or "lock",
        "run_id": active.get("run_id") or "",
        "token": active.get("token") or "",
        "resume_required": bool(active.get("resume_required")),
        "output_dir": active.get("output_dir") or "",
        "updated_at": active.get("updated_at") or now_iso(),
    }
    roi = state.get("roi") if isinstance(state.get("roi"), dict) else {}
    state["roi"] = {
        "target_blockers": list(roi.get("target_blockers") or BLOCKERS),
        "last_target_total": roi.get("last_target_total"),
        "consecutive_no_improve": int(roi.get("consecutive_no_improve") or 0),
        "expensive_no_improve_limit": int(roi.get("expensive_no_improve_limit") or 3),
        "judge_threshold": int(roi.get("judge_threshold") or 20),
    }
    state.setdefault("history", [])
    state.setdefault("next_command", None)
    state.setdefault("blocked_reason", None)
    state["updated_at"] = now_iso()
    return state


def expected_step_for_prepare(state: dict):
    current = str(state.get("current_step") or "").strip().lower()
    steps = state.get("steps") if isinstance(state.get("steps"), dict) else {}
    if current not in STEPS:
        return "lock", False, None
    current_entry = steps.get(current) if isinstance(steps.get(current), dict) else {}
    current_status = str(current_entry.get("status") or "").strip().lower()
    if current_status in {"running", "incomplete"}:
        current_run_id = str(current_entry.get("run_id") or state.get("active", {}).get("run_id") or "").strip()
        return current, True, current_run_id or None
    if current_status == "canonical":
        next_step = step_next(current)
        return next_step, False, None
    return current, False, None


def ensure_previous_step_brief(state: dict, mode: str):
    if mode == "lock":
        return True, None
    prev_mode = "lock" if mode == "replay" else "replay"
    steps = state.get("steps") if isinstance(state.get("steps"), dict) else {}
    prev_entry = steps.get(prev_mode) if isinstance(steps.get(prev_mode), dict) else {}
    if str(prev_entry.get("status") or "").strip().lower() != "canonical":
        return True, None
    output_dir = str(prev_entry.get("output_dir") or "").strip()
    if not output_dir:
        return False, f"missing_brief_for_next_agent:{prev_mode}"
    brief_path = os.path.join(output_dir, "brief_for_next_agent.md")
    if not os.path.exists(brief_path):
        return False, f"missing_brief_for_next_agent:{prev_mode}"
    return True, None


def enforce_go_to_full_gate(mode: str, resume_required: bool):
    if mode != "lock":
        return None, None
    if resume_required:
        # Existing interrupted lock already passed this gate before.
        return None, None
    return load_pg_checklist(PG_CHECKLIST_PATH)


def cmd_prepare():
    chain_id = derive_chain_id(RUN_ID, CHAIN_ID_ARG)
    if not chain_id:
        eprint("chain_id_invalid")
        raise SystemExit(2)
    path = state_path(chain_id)
    _lock = with_lock(path)
    try:
        existing = load_json(path)
        if existing is None:
            if MODE != "lock":
                eprint("chain_start_requires_lock")
                raise SystemExit(2)
            existing = {
                "chain_id": chain_id,
                "lane": "acceptance",
                "status": "active",
                "current_step": "lock",
            }
        state = ensure_state_defaults(existing, chain_id)

        status = str(state.get("status") or "").strip().lower()
        if status in {"blocked", "aborted"}:
            eprint(f"chain_blocked:{status}")
            raise SystemExit(2)

        expected_step, resume_required, expected_run_id = expected_step_for_prepare(state)
        if expected_step is None:
            eprint("chain_already_closed")
            raise SystemExit(2)
        if MODE != expected_step:
            eprint(f"chain_step_order_violation:{MODE}:{expected_step}")
            raise SystemExit(2)

        ok, reason = ensure_previous_step_brief(state, MODE)
        if not ok:
            eprint(reason or "missing_brief_for_next_agent")
            raise SystemExit(2)

        mode_ok, mode_reason = run_id_mode_ok(RUN_ID, MODE)
        if not mode_ok:
            eprint(mode_reason or "run_id_mode_mismatch")
            raise SystemExit(2)

        if resume_required and not RESUME_FLAG:
            eprint("chain_resume_required")
            raise SystemExit(2)
        if RESUME_FLAG and expected_run_id and expected_run_id != RUN_ID:
            eprint(f"chain_resume_run_id_mismatch:{expected_run_id}:{RUN_ID}")
            raise SystemExit(2)
        if (not RESUME_FLAG) and resume_required and expected_run_id and expected_run_id == RUN_ID:
            eprint("chain_resume_required")
            raise SystemExit(2)

        gate_payload, gate_error = enforce_go_to_full_gate(MODE, resume_required)
        if gate_error:
            eprint(gate_error)
            raise SystemExit(2)

        token = re.sub("-", "", os.urandom(16).hex())
        step_entry = state["steps"].get(MODE, {})
        step_entry.update(
            {
                "status": "running",
                "run_id": RUN_ID,
                "output_dir": OUTPUT_DIR,
                "go_to_full": gate_payload if isinstance(gate_payload, dict) else None,
                "updated_at": now_iso(),
            }
        )
        state["steps"][MODE] = step_entry
        state["active"] = {
            "step": MODE,
            "run_id": RUN_ID,
            "token": token,
            "resume_required": False,
            "output_dir": OUTPUT_DIR,
            "updated_at": now_iso(),
        }
        state["current_step"] = MODE
        state["status"] = "active"
        state["blocked_reason"] = None
        state["updated_at"] = now_iso()
        write_json_atomic(path, state)

        print(f"{chain_id}\t{MODE}\t{token}")
    finally:
        if fcntl is not None:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        _lock.close()


def cmd_finalize():
    chain_id = derive_chain_id(RUN_ID, CHAIN_ID_ARG)
    if not chain_id:
        eprint("chain_id_invalid")
        raise SystemExit(2)
    path = state_path(chain_id)
    _lock = with_lock(path)
    try:
        existing = load_json(path)
        if not isinstance(existing, dict):
            eprint("chain_state_missing")
            raise SystemExit(2)
        state = ensure_state_defaults(existing, chain_id)

        summary = load_json(SUMMARY_PATH) if SUMMARY_PATH and os.path.exists(SUMMARY_PATH) else {}
        manifest_path = os.path.join(OUTPUT_DIR, "run_manifest.json")
        manifest = load_json(manifest_path) if os.path.exists(manifest_path) else {}
        step_status = infer_step_status(summary, manifest, EXIT_CODE)
        stop_reason = ""
        if isinstance(summary, dict):
            stop_reason = str(summary.get("stop_reason") or "").strip()
        if not stop_reason and isinstance(manifest, dict):
            stop_reason = str(manifest.get("stop_reason") or "").strip()

        step_entry = state["steps"].get(MODE, {})
        step_entry.update(
            {
                "status": step_status,
                "run_id": RUN_ID,
                "output_dir": OUTPUT_DIR,
                "summary_path": SUMMARY_PATH if SUMMARY_PATH else None,
                "stop_reason": stop_reason or None,
                "updated_at": now_iso(),
            }
        )
        state["steps"][MODE] = step_entry
        state["current_step"] = MODE

        target_total, judged = derive_target_blocker_total(summary)
        roi = state.get("roi") if isinstance(state.get("roi"), dict) else {}
        last_total = roi.get("last_target_total")
        no_improve = int(roi.get("consecutive_no_improve") or 0)
        expensive_limit = int(roi.get("expensive_no_improve_limit") or 3)
        judge_threshold = int(roi.get("judge_threshold") or 20)
        expensive = judged >= judge_threshold

        if step_status == "canonical":
            no_improve = 0
            roi["last_target_total"] = target_total
        elif expensive:
            if last_total is not None and target_total >= int(last_total):
                no_improve += 1
            else:
                no_improve = 0
            roi["last_target_total"] = target_total

        roi["consecutive_no_improve"] = no_improve
        roi["expensive_no_improve_limit"] = expensive_limit
        roi["judge_threshold"] = judge_threshold
        if not isinstance(roi.get("target_blockers"), list) or not roi.get("target_blockers"):
            roi["target_blockers"] = list(BLOCKERS)
        state["roi"] = roi

        next_step = None
        resume_required = False
        if step_status == "incomplete":
            next_step = MODE
            resume_required = True
        elif step_status == "canonical":
            next_step = step_next(MODE)
        else:
            next_step = MODE

        if no_improve >= expensive_limit:
            state["status"] = "blocked"
            state["blocked_reason"] = "root_cause_required"
            next_step = None
            resume_required = False
        elif step_status == "canonical" and MODE == "full":
            state["status"] = "canonical_closed"
            state["blocked_reason"] = None
            next_step = None
        else:
            state["status"] = "active"
            state["blocked_reason"] = None

        active = state.get("active") if isinstance(state.get("active"), dict) else {}
        token = str(active.get("token") or "").strip()
        if step_status == "incomplete":
            state["active"] = {
                "step": MODE,
                "run_id": RUN_ID,
                "token": token,
                "resume_required": True,
                "output_dir": OUTPUT_DIR,
                "updated_at": now_iso(),
            }
        else:
            state["active"] = {
                "step": next_step or "",
                "run_id": "",
                "token": "",
                "resume_required": False,
                "output_dir": "",
                "updated_at": now_iso(),
            }

        history = state.get("history") if isinstance(state.get("history"), list) else []
        history.append(
            {
                "finished_at": now_iso(),
                "mode": MODE,
                "run_id": RUN_ID,
                "step_status": step_status,
                "stop_reason": stop_reason or None,
                "target_blockers_total": target_total,
                "judge_judged": judged,
                "exit_code": EXIT_CODE,
            }
        )
        state["history"] = history[-50:]

        next_command = build_next_command(
            state,
            mode=MODE,
            run_id=RUN_ID,
            output_dir=OUTPUT_DIR,
            step_status=step_status,
        )
        state["next_command"] = next_command
        state["updated_at"] = now_iso()

        write_brief(
            state,
            chain_id=chain_id,
            output_dir=OUTPUT_DIR,
            mode=MODE,
            run_id=RUN_ID,
            step_status=step_status,
            next_command=next_command,
        )
        write_json_atomic(path, state)
    finally:
        if fcntl is not None:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        _lock.close()


def cmd_status(chain_id: str):
    path = state_path(chain_id)
    payload = load_json(path)
    if not isinstance(payload, dict):
        eprint("chain_state_missing")
        raise SystemExit(2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_close(chain_id: str):
    path = state_path(chain_id)
    _lock = with_lock(path)
    try:
        payload = load_json(path)
        if not isinstance(payload, dict):
            eprint("chain_state_missing")
            raise SystemExit(2)
        state = ensure_state_defaults(payload, chain_id)
        state["status"] = "canonical_closed"
        state["blocked_reason"] = None
        state["updated_at"] = now_iso()
        write_json_atomic(path, state)
    finally:
        if fcntl is not None:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        _lock.close()


def cmd_abort(chain_id: str, reason: str):
    path = state_path(chain_id)
    _lock = with_lock(path)
    try:
        payload = load_json(path)
        if not isinstance(payload, dict):
            payload = {"chain_id": chain_id}
        state = ensure_state_defaults(payload, chain_id)
        state["status"] = "aborted"
        state["blocked_reason"] = reason or "manual_abort"
        state["updated_at"] = now_iso()
        write_json_atomic(path, state)
    finally:
        if fcntl is not None:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        _lock.close()


os.makedirs(CHAIN_ROOT, exist_ok=True)

if COMMAND == "prepare":
    cmd_prepare()
elif COMMAND == "finalize":
    cmd_finalize()
elif COMMAND == "status":
    chain_id = derive_chain_id("", CHAIN_ID_ARG)
    if not chain_id:
        eprint("chain_id_invalid")
        raise SystemExit(2)
    cmd_status(chain_id)
elif COMMAND == "close":
    chain_id = derive_chain_id("", CHAIN_ID_ARG)
    if not chain_id:
        eprint("chain_id_invalid")
        raise SystemExit(2)
    cmd_close(chain_id)
elif COMMAND == "abort":
    chain_id = derive_chain_id("", CHAIN_ID_ARG)
    if not chain_id:
        eprint("chain_id_invalid")
        raise SystemExit(2)
    cmd_abort(chain_id, ABORT_REASON)
else:
    eprint(f"unsupported_command:{COMMAND}")
    raise SystemExit(2)
PY
