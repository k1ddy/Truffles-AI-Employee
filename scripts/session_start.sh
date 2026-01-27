#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_start.sh --session-id ID [--title TITLE] [--task-package PATH]
                               [--branch NAME] [--worktree PATH] [--base-ref REF]

Creates a new worktree + branch and registers a session log + index entry.
Defaults:
  session-id: YYYY-MM-DD-<slug>-<agent>
  branch:     feat/<session-id>
  worktree:   <repo-parent>/worktrees/<session-id>
  base-ref:   origin/main
  task-package: docs/TASK_PACKAGES/TP-<session-id>.md
USAGE
}

session_id=""
title=""
task_package=""
branch=""
worktree=""
base_ref="origin/main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-id) session_id="$2"; shift 2;;
    --title) title="$2"; shift 2;;
    --task-package) task_package="$2"; shift 2;;
    --branch) branch="$2"; shift 2;;
    --worktree) worktree="$2"; shift 2;;
    --base-ref) base_ref="$2"; shift 2;;
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
task_package=${task_package:-"docs/TASK_PACKAGES/TP-${session_id}.md"}

if [[ -z "$title" ]]; then
  title="Session ${session_id}"
fi

index_file_root="$repo_root/docs/SESSION_INDEX.md"
if [[ -f "$index_file_root" ]]; then
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

if [[ ! -f "$worktree/$task_package" ]]; then
  mkdir -p "$(dirname "$worktree/$task_package")"
  cat <<EOF_TP > "$worktree/$task_package"
# TP-${session_id} — ${title}

- **Название/цель:** <1-2 sentences>
- **Canon refs:** <owner docs + STATE.md NOW/GAP>
- **Invariant:** <what must not get worse>
- **Scope:** <in scope>
- **Out of scope:** <out of scope>
- **Touch-list:**
  - <files/tables>
- **Plan:**
  1) <step>
- **DoD:**
  - <acceptance>
- **Checks:** <commands>
- **Evidence:** <CI/logs/trace>
- **Rollback:** <rollback>
- **No-go:** <forbidden>
- **Риски/блокеры:** <risks>
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: ${branch}
  - Worktree: ${worktree}
  - Base: ${base_ref}
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
EOF_TP
fi

echo "Session created: ${session_file}"
echo "Worktree: ${worktree}"
echo "Branch: ${branch}"
echo "Task Package: ${task_package}"
