# TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922

## Название / цель
Перепроверить и, где нужно, дочинить continuity, boundary, pack/runtime, legacy и operational closure claims по живому коду после semantic-owner reopen так, чтобы acceptance шёл уже от честной repo-side базы.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## One web search (mandatory before implementation)
- Query: `site:microservices.io transactional outbox pattern idempotent consumer`
- Date/time: `2026-03-31T23:38:00+05:00`
- Sources opened:
  - `https://microservices.io/patterns/data/transactional-outbox`
- Ready solutions found:
  - a single canonical outbox processor should own claim/process semantics while multiple callers remain thin ingress surfaces
- Decision: `reuse/integrate`
- Reason:
  - operational reproof needed one canonical runtime helper instead of several callers re-owning outbox claim/process behavior
  - the transactional outbox pattern matches the required direction: one durable processing owner with idempotent thin callers
- Rejected variants:
  - keep duplicated claim/process behavior in admin/console/worker paths
  - delete operator surfaces before converging them on one canonical runtime helper

## Root cause (mandatory)
- Symptom:
  - after semantic-owner reopen, broader closure claims for continuity, boundary restore, pack/runtime, legacy, and operational dedupe were still not reproven against live code
- Minimal reproduction:
  - pending resume / handoff restore still derived continuity from stale non-canonical expected-reply fields in `state_service.py`
  - pending-resume capture in `DialogStateService` still accepted broader context fallback than the canonical `context_manager.canonical_dialog_state.pending_question_contract`
  - live outbox execution still exposed multiple operational callers without one explicit canonical runner helper
- Evidence:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/outbox_runtime_service.py`
  - `truffles-api/app/routers/admin.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/workers/outbox.py`
- Five Whys:
  1. Why were the closure claims still unproven? Because some restore and outbox behaviors still depended on live helper fallbacks rather than one canonical contract.
  2. Why did restore remain ambiguous? Because boundary helpers still read stale expected-reply shapes instead of the canonical pending-question contract.
  3. Why did operational authority remain ambiguous? Because callers were thin in practice but still lacked one explicit canonical runner seam.
  4. Why could this survive earlier closeouts? Because previous guards were checking earlier declared shapes, not the reopened live-code envelope.
  5. Why was a new block required? Because the repo needed code-aware reproof of the remaining runtime envelopes, not more registry narrative.
- Broken invariant:
  - continuity restore must use canonical pending-question state only, and operational claim/process authority must converge on one canonical runtime helper
- Shared mechanism:
  - stale compatibility fallback in restore helpers and implicit multi-caller ownership in outbox processing
- Why the surfaced family belongs to that mechanism:
  - all remaining failures came from restore helpers or operational callers bypassing a single canonical authority seam
- Open-world envelope expected to improve after the fix:
  - pending handoff resume restore
  - resolved handoff resume restore
  - pending resume projection/capture
  - admin / console / worker outbox execution paths
- Root cause statement:
  - the repo still contained restore and operational paths that were thin in intent but not yet forced through one explicit canonical contract surface
- Fix mechanism:
  - force pending resume and boundary restore to read only canonical pending-question contract from `context_manager.canonical_dialog_state`
  - introduce `run_canonical_outbox_process(...)` and converge default/scoped/worker outbox paths on it
  - add a code-aware reproof guard over both mechanisms

## Invariant
- no claim in this block may rest on registry narrative alone
- continuity restore must not rehydrate from stale expected-reply carriers
- boundary restore may preserve canonical continuity but may not reconstruct it from non-canonical carriers
- live outbox execution callers may remain, but runtime ownership must converge on one canonical helper

## Scope
- live-code reproof of:
  - continuity writer law
  - boundary restore law
  - pack/runtime separation on the active path
  - legacy mesh non-authority on the active path
  - operational entrypoint canonical ownership
- only the minimal runtime changes needed to remove the still-live violations above

## Out of scope
- replay
- human semantic audit
- new scenario patches outside the shared mechanisms above

## Touch-list
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/outbox_runtime_service.py`
- `docs/SYSTEM_REPROOF_GUARD.yaml`
- `scripts/system_reproof_guard.py`
- `scripts/continuity_state_normalization_guard.py`
- `docs/CONTINUITY_STATE_NORMALIZATION_GUARD.yaml`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/test_admin_legacy_auth.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/architecture/test_system_reproof_guard.py`
- `truffles-api/tests/architecture/test_operational_entrypoint_dedupe_guard.py`
- active closeout docs/state/packet/registries after full block completion only

## Plan
1. Rebuild the exact live-path evidence map for continuity restore, boundary restore, pack/runtime seams, legacy surfaces, and operational callsites.
2. Classify each claim as `proven`, `partial`, or `reopened` from code first.
3. Fix only the live mechanisms that still violate the claimed invariant.
4. Add code-aware guard coverage for the reopened mechanisms.
5. Re-run focused proof checks.
6. Update active docs/state/packet once at full-block closeout.

## DoD
- continuity restore uses only canonical pending-question contract on the active resume path
- boundary restore no longer falls back to stale non-canonical expected-reply fields
- active pack/runtime and legacy claims remain reproven under the current guard set
- admin / console / worker outbox execution paths converge on one canonical runtime helper
- every targeted claim in this envelope is either reproven by code or explicitly left to the acceptance lane only

## Checks
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

## Evidence
- `docs/REPORTS/2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md`
- `docs/SYSTEM_REPROOF_GUARD.yaml`
- `scripts/system_reproof_guard.py`
- `truffles-api/tests/architecture/test_system_reproof_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/outbox_runtime_service.py`

## Rollback
- revert only the reproof block commit if canonical pending-question restore or canonical outbox runner convergence regresses the typed runtime contracts

## No-go
- no replay
- no product/practical closure claim
- no registry-only proof
- no reintroduction of non-canonical expected-reply restore fallback
- no new duplicated claim/process logic in outbox callers

## Риски / блокеры
- if any targeted claim still fails after this block, the next move must reopen that exact mechanism instead of jumping to replay
- acceptance may still fail even when repo-side live-code reproof is complete

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- acceptance is still open: fresh replay and full human semantic audit remain required

### Why not in this block
This block proves repo-side live-code invariants. Acceptance is a separate behavioral layer.

### Risk if deferred
Without acceptance, no product or practical closure claim is admissible.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-replay-and-full-human-semantic-audit-acceptance-a922.md`

### Expiry / trigger to stop deferral
- stop deferral before any `done`, `green`, product, practical, or baseline-refresh claim

## Next-block contract (mandatory)
### Next block objective
Run fresh replay plus full human semantic audit from the now-reproved repo-side base and decide product/practical closure honestly.

### First deterministic check command
`python3 scripts/recovery_execution_guard.py`

### Blocked-by conditions
- this reproof block must stay synced in canon/state/packet
- fresh acceptance run must be infra-valid and accompanied by full human semantic audit artifacts

### Owner role for closure
Brain / Top Architect
