# 2026-03-31 Consultant Core Pack / Runtime Separation Completion

## Summary
- Completed the seventh whole-system implementation block: `Consultant Core Pack / Runtime Separation Completion`.
- The active fact/service hot path now consumes only the public `pack_runtime_service` helper seam instead of adapter-private pack helper calls.
- The next admissible runtime block is now `Legacy Mesh Drain`.

## What Changed
- `truffles-api/app/services/pack_runtime_service.py`
  - now owns the active public runtime helper surface for service truth, pricing, duration, presence, and not-found replies
  - no longer imports `app.services.pack_runtime_default`
  - no longer exposes `get_pack_adapter(...)` on the active runtime facade
- `truffles-api/app/services/tool_registry_service.py`
  - no longer imports `get_pack_adapter(...)`
  - no longer calls adapter-private pack helper names on the active runtime path
  - now consumes only the public helper seam from `pack_runtime_service.py`
- `truffles-api/app/core/turn_executor.py`
  - active pricing/service fallback no longer depends on adapter-private pack behavior
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
  - freezes the narrowed hotspot/callsite set for the active pack/runtime seam

## Why Necessary
- The explicit fact contract and first narrow fact-family cutover were already active, but active runtime callers still reached pack behavior through adapter-private helpers and dynamic default-adapter dispatch.
- That left pack truth and pack behavior only partially separated on the live hot path.
- Legacy-mesh drain is not honest until the active runtime path can survive without adapter-private pack behavior ownership.

## Authority Delta
- Public `pack_runtime_service.py` helpers now own the active service retrieval/rendering seam.
- `tool_registry_service.py` and `turn_executor.py` no longer co-own pack behavior by reaching adapter-private helpers.
- Demo/default/fallback adapter modules remain frozen residual surfaces for later drain, but they no longer govern the active hot path.

## Residual Architecture Debt
- Broader fact families remain open.
- Legacy mesh drain remains open.
- Shadow lane elimination remains open.
- Operational entrypoint dedupe remains open.
- Replay and full human semantic audit remain forbidden until the whole-system architecture blocks close.

## Block Status
- Repo status: complete
- Active block: `Consultant Core Pack / Runtime Separation Completion`
- Next admissible move: `Legacy Mesh Drain`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/governance_delta.json`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`

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
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_pack_query_engine_contract.py truffles-api/tests/test_pack_grounding_contract.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py -k "service_query_pricing_uses_price_item_fallback or service_query_duration_prefers_message_service_over_stale_slot or avoids_unrelated_semantic_fallback"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "direct_truth_and_pack_bypass or pack_runtime or service_query or fact_family or public_pack_runtime_seam"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`
- `git diff --check`
