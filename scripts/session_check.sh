#!/usr/bin/env bash
set -euo pipefail

hooks_path_expected=".githooks"

repo_root=$(git rev-parse --show-toplevel)
branch=$(git rev-parse --abbrev-ref HEAD)

if [[ "$branch" == "HEAD" ]]; then
  echo "ERROR: Detached HEAD; session check requires a named branch." >&2
  exit 1
fi

if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  if [[ "${SESSION_ALLOW_MAIN:-}" != "1" ]]; then
    echo "ERROR: Work on main/master is запрещено. Use a worktree branch." >&2
    exit 1
  fi
fi

hooks_path=$(git config --get core.hooksPath || true)
if [[ "$hooks_path" != "$hooks_path_expected" && "$hooks_path" != "${repo_root}/${hooks_path_expected}" ]]; then
  echo "ERROR: git hooks not installed. Run: scripts/install_hooks.sh" >&2
  exit 1
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

if ! grep -q "^| ${session_id} |" "$index_file"; then
  echo "ERROR: Session ID missing in SESSION_INDEX: ${session_id}" >&2
  exit 1
fi

echo "Session OK: ${session_id} (${branch})"
