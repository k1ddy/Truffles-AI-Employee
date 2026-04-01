# 2026-03-31 Consultant Core Post-Owner Semantic Constriction — A922

## Summary
This block closes the active post-owner semantic constriction work on the whole-system hot path. It does not claim boundary constriction, pack/runtime separation completion, or legacy mesh drain.

## What changed
- Promoted `Post-Owner Semantic Constriction` to the active whole-system block.
- `TurnExecutor` owner-backed pending-question and semantic contract builders now return canonical owner contracts instead of rebuilding them from booking state, service-query hints, or runtime convenience data.
- Owner-backed execution meta now stays enrichment-only: canonical owner data no longer reappears as execution-side `semantic_enrichment`, while real downstream grounding deltas can still flow as bounded enrichment.
- `DialogStateService` owner-backed state write now preserves owner-authored semantic contracts and ignores conflicting booking/runtime semantic projections when materializing canonical state.
- `ConsultantRuntime` owner-backed trace/meta projection now ignores stale runtime semantic projection state and records the owner contract plus explicit execution enrichment only.
- Extended the semantic bridge hotspot freeze to cover `truffles-api/app/routers/webhook/context_manager.py` and refreshed deterministic proof coverage for post-owner mutations, owner-backed executor contracts, and owner-backed projection state.

## Why this was necessary
The fact-plane cutover and continuity normalization already narrowed the active slice, but downstream executor/runtime/state helpers could still rebuild meaning-bearing contracts after the owner spoke. Without this block, booking state, runtime projection state, or compatibility payloads could remain a practical second semantic lane.

## Authority delta
- Owner-backed semantic and pending-question contracts now remain canonical downstream artifacts.
- Executor no longer re-authors owner meaning from booking state or service hints on owner-backed turns.
- Runtime trace/meta no longer merges stale runtime semantic projections over the owner contract.
- Canonical state write no longer repopulates owner-backed semantic contract meaning from booking/runtime semantic residue.
- The next admissible runtime block is now `Boundary Constriction`.

## Residual debt
- boundary constriction remains open
- pack/runtime separation completion remains open
- broader fact families remain open
- legacy mesh drain remains open
- broader continuity carrier collapse beyond the active slice remains open

## Block status
- Repo status: complete.
- Program status: `Post-Owner Semantic Constriction` is the active block; `Boundary Constriction` is the next admissible runtime move.
- Next admissible move: complete boundary constriction before pack/runtime separation or replay.

## Evidence
- `python3 scripts/build_agent_packet.py` — pass
- `python3 scripts/build_agent_packet.py --check` — pass
- `python3 scripts/recovery_execution_guard.py` — pass
- `python3 scripts/authority_freeze_guard.py` — pass
- `python3 scripts/fact_plane_guard.py` — pass
- `python3 scripts/fact_family_cutover_guard.py` — pass
- `python3 scripts/touched_slice_continuity_guard.py` — pass
- `python3 scripts/continuity_state_normalization_guard.py` — pass
- `python3 scripts/semantic_bridge_growth_guard.py` — pass
- `python3 scripts/arch_guard.py` — pass
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_mutation or semantic_frame or owner_backed or memory_profile or execution_contract"` — pass
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision_state_write or owner_backed_projection or conflicting_booking_semantics"` — pass
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py truffles-api/tests/architecture/test_authority_registry.py truffles-api/tests/architecture/test_recovery_execution_guard.py truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py` — pass
- `git diff --check` — pass
