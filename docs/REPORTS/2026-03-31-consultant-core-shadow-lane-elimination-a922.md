# 2026-03-31 Consultant Core Shadow Lane Elimination

## Summary
- Completed the ninth whole-system implementation block: `Consultant Core Shadow Lane Elimination`.
- Removed runtime wrapper files `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/webhook.py`.
- Preserved their former contracts only through test-only shadow support modules.
- The next admissible runtime block is now `Operational Entrypoint Dedupe`.

## What Changed
- `truffles-api/app/services/reasoning_core.py`
  - removed from runtime code
- `truffles-api/app/webhook.py`
  - removed from runtime code
- `truffles-api/tests/support_reasoning_core_shadow.py`
  - preserves the former reasoning-core shim contract only for deterministic tests
- `truffles-api/tests/support_legacy_webhook_shadow.py`
  - preserves the former legacy root webhook contract only for deterministic tests
- `truffles-api/tests/test_reasoning_core.py`
  - now imports the test-only reasoning-core shadow support
- `truffles-api/tests/test_outbox_payload_contract.py`
  - now imports the test-only reasoning-core shadow support
- `truffles-api/tests/test_message_endpoint.py`
  - now imports the test-only legacy webhook shadow support
- `scripts/shadow_lane_elimination_guard.py`
  - freezes the removed-wrapper topology, repo import contract, and registry alignment
- `docs/SHADOW_LANE_ELIMINATION_GUARD.yaml`
  - machine-readable guard contract for the block
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
  - cumulative boundary snapshot no longer allows repo callsites from the removed runtime wrapper lanes
- `docs/system_forensics/dead_surface_registry.json`
  - now records removed runtime wrappers plus test-only shadow support residues
- `docs/system_forensics/legacy_caller_surface.json`
  - now removes deleted runtime wrapper files from the live frozen-module inventory

## Why Necessary
- After Legacy Mesh Drain, mounted router composition no longer needed `reasoning_core.py` or `app/webhook.py`.
- Leaving those runtime files in place preserved dormant authority lanes that could silently re-enter later work.
- This block makes the removal real while keeping deterministic tests intact through explicit test-only shadow support.

## Authority Delta
- No runtime file remains at `truffles-api/app/services/reasoning_core.py`.
- No runtime file remains at `truffles-api/app/webhook.py`.
- Repo imports for `app.services.reasoning_core` and `app.webhook` are now zero.
- `decision.py` remains shadow-only through `_legacy.py`, and `_legacy.py` remains outside app runtime.
- Removed wrapper contracts survive only in test-only support modules.

## Residual Architecture Debt
- `decision.py` remains a shadow-only router residue.
- `_legacy.py` remains a shadow-only router residue.
- Broader fact families remain open.
- Operational entrypoint dedupe remains open.
- Whole-system governance closure remains open.
- Replay and full human semantic audit remain forbidden until the whole-system architecture blocks close.

## Block Status
- Repo status: complete
- Active block: `Consultant Core Shadow Lane Elimination`
- Next admissible move: `Operational Entrypoint Dedupe`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-shadow-lane-elimination-a922.md`
- `docs/SHADOW_LANE_ELIMINATION_GUARD.yaml`
- `scripts/shadow_lane_elimination_guard.py`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `truffles-api/tests/support_reasoning_core_shadow.py`
- `truffles-api/tests/support_legacy_webhook_shadow.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_outbox_payload_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_shadow_lane_elimination_guard.py`

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
- `python3 scripts/shadow_lane_elimination_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_outbox_payload_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_removed_from_app_runtime or reasoning_core_has_no_app_runtime_importers or reasoning_core_shadow_support_has_no_direct_decision_router_import or reasoning_core_routing_reads_compiled_policy_snapshot"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_shadow_lane_elimination_guard.py`
- `git diff --check`
