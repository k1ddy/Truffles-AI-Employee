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
  "Invariant"
  "Scope"
  "Out of scope"
  "Touch-list"
  "Plan (1..N)"
  "DoD"
  "Checks"
  "Evidence"
  "Doc sync plan (after implementation)"
  "Rollback"
  "No-go"
  "Handoff (for zero-context next agent)"
)

report_required_sections=(
  "Block identity"
  "Input baseline (FACT)"
  "FACT pre-check evidence (before changes)"
  "Contract delta"
  "Implemented changes"
  "Checks + outcomes"
  "Evidence"
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

if [[ -n "$GRAPH_PATH" ]]; then
  if ! rg -Fq "blocks:" "$GRAPH_PATH"; then
    echo "ERROR: Invalid block graph (missing 'blocks:'): $GRAPH_PATH" >&2
    exit 1
  fi
fi

echo "zero_context_gate: OK"
