# 2026-03-31 Consultant Core Continuity / State Normalization — A922

## Summary
This block closes the active-slice continuity/state normalization work after the first governed fact-family cutover. It does not claim broader carryover collapse, boundary constriction, or legacy drain closure.

## What changed
- Promoted `Continuity / State Normalization` to the active whole-system block.
- Added canonical compatibility re-projection to `DialogStateService.write_runtime_payload(...)`.
- Canonical runtime writes now rebuild `context_manager` and `session_memory` continuity snapshots from `DialogState` on the active path.
- Stale top-level `expected_reply_*` and `current_goal` no longer survive canonical runtime writes.
- `pending_resume` capture now uses canonical-derived compatibility snapshots instead of stale legacy continuity fields.
- Added `docs/CONTINUITY_STATE_NORMALIZATION_GUARD.yaml`, `scripts/continuity_state_normalization_guard.py`, and architecture/runtime proof coverage.
- Rebased the whole-system authority and compatibility registries so continuity truth now closes this block honestly and names `post_owner_semantic_constriction` as the next phase.

## Why this was necessary
The first governed fact family was already cut over, but continuity truth still remained split across canonical runtime state, `context_manager`, `session_memory`, top-level expected-reply/current-goal fields, and `pending_resume`. Without this block, the system could keep stale observable continuity alive beside the canonical writer even after the fact-side mechanism was repaired.

## Authority delta
- Canonical runtime state now reprojects active-slice compatibility continuity surfaces on write instead of leaving them stale.
- `context_manager` and `session_memory` remain derived compatibility surfaces on the active path, not continuity co-writers.
- `pending_resume` is now captured from canonical-derived continuity state rather than stale legacy shadows.
- The next admissible runtime block is now `Post-Owner Semantic Constriction`.

## Residual debt
- broader service/consult carryover surfaces remain legacy-heavy beyond the active slice
- post-owner semantic constriction remains open
- boundary constriction remains open
- broader fact families remain open
- legacy mesh drain remains open

## Block status
- Repo status: complete.
- Program status: `Continuity / State Normalization` is the active block; `Post-Owner Semantic Constriction` is the next admissible runtime move.
- Next admissible move: complete post-owner semantic constriction before boundary constriction or replay.

## Evidence
- `python3 scripts/build_agent_packet.py` — pass
- `python3 scripts/build_agent_packet.py --check` — pass
- `python3 scripts/recovery_execution_guard.py` — pass
- `python3 scripts/authority_freeze_guard.py` — pass
- `python3 scripts/fact_plane_guard.py` — pass
- `python3 scripts/fact_family_cutover_guard.py` — pass
- `python3 scripts/touched_slice_continuity_guard.py` — pass
- `python3 scripts/continuity_state_normalization_guard.py` — pass
- `python3 scripts/arch_guard.py` — pass
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume or current_goal or expected_reply or class_carryover or session_memory"` — pass
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "touched_slice_class_carryover or pending_resume or current_goal or expected_reply or session_memory"` — pass
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` — pass
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py` — pass
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py` — pass
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py` — pass
- `pytest -q truffles-api/tests/architecture/test_touched_slice_continuity_guard.py` — pass
- `pytest -q truffles-api/tests/architecture/test_continuity_state_normalization_guard.py` — pass
- `git diff --check` — pass
