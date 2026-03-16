#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROOF_PYTHON="${KNOWLEDGE_ACTIVATION_PROOF_PYTHON:-python3}"
GUARD_SCRIPT="${KNOWLEDGE_ACTIVATION_GUARD_SCRIPT:-${SCRIPT_DIR}/../truffles-api/scripts/knowledge_activation_release_guard.py}"
CLOSEOUT_SCRIPT="${KNOWLEDGE_ACTIVATION_CLOSEOUT_SCRIPT:-${SCRIPT_DIR}/../ops/knowledge_activation_closeout.py}"
OUTPUT_DIR="${KNOWLEDGE_ACTIVATION_PROOF_OUTPUT_DIR:-/tmp/knowledge_activation_postdeploy}"
GUARD_JSON="${KNOWLEDGE_ACTIVATION_PROOF_GUARD_JSON:-${OUTPUT_DIR}/release_guard.json}"
MANIFEST_JSON="${OUTPUT_DIR}/manifest.json"
SUMMARY_MD="${OUTPUT_DIR}/summary.md"
CLOSEOUT_JSON="${OUTPUT_DIR}/closeout.json"
POSTGRES_CONTAINER="${KNOWLEDGE_ACTIVATION_POSTGRES_CONTAINER:-truffles_postgres_1}"
POSTGRES_DB="${KNOWLEDGE_ACTIVATION_POSTGRES_DB:-chatbot}"
CLIENT_SLUG="${KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG:-}"
BRANCH_SLUG="${KNOWLEDGE_ACTIVATION_CLOSEOUT_BRANCH_SLUG:-}"
REQUIRE_CLOSEOUT="${KNOWLEDGE_ACTIVATION_PROOF_REQUIRE_CLOSEOUT:-0}"
TOKEN_SOURCE_CONTAINER="${KNOWLEDGE_ACTIVATION_TOKEN_SOURCE_CONTAINER:-truffles-api}"

mkdir -p "${OUTPUT_DIR}"

SERVICE_TOKEN="${KNOWLEDGE_ACTIVATION_SERVICE_TOKEN:-}"
if [ -z "${SERVICE_TOKEN}" ] && command -v docker >/dev/null 2>&1; then
  SERVICE_TOKEN="$(docker exec "${TOKEN_SOURCE_CONTAINER}" /bin/sh -lc 'printf "%s" "${KNOWLEDGE_ACTIVATION_SERVICE_TOKEN:-}"' 2>/dev/null || true)"
fi

guard_args=(--output "${GUARD_JSON}" --pretty)
if [ -n "${SERVICE_TOKEN}" ]; then
  guard_args+=(--service-token "${SERVICE_TOKEN}")
fi

guard_exit=0
if [ -f "${GUARD_JSON}" ]; then
  echo "Using existing release guard artifact: ${GUARD_JSON}"
else
  if "${PROOF_PYTHON}" "${GUARD_SCRIPT}" "${guard_args[@]}"; then
    guard_exit=0
  else
    guard_exit=$?
  fi
fi

closeout_status="skipped"
closeout_reason="closeout_target_not_configured"
closeout_exit=0
if [ -n "${CLIENT_SLUG}" ] || [ -n "${BRANCH_SLUG}" ]; then
  if [ -z "${CLIENT_SLUG}" ] || [ -z "${BRANCH_SLUG}" ]; then
    closeout_status="invalid_configuration"
    closeout_reason="closeout_target_incomplete"
    closeout_exit=1
  else
    closeout_status="executed"
    closeout_reason=""
    closeout_args=(
      --client-slug "${CLIENT_SLUG}"
      --branch-slug "${BRANCH_SLUG}"
      --guard-json "${GUARD_JSON}"
      --output "${CLOSEOUT_JSON}"
      --pretty
      --postgres-container "${POSTGRES_CONTAINER}"
      --postgres-db "${POSTGRES_DB}"
    )
    if [ -n "${SERVICE_TOKEN}" ]; then
      closeout_args+=(--service-token "${SERVICE_TOKEN}")
    fi
    if "${PROOF_PYTHON}" "${CLOSEOUT_SCRIPT}" "${closeout_args[@]}"; then
      closeout_exit=0
    else
      closeout_exit=$?
    fi
  fi
fi

if [ "${REQUIRE_CLOSEOUT}" = "1" ] && [ "${closeout_status}" = "skipped" ]; then
  closeout_status="invalid_configuration"
  closeout_reason="closeout_target_required_but_missing"
  closeout_exit=1
fi

export GUARD_JSON
export MANIFEST_JSON
export SUMMARY_MD
export CLOSEOUT_JSON
export CLIENT_SLUG
export BRANCH_SLUG
export CLOSEOUT_STATUS="${closeout_status}"
export CLOSEOUT_REASON="${closeout_reason}"
export REQUIRE_CLOSEOUT
export GUARD_EXIT="${guard_exit}"
export CLOSEOUT_EXIT="${closeout_exit}"

"${PROOF_PYTHON}" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def load_json(path_str: str) -> dict | None:
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


guard_path = Path(os.environ["GUARD_JSON"])
closeout_path = Path(os.environ["CLOSEOUT_JSON"])
manifest_path = Path(os.environ["MANIFEST_JSON"])
summary_path = Path(os.environ["SUMMARY_MD"])
closeout_status = os.environ["CLOSEOUT_STATUS"]
closeout_reason = os.environ["CLOSEOUT_REASON"]
require_closeout = os.environ["REQUIRE_CLOSEOUT"] == "1"
guard_exit = int(os.environ["GUARD_EXIT"])
closeout_exit = int(os.environ["CLOSEOUT_EXIT"])

guard_payload = load_json(str(guard_path))
closeout_payload = load_json(str(closeout_path))
guard_decision = str((guard_payload or {}).get("decision") or "").strip().lower() or None
closeout_decision = str((closeout_payload or {}).get("decision") or "").strip().lower() or None

reasons: list[str] = []
overall_decision = "go"
proof_mode = "guard_only"

if guard_exit != 0 or guard_decision != "go":
    overall_decision = "no_go"
    reasons.append("release_guard_failed")

if closeout_status == "executed":
    proof_mode = "guard_and_closeout"
    if closeout_exit != 0 or closeout_decision != "go":
        overall_decision = "no_go"
        reasons.append("closeout_failed")
elif closeout_status == "skipped":
    if require_closeout:
        overall_decision = "no_go"
        reasons.append("closeout_required_but_skipped")
    elif closeout_reason:
        reasons.append(closeout_reason)
elif closeout_status == "invalid_configuration":
    overall_decision = "no_go"
    reasons.append(closeout_reason or "closeout_invalid_configuration")

manifest = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "decision": overall_decision,
    "proof_mode": proof_mode,
    "reasons": reasons,
    "release_guard": {
        "path": str(guard_path),
        "decision": guard_decision,
        "exit_code": guard_exit,
        "present": guard_payload is not None,
    },
    "closeout": {
        "status": closeout_status,
        "reason": closeout_reason or None,
        "required": require_closeout,
        "path": str(closeout_path),
        "decision": closeout_decision,
        "exit_code": closeout_exit,
        "present": closeout_payload is not None,
    },
    "target": {
        "client_slug": os.environ.get("CLIENT_SLUG") or None,
        "branch_slug": os.environ.get("BRANCH_SLUG") or None,
    },
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

summary_lines = [
    "# Knowledge Activation Post-Deploy Proof",
    "",
    f"- overall_decision: `{overall_decision}`",
    f"- proof_mode: `{proof_mode}`",
    f"- release_guard: `{guard_decision or 'missing'}` (exit `{guard_exit}`)",
    f"- closeout_status: `{closeout_status}`",
]
if closeout_decision:
    summary_lines.append(f"- closeout_decision: `{closeout_decision}` (exit `{closeout_exit}`)")
if manifest["target"]["client_slug"] and manifest["target"]["branch_slug"]:
    summary_lines.append(
        "- closeout_target: "
        f"`{manifest['target']['client_slug']}` / `{manifest['target']['branch_slug']}`"
    )
if reasons:
    summary_lines.append(f"- reasons: `{', '.join(reasons)}`")
summary_lines.append(f"- manifest: `{manifest_path}`")
summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
PY

manifest_decision="$("${PROOF_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["MANIFEST_JSON"]).read_text(encoding="utf-8"))
print(payload.get("decision") or "no_go")
PY
)"

if [ "${manifest_decision}" != "go" ]; then
  exit 1
fi
