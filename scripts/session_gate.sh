#!/usr/bin/env bash
set -euo pipefail

mode=""
target_branch=""
base_ref=""
head_ref=""
allow_doc_only_pr="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) mode="$2"; shift 2;;
    --target-branch) target_branch="$2"; shift 2;;
    --base) base_ref="$2"; shift 2;;
    --head) head_ref="$2"; shift 2;;
    --allow-doc-only-pr) allow_doc_only_pr="true"; shift 1;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/session_gate.sh --mode pre-push|ci --target-branch BRANCH --base BASE_SHA --head HEAD_SHA [--allow-doc-only-pr]
USAGE
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "$mode" || -z "$target_branch" || -z "$head_ref" ]]; then
  echo "ERROR: mode, target-branch, base, head are required." >&2
  exit 1
fi

if [[ -z "$base_ref" ]]; then
  base_ref="origin/main"
fi

repo_root=$(git rev-parse --show-toplevel)

empty_tree=$(git hash-object -t tree /dev/null)
if [[ "$base_ref" =~ ^0+$ ]]; then
  diff_files=$(git diff --name-only "$empty_tree" "$head_ref")
else
  diff_files=$(git diff --name-only "$base_ref" "$head_ref")
fi

if [[ -z "$diff_files" ]]; then
  echo "No changes detected for gate; skipping." >&2
  exit 0
fi

allowed_doc_regex='^(docs/|STATE.md$|STRUCTURE.md$|AGENTS.md$)'

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
done <<< "$diff_files"

require_session_log="false"
if [[ "$mode" == "ci" || "$target_branch" == "main" ]]; then
  require_session_log="true"
fi

if [[ "$require_session_log" == "true" ]]; then
  if [[ "$has_session_file" != "true" || "$has_session_index" != "true" ]]; then
    echo "ERROR: Missing session log updates (docs/SESSIONS + docs/SESSION_INDEX.md)." >&2
    exit 1
  fi
fi

if [[ "$doc_only" == "true" ]]; then
  if [[ "$target_branch" == "main" ]]; then
    exit 0
  fi
  if [[ "$allow_doc_only_pr" == "true" || "${ALLOW_DOC_ONLY_PR:-}" == "1" ]]; then
    exit 0
  fi
  echo "ERROR: Doc-only change detected. Push directly to main (fast-forward) instead of PR." >&2
  exit 1
fi

if [[ "$mode" != "ci" && "$target_branch" == "main" ]]; then
  echo "ERROR: Non-doc changes cannot be pushed directly to main. Use PR." >&2
  exit 1
fi

"$repo_root/scripts/doc_truth_gate.sh"

exit 0
