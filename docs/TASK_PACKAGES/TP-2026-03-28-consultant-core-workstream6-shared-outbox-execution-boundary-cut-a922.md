# TP-2026-03-28-consultant-core-workstream6-shared-outbox-execution-boundary-cut-a922

## Title / Goal
Move the concrete outbox executor into a shared service boundary so live app runtime stops importing `webhook/outbox.py` directly, and remove the dead `decision.py` outbox wrapper seam.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 5 done`, `Workstream 6 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`
- `docs/system_forensics/files/app_routers_outbox_service.md`
- `docs/system_forensics/files/app_workers_outbox.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com move function refactoring module boundary`
- Date/time: `2026-03-28T16:34:00+05:00`
- Opened sources:
  - `https://www.martinfowler.com/ieeeSoftware/dataAccessRoutines.pdf`
- High-signal source quality:
  - Martin Fowler primary-source essay on module boundaries and data access routines; it emphasizes moving code to the module that owns the responsibility so callers depend on one clear boundary.
- Found reusable idea:
  - when a routine is operational rather than presentation-layer logic, move it behind the owning boundary and let outer modules become thin adapters.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has one concrete outbox executor; this block should move ownership to the service/action-plane boundary instead of inventing a new workflow platform.
- Rejected options:
  - keeping the executor under `webhook/outbox.py` and only changing import style: rejected because router namespace would still own the action-plane implementation.
  - rewriting outbox internals and orchestration in one block: rejected because it would exceed a bounded family and mix boundary movement with algorithm changes.

## Root Cause (mandatory)
### Symptom
Even after the direct-import cut, live app runtime still depends on `app.routers.webhook.outbox` as the concrete executor owner, and `decision.py` still keeps a dead `_process_outbox_rows(...)` wrapper duplicate.

### Minimal Reproduction
1. `rg -n "from app\.routers\.webhook\.outbox import|import outbox as outbox_router" truffles-api/app truffles-api/tests`
2. Observe live app runtime callers in `outbox_service.py`, `admin.py`, `console.py`, and `workers/outbox.py`.
3. Observe duplicate wrapper in `truffles-api/app/routers/webhook/decision.py`.
4. Confirm direct helper tests still bind to router namespace rather than a shared service boundary.

### Evidence
- `rg -n "from app\.routers\.webhook\.outbox import|import outbox as outbox_router" truffles-api/app truffles-api/tests`
- `rg -n "async def _process_outbox_rows" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/outbox.py`
- focused deterministic tests and architecture guards

### Five Whys
1. Why is the durable action plane still not clearly separated?
   - Because the concrete executor still lives under the webhook router namespace.
2. Why does that matter?
   - Because routers/control-plane callers still depend on a legacy placement rather than one shared action-plane service boundary.
3. Why is `decision.py` still relevant here?
   - Because it keeps a duplicate wrapper seam for the same executor, even if the live package-export caller path has been cut.
4. Why move tests too?
   - Because direct helper coverage should pin the new owner, not the legacy router shell.
5. Why keep `webhook/outbox.py` at all?
   - As a compatibility shell during migration; it should stop being the implementation owner.

### Root Cause Statement
The remaining Workstream 6 boundary debt is module ownership: the outbox executor still belongs to a router file, and `decision.py` still carries a duplicate wrapper seam around it.

### Fix Mechanism
Move the concrete executor into `app/services/outbox_runtime_service.py`, switch live callers and direct helper tests to that owner, collapse `webhook/outbox.py` to a compatibility shim, and remove the dead `decision.py` outbox wrapper.

## Invariant
- No behavior change in outbox processing results.
- No semantic/runtime-core authority changes.
- Compatibility shim stays thin.

## Scope
- Create shared outbox execution owner under `app/services`.
- Switch live callers and direct helper tests to the new owner.
- Remove `decision.py` outbox wrapper.
- Add architecture proof for the new boundary.

## Out of Scope
- Rewriting outbox processing logic.
- Consolidating admin/console/worker orchestration.
- Deleting `webhook/outbox.py`.

## Touch-list
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/tests/test_provider_gateway_integration.py`
- `truffles-api/tests/test_outbox_transport_degraded.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Copy the concrete executor into `app/services/outbox_runtime_service.py`.
2. Collapse `webhook/outbox.py` into a compatibility shim.
3. Switch live callers and direct helper tests to the new service owner.
4. Remove the dead `decision.py` outbox wrapper.
5. Add architecture proof and update repo truth.

## DoD
- Live app runtime no longer imports `app.routers.webhook.outbox`.
- Direct helper tests pin `app.services.outbox_runtime_service`.
- `decision.py` no longer defines `_process_outbox_rows(...)`.
- `webhook/outbox.py` is compatibility-only.
- Focused deterministic checks are green.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/outbox_runtime_service.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_outbox_transport_degraded.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_provider_gateway_integration.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_transport_degraded.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "app_runtime_has_no_webhook_outbox_importers or decision_router_has_no_outbox_process_wrapper"`
- `git diff --check`

## Evidence
- Focused deterministic test output
- `STATE.md` entry for this Workstream 6 block
- New service boundary in `STRUCTURE.md`

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No logic rewrite inside `_process_outbox_rows(...)`.
- No new package-export seam.
- No new dependency from runtime core back into planner/semantic layers.

## Risks / Blockers
- `webhook/outbox.py` currently exports helper symbols consumed by `decision.py`; the shim must preserve those imports.
- The wider architecture suite still has unrelated residuals outside this family.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `webhook/outbox.py` remains on disk as a compatibility shell.
- Admin/console/worker still duplicate orchestration around the same executor.

### Why not in this block
- This block moves the concrete executor boundary first; orchestration dedup is the next family.

### Risk if deferred
- The executor owner is fixed, but duplicated action-plane orchestration still increases maintenance and release risk.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-outbox-orchestration-unification-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if any new live caller imports `app.routers.webhook.outbox` directly.

## Next-block Contract (mandatory)
### Next block objective
Unify duplicated outbox orchestration across admin/console/outbox-service/worker on top of the shared execution boundary.

### First deterministic check command
`rg -n "claim_pending_outbox_batches\(|release_stale_processing\(|schedule_inbound_syncs\(|process_reminder_jobs\(" truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/routers/outbox_service.py truffles-api/app/workers/outbox.py`

### Blocked-by conditions
- This block must first land with the shared execution boundary and green focused checks.

### Owner role for closure
- Brain / Top Architect
