#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/session_index_rebuild.sh [--stdout]

Rebuilds docs/SESSION_INDEX.md from docs/SESSIONS/SESSION-*.md.
USAGE
}

mode="write"

case "${1:-}" in
  --stdout) mode="stdout";;
  -h|--help) usage; exit 0;;
  "") ;;
  *) echo "Unknown arg: $1" >&2; usage; exit 1;;
esac

repo_root=$(git rev-parse --show-toplevel)
sessions_dir="$repo_root/docs/SESSIONS"
index_file="$repo_root/docs/SESSION_INDEX.md"

if [[ ! -d "$sessions_dir" ]]; then
  echo "ERROR: docs/SESSIONS not found at ${sessions_dir}" >&2
  exit 1
fi

tmp_file=$(mktemp)
rows_file=$(mktemp)

cleanup() {
  rm -f "$tmp_file" "$rows_file"
}
trap cleanup EXIT

get_field() {
  local key="$1"
  local file="$2"
  local value

  value=$(sed -n "s/^- ${key}: //p" "$file" | head -n1)
  value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  if [[ -z "$value" ]]; then
    echo ""
    return
  fi
  echo "$value" | tr '|' '-'
}

warn_missing() {
  local field="$1"
  local file="$2"
  echo "WARN: missing ${field} in ${file}" >&2
}

while IFS= read -r -d '' file; do
  session_id=$(basename "$file")
  session_id="${session_id#SESSION-}"
  session_id="${session_id%.md}"

  status=$(get_field "status" "$file")
  branch=$(get_field "branch" "$file")
  worktree=$(get_field "worktree" "$file")
  task_package=$(get_field "task_package" "$file")
  last_updated=$(get_field "last_updated" "$file")

  if [[ -z "$status" ]]; then
    warn_missing "status" "$file"
    status="unknown"
  fi
  if [[ -z "$branch" ]]; then
    warn_missing "branch" "$file"
    branch="unknown"
  fi
  if [[ -z "$worktree" ]]; then
    warn_missing "worktree" "$file"
    worktree="unknown"
  fi
  if [[ -z "$task_package" ]]; then
    warn_missing "task_package" "$file"
    task_package="unknown"
  fi
  if [[ -z "$last_updated" ]]; then
    warn_missing "last_updated" "$file"
    last_updated="unknown"
  fi

  printf "| %s | %s | %s | %s | %s | %s |\n" \
    "$session_id" "$status" "$branch" "$worktree" "$task_package" "$last_updated" >> "$rows_file"
done < <(find "$sessions_dir" -maxdepth 1 -type f -name 'SESSION-*.md' -print0)

{
  echo "# SESSION INDEX"
  echo ""
  echo "**Источник правды по активным сессиям.** Обновляется вместе с \`docs/SESSIONS/*.md\`."
  echo ""
  echo "| session_id | status | branch | worktree | task_package | last_updated |"
  echo "| --- | --- | --- | --- | --- | --- |"
  if [[ -s "$rows_file" ]]; then
    LC_ALL=C sort -r "$rows_file"
  fi
} > "$tmp_file"

if [[ "$mode" == "stdout" ]]; then
  cat "$tmp_file"
else
  mv "$tmp_file" "$index_file"
fi
