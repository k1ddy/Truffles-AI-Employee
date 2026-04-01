# REPORT 2026-02-28-process-gates-adoption-audit-a912

## Block identity
- `BLOCK_ID`: `PROCESS-GATES-ADOPTION-AUDIT-2026Q2`
- `Session`: `2026-02-28-process-gates-adoption-audit-a912`
- `Branch`: `feat/2026-02-28-process-gates-adoption-audit-a912`

## Goal
Сформировать machine-readable adoption evidence для phased migration research-driven gates по legacy-сессиям без изменения runtime behavior.

## FACT baseline
- Command: `scripts/session_audit.sh`
- Result:
  - `open_sessions=112`
  - `research/root_cause/reuse/release_safety`: `required=4`, `missing=108`, `invalid=0`
  - `warnings=319`, `errors=0`

## Implementation
- Added structured output mode in `session_audit`:
  - `--adoption-report-json <path>`
  - output includes gate counts + cohorts (`all_required`, `legacy_missing`, `legacy_partial`, `invalid_mode`, `stale_active`, `done_cleanup_candidates`, `legacy_bundle`).
- Preserved existing human-readable output and exit semantics (`strict` behavior unchanged).

## Evidence
- Structured artifact: `/tmp/session_adoption_a912.json`
- Validation command:
  - `jq '.gate_counts.research_gate, (.cohorts.legacy_missing|length), (.cohorts.all_required|length), (.cohorts.stale_active|length), (.cohorts.done_cleanup_candidates|length)' /tmp/session_adoption_a912.json`
- Output snapshot:
  - `research_gate`: `{required: 4, optional: 0, off: 0, missing: 108, invalid: 0}`
  - `legacy_missing=108`
  - `all_required=4`
  - `stale_active=107`
  - `done_cleanup_candidates=93`

## Cohort migration criteria
1. `all_required` (4 sessions)
- Criteria: all four gates in `required`, no invalid modes.
- Action: keep as enforcement baseline.

2. `legacy_missing` (108 sessions)
- Criteria: at least one gate field absent.
- Action: phase-1 migration: fill metadata with `optional`; phase-2 promote to `required` per owner decision.

3. `stale_active` (107 sessions)
- Criteria: `status=active` and `age_hours > stale_hours`.
- Action: close/refresh stale sessions before raising gate strictness.

4. `done_cleanup_candidates` (93 sessions)
- Criteria: `status=done` but branch/worktree still exists.
- Action: cleanup backlog (`worktree remove` + branch delete) by governance owner.

## Checks
- `bash -n scripts/session_audit.sh scripts/session_check.sh scripts/session_gate.sh`
- `SESSION_AGENT=a912 scripts/session_check.sh`
- `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_a912.json`

## Risk notes
- Historical metadata quality drives noise in first adoption cycles.
- Migration to `required` must stay phased; instant strict rollout for legacy remains out of scope.

## Next block handoff
- `UNLOCK`: `PROCESS-GATES-LEGACY-MIGRATION-2026Q2`
- First command:
  - `scripts/session_audit.sh --adoption-report-json /tmp/session_adoption_next.json`
- Start with `legacy_missing` cohort and convert by controlled batches.
