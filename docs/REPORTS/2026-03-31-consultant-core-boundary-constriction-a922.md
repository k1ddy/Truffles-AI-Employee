# 2026-03-31 Consultant Core Boundary Constriction

## Summary
- Completed the sixth whole-system implementation block: `Consultant Core Boundary Constriction`.
- The active boundary/degrade hot path now stays inside an explicit handoff-safe envelope instead of inheriting visible `fact/collect` reply kinds from owner outcome.
- The next admissible runtime block is now `Pack / Runtime Separation Completion`.

## What Changed
- `truffles-api/app/core/response_realizer.py`
  - degrade replies now default to `handoff` unless a boundary-safe override explicitly requests `system`
- `truffles-api/app/core/consultant_runtime.py`
  - generic planner `degrade_path` now emits explicit boundary metadata:
    - `activate_handoff=true`
    - `reply_kind=handoff`
    - `degrade_stage=planner`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - added runtime proof for explicit planner degrade metadata
  - corrected boundary expectations so degrade cannot reuse `fact/collect` reply kind

## Why Necessary
- The typed boundary seam already existed, but degrade handling still retained one implicit visible-reply fallback through `decision.outcome`.
- That left boundary narrower than before, but not yet compiled into a strict validator/degrade-only contract.
- Pack/runtime separation cannot start honestly while boundary is still allowed to choose visible `fact/collect` reply semantics after the owner has spoken.

## Authority Delta
- Boundary reply-kind fallback no longer reuses owner outcome on degrade paths.
- Planner-generated degrade paths now declare the boundary-safe envelope explicitly instead of relying on implicit realizer behavior.
- The typed boundary hotspot set remains frozen and machine-readable under `docs/BOUNDARY_DEGRADE_GUARD.yaml`.

## Residual Architecture Debt
- Pack/runtime separation completion remains open.
- Broader fact families remain open.
- Legacy mesh drain remains open.
- Replay and full human semantic audit remain forbidden until the whole-system architecture blocks close.

## Block Status
- Repo status: complete
- Active block: `Consultant Core Boundary Constriction`
- Next admissible move: `Pack / Runtime Separation Completion`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-boundary-constriction-a922.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_boundary_degrade_guard.py`

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
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "boundary or invalid_outcome or handoff or ignored_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py truffles-api/tests/architecture/test_authority_registry.py truffles-api/tests/architecture/test_recovery_execution_guard.py truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `git diff --check`
