#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_resume.sh [--agent SUFFIX] [--session-id ID]

Lists open sessions and prints resume instructions.
Defaults:
  --agent: current agent suffix inferred from SESSION_AGENT or required.
USAGE
}

agent=""
session_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) agent="$2"; shift 2;;
    --session-id) session_id="$2"; shift 2;;
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

if [[ -z "$session_id" && -z "$agent" ]]; then
  agent="${SESSION_AGENT:-}"
fi

if [[ -z "$session_id" && -z "$agent" ]]; then
  echo "ERROR: Provide --session-id or --agent (or set SESSION_AGENT)." >&2
  exit 1
fi

matches=$(awk -F'|' -v agent="$agent" -v sid_filter="$session_id" '
  function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
  /^\|/ {
    sid=trim($2); status=trim($3); branch=trim($4); worktree=trim($5); tp=trim($6);
    if (sid=="" || sid=="session_id") next;
    if (status=="done") next;
    if (sid_filter!="" && sid!=sid_filter) next;
    if (sid_filter=="" && agent!="" && sid !~ "-"agent"$") next;
    print sid "|" status "|" branch "|" worktree "|" tp;
  }
' "$index_file")

if [[ -z "$matches" ]]; then
  echo "No open sessions found." >&2
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
  echo "Session: ${sid} (${status})"
  echo "Worktree: ${wt}"
  echo "Branch: ${branch}"
  echo "Task Package: ${tp}"
  echo "Resume: cd ${wt} && scripts/session_check.sh"
  echo ""
done
