#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/platform_admin_control_loop.sh [options]

Options:
  --run-id <id>                  Deterministic run id (default: UTC timestamp)
  --run-e2e <0|1>                Run platform-admin e2e lane (default: 0)
  --run-remediation-assist <0|1> Generate remediation assist artifacts (default: 1)
  --remediation-strict <0|1>     Fail on blocked remediation decision (default: 0)
  --fail-level <warning|critical>  KPI guard fail level (default: critical)
  --output-root <dir>            Artifact root (default: /tmp/platform_admin_control_loop)
  --playwright-base-url <url>    Base URL for optional e2e run
  -h, --help                     Show help
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

RUN_ID=""
RUN_E2E="0"
RUN_REMEDIATION_ASSIST="1"
REMEDIATION_STRICT="0"
FAIL_LEVEL="critical"
OUTPUT_ROOT="/tmp/platform_admin_control_loop"
PLAYWRIGHT_BASE_URL_INPUT="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:3100}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --run-e2e)
      RUN_E2E="${2:-}"
      shift 2
      ;;
    --run-remediation-assist)
      RUN_REMEDIATION_ASSIST="${2:-}"
      shift 2
      ;;
    --remediation-strict)
      REMEDIATION_STRICT="${2:-}"
      shift 2
      ;;
    --fail-level)
      FAIL_LEVEL="${2:-}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:-}"
      shift 2
      ;;
    --playwright-base-url)
      PLAYWRIGHT_BASE_URL_INPUT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
fi

if [[ "${RUN_E2E}" != "0" && "${RUN_E2E}" != "1" ]]; then
  echo "--run-e2e must be 0 or 1" >&2
  exit 2
fi

if [[ "${RUN_REMEDIATION_ASSIST}" != "0" && "${RUN_REMEDIATION_ASSIST}" != "1" ]]; then
  echo "--run-remediation-assist must be 0 or 1" >&2
  exit 2
fi

if [[ "${REMEDIATION_STRICT}" != "0" && "${REMEDIATION_STRICT}" != "1" ]]; then
  echo "--remediation-strict must be 0 or 1" >&2
  exit 2
fi

if [[ "${FAIL_LEVEL}" != "warning" && "${FAIL_LEVEL}" != "critical" ]]; then
  echo "--fail-level must be warning or critical" >&2
  exit 2
fi

if [[ "${OUTPUT_ROOT}" != /* ]]; then
  OUTPUT_ROOT="${REPO_ROOT}/${OUTPUT_ROOT}"
fi

RUN_DIR="${OUTPUT_ROOT}/${RUN_ID}"
mkdir -p "${RUN_DIR}"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"

echo "[platform-admin-control-loop] run_id=${RUN_ID}"
echo "[platform-admin-control-loop] run_dir=${RUN_DIR}"
echo "[platform-admin-control-loop] branch=${GIT_BRANCH} commit=${GIT_COMMIT}"

run_step() {
  local step_name="$1"
  shift
  local log_file="${RUN_DIR}/${step_name}.log"
  echo "[platform-admin-control-loop] step=${step_name} started"
  set +e
  "$@" > >(tee "${log_file}") 2>&1
  local exit_code=$?
  set -e
  if [[ ${exit_code} -eq 0 ]]; then
    echo "[platform-admin-control-loop] step=${step_name} status=pass"
  else
    echo "[platform-admin-control-loop] step=${step_name} status=fail exit=${exit_code}"
  fi
  return "${exit_code}"
}

KPI_STATUS="pass"
ANTI_DRIFT_STATUS="pass"
AUDIT_GOVERNANCE_STATUS="pass"
E2E_STATUS="skipped"
REMEDIATION_ASSIST_STATUS="skipped"

if ! run_step "kpi_snapshot" \
  python3 ops/console_platform_admin_kpi_snapshot.py \
    --pretty \
    --fail-on-breach \
    --fail-level "${FAIL_LEVEL}" \
    --output "${RUN_DIR}/kpi_snapshot.json"; then
  KPI_STATUS="fail"
fi

if ! run_step "anti_drift" npm --prefix console-web run check:uvc-antidrift; then
  ANTI_DRIFT_STATUS="fail"
fi

if ! run_step "audit_governance" \
  python3 scripts/check_console_audit_governance.py \
    --pretty \
    --output "${RUN_DIR}/governance_audit.json"; then
  AUDIT_GOVERNANCE_STATUS="fail"
fi

if [[ "${RUN_E2E}" == "1" ]]; then
  E2E_STATUS="pass"
  if ! run_step "e2e_lane" \
    env PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL_INPUT}" \
      npm --prefix console-web run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"; then
    E2E_STATUS="fail"
  fi
fi

if [[ "${RUN_REMEDIATION_ASSIST}" == "1" ]]; then
  REMEDIATION_ASSIST_STATUS="pass"
  if [[ ! -f "${RUN_DIR}/kpi_snapshot.json" ]]; then
    echo "[platform-admin-control-loop] missing KPI snapshot for remediation assist" >&2
    REMEDIATION_ASSIST_STATUS="fail"
  else
    remediation_args=()
    if [[ "${REMEDIATION_STRICT}" == "1" ]]; then
      remediation_args+=(--strict)
    fi
    if ! run_step "remediation_assist" \
      python3 ops/platform_admin_remediation_assist.py \
        --kpi-snapshot "${RUN_DIR}/kpi_snapshot.json" \
        --output-dir "${RUN_DIR}" \
        --run-id "${RUN_ID}" \
        "${remediation_args[@]}"; then
      REMEDIATION_ASSIST_STATUS="fail"
    fi
  fi
fi

OVERALL_STATUS="pass"
if [[ "${KPI_STATUS}" == "fail" || "${ANTI_DRIFT_STATUS}" == "fail" || "${AUDIT_GOVERNANCE_STATUS}" == "fail" || "${E2E_STATUS}" == "fail" || "${REMEDIATION_ASSIST_STATUS}" == "fail" ]]; then
  OVERALL_STATUS="fail"
fi

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "${RUN_DIR}/summary.json" <<EOF
{
  "run_id": "${RUN_ID}",
  "started_at": "${STARTED_AT}",
  "finished_at": "${FINISHED_AT}",
  "repo": {
    "root": "${REPO_ROOT}",
    "branch": "${GIT_BRANCH}",
    "commit": "${GIT_COMMIT}"
  },
  "parameters": {
    "run_e2e": ${RUN_E2E},
    "run_remediation_assist": ${RUN_REMEDIATION_ASSIST},
    "remediation_strict": ${REMEDIATION_STRICT},
    "fail_level": "${FAIL_LEVEL}",
    "playwright_base_url": "${PLAYWRIGHT_BASE_URL_INPUT}"
  },
  "steps": {
    "kpi_snapshot": "${KPI_STATUS}",
    "anti_drift": "${ANTI_DRIFT_STATUS}",
    "audit_governance": "${AUDIT_GOVERNANCE_STATUS}",
    "e2e_lane": "${E2E_STATUS}",
    "remediation_assist": "${REMEDIATION_ASSIST_STATUS}"
  },
  "overall_status": "${OVERALL_STATUS}",
  "artifacts": {
    "kpi_snapshot": "${RUN_DIR}/kpi_snapshot.json",
    "governance_audit": "${RUN_DIR}/governance_audit.json",
    "remediation_plan": "${RUN_DIR}/remediation_plan.json",
    "remediation_brief": "${RUN_DIR}/remediation_brief.md",
    "remediation_commands": "${RUN_DIR}/remediation_commands.sh",
    "summary": "${RUN_DIR}/summary.json"
  }
}
EOF

echo "[platform-admin-control-loop] summary=${RUN_DIR}/summary.json"
if [[ "${OVERALL_STATUS}" != "pass" ]]; then
  exit 1
fi
