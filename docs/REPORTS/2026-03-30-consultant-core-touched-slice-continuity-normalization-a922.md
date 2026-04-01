# 2026-03-30 Consultant Core Touched-Slice Continuity Normalization — A922

## Summary
Repo-side block 9 moves the touched continuity artifact for the first fact family into canonical runtime state. The main changes are: `DialogStateService.write_runtime_payload(...)` now authors `DialogState.meta.class_carryover` for the governed `location / hours / parking` family, the same payload is mirrored into `context_manager.class_carryover` and `context_manager.canonical_dialog_state.meta.class_carryover`, and a dedicated touched-slice continuity guard now freezes that runtime-to-compatibility projection.

This block is now the active program block under the explicit user phase-advance waiver recorded in `docs/RECOVERY_PHASE_WAIVER.yaml` while practical truth remains `r35f`.

## What changed
- Activated `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md` as the current block in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_CANON.md`, and `docs/ACTIVE_PROGRAM.md`.
- Updated `truffles-api/app/core/dialog_state_service.py` so the governed first fact family now writes canonical `meta.class_carryover` inside runtime dialog state and mirrors that payload into `context_manager.class_carryover` plus `context_manager.canonical_dialog_state.meta.class_carryover`.
- Added `docs/TOUCHED_SLICE_CONTINUITY_GUARD.yaml`, `scripts/touched_slice_continuity_guard.py`, and `truffles-api/tests/architecture/test_touched_slice_continuity_guard.py` and wired the guard into `scripts/arch_guard.py`.
- Added deterministic proof in `truffles-api/tests/test_dialog_state_service.py` and `truffles-api/tests/test_consultant_core_runtime_contracts.py`.
- Updated `docs/system_forensics/authority_registry.json` and `docs/system_forensics/compatibility_carrier_inventory.json` so the continuity mechanism now records the touched-slice class-carryover authority shift explicitly.

## Machine-readable authority delta
New machine-readable truths in this block:
- the first fact family now writes its carryover continuity artifact inside canonical runtime state;
- `context_manager.class_carryover` for the touched slice is now a derived compatibility mirror of canonical runtime state;
- the next non-family turn preserves the canonical touched-slice artifact instead of dropping it back to legacy authorship;
- the active continuity registry now treats touched-slice closure as incomplete unless canonical runtime carryover and derived compatibility projection remain frozen by guard.

## Residual debt
- only the first fact family continuity is normalized; broader compatibility carriers remain mixed
- session-memory and pending-resume continuity still remain outside this block
- legacy mesh and final proof closure remain open
- practical replay and full human semantic audit are still required before any product-quality claim

## Block status
- Repo status: materially complete in repo if the touched-slice continuity guard/test suite stays green.
- Program status: this block is active under the explicit user phase-advance waiver, and the next phase advance still requires Brain / Top Architect acceptance.
- Next admissible block after acceptance: `legacy_drain_and_proof_closure`.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "touched_slice_class_carryover or materializes_touched_slice_class_carryover or preserves_existing_touched_slice_class_carryover"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "projects_touched_slice_class_carryover or persists_semantic_runtime_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_plane_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `git diff --check`
