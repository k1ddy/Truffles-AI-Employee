#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_resume.sh [--agent SUFFIX] [--session-id ID] [--all]

Lists open sessions and prints resume instructions.
Defaults:
  --agent: current agent suffix inferred from SESSION_AGENT (if set).
  --all: list sessions across all agents.
USAGE
}

agent=""
session_id=""
all="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) agent="$2"; shift 2;;
    --session-id) session_id="$2"; shift 2;;
    --all) all="true"; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

repo_root=$(git rev-parse --show-toplevel)
index_file="$repo_root/docs/SESSION_INDEX.md"

if [[ ! -f "$index_file" ]]; then
  echo "ERROR: docs/SESSION_INDEX.md missing." >&2
  exit 1
fi

if [[ -z "$session_id" && -z "$agent" && "$all" != "true" ]]; then
  agent="${SESSION_AGENT:-}"
fi

if [[ "$all" != "true" && -z "$session_id" && -z "$agent" ]]; then
  echo "ERROR: Set SESSION_AGENT or pass --agent/--all." >&2
  exit 1
fi

if [[ "$all" == "true" ]]; then
  agent=""
fi

if [[ -n "$session_id" && -n "$agent" && "$all" != "true" ]]; then
  if [[ "$session_id" != *"-${agent}" ]]; then
    echo "ERROR: session-id '${session_id}' does not match agent suffix '${agent}'." >&2
    echo "Use --all to override." >&2
    exit 1
  fi
fi

matches=$(awk -F'|' -v agent="$agent" -v sid_filter="$session_id" -v all="$all" '
  function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
  /^\|/ {
    sid=trim($2); status=trim($3); branch=trim($4); worktree=trim($5); tp=trim($6);
    if (sid=="" || sid=="session_id") next;
    if (status=="done") next;
    if (sid_filter!="" && sid!=sid_filter) next;
    if (all!="true" && sid_filter=="" && agent!="" && sid !~ "-"agent"$") next;
    print sid "|" status "|" branch "|" worktree "|" tp;
  }
' "$index_file")

if [[ -z "$matches" ]]; then
  if [[ -n "$agent" ]]; then
    echo "No open sessions found for agent suffix '-${agent}'." >&2
    echo "Use --all to list sessions across all agents." >&2
  else
    echo "No open sessions found." >&2
  fi
  exit 1
fi

count=$(echo "$matches" | wc -l | tr -d ' ')
if [[ "$count" -gt 1 && -z "$session_id" ]]; then
  echo "Multiple open sessions found. Re-run with --session-id." >&2
  echo "$matches" | while IFS='|' read -r sid status branch wt tp; do
    echo "- ${sid} (${status}) ${wt} ${branch} ${tp}" >&2
  done
  exit 1
fi

echo "$matches" | while IFS='|' read -r sid status branch wt tp; do
  dirty="clean"
  if [[ -d "$wt/.git" ]]; then
    if ! git -C "$wt" diff --quiet || ! git -C "$wt" diff --cached --quiet; then
      dirty="dirty"
    fi
    if [[ -n "$(git -C "$wt" status --porcelain -uall 2>/dev/null)" ]]; then
      dirty="dirty"
    fi
  fi
  echo "Session: ${sid} (${status})"
  echo "Worktree: ${wt} (${dirty})"
  echo "Branch: ${branch}"
  echo "Task Package: ${tp}"
  echo "Resume: cd ${wt} && scripts/session_check.sh"
  echo ""
done
