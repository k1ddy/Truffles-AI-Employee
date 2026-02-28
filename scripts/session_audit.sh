#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_audit.sh [--strict] [--stale-hours N] [--adoption-report-json PATH]

Validates session metadata consistency.
Default mode:
  - hard errors fail the audit
  - stale/legacy session drift is reported as warning
Strict mode:
  - warnings also fail the audit
If --adoption-report-json is set:
  - writes machine-readable adoption coverage and migration cohorts
USAGE
}

strict="false"
stale_hours="${SESSION_LEASE_HOURS:-24}"
canonical_repo_root="${TRUFFLES_CANONICAL_REPO_ROOT:-/home/zhan/truffles-main}"
adoption_report_json=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) strict="true"; shift 1;;
    --stale-hours) stale_hours="$2"; shift 2;;
    --adoption-report-json) adoption_report_json="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if ! [[ "$stale_hours" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --stale-hours must be an integer (got '${stale_hours}')." >&2
  exit 1
fi

if [[ -z "${adoption_report_json}" && "${SESSION_ADOPTION_REPORT_JSON:-}" != "" ]]; then
  adoption_report_json="${SESSION_ADOPTION_REPORT_JSON}"
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

cohort_all_required=()
cohort_missing=()
cohort_partial=()
cohort_invalid=()
cohort_stale_active=()
cohort_done_cleanup=()
cohort_legacy_bundle=()

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
  RECORDED_GATE_CLASS="$classified_mode"
}

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  printf '%s' "$value"
}

make_session_entry_json() {
  local session_id="$1"
  local status="$2"
  local branch="$3"
  local last_updated="$4"
  local worktree="$5"
  local age_hours="$6"
  printf '{"session_id":"%s","status":"%s","branch":"%s","last_updated":"%s","worktree":"%s","age_hours":%s}' \
    "$(json_escape "$session_id")" \
    "$(json_escape "$status")" \
    "$(json_escape "$branch")" \
    "$(json_escape "$last_updated")" \
    "$(json_escape "$worktree")" \
    "${age_hours}"
}

append_cohort_entry() {
  local array_name="$1"
  local session_id="$2"
  local status="$3"
  local branch="$4"
  local last_updated="$5"
  local worktree="$6"
  local age_hours="$7"
  local -n target_array="$array_name"
  target_array+=("$(make_session_entry_json "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$age_hours")")
}

print_json_array() {
  local array_name="$1"
  local -n items="$array_name"
  local first="true"
  printf '['
  for item in "${items[@]}"; do
    if [[ "$first" == "true" ]]; then
      first="false"
    else
      printf ','
    fi
    printf '%s' "$item"
  done
  printf ']'
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

write_adoption_report_json() {
  if [[ -z "$adoption_report_json" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$adoption_report_json")"

  local audit_result="ok"
  if [[ $errors -gt 0 ]]; then
    audit_result="failed"
  elif [[ "$strict" == "true" && $warnings -gt 0 ]]; then
    audit_result="strict_failed"
  fi

  {
    printf '{\n'
    printf '  "generated_at": "%s",\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '  "repo_root": "%s",\n' "$(json_escape "$repo_root")"
    printf '  "stale_hours": %s,\n' "$stale_hours"
    printf '  "audit_result": "%s",\n' "$audit_result"
    printf '  "open_sessions": %s,\n' "$open_sessions"
    printf '  "warnings": %s,\n' "$warnings"
    printf '  "errors": %s,\n' "$errors"
    printf '  "legacy_bundle_sessions": %s,\n' "$legacy_bundle_sessions"
    printf '  "gate_counts": {\n'
    printf '    "research_gate": {"required": %s, "optional": %s, "off": %s, "missing": %s, "invalid": %s},\n' \
      "${gate_mode_counts["research_gate:required"]}" "${gate_mode_counts["research_gate:optional"]}" "${gate_mode_counts["research_gate:off"]}" "${gate_mode_counts["research_gate:missing"]}" "${gate_mode_counts["research_gate:invalid"]}"
    printf '    "root_cause_gate": {"required": %s, "optional": %s, "off": %s, "missing": %s, "invalid": %s},\n' \
      "${gate_mode_counts["root_cause_gate:required"]}" "${gate_mode_counts["root_cause_gate:optional"]}" "${gate_mode_counts["root_cause_gate:off"]}" "${gate_mode_counts["root_cause_gate:missing"]}" "${gate_mode_counts["root_cause_gate:invalid"]}"
    printf '    "reuse_gate": {"required": %s, "optional": %s, "off": %s, "missing": %s, "invalid": %s},\n' \
      "${gate_mode_counts["reuse_gate:required"]}" "${gate_mode_counts["reuse_gate:optional"]}" "${gate_mode_counts["reuse_gate:off"]}" "${gate_mode_counts["reuse_gate:missing"]}" "${gate_mode_counts["reuse_gate:invalid"]}"
    printf '    "release_safety_gate": {"required": %s, "optional": %s, "off": %s, "missing": %s, "invalid": %s}\n' \
      "${gate_mode_counts["release_safety_gate:required"]}" "${gate_mode_counts["release_safety_gate:optional"]}" "${gate_mode_counts["release_safety_gate:off"]}" "${gate_mode_counts["release_safety_gate:missing"]}" "${gate_mode_counts["release_safety_gate:invalid"]}"
    printf '  },\n'
    printf '  "cohorts": {\n'
    printf '    "all_required": '; print_json_array cohort_all_required; printf ',\n'
    printf '    "legacy_missing": '; print_json_array cohort_missing; printf ',\n'
    printf '    "legacy_partial": '; print_json_array cohort_partial; printf ',\n'
    printf '    "invalid_mode": '; print_json_array cohort_invalid; printf ',\n'
    printf '    "stale_active": '; print_json_array cohort_stale_active; printf ',\n'
    printf '    "done_cleanup_candidates": '; print_json_array cohort_done_cleanup; printf ',\n'
    printf '    "legacy_bundle": '; print_json_array cohort_legacy_bundle; printf '\n'
    printf '  }\n'
    printf '}\n'
  } > "$adoption_report_json"
  echo "Adoption report JSON: ${adoption_report_json}"
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

    session_age_hours="null"
    last_updated_state="missing"
    if [[ -n "$last_updated" ]]; then
      if parsed_ts=$(date -d "$last_updated" +%s 2>/dev/null); then
        session_age_hours=$(( (now_ts - parsed_ts) / 3600 ))
        last_updated_state="ok"
      else
        last_updated_state="invalid"
      fi
    fi

    research_gate_mode=$(grep -E "^- research_gate: " "$session_file" | head -n1 | sed 's/^- research_gate: //' || true)
    root_cause_gate_mode=$(grep -E "^- root_cause_gate: " "$session_file" | head -n1 | sed 's/^- root_cause_gate: //' || true)
    reuse_gate_mode=$(grep -E "^- reuse_gate: " "$session_file" | head -n1 | sed 's/^- reuse_gate: //' || true)
    release_safety_gate_mode=$(grep -E "^- release_safety_gate: " "$session_file" | head -n1 | sed 's/^- release_safety_gate: //' || true)

    record_gate_mode "research_gate" "$session_id" "$research_gate_mode"
    research_gate_class="$RECORDED_GATE_CLASS"
    record_gate_mode "root_cause_gate" "$session_id" "$root_cause_gate_mode"
    root_cause_gate_class="$RECORDED_GATE_CLASS"
    record_gate_mode "reuse_gate" "$session_id" "$reuse_gate_mode"
    reuse_gate_class="$RECORDED_GATE_CLASS"
    record_gate_mode "release_safety_gate" "$session_id" "$release_safety_gate_mode"
    release_safety_gate_class="$RECORDED_GATE_CLASS"

    if [[ "$research_gate_mode" == "required" && -z "$root_cause_gate_mode" && -z "$reuse_gate_mode" && -z "$release_safety_gate_mode" ]]; then
      legacy_bundle_sessions=$((legacy_bundle_sessions + 1))
      append_cohort_entry "cohort_legacy_bundle" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
    fi

    if [[ "$research_gate_class" == "required" && "$root_cause_gate_class" == "required" && "$reuse_gate_class" == "required" && "$release_safety_gate_class" == "required" ]]; then
      append_cohort_entry "cohort_all_required" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
    elif [[ "$research_gate_class" == "invalid" || "$root_cause_gate_class" == "invalid" || "$reuse_gate_class" == "invalid" || "$release_safety_gate_class" == "invalid" ]]; then
      append_cohort_entry "cohort_invalid" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
    elif [[ "$research_gate_class" == "missing" || "$root_cause_gate_class" == "missing" || "$reuse_gate_class" == "missing" || "$release_safety_gate_class" == "missing" ]]; then
      append_cohort_entry "cohort_missing" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
    else
      append_cohort_entry "cohort_partial" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
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
    done_cleanup_needed="false"
    if [[ -d "$worktree" ]]; then
      echo "WARN: ${session_id} status=done but worktree still exists: ${worktree}" >&2
      warnings=$((warnings + 1))
      done_cleanup_needed="true"
    fi
    if git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
      echo "WARN: ${session_id} status=done but branch still exists: ${branch}" >&2
      warnings=$((warnings + 1))
      done_cleanup_needed="true"
    fi
    if [[ "$done_cleanup_needed" == "true" ]]; then
      append_cohort_entry "cohort_done_cleanup" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "null"
    fi
  fi

  if [[ "$status" == "active" ]]; then
    if [[ "$last_updated_state" == "missing" ]]; then
      echo "WARN: ${session_id} active but last_updated is missing." >&2
      warnings=$((warnings + 1))
    elif [[ "$last_updated_state" == "ok" ]]; then
      if (( session_age_hours > stale_hours )); then
        echo "WARN: ${session_id} active but stale ${session_age_hours}h (last_updated=${last_updated})." >&2
        warnings=$((warnings + 1))
        append_cohort_entry "cohort_stale_active" "$session_id" "$status" "$branch" "$last_updated" "$worktree" "$session_age_hours"
      fi
    else
      echo "WARN: ${session_id} active but last_updated is not parseable: ${last_updated}" >&2
      warnings=$((warnings + 1))
    fi
  fi
done

print_gate_adoption_summary
write_adoption_report_json

if [[ $errors -gt 0 ]]; then
  echo "Session audit failed: ${errors} error(s), ${warnings} warning(s)." >&2
  exit 1
fi

if [[ "$strict" == "true" && $warnings -gt 0 ]]; then
  echo "Session audit strict-failed: ${warnings} warning(s)." >&2
  exit 1
fi

echo "Session audit OK: ${warnings} warning(s), ${errors} error(s)."
