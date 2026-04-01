# TP-2026-03-28-consultant-core-workstream6-outbox-orchestration-unification-cut-a922

## Title / Goal
Unify the duplicated outbox processing orchestration on top of `outbox_runtime_service` so request wrappers stop reimplementing the same release/schedule/claim/process flow and console/worker stop parsing execution settings independently.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 6 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_routers_outbox_service.md`
- `docs/system_forensics/files/app_routers_console.md`
- `docs/system_forensics/files/app_workers_outbox.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com consolidate duplicate code refactoring shared function`
- Date/time: `2026-03-28T16:48:00+05:00`
- Opened sources:
  - `https://martinfowler.com/apsupp/appfacades.pdf`
- High-signal source quality:
  - Martin Fowler primary-source supplement on application facades; it shows duplicated application-layer flows should collapse behind one facade/boundary rather than being repeated across entrypoints.
- Found reusable idea:
  - duplicate orchestration at multiple entrypoints should move into one application/service boundary, leaving outer routers/workers as thin callers.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has one action-plane owner (`outbox_runtime_service`); the next step is to concentrate orchestration there instead of repeating it in routers/workers.
- Rejected options:
  - leaving admin/outbox-service duplication in place and only documenting it: rejected because it keeps wrong control ownership.
  - rewriting console worker logic completely in this block: rejected because it would exceed a bounded family.

## Root Cause (mandatory)
### Symptom
After moving the executor to `outbox_runtime_service`, the surrounding orchestration is still duplicated: `outbox_service.py` and `admin.py` reimplement the same release/schedule/claim/process flow, while `console.py` and `workers/outbox.py` still parse outbox execution settings separately.

### Minimal Reproduction
1. `rg -n "release_stale_processing\(|schedule_inbound_syncs\(|claim_pending_outbox_batches\(|process_reminder_jobs\(" truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py`
2. Observe that `outbox_service.py` and `admin.py` carry near-identical flow.
3. Observe env parsing duplication for outbox execution settings in `console.py` and `workers/outbox.py`.
4. Run focused deterministic wrapper/ops tests.

### Evidence
- duplicated flow excerpts in `outbox_service.py` / `admin.py`
- duplicated settings parsing in `console.py` / `workers/outbox.py`
- focused deterministic tests and architecture guards

### Five Whys
1. Why is Workstream 6 still open after moving the executor owner?
   - Because the execution-plane control flow is still duplicated across entrypoints.
2. Why is that a problem?
   - Because action-plane orchestration remains smeared across routers/workers instead of one governed service boundary.
3. Why focus on wrappers and settings first?
   - Because they are the smallest live duplication seam that removes control authority without rewriting algorithms.
4. Why not unify all console/worker logic now?
   - Because their scoped claiming and loop scheduling differ and should be handled in a separate family.
5. Why add guards?
   - Because thin wrappers regress silently unless the boundary is frozen.

### Root Cause Statement
The current durable action-plane debt is duplicated orchestration ownership: release/schedule/claim/process logic and execution settings are still scattered across multiple entrypoints instead of being concentrated in one service boundary.

### Fix Mechanism
Add shared orchestration helpers to `outbox_runtime_service`, switch request wrappers to that facade, make console/worker read shared settings and batch-processing helper, then freeze the thin-wrapper boundary with architecture guards.

## Invariant
- No behavior change in outbox processing semantics.
- No semantic-owner/runtime-core changes.
- Scoped console claim behavior and worker scheduling semantics stay intact.

## Scope
- Shared outbox process settings owner.
- Shared claimed-row processing helper.
- Shared default outbox-process facade for request wrappers.
- Thin-wrapper guard for `outbox_service.py` and `admin.py`.

## Out of Scope
- Full console scoped-claim rewrite.
- Full worker loop rewrite.
- Deleting legacy/compat files.

## Touch-list
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add shared settings + process facade helpers to `outbox_runtime_service`.
2. Switch `outbox_service.py` and `admin.py` to the shared default-process facade.
3. Switch `console.py` and `workers/outbox.py` to the shared settings / claimed-row process helper.
4. Add thin-wrapper architecture guards.
5. Run focused deterministic checks and update repo truth.

## DoD
- `outbox_service.py` and `admin.py` no longer directly release/claim/schedule/process outbox rows.
- `console.py` and `workers/outbox.py` use shared settings/process helpers.
- Focused deterministic checks are green.
- Repo truth records the authority reduction truthfully.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/outbox_runtime_service.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "outbox_request_wrappers_are_thin or outbox_worker_and_console_use_shared_runtime_settings"`
- `git diff --check`

## Evidence
- Focused deterministic test output
- `STATE.md` entry for the new family
- Updated architecture guard

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No semantic changes inside `_process_outbox_rows(...)`.
- No new package/router wrapper layer.
- No scope growth into full worker/control-plane redesign.

## Risks / Blockers
- `console.py` is a large file; keep changes limited to settings/process delegation.
- The broader architecture suite still has unrelated residuals outside this family.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Scoped console claim logic remains local.
- Worker loop scheduling and metrics cadence remain local.

### Why not in this block
- This family removes duplicated orchestration ownership first; full loop/scoped-claim convergence is a separate boundary.

### Risk if deferred
- Some operational duplication remains, but thin wrappers and shared settings reduce most of the wrong authority.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-console-worker-orchestration-convergence-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if a new wrapper reintroduces direct release/claim/schedule/process flow outside `outbox_runtime_service`.

## Next-block Contract (mandatory)
### Next block objective
Converge remaining scoped console claim and worker loop orchestration onto a smaller shared action-plane surface.

### First deterministic check command
`rg -n "_claim_scoped_outbox_rows\(|while True:|schedule_inbound_syncs\(" truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py`

### Blocked-by conditions
- This block must first land with shared settings/process helpers and green focused checks.

### Owner role for closure
- Brain / Top Architect
