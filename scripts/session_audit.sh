#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_audit.sh [--strict] [--stale-hours N]

Validates session metadata consistency.
Default mode:
  - hard errors fail the audit
  - stale/legacy session drift is reported as warning
Strict mode:
  - warnings also fail the audit
USAGE
}

strict="false"
stale_hours="${SESSION_LEASE_HOURS:-24}"
canonical_repo_root="${TRUFFLES_CANONICAL_REPO_ROOT:-/home/zhan/truffles-main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) strict="true"; shift 1;;
    --stale-hours) stale_hours="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if ! [[ "$stale_hours" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --stale-hours must be an integer (got '${stale_hours}')." >&2
  exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
sessions_dir="$repo_root/docs/SESSIONS"
index_file="$repo_root/docs/SESSION_INDEX.md"

if [[ ! -d "$sessions_dir" ]]; then
  echo "ERROR: docs/SESSIONS not found." >&2
  exit 1
fi

errors=0
warnings=0
now_ts=$(date +%s)
open_sessions=0
legacy_bundle_sessions=0

gates=(research_gate root_cause_gate reuse_gate release_safety_gate)
declare -A gate_mode_counts
for gate in "${gates[@]}"; do
  for mode in required optional off missing invalid; do
    gate_mode_counts["${gate}:${mode}"]=0
  done
done

increment_gate_mode_count() {
  local gate="$1"
  local mode="$2"
  local key="${gate}:${mode}"
  gate_mode_counts["$key"]=$((gate_mode_counts["$key"] + 1))
}

classify_gate_mode() {
  local mode="$1"

  if [[ -z "$mode" ]]; then
    printf '%s\n' "missing"
    return 0
  fi
  if [[ "$mode" == "required" || "$mode" == "optional" || "$mode" == "off" ]]; then
    printf '%s\n' "$mode"
    return 0
  fi

  printf '%s\n' "invalid"
}

record_gate_mode() {
  local gate="$1"
  local session_id="$2"
  local mode="$3"
  local classified_mode
  classified_mode=$(classify_gate_mode "$mode")
  increment_gate_mode_count "$gate" "$classified_mode"
  if [[ "$classified_mode" == "invalid" ]]; then
    echo "WARN: ${session_id} has invalid ${gate} mode '${mode}' (allowed: required|optional|off)." >&2
    warnings=$((warnings + 1))
  fi
}

print_gate_adoption_summary() {
  echo "Gate adoption summary (open sessions: ${open_sessions})"
  local gate
  for gate in "${gates[@]}"; do
    local required optional off missing invalid
    required=${gate_mode_counts["${gate}:required"]}
    optional=${gate_mode_counts["${gate}:optional"]}
    off=${gate_mode_counts["${gate}:off"]}
    missing=${gate_mode_counts["${gate}:missing"]}
    invalid=${gate_mode_counts["${gate}:invalid"]}
    echo "  ${gate}: required=${required} optional=${optional} off=${off} missing=${missing} invalid=${invalid}"
  done
  echo "  legacy_bundle_sessions (research_gate=required + no explicit subgates)=${legacy_bundle_sessions}"
}

for session_file in "$sessions_dir"/SESSION-*.md; do
  [[ -f "$session_file" ]] || continue

  session_id=$(basename "$session_file")
  session_id=${session_id#SESSION-}
  session_id=${session_id%.md}

  status=$(grep -E "^- status: " "$session_file" | head -n1 | sed 's/^- status: //')
  branch=$(grep -E "^- branch: " "$session_file" | head -n1 | sed 's/^- branch: //')
  worktree=$(grep -E "^- worktree: " "$session_file" | head -n1 | sed 's/^- worktree: //')
  task_package=$(grep -E "^- task_package: " "$session_file" | head -n1 | sed 's/^- task_package: //')
  last_updated=$(grep -E "^- last_updated: " "$session_file" | head -n1 | sed 's/^- last_updated: //')

  if [[ -z "$status" || -z "$branch" || -z "$worktree" || -z "$task_package" ]]; then
    echo "ERROR: ${session_id} has missing required fields." >&2
    errors=$((errors + 1))
  fi

  if [[ -f "$index_file" ]] && ! grep -q "^| ${session_id} |" "$index_file"; then
    echo "ERROR: ${session_id} missing from SESSION_INDEX." >&2
    errors=$((errors + 1))
  fi

  if [[ "$status" == "active" || "$status" == "paused" ]]; then
    open_sessions=$((open_sessions + 1))

    research_gate_mode=$(grep -E "^- research_gate: " "$session_file" | head -n1 | sed 's/^- research_gate: //' || true)
    root_cause_gate_mode=$(grep -E "^- root_cause_gate: " "$session_file" | head -n1 | sed 's/^- root_cause_gate: //' || true)
    reuse_gate_mode=$(grep -E "^- reuse_gate: " "$session_file" | head -n1 | sed 's/^- reuse_gate: //' || true)
    release_safety_gate_mode=$(grep -E "^- release_safety_gate: " "$session_file" | head -n1 | sed 's/^- release_safety_gate: //' || true)

    record_gate_mode "research_gate" "$session_id" "$research_gate_mode"
    record_gate_mode "root_cause_gate" "$session_id" "$root_cause_gate_mode"
    record_gate_mode "reuse_gate" "$session_id" "$reuse_gate_mode"
    record_gate_mode "release_safety_gate" "$session_id" "$release_safety_gate_mode"

    if [[ "$research_gate_mode" == "required" && -z "$root_cause_gate_mode" && -z "$reuse_gate_mode" && -z "$release_safety_gate_mode" ]]; then
      legacy_bundle_sessions=$((legacy_bundle_sessions + 1))
    fi

    if [[ ! -d "$worktree" ]]; then
      echo "WARN: ${session_id} status=${status} but worktree missing: ${worktree}" >&2
      warnings=$((warnings + 1))
    fi
    if ! git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
      echo "WARN: ${session_id} status=${status} but branch missing: ${branch}" >&2
      warnings=$((warnings + 1))
    fi
    if [[ "$worktree" == "$canonical_repo_root" && "$branch" != "main" && "$branch" != "master" ]]; then
      echo "WARN: ${session_id} uses canonical root on non-main branch (${branch}); move to dedicated worktree." >&2
      warnings=$((warnings + 1))
    fi
  fi

  if [[ "$status" == "done" ]]; then
    if [[ -d "$worktree" ]]; then
      echo "WARN: ${session_id} status=done but worktree still exists: ${worktree}" >&2
      warnings=$((warnings + 1))
    fi
    if git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
      echo "WARN: ${session_id} status=done but branch still exists: ${branch}" >&2
      warnings=$((warnings + 1))
    fi
  fi

  if [[ "$status" == "active" ]]; then
    if [[ -z "$last_updated" ]]; then
      echo "WARN: ${session_id} active but last_updated is missing." >&2
      warnings=$((warnings + 1))
    elif parsed_ts=$(date -d "$last_updated" +%s 2>/dev/null); then
      age_hours=$(( (now_ts - parsed_ts) / 3600 ))
      if (( age_hours > stale_hours )); then
        echo "WARN: ${session_id} active but stale ${age_hours}h (last_updated=${last_updated})." >&2
        warnings=$((warnings + 1))
      fi
    else
      echo "WARN: ${session_id} active but last_updated is not parseable: ${last_updated}" >&2
      warnings=$((warnings + 1))
    fi
  fi
done

print_gate_adoption_summary

if [[ $errors -gt 0 ]]; then
  echo "Session audit failed: ${errors} error(s), ${warnings} warning(s)." >&2
  exit 1
fi

if [[ "$strict" == "true" && $warnings -gt 0 ]]; then
  echo "Session audit strict-failed: ${warnings} warning(s)." >&2
  exit 1
fi

echo "Session audit OK: ${warnings} warning(s), ${errors} error(s)."
