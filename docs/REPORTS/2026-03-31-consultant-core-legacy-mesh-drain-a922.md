# 2026-03-31 Consultant Core Legacy Mesh Drain

## Summary
- Completed the eighth whole-system implementation block: `Consultant Core Legacy Mesh Drain`.
- Mounted webhook package exports no longer import `decision.py`.
- `decision.py` and `_legacy.py` now remain only as shadow/test or unmounted residual router surfaces.
- The next admissible runtime block is now `Shadow Lane Elimination`.

## What Changed
- `truffles-api/app/routers/webhook/expected_reply_interrupt_runtime.py`
  - new dedicated helper module for expected-reply info-interrupt logic previously attached to `decision.py`
- `truffles-api/app/routers/webhook/__init__.py`
  - package-root lazy export for `_should_block_expected_reply_by_info` now resolves through `expected_reply_interrupt_runtime.py`
  - no longer imports `app.routers.webhook.decision`
- `truffles-api/app/routers/webhook/decision.py`
  - now delegates the expected-reply info-interrupt helper cluster to the new dedicated helper module for compatibility callers
- `scripts/legacy_mesh_drain_guard.py`
  - freezes the drained import topology
- `scripts/build_agent_packet.py`
  - now treats `program.allowed_touch` as the explicit waiver set for frozen semantic files so the active block can touch `decision.py` without weakening the global forbidden-file law
- `docs/LEGACY_SUNSET.yaml`
  - decision-surface active waiver now includes the current shadow-only delegation lines so `legacy_freeze_guard.py` stays aligned with the real frozen baseline
- `docs/system_forensics/dead_surface_registry.json`
  - now records `decision.py` as a shadow/test compatibility surface with `_legacy.py` as its only app-side importer
- `docs/system_forensics/legacy_caller_surface.json`
  - now records the drained router shadow surfaces explicitly, including `_legacy.py`

## Why Necessary
- After pack/runtime separation, the live hot path no longer needed `decision.py`, but the mounted webhook package still depended on it for one compatibility export.
- That kept the router legacy megafile inside the mounted package boundary and made legacy-mesh drain incomplete.
- This block severs that last package-root dependency without pretending shadow wrappers are already deleted.

## Authority Delta
- Mounted webhook package no longer depends on `decision.py`.
- App-runtime `decision.py` importers shrink to `_legacy.py` only.
- App runtime has no `_legacy.py` importers.
- Router legacy mesh is now represented as shadow-only or unmounted residue rather than as a live package-boundary dependency.

## Residual Architecture Debt
- `reasoning_core.py` remains open as a shadow wrapper surface.
- `app/webhook.py` remains open as a wrapper/delete-candidate surface.
- Broader fact families remain open.
- Operational entrypoint dedupe remains open.
- Replay and full human semantic audit remain forbidden until the whole-system architecture blocks close.

## Block Status
- Repo status: complete
- Active block: `Consultant Core Legacy Mesh Drain`
- Next admissible move: `Shadow Lane Elimination`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/LEGACY_MESH_DRAIN_GUARD.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/build_agent_packet.py`
- `scripts/legacy_mesh_drain_guard.py`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/expected_reply_interrupt_runtime.py`
- `truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `truffles-api/tests/test_message_endpoint.py`

## Validation
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/pack_runtime_separation_guard.py`
- `python3 scripts/legacy_mesh_drain_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py::test_expected_reply_info_block_detects_booking_interrupt_info_turns truffles-api/tests/test_booking_info_interrupt_contract.py::test_decision_expected_reply_block_check_is_localized_to_single_contract_site`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "question_like_hour_reply_not_blocked_for_expected_time or question_like_daypart_reply_not_blocked_for_expected_time or declarative_daypart_reply_not_blocked_for_expected_time or question_like_daypart_exact_time_reply_not_blocked_for_expected_time or duration_question_without_booking_signal_stays_blocked_for_expected_time or booking_verification_handoff_intent_detection"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_eager_decision_import or app_runtime_has_no_eager_decision_importers"`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py`
- `git diff --check`
