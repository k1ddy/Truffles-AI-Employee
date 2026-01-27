#!/usr/bin/env bash
set -euo pipefail

status="done"
add_done=""
add_next=""
doc_only="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --status) status="$2"; shift 2;;
    --done) add_done="$2"; shift 2;;
    --next) add_next="$2"; shift 2;;
    --doc-only) doc_only="true"; shift 1;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/session_end.sh [--status done|paused|needs_fix] [--done NOTE] [--next NOTE] [--doc-only]
USAGE
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

case "$status" in
  done|paused|needs_fix) ;;
  *) echo "ERROR: Invalid status: $status (use done|paused|needs_fix)"; exit 1;;
esac

repo_root=$(git rev-parse --show-toplevel)
"$repo_root/scripts/session_check.sh"

sessions_dir="$repo_root/docs/SESSIONS"
branch=$(git rev-parse --abbrev-ref HEAD)
session_file=$(grep -rlxF -- "- branch: ${branch}" "$sessions_dir" | head -n1)

if [[ -z "$session_file" ]]; then
  echo "ERROR: Session file not found for branch ${branch}." >&2
  exit 1
fi

update_line() {
  local key="$1"
  local value="$2"
  local file="$3"
  if grep -q "^- ${key}: " "$file"; then
    sed -i "s|^- ${key}: .*|- ${key}: ${value}|" "$file"
  else
    echo "- ${key}: ${value}" >> "$file"
  fi
}

append_note() {
  local section="$1"
  local note="$2"
  local file="$3"
  [[ -z "$note" ]] && return 0
  if grep -q "^${section}:$" "$file"; then
    awk -v sec="$section:" -v note="  - ${note}" '
      $0==sec {print; getline; print note; while ($0 ~ /^  - /) {print $0; if (getline<=0) break} if ($0!="") print $0; next}
      {print}
    ' "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
  else
    echo "${section}:" >> "$file"
    echo "  - ${note}" >> "$file"
  fi
}

update_line "status" "$status" "$session_file"
update_line "last_updated" "$(date +%F)" "$session_file"
append_note "- done" "$add_done" "$session_file"
append_note "- next" "$add_next" "$session_file"

worktree=$(grep -E "^- worktree: " "$session_file" | head -n1 | sed 's/^- worktree: //')
task_package=$(grep -E "^- task_package: " "$session_file" | head -n1 | sed 's/^- task_package: //')

session_id=$(basename "$session_file")
session_id=${session_id#SESSION-}
session_id=${session_id%.md}

index_file="$repo_root/docs/SESSION_INDEX.md"
row="| ${session_id} | ${status} | ${branch} | ${worktree} | ${task_package} | $(date +%F) |"

if grep -q "^| ${session_id} |" "$index_file"; then
  awk -v sid="$session_id" -v row="$row" '
    $0 ~ "^\\| "sid" \\|" {print row; next} {print}
  ' "$index_file" > "${index_file}.tmp"
  mv "${index_file}.tmp" "$index_file"
else
  echo "$row" >> "$index_file"
fi

if [[ "$doc_only" == "true" ]]; then
  allowed_regex='^(docs/|STATE.md$|STRUCTURE.md$|AGENTS.md$)'
  changed=$(git diff --name-only HEAD)
  if [[ -z "$changed" ]]; then
    echo "ERROR: No changes detected for doc-only path." >&2
    exit 1
  fi
  while read -r file; do
    [[ -z "$file" ]] && continue
    if ! echo "$file" | grep -Eq "$allowed_regex"; then
      echo "ERROR: Non-doc file detected in doc-only mode: $file" >&2
      exit 1
    fi
  done <<< "$changed"
fi

echo "Session updated: ${session_file}"

git status -sb

git diff --stat
