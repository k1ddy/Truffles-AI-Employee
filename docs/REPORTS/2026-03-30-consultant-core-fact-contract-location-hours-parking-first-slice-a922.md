# 2026-03-30 Consultant Core First Fact-Family Cutover — A922

## Summary
Repo-side block 8 moves the first canary fact family `location / hours / parking` onto the explicit fact plane on the governed consultant-core hot path. The main changes are: executor-side reroute of the family to `catalog.location`, removal of direct-truth / pack-runtime sibling bypass for that family, a narrower `catalog.location` branch that obeys binding-authorized `allowed_fact_refs`, and a deterministic family-cutover guard.

This block is now the active program block under the explicit user phase-advance waiver recorded in `docs/RECOVERY_PHASE_WAIVER.yaml` while practical truth remains `r35f`.

## What changed
- Activated `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md` as the current block in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_CANON.md`, and `docs/ACTIVE_PROGRAM.md`.
- Updated `truffles-api/app/core/turn_executor.py` so the targeted family now reroutes to `catalog.location` on the live fact-plane hot path even when stale binding still points at `info` or `catalog.service_query`.
- Updated `truffles-api/app/core/turn_executor.py` so the targeted family now returns explicit unresolved fact-plane output instead of falling through to direct-truth or pack-runtime sibling replies.
- Updated `truffles-api/app/services/tool_registry_service.py` so `catalog.location` respects binding-authorized `allowed_fact_refs` and cannot re-infer `parking` from raw message text when parking is out of scope.
- Added `docs/FACT_FAMILY_CUTOVER_GUARD.yaml` plus `scripts/fact_family_cutover_guard.py`, and wired the guard into `scripts/arch_guard.py`.
- Updated `docs/system_forensics/authority_registry.json` so the `fact_scope` mechanism now records the first-family cutover closure criteria, the new evidence set, and the next required phase.
- Added deterministic proof in `truffles-api/tests/test_consultant_core_runtime_contracts.py` and `truffles-api/tests/architecture/test_fact_family_cutover_guard.py`.

## Machine-readable authority delta
New machine-readable truths in this block:
- the first canary family no longer relies on raw binding tool_action if that binding points outside the explicit family resolver;
- the first canary family no longer falls through to direct-truth or pack-runtime sibling responses on the governed hot path;
- `catalog.location` may not widen `parking` from raw text when the binding plan excludes parking;
- the active authority registry now treats the first-family cutover as complete only if the reroute, bypass removal, and narrowed `catalog.location` behavior all stay frozen by guard.

## Residual debt
- Only the first fact family is cut over; other fact families still remain mixed.
- Touched-slice continuity normalization is still open.
- Legacy mesh and pack-runtime adapters still exist outside the governed family slice.
- Practical replay and full human semantic audit are still required before any product-quality claim.

## Block status
- Repo status: materially complete in repo if the deterministic family-cutover guard/test suite stays green.
- Program status: phase-advanced to block 9 under the explicit user waiver; any phase advance beyond block 9 still requires Brain / Top Architect acceptance.
- Next admissible block after block-9 acceptance: `legacy_drain_and_proof_closure`.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "location_base_bundle or stale_service_query_binding or direct_truth_and_pack_bypass or reinfer_parking_outside_allowed_scope or fact_family"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_fact_plane_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `git diff --check`
