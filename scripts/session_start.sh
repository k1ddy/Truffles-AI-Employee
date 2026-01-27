#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_start.sh --session-id ID --task-package PATH [--title TITLE]
                               [--branch NAME] [--worktree PATH] [--base-ref REF] [--force-new]

Creates a new worktree + branch and registers a session log + index entry.
Defaults:
  session-id: YYYY-MM-DD-<slug>-<agent>
  branch:     feat/<session-id>
  worktree:   <repo-parent>/worktrees/<session-id>
  base-ref:   origin/main
  task-package: <required; must exist>
  force-new:  allow new session even when open sessions exist
USAGE
}

session_id=""
title=""
task_package=""
branch=""
worktree=""
base_ref="origin/main"
force_new="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-id) session_id="$2"; shift 2;;
    --title) title="$2"; shift 2;;
    --task-package) task_package="$2"; shift 2;;
    --branch) branch="$2"; shift 2;;
    --worktree) worktree="$2"; shift 2;;
    --base-ref) base_ref="$2"; shift 2;;
    --force-new) force_new="true"; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

repo_root=$(git rev-parse --show-toplevel)
repo_parent=$(dirname "$repo_root")

if [[ -z "$session_id" ]]; then
  echo "ERROR: --session-id is required (format: YYYY-MM-DD-<slug>-<agent>)." >&2
  exit 1
fi

if ! [[ "$session_id" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9][a-z0-9-]*-[a-z0-9][a-z0-9-]*$ ]]; then
  echo "ERROR: Invalid session-id '$session_id'." >&2
  echo "Expected: YYYY-MM-DD-<slug>-<agent> (lowercase, digits, dashes)." >&2
  exit 1
fi

branch=${branch:-"feat/${session_id}"}
worktree=${worktree:-"${repo_parent}/worktrees/${session_id}"}

if [[ -z "$title" ]]; then
  title="Session ${session_id}"
fi

if [[ -z "$task_package" ]]; then
  echo "ERROR: --task-package is required and must point to an existing file." >&2
  exit 1
fi

if [[ "$task_package" == /* ]]; then
  if [[ "$task_package" != "$repo_root/"* ]]; then
    echo "ERROR: task-package must be inside repo root: ${repo_root}" >&2
    exit 1
  fi
  task_package="${task_package#"$repo_root/"}"
fi

if [[ ! -f "$repo_root/$task_package" ]]; then
  echo "ERROR: Task Package not found: ${task_package}" >&2
  exit 1
fi

index_file_root="$repo_root/docs/SESSION_INDEX.md"
if [[ -f "$index_file_root" ]]; then
  open_sessions=$(awk -F'|' '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^\|/ {
      sid=trim($2); status=trim($3); worktree=trim($5);
      if (sid=="" || sid=="session_id") next;
      if (status=="done") next;
      print sid "|" status "|" worktree;
    }
  ' "$index_file_root")
  if [[ -n "$open_sessions" && "$force_new" != "true" ]]; then
    echo "ERROR: Open sessions exist. Resume before starting a new session." >&2
    while IFS='|' read -r sid status wt; do
      [[ -z "$sid" ]] && continue
      echo "  - ${sid} (${status}) ${wt}" >&2
    done <<< "$open_sessions"
    echo "Resume with: scripts/session_resume.sh (then pick session-id)" >&2
    echo "Or pass --force-new if you intentionally start a parallel session." >&2
    exit 1
  fi
  agent_suffix="${session_id##*-}"
  open_matches=$(awk -F'|' -v agent="$agent_suffix" '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^\|/ {
      sid=trim($2); status=trim($3); worktree=trim($5);
      if (sid=="" || sid=="session_id") next;
      if (status=="done") next;
      if (sid ~ "-"agent"$") {
        print sid "|" status "|" worktree;
      }
    }
  ' "$index_file_root")
  if [[ -n "$open_matches" ]]; then
    echo "ERROR: Open session exists for agent suffix '-${agent_suffix}'." >&2
    while IFS='|' read -r sid status wt; do
      [[ -z "$sid" ]] && continue
      echo "  - ${sid} (${status}) ${wt}" >&2
    done <<< "$open_matches"
    echo "Resume with: scripts/session_resume.sh --session-id <id>" >&2
    exit 1
  fi
  if grep -q "^| ${session_id} |" "$index_file_root"; then
    echo "ERROR: session-id already exists in SESSION_INDEX: ${session_id}" >&2
    exit 1
  fi
fi

if [[ -e "$worktree" ]]; then
  echo "ERROR: worktree path already exists: $worktree" >&2
  exit 1
fi

if git -C "$repo_root" show-ref --verify --quiet "refs/heads/${branch}"; then
  echo "ERROR: branch already exists: ${branch}" >&2
  exit 1
fi

if git -C "$repo_root" show-ref --verify --quiet "refs/remotes/origin/${branch}"; then
  echo "ERROR: remote branch already exists: origin/${branch}" >&2
  exit 1
fi

git -C "$repo_root" worktree add -b "$branch" "$worktree" "$base_ref"

mkdir -p "$worktree/docs/SESSIONS"

session_file="$worktree/docs/SESSIONS/SESSION-${session_id}.md"
index_file="$worktree/docs/SESSION_INDEX.md"

if [[ ! -f "$session_file" ]]; then
  cat <<EOF_SESSION > "$session_file"
# SESSION ${session_id} — ${title}

- status: active
- owner: Top Architect / Brain / Hands
- task_package: ${task_package}
- branch: ${branch}
- worktree: ${worktree}
- base_ref: ${base_ref}
- scope: <fill scope>
- done:
  - Session created.
- next:
  - Fill Task Package and execute plan.
- evidence:
  - ${task_package}
- last_updated: $(date +%F)
EOF_SESSION
fi

if [[ ! -f "$index_file" ]]; then
  cat <<'EOF_INDEX' > "$index_file"
# SESSION INDEX

**Источник правды по активным сессиям.** Обновляется вместе с `docs/SESSIONS/*.md`.

| session_id | status | branch | worktree | task_package | last_updated |
| --- | --- | --- | --- | --- | --- |
EOF_INDEX
fi

if ! grep -q "^| ${session_id} |" "$index_file"; then
  echo "| ${session_id} | active | ${branch} | ${worktree} | ${task_package} | $(date +%F) |" >> "$index_file"
fi

echo "Session created: ${session_file}"
echo "Worktree: ${worktree}"
echo "Branch: ${branch}"
echo "Task Package: ${task_package}"
