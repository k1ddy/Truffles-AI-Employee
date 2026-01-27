#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
sessions_dir="$repo_root/docs/SESSIONS"
index_file="$repo_root/docs/SESSION_INDEX.md"

if [[ ! -d "$sessions_dir" ]]; then
  echo "ERROR: docs/SESSIONS not found." >&2
  exit 1
fi

issues=0

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
    echo "ISSUE: ${session_id} has missing required fields." >&2
    issues=$((issues + 1))
  fi

  if [[ -f "$index_file" ]] && ! grep -q "^| ${session_id} |" "$index_file"; then
    echo "ISSUE: ${session_id} missing from SESSION_INDEX." >&2
    issues=$((issues + 1))
  fi

  if [[ "$status" == "active" || "$status" == "paused" ]]; then
    if [[ ! -d "$worktree" ]]; then
      echo "ISSUE: ${session_id} status=${status} but worktree missing: ${worktree}" >&2
      issues=$((issues + 1))
    fi
    if ! git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
      echo "ISSUE: ${session_id} status=${status} but branch missing: ${branch}" >&2
      issues=$((issues + 1))
    fi
  fi

  if [[ "$status" == "done" ]]; then
    if [[ -d "$worktree" ]]; then
      echo "ISSUE: ${session_id} status=done but worktree still exists: ${worktree}" >&2
      issues=$((issues + 1))
    fi
    if git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
      echo "ISSUE: ${session_id} status=done but branch still exists: ${branch}" >&2
      issues=$((issues + 1))
    fi
  fi

  if [[ -n "$last_updated" && "$status" == "active" ]]; then
    if date -d "$last_updated" +%s >/dev/null 2>&1; then
      last_ts=$(date -d "$last_updated" +%s)
      now_ts=$(date +%s)
      age_days=$(( (now_ts - last_ts) / 86400 ))
      if (( age_days > 7 )); then
        echo "ISSUE: ${session_id} active but stale ${age_days} days (last_updated=${last_updated})." >&2
        issues=$((issues + 1))
      fi
    fi
  fi

done

if [[ $issues -gt 0 ]]; then
  echo "Session audit failed: ${issues} issue(s)." >&2
  exit 1
fi

echo "Session audit OK"
