#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_start.sh --session-id ID --task-package PATH [--title TITLE]
                               [--branch NAME] [--worktree PATH] [--base-ref REF] [--agent SUFFIX]
                               [--force-new] [--auto-commit]

Creates a new worktree + branch and registers a session log + index entry.
Defaults:
  session-id: YYYY-MM-DD-<slug>-<agent>
  branch:     feat/<session-id>
  worktree:   <repo-parent>/worktrees/<session-id>
  base-ref:   origin/main
  task-package: <required; must exist>
  agent:      required (or via SESSION_AGENT) and must match session-id suffix
  force-new:  allow new session even when open sessions exist for the same agent
  auto-commit: commit session log + index after creation (or set SESSION_AUTO_COMMIT=1)
  sync/dedupe: fetches `origin/main`, requires local `main` == `origin/main`,
               and blocks duplicate active `BLOCK_ID` sessions when TP defines `BLOCK_ID`
USAGE
}

session_id=""
title=""
task_package=""
branch=""
worktree=""
base_ref="origin/main"
force_new="false"
auto_commit="false"
agent=""
block_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-id) session_id="$2"; shift 2;;
    --title) title="$2"; shift 2;;
    --task-package) task_package="$2"; shift 2;;
    --branch) branch="$2"; shift 2;;
    --worktree) worktree="$2"; shift 2;;
    --base-ref) base_ref="$2"; shift 2;;
    --agent) agent="$2"; shift 2;;
    --force-new) force_new="true"; shift 1;;
    --auto-commit) auto_commit="true"; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

repo_root=$(git rev-parse --show-toplevel)
repo_parent=$(dirname "$repo_root")
canonical_repo_root="${TRUFFLES_CANONICAL_REPO_ROOT:-/home/zhan/truffles-main}"
session_lease_hours="${SESSION_LEASE_HOURS:-24}"
now_ts=$(date +%s)

extract_block_id_from_tp_file() {
  local tp_file="$1"
  if [[ ! -f "$tp_file" ]]; then
    echo ""
    return 0
  fi
  awk -F': ' '
    {
      if ($0 ~ /`BLOCK_ID`/) {
        value=$2
        gsub(/\r/, "", value)
        gsub(/^[ \t]+|[ \t]+$/, "", value)
        gsub(/`/, "", value)
        if (value == "" || value == "none" || value ~ /^<.*>$/) {
          next
        }
        print value
        exit
      }
    }
  ' "$tp_file"
}

ensure_origin_main_sync() {
  if ! git -C "$repo_root" remote get-url origin >/dev/null 2>&1; then
    echo "ERROR: remote 'origin' not configured; cannot validate sync with main." >&2
    exit 1
  fi

  if ! git -C "$repo_root" fetch --quiet origin main; then
    echo "ERROR: failed to fetch origin/main; sync check cannot continue." >&2
    exit 1
  fi

  local origin_main_sha local_main_sha
  origin_main_sha=$(git -C "$repo_root" rev-parse --verify origin/main 2>/dev/null || true)
  local_main_sha=$(git -C "$repo_root" rev-parse --verify main 2>/dev/null || true)

  if [[ -z "$origin_main_sha" || -z "$local_main_sha" ]]; then
    echo "ERROR: unable to resolve local/main or origin/main for sync check." >&2
    exit 1
  fi

  if [[ "$origin_main_sha" != "$local_main_sha" ]]; then
    echo "ERROR: local main is not synchronized with origin/main." >&2
    echo "Run: cd ${repo_root} && git checkout main && git pull --ff-only origin main" >&2
    exit 1
  fi
}

check_duplicate_active_block_session() {
  local candidate_block_id="$1"
  if [[ -z "$candidate_block_id" ]]; then
    return 0
  fi

  local index_file="$repo_root/docs/SESSION_INDEX.md"
  if [[ ! -f "$index_file" ]]; then
    return 0
  fi

  local active_entries
  active_entries=$(awk -F'|' '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^\|/ {
      sid=trim($2); status=trim($3); task_package=trim($6)
      if (sid=="" || sid=="session_id") next
      if (status!="active") next
      print sid "|" task_package
    }
  ' "$index_file")

  local sid tp_rel tp_abs active_block_id
  while IFS='|' read -r sid tp_rel; do
    [[ -z "$sid" || -z "$tp_rel" ]] && continue
    if [[ "$tp_rel" == /* ]]; then
      tp_abs="$tp_rel"
    else
      tp_abs="$repo_root/$tp_rel"
    fi
    active_block_id=$(extract_block_id_from_tp_file "$tp_abs")
    if [[ "$active_block_id" == "$candidate_block_id" ]]; then
      echo "ERROR: duplicate active block detected for BLOCK_ID '${candidate_block_id}'." >&2
      echo "Active session: ${sid} (task_package: ${tp_rel})" >&2
      echo "Resume existing session or close it before starting a duplicate block." >&2
      exit 1
    fi
  done <<< "$active_entries"
}

if ! [[ "$session_lease_hours" =~ ^[0-9]+$ ]]; then
  echo "ERROR: SESSION_LEASE_HOURS must be an integer (got '${session_lease_hours}')." >&2
  exit 1
fi

if [[ "$repo_root" == "$canonical_repo_root" ]]; then
  current_branch=$(git -C "$repo_root" rev-parse --abbrev-ref HEAD)
  if [[ "$current_branch" != "main" && "$current_branch" != "master" ]]; then
    echo "ERROR: Canonical repo root must stay on main/master before starting a session." >&2
    echo "Run: cd ${repo_root} && git checkout main" >&2
    exit 1
  fi
fi

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

if [[ "$worktree" == "$repo_root" ]]; then
  echo "ERROR: worktree must not be canonical repo root (${repo_root})." >&2
  echo "Use a dedicated worktree under ${repo_parent}/worktrees/." >&2
  exit 1
fi

if [[ -z "$title" ]]; then
  title="Session ${session_id}"
fi

if [[ -z "$agent" ]]; then
  agent="${SESSION_AGENT:-}"
fi

if [[ -z "$agent" ]]; then
  echo "ERROR: --agent is required (or set SESSION_AGENT)." >&2
  exit 1
fi

if ! [[ "$agent" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "ERROR: Invalid agent suffix '${agent}'." >&2
  exit 1
fi

if [[ "$session_id" != *"-${agent}" ]]; then
  echo "ERROR: session-id must end with '-${agent}'." >&2
  exit 1
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

block_id=$(extract_block_id_from_tp_file "$repo_root/$task_package")
ensure_origin_main_sync
check_duplicate_active_block_session "$block_id"

if [[ "${SESSION_AUTO_COMMIT:-}" == "1" || "${SESSION_AUTO_COMMIT:-}" == "true" ]]; then
  auto_commit="true"
fi

index_file_root="$repo_root/docs/SESSION_INDEX.md"
if [[ -f "$index_file_root" ]]; then
  open_matches_raw=$(awk -F'|' -v agent="$agent" '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^\|/ {
      sid=trim($2); status=trim($3); branch=trim($4); worktree=trim($5); last_updated=trim($7);
      if (sid=="" || sid=="session_id") next;
      if (status!="active") next;
      if (sid ~ "-"agent"$") { print sid "|" status "|" branch "|" worktree "|" last_updated; }
    }
  ' "$index_file_root")

  open_matches=""
  stale_matches=""
  if [[ -n "$open_matches_raw" ]]; then
    while IFS='|' read -r sid status sid_branch sid_worktree sid_last_updated; do
      [[ -z "$sid" ]] && continue
      stale_reasons=""

      if [[ ! -d "$sid_worktree" ]]; then
        stale_reasons="worktree_missing"
      fi
      if ! git -C "$repo_root" show-ref --verify --quiet "refs/heads/${sid_branch}"; then
        stale_reasons="${stale_reasons:+${stale_reasons},}branch_missing"
      fi

      session_file="$repo_root/docs/SESSIONS/SESSION-${sid}.md"
      ref_last_updated="$sid_last_updated"
      if [[ -f "$session_file" ]]; then
        file_last_updated=$(grep -E "^- last_updated: " "$session_file" | head -n1 | sed 's/^- last_updated: //' || true)
        if [[ -n "$file_last_updated" ]]; then
          ref_last_updated="$file_last_updated"
        fi
      fi

      if [[ -z "$ref_last_updated" ]]; then
        stale_reasons="${stale_reasons:+${stale_reasons},}last_updated_missing"
      else
        if parsed_ts=$(date -d "$ref_last_updated" +%s 2>/dev/null); then
          age_hours=$(( (now_ts - parsed_ts) / 3600 ))
          if (( age_hours > session_lease_hours )); then
            stale_reasons="${stale_reasons:+${stale_reasons},}stale_${age_hours}h"
          fi
        else
          stale_reasons="${stale_reasons:+${stale_reasons},}last_updated_invalid"
        fi
      fi

      if [[ -n "$stale_reasons" ]]; then
        stale_matches+="${sid}|${status}|${sid_worktree}|${sid_branch}|${stale_reasons}"$'\n'
        continue
      fi

      open_matches+="${sid}|${status}|${sid_worktree}|${sid_branch}"$'\n'
    done <<< "$open_matches_raw"
  fi

  if [[ -n "$stale_matches" ]]; then
    echo "WARN: stale active sessions ignored for '-${agent}' (lease=${session_lease_hours}h):" >&2
    while IFS='|' read -r sid status wt br reasons; do
      [[ -z "$sid" ]] && continue
      echo "  - ${sid} (${status}) ${wt} ${br} [${reasons}]" >&2
    done <<< "$stale_matches"
    echo "Hint: run scripts/session_audit.sh for governance cleanup." >&2
  fi

  if [[ -n "$open_matches" && "$force_new" != "true" ]]; then
    echo "ERROR: Open session exists for agent suffix '-${agent}'." >&2
    while IFS='|' read -r sid status wt br; do
      [[ -z "$sid" ]] && continue
      echo "  - ${sid} (${status}) ${wt} ${br}" >&2
    done <<< "$open_matches"
    echo "Resume with: scripts/session_resume.sh --agent ${agent}" >&2
    echo "Or pass --force-new if you intentionally start a parallel session for ${agent}." >&2
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
- block_id: ${block_id:-n/a}
- research_gate: required
- root_cause_gate: required
- reuse_gate: required
- release_safety_gate: required
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

if [[ "$auto_commit" == "true" ]]; then
  git -C "$worktree" add "docs/SESSIONS/SESSION-${session_id}.md" "docs/SESSION_INDEX.md"
  if ! git -C "$worktree" diff --cached --quiet; then
    if ! git -C "$worktree" commit -m "chore: start session ${session_id}"; then
      echo "ERROR: auto-commit failed; run scripts/session_check.sh and commit manually." >&2
      exit 1
    fi
  fi
fi

echo "Session created: ${session_file}"
echo "Worktree: ${worktree}"
echo "Branch: ${branch}"
echo "Task Package: ${task_package}"
if [[ -n "$block_id" ]]; then
  echo "Block ID: ${block_id}"
fi
