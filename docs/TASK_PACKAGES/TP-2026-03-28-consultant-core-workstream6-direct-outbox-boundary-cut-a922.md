# TP-2026-03-28-consultant-core-workstream6-direct-outbox-boundary-cut-a922

## Title / Goal
Start `Workstream 6 — Durable Action Plane` by removing the live package-export `_process_outbox_rows` seam from worker/admin/console/outbox-service callers so they import the real outbox executor directly.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 5 done`, overall program `open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`
- `docs/system_forensics/files/app_routers_outbox_service.md`
- `docs/system_forensics/files/app_routers_console.md`

## One Web Search (mandatory before implementation)
- Query: `site:microservices.io transactional outbox pattern data transactional outbox`
- Date/time: `2026-03-28T16:10:00+05:00`
- Opened sources:
  - `https://microservices.io/i/MicroservicePatternLanguage.pdf`
- High-signal source quality:
  - Chris Richardson primary source for the transactional outbox pattern; it frames outbox delivery as an execution-plane concern with one publisher boundary instead of scattered callers.
- Found reusable idea:
  - durable message delivery should have one concrete execution boundary; callers should trigger that boundary directly rather than route through compatibility indirection.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has one concrete executor in `webhook/outbox.py`; the wrong authority is the package-export compatibility seam, not the transport logic itself.
- Rejected options:
  - introducing a new workflow platform/service in this block: rejected because it grows scope before the live seam is cut.
  - leaving package-export indirection in place and only documenting it: rejected because it preserves duplicated action-plane routing.

## Root Cause (mandatory)
### Symptom
`_process_outbox_rows(...)` already lives in `truffles-api/app/routers/webhook/outbox.py`, but active worker/admin/console/outbox-service callers still import it through `app.routers.webhook`, preserving a compatibility routing seam on a live execution path.

### Minimal Reproduction
1. `rg -n "from app\.routers\.webhook import _process_outbox_rows" truffles-api/app`
2. Observe live callers in:
   - `truffles-api/app/routers/outbox_service.py`
   - `truffles-api/app/routers/admin.py`
   - `truffles-api/app/routers/console.py`
   - `truffles-api/app/workers/outbox.py`
3. Observe package re-export in `truffles-api/app/routers/webhook/__init__.py`
4. Run deterministic regression checks around outbox worker/service/console callers.

### Evidence
- `rg -n "from app\.routers\.webhook import _process_outbox_rows|_process_outbox_rows" truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/app/routers/webhook/__init__.py`
- focused deterministic tests and architecture guards

### Five Whys
1. Why is Workstream 6 not started in the code yet?
   - Because live outbox execution still routes through compatibility package exports.
2. Why is that a problem?
   - Because execution-plane ownership is still smeared across mounted/router package surfaces instead of one direct executor boundary.
3. Why does the package seam survive?
   - Because callers historically imported `_process_outbox_rows` from `app.routers.webhook` rather than from the actual owner module.
4. Why does that matter even if behavior is unchanged?
   - Because it preserves an avoidable routing layer and keeps the durable action plane coupled to the legacy webhook package shell.
5. Why cut this first?
   - Because it is the highest-leverage live seam already singled out by the forensic packet, and removing it does not require a platform rewrite.

### Root Cause Statement
The first active durable-action blocker is not transport logic itself; it is the live compatibility import seam that routes outbox execution through `app.routers.webhook` instead of the concrete `webhook.outbox` owner.

### Fix Mechanism
Switch live callers to direct `webhook.outbox._process_outbox_rows` imports, remove the package re-export, freeze the new boundary with architecture guards, and update repo truth.

## Invariant
- No behavior change in outbox processing results.
- No new semantic/control authority added to planner/runtime.
- Outbox execution remains one concrete helper owner.

## Scope
- Rewire live callers to direct outbox executor imports.
- Remove package-export `_process_outbox_rows` seam from `webhook.__init__`.
- Add architecture proof for the direct boundary.

## Out of Scope
- Rewriting `_process_outbox_rows(...)` internals.
- Deleting `decision.py`.
- Unifying admin/console/worker orchestration into one new service boundary.

## Touch-list
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Switch live callers to direct `app.routers.webhook.outbox._process_outbox_rows` imports.
2. Remove the package re-export from `webhook.__init__`.
3. Add an architecture guard that forbids package-export outbox imports from app runtime.
4. Run focused deterministic checks and update repo truth.

## DoD
- Live callers no longer import `_process_outbox_rows` from `app.routers.webhook`.
- `webhook.__init__` no longer re-exports `_process_outbox_rows`.
- Focused deterministic checks are green.
- Repo truth records the new Workstream 6 entry truthfully.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/app/routers/webhook/__init__.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_outbox_export or app_runtime_has_no_webhook_package_outbox_importers"`
- `git diff --check`

## Evidence
- Focused deterministic test output
- `STATE.md` entry for the new Workstream 6 block
- Updated architecture guard

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No new compatibility wrapper around `_process_outbox_rows`.
- No semantic changes inside the outbox executor.
- No doc-only progress.

## Risks / Blockers
- `console.py` and `admin.py` are large files; keep edits to import boundary only.
- The broader architecture suite still has unrelated residuals outside this family.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `_process_outbox_rows(...)` still lives in `truffles-api/app/routers/webhook/outbox.py` instead of a dedicated action-plane service.
- Admin/console/worker orchestration remains duplicated around the same executor.

### Why not in this block
- This block cuts the live routing seam first; moving the executor or deduplicating orchestration is a larger family.

### Risk if deferred
- Durable action-plane ownership remains clearer than before, but the concrete executor still lives under a router module and orchestration duplication remains.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-shared-outbox-execution-boundary-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if a new caller reintroduces `from app.routers.webhook import _process_outbox_rows`.

## Next-block Contract (mandatory)
### Next block objective
Move the durable outbox executor behind one shared action-plane boundary instead of leaving it under `webhook/outbox.py` plus duplicated admin/console/worker orchestration.

### First deterministic check command
`rg -n "from app\.routers\.webhook import _process_outbox_rows" truffles-api/app`

### Blocked-by conditions
- This block must first land with direct imports and green deterministic checks.

### Owner role for closure
- Brain / Top Architect
