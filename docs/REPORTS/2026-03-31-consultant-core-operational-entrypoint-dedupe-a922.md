# 2026-03-31 Consultant Core Operational Entrypoint Dedupe

## Summary
- Completed the tenth whole-system implementation block: `Consultant Core Operational Entrypoint Dedupe`.
- Narrowed live outbox execution surfaces to shared public helpers in `truffles-api/app/services/outbox_runtime_service.py`.
- Added visible repo-contract coverage for `/admin/outbox/process`.
- The next admissible runtime block is now `Whole-System Governance Closure`.

## What Changed
- `truffles-api/app/services/outbox_runtime_service.py`
  - added public `run_scoped_outbox_process(...)` so scoped operator execution no longer reconstructs local low-level orchestration outside the shared runtime owner
- `truffles-api/app/routers/console.py`
  - `_run_outbox_process_job(...)` execute mode now delegates through `run_scoped_outbox_process(...)`
- `truffles-api/tests/test_console_ops_jobs.py`
  - updated console execute coverage to pin delegation into the shared scoped runtime helper
- `truffles-api/tests/test_outbox_worker_settings.py`
  - added direct runtime-helper proof for `run_scoped_outbox_process(...)`
- `truffles-api/tests/test_admin_legacy_auth.py`
  - added visible token/delegation coverage for `/admin/outbox/process`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - updated outbox topology expectations so console must use `run_scoped_outbox_process(...)`
- `scripts/operational_entrypoint_dedupe_guard.py`
  - freezes the outbox operational caller topology and repo callsite set
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
  - machine-readable guard contract for the block

## Why Necessary
- Shadow-lane elimination removed dormant runtime wrappers, but the outbox mechanism still had one remaining local operator execution path in `console.py` plus missing visible repo-contract coverage for `/admin/outbox/process`.
- This block makes operational narrowing real without guessing at deployment removal of the dedicated service-app boundary.

## Authority Delta
- `outbox_runtime_service.py` is now the only app-runtime owner of low-level outbox claim/process/archive orchestration.
- `outbox_service.py` and `admin.py` remain thin delegates to `run_default_outbox_process(...)`.
- `console.py` execute mode no longer holds a local scoped claim/process path; it delegates to `run_scoped_outbox_process(...)`.
- `workers/outbox.py` remains on `run_outbox_worker_cycle(...)` only.
- `/admin/outbox/process` now has visible repo-contract coverage.

## Residual Architecture Debt
- `outbox_service_app.py` remains a separate dedicated service-app composition root.
- Console `outbox_process` execute remains a live scoped operator surface, now intentionally thin.
- Broader fact families and pack-specific truth/catalog residue remain open.
- Whole-system governance closure remains open.
- Replay and full human semantic audit remain forbidden until the whole-system architecture blocks close.

## Block Status
- Repo status: complete
- Active block: `Consultant Core Operational Entrypoint Dedupe`
- Next admissible move: `Whole-System Governance Closure`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`
- `scripts/operational_entrypoint_dedupe_guard.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/test_admin_legacy_auth.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- updated machine-readable registries and generated packet

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
- `python3 scripts/operational_entrypoint_dedupe_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py -k "run_scoped_outbox_process_uses_shared_runtime_helpers"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_admin_legacy_auth.py -k "admin_outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "run_outbox_process_job_execute"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "outbox_worker_and_console_use_shared_runtime_settings or console_router_has_no_local_outbox_claim_helper or outbox_request_wrappers_are_thin"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- `git diff --check`
