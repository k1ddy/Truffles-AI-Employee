# 2026-03-31 Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof

## Summary
- Reproved the remaining continuity, boundary restore, pack/runtime, legacy, and operational claims against live code after the semantic-owner reopen block.
- Forced pending-resume and handoff-resume restore to reuse only canonical pending-question contracts from `context_manager.canonical_dialog_state`.
- Converged live outbox execution surfaces on one canonical runtime helper: `run_canonical_outbox_process(...)`.
- Kept product/practical closure blocked; acceptance remains the next and only admissible lane.

## What Changed
- `DialogStateService` now exposes `project_context_manager_pending_question_contract(...)` as the canonical-only restore reader.
- `restore_pending_resume_payload(...)`, `derive_pending_resume_reason(...)`, and `derive_pending_booking_resume_boundary_payload(...)` now read canonical pending-question contract only.
- `state_service` boundary restore helpers removed stale fallback from `boundary_payload[expected_reply_type]` and `_derive_pending_resume_reason(...)`.
- `outbox_runtime_service` now owns one canonical processing helper used by default, scoped, and worker execution paths.
- added block guard:
  - `docs/SYSTEM_REPROOF_GUARD.yaml`
  - `scripts/system_reproof_guard.py`
  - `truffles-api/tests/architecture/test_system_reproof_guard.py`

## Why Necessary
- semantic-owner reopen fixed the first reopened invariant, but broader closure claims were still only narrative until continuity restore and operational callsites were reproven in code.
- canonical continuity cannot be claimed while pending-resume restore still accepts stale expected-reply fallback.
- operational dedupe cannot be claimed while multiple callers still implicitly own claim/process behavior without one explicit canonical runtime helper.

## Authority Delta
- boundary resume restore is no longer allowed to reconstruct pending continuity from non-canonical carriers on the active path.
- canonical pending-question contract is now the only restore source for pending-resume capture/restore inside this block.
- live outbox execution authority now converges on `run_canonical_outbox_process(...)`, while admin/console/worker remain thin caller surfaces only.
- active pack/runtime and legacy claims are reproven, not re-expanded; acceptance remains separate.

## Residual Architecture Debt
- current practical truth is still `r35f`
- replay and full human semantic audit remain open
- no product or practical closure claim is admissible yet

## Block Status
- Repo status: complete for continuity, boundary restore, pack/runtime, legacy, and operational live-code reproof
- Active block: `Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof`
- Next admissible move: `Replay + Full Human Semantic Audit`

## Evidence
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `docs/SYSTEM_REPROOF_GUARD.yaml`
- `scripts/system_reproof_guard.py`
- `truffles-api/tests/architecture/test_system_reproof_guard.py`
- `docs/CONTINUITY_STATE_NORMALIZATION_GUARD.yaml`
- `docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml`

## Validation
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/pack_runtime_separation_guard.py`
- `python3 scripts/legacy_mesh_drain_guard.py`
- `python3 scripts/operational_entrypoint_dedupe_guard.py`
- `python3 scripts/system_reproof_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "restore_pending_resume_payload or prepare_pending_handoff_resume_boundary_restore or prepare_resolved_handoff_resume_boundary_restore or resolve_resolved_handoff_resume_boundary_restore or resolve_pending_resume_boundary_activation"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume_payload"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "provider_unavailable_human_request_pending_resume"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py truffles-api/tests/test_admin_legacy_auth.py -k "outbox_service or admin_outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "run_outbox_process_job_execute"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_continuity_state_normalization_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_system_reproof_guard.py`
- `git diff --check`
