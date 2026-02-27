#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/zero_context_gate.sh --tp <task_package.md> --report <report.md> [--graph docs/BLOCK_GRAPH.yaml]

Validates required zero-context sections for block delivery.
USAGE
}

TP_PATH=""
REPORT_PATH=""
GRAPH_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tp)
      TP_PATH="${2:-}"
      shift 2
      ;;
    --report)
      REPORT_PATH="${2:-}"
      shift 2
      ;;
    --graph)
      GRAPH_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TP_PATH" || -z "$REPORT_PATH" ]]; then
  usage
  exit 1
fi

if [[ ! -f "$TP_PATH" ]]; then
  echo "ERROR: TP file not found: $TP_PATH" >&2
  exit 1
fi

if [[ ! -f "$REPORT_PATH" ]]; then
  echo "ERROR: Report file not found: $REPORT_PATH" >&2
  exit 1
fi

if [[ -n "$GRAPH_PATH" && ! -f "$GRAPH_PATH" ]]; then
  echo "ERROR: Block graph file not found: $GRAPH_PATH" >&2
  exit 1
fi

require_section() {
  local file="$1"
  local section="$2"
  if ! rg -Fq "## ${section}" "$file"; then
    echo "ERROR: Missing section '## ${section}' in ${file}" >&2
    return 1
  fi
}

require_token() {
  local file="$1"
  local token="$2"
  if ! rg -Fq "$token" "$file"; then
    echo "ERROR: Missing token '${token}' in ${file}" >&2
    return 1
  fi
}

tp_required_sections=(
  "Block identity"
  "Название/цель"
  "Canon refs"
  "FACT pre-check (before implementation)"
  "One web search (mandatory before implementation)"
  "Root cause (mandatory)"
  "Reuse-first plan (mandatory)"
  "Invariant"
  "Scope"
  "Out of scope"
  "Touch-list"
  "Plan (1..N)"
  "DoD"
  "Checks"
  "Evidence"
  "Token / run budget (mandatory for expensive suites)"
  "Release safety (mandatory for non-doc changes)"
  "Doc sync plan (after implementation)"
  "Rollback"
  "No-go"
  "Risks/Blockers"
  "Handoff (for zero-context next agent)"
)

report_required_sections=(
  "Block identity"
  "Input baseline (FACT)"
  "FACT pre-check evidence (before changes)"
  "One web search evidence"
  "Root cause validation"
  "Reuse-first outcome"
  "Contract delta"
  "Implemented changes"
  "Checks + outcomes"
  "Iteration budget outcomes"
  "Evidence"
  "Release safety decision"
  "Canon/doc sync updates"
  "Residual GAP / Risks"
  "Handoff (for zero-context next agent)"
  "Verdict"
)

for section in "${tp_required_sections[@]}"; do
  require_section "$TP_PATH" "$section"
done

for section in "${report_required_sections[@]}"; do
  require_section "$REPORT_PATH" "$section"
done

for token in '`BLOCK_ID`' '`DEPENDS_ON`' '`UNLOCKS`'; do
  require_token "$TP_PATH" "$token"
  require_token "$REPORT_PATH" "$token"
done

for file in "$TP_PATH" "$REPORT_PATH"; do
  if rg -n "<[^>]+>" "$file" >/dev/null; then
    echo "ERROR: Unresolved placeholders found in ${file}" >&2
    rg -n "<[^>]+>" "$file" >&2 || true
    exit 1
  fi
done

for token in "Query (exact)" "Five Whys" "Decision:" "Max full runs" "Strategy:"; do
  require_token "$TP_PATH" "$token"
done

if [[ -n "$GRAPH_PATH" ]]; then
  if ! rg -Fq "blocks:" "$GRAPH_PATH"; then
    echo "ERROR: Invalid block graph (missing 'blocks:'): $GRAPH_PATH" >&2
    exit 1
  fi
fi

echo "zero_context_gate: OK"
