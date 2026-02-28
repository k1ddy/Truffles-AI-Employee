#!/usr/bin/env bash
set -euo pipefail

mode=""
target_branch=""
base_ref=""
head_ref=""
allow_doc_only_pr="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) mode="$2"; shift 2;;
    --target-branch) target_branch="$2"; shift 2;;
    --base) base_ref="$2"; shift 2;;
    --head) head_ref="$2"; shift 2;;
    --allow-doc-only-pr) allow_doc_only_pr="true"; shift 1;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/session_gate.sh --mode pre-push|ci --target-branch BRANCH --base BASE_SHA --head HEAD_SHA [--allow-doc-only-pr]
USAGE
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "$mode" || -z "$target_branch" || -z "$head_ref" ]]; then
  echo "ERROR: mode, target-branch, base, head are required." >&2
  exit 1
fi

if [[ -z "$base_ref" ]]; then
  base_ref="origin/main"
fi

repo_root=$(git rev-parse --show-toplevel)

resolve_repo_path() {
  local path="$1"
  if [[ -z "$path" || "$path" == "null" ]]; then
    echo ""
    return 0
  fi
  if [[ "$path" == /* ]]; then
    echo "$path"
    return 0
  fi
  echo "$repo_root/$path"
}

session_meta_value_from_file() {
  local file="$1"
  local key="$2"
  grep -E "^- ${key}: " "$file" | head -n1 | sed "s/^- ${key}: //" || true
}

has_rg() {
  command -v rg >/dev/null 2>&1
}

contains_fixed() {
  local needle="$1"
  local file="$2"
  if has_rg; then
    rg -Fq "$needle" "$file"
  else
    grep -Fq "$needle" "$file"
  fi
}

count_regex_lines() {
  local pattern="$1"
  local file="$2"
  if has_rg; then
    rg -n "$pattern" "$file" | wc -l | tr -d '[:space:]'
  else
    grep -nE "$pattern" "$file" | wc -l | tr -d '[:space:]'
  fi
}

require_tp_section_in_file() {
  local file="$1"
  local section="$2"
  if ! contains_fixed "## ${section}" "$file"; then
    echo "ERROR: Task Package missing section '## ${section}' in ${file}." >&2
    exit 1
  fi
}

require_tp_token_in_file() {
  local file="$1"
  local token="$2"
  if ! contains_fixed "$token" "$file"; then
    echo "ERROR: Task Package missing token '${token}' in ${file}." >&2
    exit 1
  fi
}

validate_gate_mode() {
  local gate="$1"
  local mode="$2"
  if [[ -z "$mode" || "$mode" == "off" || "$mode" == "optional" || "$mode" == "required" ]]; then
    return 0
  fi
  echo "ERROR: Unsupported ${gate} mode '${mode}' in ${session_file}." >&2
  exit 1
}

research_mode_from_session() {
  local session_file="$1"
  local mode
  mode=$(session_meta_value_from_file "$session_file" "research_gate")
  validate_gate_mode "research_gate" "$mode"
  if [[ -z "$mode" ]]; then
    echo "off"
    return 0
  fi
  echo "$mode"
}

has_explicit_research_subgate_modes() {
  local session_file="$1"
  local gate
  for gate in root_cause_gate reuse_gate release_safety_gate; do
    local mode
    mode=$(session_meta_value_from_file "$session_file" "$gate")
    validate_gate_mode "$gate" "$mode"
    if [[ -n "$mode" ]]; then
      return 0
    fi
  done
  return 1
}

research_subgate_mode_from_session() {
  local session_file="$1"
  local gate="$2"
  local mode
  mode=$(session_meta_value_from_file "$session_file" "$gate")
  validate_gate_mode "$gate" "$mode"
  if [[ -n "$mode" ]]; then
    echo "$mode"
    return 0
  fi

  local research_mode
  research_mode=$(research_mode_from_session "$session_file")
  if [[ "$research_mode" == "required" ]] && ! has_explicit_research_subgate_modes "$session_file"; then
    echo "required"
    return 0
  fi
  echo "off"
}

require_single_web_query_in_tp() {
  local file="$1"
  local query_count
  query_count=$(count_regex_lines '^- \*\*Query \(exact\):\*\*' "$file")
  if [[ "$query_count" != "1" ]]; then
    echo "ERROR: Task Package must contain exactly one 'Query (exact)' entry (found ${query_count}) in ${file}." >&2
    exit 1
  fi
}

require_web_sources_block_has_url() {
  local file="$1"
  local sources_block
  sources_block=$(awk '
    /^## One web search \(mandatory before implementation\)/ {in_section=1; next}
    in_section && /^## / {exit}
    in_section {print}
  ' "$file")
  if ! printf '%s\n' "$sources_block" | grep -Eq 'https?://'; then
    echo "ERROR: Task Package one-web-search section must include at least one URL source in ${file}." >&2
    exit 1
  fi
}

require_web_search_section() {
  local tp_file="$1"
  require_tp_section_in_file "$tp_file" "One web search (mandatory before implementation)"
  require_tp_token_in_file "$tp_file" "Query (exact):"
  require_tp_token_in_file "$tp_file" "Date/time (local):"
  require_tp_token_in_file "$tp_file" "Sources opened (from this query):"
  require_tp_token_in_file "$tp_file" "Decision:"
  require_tp_token_in_file "$tp_file" "Rejected options:"
  require_single_web_query_in_tp "$tp_file"
  require_web_sources_block_has_url "$tp_file"
}

require_root_cause_section() {
  local tp_file="$1"
  require_tp_section_in_file "$tp_file" "Root cause (mandatory)"
  require_tp_token_in_file "$tp_file" "Symptom:"
  require_tp_token_in_file "$tp_file" "Minimal reproduction:"
  require_tp_token_in_file "$tp_file" "Five Whys"
  require_tp_token_in_file "$tp_file" "Root cause statement:"
  require_tp_token_in_file "$tp_file" "Fix mechanism:"
}

require_reuse_section() {
  local tp_file="$1"
  require_tp_section_in_file "$tp_file" "Reuse-first plan (mandatory)"
  require_tp_token_in_file "$tp_file" "Internal reuse:"
  require_tp_token_in_file "$tp_file" "External reuse:"
}

require_iteration_budget_section() {
  local tp_file="$1"
  require_tp_section_in_file "$tp_file" "Token / run budget (mandatory for expensive suites)"
  require_tp_token_in_file "$tp_file" "Max full runs:"
}

require_release_safety_section() {
  local tp_file="$1"
  require_tp_section_in_file "$tp_file" "Release safety (mandatory for non-doc changes)"
  require_tp_token_in_file "$tp_file" "Strategy:"
  require_tp_token_in_file "$tp_file" "Go/no-go signals:"
  require_tp_token_in_file "$tp_file" "Rollback:"
  require_tp_token_in_file "$tp_file" "Post-release monitoring window:"
}

enforce_session_scoped_gates() {
  local session_rel="$1"
  local session_file="$repo_root/$session_rel"
  if [[ ! -f "$session_file" ]]; then
    echo "ERROR: Session file listed in diff is missing: ${session_rel}" >&2
    exit 1
  fi

  local research_mode root_cause_mode reuse_mode release_safety_mode
  research_mode=$(research_mode_from_session "$session_file")
  root_cause_mode=$(research_subgate_mode_from_session "$session_file" "root_cause_gate")
  reuse_mode=$(research_subgate_mode_from_session "$session_file" "reuse_gate")
  release_safety_mode=$(research_subgate_mode_from_session "$session_file" "release_safety_gate")

  local requires_any="false"
  if [[ "$research_mode" == "required" || "$root_cause_mode" == "required" || "$reuse_mode" == "required" || "$release_safety_mode" == "required" ]]; then
    requires_any="true"
  fi
  if [[ "$requires_any" == "true" ]]; then
    local task_package tp_path
    task_package=$(session_meta_value_from_file "$session_file" "task_package")
    tp_path=$(resolve_repo_path "$task_package")
    if [[ -z "$tp_path" ]]; then
      echo "ERROR: research-driven gate is required but task_package is missing in ${session_file}." >&2
      exit 1
    fi
    if [[ ! -f "$tp_path" ]]; then
      echo "ERROR: Task Package not found for research-driven gates: ${tp_path}" >&2
      exit 1
    fi

    if [[ "$research_mode" == "required" ]]; then
      require_web_search_section "$tp_path"
    fi
    if [[ "$root_cause_mode" == "required" ]]; then
      require_root_cause_section "$tp_path"
    fi
    if [[ "$reuse_mode" == "required" ]]; then
      require_reuse_section "$tp_path"
    fi
    if [[ "$release_safety_mode" == "required" ]]; then
      require_release_safety_section "$tp_path"
    fi

    require_iteration_budget_section "$tp_path"
  fi

  local zero_mode
  zero_mode=$(session_meta_value_from_file "$session_file" "zero_context_gate")
  if [[ -n "$zero_mode" && "$zero_mode" != "off" && "$zero_mode" != "optional" ]]; then
    if [[ "$zero_mode" != "required" ]]; then
      echo "ERROR: Unsupported zero_context_gate mode '${zero_mode}' in ${session_file}." >&2
      exit 1
    fi
    local zc_tp_rel zc_report_rel zc_graph_rel zc_tp_path zc_report_path zc_graph_path
    zc_tp_rel=$(session_meta_value_from_file "$session_file" "zero_context_tp")
    zc_report_rel=$(session_meta_value_from_file "$session_file" "zero_context_report")
    zc_graph_rel=$(session_meta_value_from_file "$session_file" "zero_context_graph")
    zc_tp_path=$(resolve_repo_path "$zc_tp_rel")
    zc_report_path=$(resolve_repo_path "$zc_report_rel")
    zc_graph_path=$(resolve_repo_path "$zc_graph_rel")
    if [[ -z "$zc_tp_path" || -z "$zc_report_path" ]]; then
      echo "ERROR: zero_context_gate=required needs zero_context_tp and zero_context_report in ${session_file}." >&2
      exit 1
    fi
    local cmd=("$repo_root/scripts/zero_context_gate.sh" --tp "$zc_tp_path" --report "$zc_report_path")
    if [[ -n "$zc_graph_path" ]]; then
      cmd+=(--graph "$zc_graph_path")
    fi
    "${cmd[@]}"
  fi
}

enforce_changed_session_files_gates() {
  while read -r file; do
    [[ -z "$file" ]] && continue
    if [[ "$file" == docs/SESSIONS/SESSION-* ]]; then
      enforce_session_scoped_gates "$file"
    fi
  done <<< "$diff_files"
}

resolve_zero_base_diff_ref() {
  local head="$1"
  local merge_base=""

  if git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
    merge_base=$(git merge-base "$head" origin/main 2>/dev/null || true)
  fi
  if [[ -z "$merge_base" ]] && git rev-parse --verify --quiet main >/dev/null 2>&1; then
    merge_base=$(git merge-base "$head" main 2>/dev/null || true)
  fi
  if [[ -n "$merge_base" ]]; then
    printf '%s\n' "$merge_base"
    return 0
  fi

  git hash-object -t tree /dev/null
}

if [[ "$base_ref" =~ ^0+$ ]]; then
  zero_base_ref=$(resolve_zero_base_diff_ref "$head_ref")
  diff_files=$(git diff --name-only "$zero_base_ref" "$head_ref")
else
  diff_files=$(git diff --name-only "$base_ref" "$head_ref")
fi

if [[ -z "$diff_files" ]]; then
  echo "No changes detected for gate; skipping." >&2
  exit 0
fi

allowed_doc_regex='^(docs/|STATE.md$|STRUCTURE.md$|AGENTS.md$)'

doc_only="true"
has_session_file="false"
has_session_index="false"

while read -r file; do
  [[ -z "$file" ]] && continue
  if [[ "$file" == docs/SESSIONS/* ]]; then
    has_session_file="true"
  fi
  if [[ "$file" == docs/SESSION_INDEX.md ]]; then
    has_session_index="true"
  fi
  if ! echo "$file" | grep -Eq "$allowed_doc_regex"; then
    doc_only="false"
  fi
done <<< "$diff_files"

require_session_log="false"
if [[ "$mode" == "ci" || "$target_branch" == "main" ]]; then
  require_session_log="true"
fi

if [[ "$require_session_log" == "true" ]]; then
  if [[ "$has_session_file" != "true" || "$has_session_index" != "true" ]]; then
    echo "ERROR: Missing session log updates (docs/SESSIONS + docs/SESSION_INDEX.md)." >&2
    exit 1
  fi
fi

if [[ "$doc_only" == "true" ]]; then
  if [[ "$target_branch" == "main" ]]; then
    exit 0
  fi
  if [[ "$allow_doc_only_pr" == "true" || "${ALLOW_DOC_ONLY_PR:-}" == "1" ]]; then
    exit 0
  fi
  echo "ERROR: Doc-only change detected. Push directly to main (fast-forward) instead of PR." >&2
  exit 1
fi

if [[ "$mode" != "ci" && "$target_branch" == "main" ]]; then
  echo "ERROR: Non-doc changes cannot be pushed directly to main. Use PR." >&2
  exit 1
fi

"$repo_root/scripts/doc_truth_gate.sh"
enforce_changed_session_files_gates

exit 0
