# 2026-03-22 — Consultant Core Debug Cadence Reset And Shadow-Def Guard A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEBUG-CADENCE-RESET-AND-SHADOW-DEF-GUARD-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Switched the active consultant-core block from turn-level runtime chasing to a meta-level cadence reset.
- Codified family-first residual work as `forensic -> implementation -> closure` in governance docs.
- Added an explicit forensic override path to `scripts/llm_quality_guarded.sh` so discovery can continue in `dev` lane without weakening `acceptance` semantics.
- Added an architecture test that locks the current duplicate top-level def debt in `truffles-api/app/services/reasoning_core.py` and blocks silent growth.
- Preserved `turn 11` as the next runtime family after this meta-block.

## Evidence chain
### 1. Structural hotspot facts
- `truffles-api/app/services/reasoning_core.py` is `15345` lines.
- It currently contains `147` top-level function defs with only `110` unique names.
- Current duplicate top-level name count: `37`.
- Representative shadowed owner names:
  - `_try_handle_turn_planner_safe_booking_verification_owner_cutover`
  - `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover`
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover`
  - `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover`

### 2. Process-cadence facts
- `AGENTS.md` and `docs/SESSION_START_PROMPT.txt` previously pushed residual debugging into a one-issue, early-full-TP cadence.
- `scripts/llm_quality_guarded.sh` previously required operators to manually stack multiple overrides when continuing forensic work after non-canonical or pending artifacts.
- The runbook already had a `dev/forensic` concept, but it was not explicit enough to prevent turn-by-turn churn in practice.

### 3. Implemented changes
- `AGENTS.md`
  - now treats residual debugging as family-first work
  - distinguishes `forensic`, `implementation`, and `closure`
  - clarifies that fail-fast replay is a closure tool, not the default discovery tool
- `docs/SESSION_START_PROMPT.txt`
  - now instructs agents to open forensic/family-level work before creating a new turn-level block
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - now documents the new guarded forensic override path and its limits
- `scripts/llm_quality_guarded.sh`
  - now supports `--forensic-override-reason <reason>`
  - when used in `dev` lane, it automatically enables repeat/pending continuation and downgrades manual-audit / forensic-SLA gates to `warn`
  - it does not allow this path to weaken `acceptance`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
  - now records the current duplicate-def debt by explicit counts and fails on unreviewed growth/drift

### 4. Canon truth after this block
- Active block becomes this cadence-reset meta-block.
- `turn 11` remains the next runtime family.
- Known duplicate top-level defs in `reasoning_core.py` are now explicit structural debt instead of invisible background risk.
- Acceptance remains strict; only forensic ergonomics changed.

## Residual debt
- `turn 11` runtime continuity is still open
- `reasoning_core.py` duplicate-def debt still exists and requires cleanup in a follow-up family
- session bootstrapping still does not auto-derive work mode metadata from the TP
- final program acceptance remains open

## Next move
- `implement_consultant_core_demo_salon_turn11_check_booking_reference_continuity_runtime_family_under_family_first_cadence`
