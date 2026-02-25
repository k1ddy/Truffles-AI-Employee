#!/usr/bin/env bash
set -euo pipefail

hooks_path_expected=".githooks"

repo_root=$(git rev-parse --show-toplevel)
branch=$(git rev-parse --abbrev-ref HEAD)
canonical_repo_root="${TRUFFLES_CANONICAL_REPO_ROOT:-/home/zhan/truffles-main}"
allowed_doc_regex='^(docs/|STATE.md$|STRUCTURE.md$|AGENTS.md$)'
core_behavior_regex='^(truffles-api/app/routers/webhook/|truffles-api/app/services/(intent_service|ai_service)\.py$|truffles-api/app/schemas/intent\.py$|prompts/llm_policy_core\.md$|contracts/llm/)'

collect_scope_changed_files() {
  local changed_files
  changed_files=$(git diff --name-only --cached)
  if [[ -n "$changed_files" ]]; then
    printf '%s\n' "$changed_files"
    return 0
  fi

  if git rev-parse --verify --quiet "@{u}" >/dev/null; then
    git diff --name-only "@{u}"..HEAD || true
    return 0
  fi

  if git rev-parse --verify --quiet "origin/main" >/dev/null; then
    local merge_base
    merge_base=$(git merge-base HEAD origin/main || true)
    if [[ -n "$merge_base" ]]; then
      git diff --name-only "$merge_base"..HEAD || true
      return 0
    fi
  fi
}

summary_gate_validate_candidate() {
  local candidate="$1"
  local summary_path="$candidate"
  if [[ "$summary_path" != /* ]]; then
    summary_path="$repo_root/$summary_path"
  fi
  if [[ ! -f "$summary_path" ]]; then
    echo "${candidate}: file_not_found"
    return 1
  fi
  if ! jq -e '.infra_valid == true and .semantic_valid == true' "$summary_path" >/dev/null 2>&1; then
    echo "${candidate}: infra_or_semantic_invalid"
    return 1
  fi
  if ! jq -e '(.config.dry_run // false) == false' "$summary_path" >/dev/null 2>&1; then
    echo "${candidate}: dry_run_non_evaluable"
    return 1
  fi
  if ! jq -e '(.judge.enabled // false) == true' "$summary_path" >/dev/null 2>&1; then
    echo "${candidate}: judge_disabled"
    return 1
  fi
  if ! jq -e '(.config.mode // "") == "llm"' "$summary_path" >/dev/null 2>&1; then
    echo "${candidate}: mode_is_not_llm"
    return 1
  fi
  if ! jq -e '((.openai_preflight // []) | any(.purpose == "llm" and .valid == true))' "$summary_path" >/dev/null 2>&1; then
    echo "${candidate}: missing_valid_llm_openai_preflight"
    return 1
  fi
  echo "$summary_path"
  return 0
}

enforce_llm_evidence_gate() {
  local changed_files="$1"
  local requires_gate="false"
  while read -r file; do
    [[ -z "$file" ]] && continue
    if echo "$file" | grep -Eq "$core_behavior_regex"; then
      requires_gate="true"
      break
    fi
  done <<< "$changed_files"

  if [[ "$requires_gate" != "true" ]]; then
    return 0
  fi

  if [[ "$status" != "done" && "${SESSION_ENFORCE_LLM_EVIDENCE:-}" != "1" ]]; then
    return 0
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required for LLM evidence gate validation." >&2
    exit 1
  fi

  mapfile -t summary_candidates < <(
    grep -Eo '[^[:space:]]*summary\.json' "$session_file" \
      | sed 's/[),.;]$//' \
      | sort -u
  )
  if [[ ${#summary_candidates[@]} -eq 0 ]]; then
    echo "ERROR: Core behavior change requires LLM-quality evidence in session log." >&2
    echo "Add a summary path under '- evidence:' (example: /tmp/booking_quality/<run-id>/summary.json)." >&2
    exit 1
  fi

  local valid_summary=""
  local candidate
  local check_result=""
  declare -a errors=()
  for candidate in "${summary_candidates[@]}"; do
    if check_result=$(summary_gate_validate_candidate "$candidate"); then
      valid_summary="$check_result"
      break
    fi
    errors+=("$check_result")
  done

  if [[ -z "$valid_summary" ]]; then
    echo "ERROR: Core behavior change requires valid LLM-quality evidence." >&2
    echo "Expected: infra_valid=true, semantic_valid=true, config.dry_run=false, judge.enabled=true, config.mode=llm, llm openai_preflight valid." >&2
    for item in "${errors[@]}"; do
      echo "  - $item" >&2
    done
    exit 1
  fi
}

session_meta_value() {
  local key="$1"
  grep -E "^- ${key}: " "$session_file" | head -n1 | sed "s/^- ${key}: //"
}

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

enforce_zero_context_gate_if_required() {
  local mode
  mode=$(session_meta_value "zero_context_gate")
  if [[ -z "$mode" || "$mode" == "off" || "$mode" == "optional" ]]; then
    return 0
  fi
  if [[ "$mode" != "required" ]]; then
    echo "ERROR: Unsupported zero_context_gate mode '${mode}' in ${session_file}." >&2
    exit 1
  fi

  local tp_rel report_rel graph_rel
  tp_rel=$(session_meta_value "zero_context_tp")
  report_rel=$(session_meta_value "zero_context_report")
  graph_rel=$(session_meta_value "zero_context_graph")

  if [[ -z "$tp_rel" || -z "$report_rel" ]]; then
    echo "ERROR: zero_context_gate=required needs zero_context_tp and zero_context_report in ${session_file}." >&2
    exit 1
  fi

  local tp_path report_path graph_path gate_script
  tp_path=$(resolve_repo_path "$tp_rel")
  report_path=$(resolve_repo_path "$report_rel")
  graph_path=$(resolve_repo_path "$graph_rel")
  gate_script="$repo_root/scripts/zero_context_gate.sh"

  if [[ ! -x "$gate_script" ]]; then
    echo "ERROR: zero context gate script is missing or not executable: ${gate_script}" >&2
    exit 1
  fi

  local cmd=("$gate_script" --tp "$tp_path" --report "$report_path")
  if [[ -n "$graph_path" ]]; then
    cmd+=(--graph "$graph_path")
  fi
  "${cmd[@]}"
}

if [[ "$branch" == "HEAD" ]]; then
  echo "ERROR: Detached HEAD; session check requires a named branch." >&2
  exit 1
fi

if [[ "$repo_root" == "$canonical_repo_root" && "$branch" != "main" && "$branch" != "master" ]]; then
  echo "ERROR: Canonical repo root must stay on main/master. Use a worktree branch under /home/zhan/worktrees." >&2
  exit 1
fi

hooks_path=$(git config --get core.hooksPath || true)
if [[ "$hooks_path" != "$hooks_path_expected" && "$hooks_path" != "${repo_root}/${hooks_path_expected}" ]]; then
  echo "ERROR: git hooks not installed. Run: scripts/install_hooks.sh" >&2
  exit 1
fi

if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  changed_files=$(git diff --name-only --cached)
  if [[ -z "$changed_files" ]]; then
    base_ref=""
    if git rev-parse --verify --quiet "@{u}" >/dev/null; then
      base_ref="@{u}"
    else
      base_ref="origin/main"
    fi
    if git rev-parse --verify --quiet "$base_ref" >/dev/null; then
      changed_files=$(git diff --name-only "$base_ref"..HEAD || true)
    fi
  fi

  if [[ -n "$changed_files" ]]; then
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
    done <<< "$changed_files"

    if [[ "$doc_only" == "true" ]]; then
      if [[ "$has_session_file" != "true" || "$has_session_index" != "true" ]]; then
        echo "ERROR: Doc-only on main requires session log + index in the same commit." >&2
        exit 1
      fi
      echo "Session OK: doc-only main"
      exit 0
    fi
  fi

  if [[ "${SESSION_ALLOW_MAIN:-}" != "1" ]]; then
    echo "ERROR: Work on main/master is запрещено. Use a worktree branch." >&2
    exit 1
  fi
fi

sessions_dir="$repo_root/docs/SESSIONS"
if [[ ! -d "$sessions_dir" ]]; then
  echo "ERROR: docs/SESSIONS not found. Create session log first." >&2
  exit 1
fi

session_file=$(grep -rlxF -- "- branch: ${branch}" "$sessions_dir" || true)

if [[ -z "$session_file" ]]; then
  echo "ERROR: Session file not found for branch ${branch}." >&2
  exit 1
fi

if [[ $(echo "$session_file" | wc -l) -ne 1 ]]; then
  echo "ERROR: Multiple session files match branch ${branch}." >&2
  echo "$session_file" >&2
  exit 1
fi

status=$(grep -E "^- status: " "$session_file" | head -n1 | sed 's/^- status: //')
worktree=$(grep -E "^- worktree: " "$session_file" | head -n1 | sed 's/^- worktree: //')
task_package=$(grep -E "^- task_package: " "$session_file" | head -n1 | sed 's/^- task_package: //')

if [[ "$status" != "active" ]]; then
  if [[ "$status" == "done" && "${SESSION_ALLOW_DONE:-}" == "1" ]]; then
    :
  else
    echo "ERROR: Session status is '${status}'. Set status to active before work." >&2
    exit 1
  fi
fi

if [[ "$worktree" != "$repo_root" ]]; then
  echo "ERROR: Worktree mismatch. Expected ${worktree}, got ${repo_root}." >&2
  exit 1
fi

if [[ -z "$task_package" || ! -f "$repo_root/$task_package" ]]; then
  echo "ERROR: Task Package not found: ${task_package}" >&2
  exit 1
fi

tp_placeholders=$(grep -nE "<[^>]+>" "$repo_root/$task_package" || true)
if [[ -n "$tp_placeholders" ]]; then
  echo "ERROR: Task Package contains placeholders; fill them before commit." >&2
  echo "$tp_placeholders" >&2
  exit 1
fi

index_file="$repo_root/docs/SESSION_INDEX.md"
if [[ ! -f "$index_file" ]]; then
  echo "ERROR: docs/SESSION_INDEX.md missing." >&2
  exit 1
fi

session_id=$(basename "$session_file")
session_id=${session_id#SESSION-}
session_id=${session_id%.md}

agent="${SESSION_AGENT:-}"
if [[ -n "$agent" ]]; then
  if [[ "$session_id" != *"-${agent}" ]]; then
    echo "ERROR: SESSION_AGENT='${agent}' does not match session id '${session_id}'." >&2
    echo "Resume the correct worktree or unset SESSION_AGENT for legacy sessions." >&2
    exit 1
  fi
fi

if ! grep -q "^| ${session_id} |" "$index_file"; then
  echo "ERROR: Session ID missing in SESSION_INDEX: ${session_id}" >&2
  exit 1
fi

scope_changed_files=$(collect_scope_changed_files)
enforce_zero_context_gate_if_required
enforce_llm_evidence_gate "$scope_changed_files"

echo "Session OK: ${session_id} (${branch})"
