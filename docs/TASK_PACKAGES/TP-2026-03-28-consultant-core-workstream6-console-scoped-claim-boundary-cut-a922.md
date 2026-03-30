# TP-2026-03-28-consultant-core-workstream6-console-scoped-claim-boundary-cut-a922

## Title / Goal
Remove the remaining local outbox execute-claim logic from `console.py` by moving scoped claim ownership into `outbox_runtime_service`, so console stays a control-plane wrapper instead of an action-plane claimant.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 6 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_routers_console.md`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com extract method move code to service boundary`
- Date/time: `2026-03-28T17:04:00+05:00`
- Opened sources:
  - `https://martinfowler.com/ieeeSoftware/netAttributes.pdf`
- High-signal source quality:
  - Martin Fowler primary-source essay on module boundaries and net attributes; it reinforces moving behavior to the boundary that owns the responsibility rather than leaving operational logic in outer layers.
- Found reusable idea:
  - control-plane/router layers should delegate operational work to the owning boundary instead of keeping their own embedded query/update flow.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has an outbox action-plane owner; the remaining wrong authority is console’s embedded scoped-claim implementation.
- Rejected options:
  - leaving `_claim_scoped_outbox_rows(...)` in `console.py` and only calling more helpers around it: rejected because the control-plane would still own outbox claim logic.
  - redesigning the whole worker loop in this block: rejected because it is a separate residual family.

## Root Cause (mandatory)
### Symptom
`console.py` still defines `_claim_scoped_outbox_rows(...)`, which performs action-plane pending-row selection and claim mutation locally inside the control-plane router.

### Minimal Reproduction
1. `rg -n "def _claim_scoped_outbox_rows\(" truffles-api/app/routers/console.py`
2. Inspect the function: it queries `OutboxMessage`, applies pending/branch/time windows, mutates row status/attempts, commits, and returns claimed rows.
3. Observe `_run_outbox_process_job(...)` calling that local helper.

### Evidence
- `truffles-api/app/routers/console.py` local scoped-claim function and execute path
- focused deterministic tests and architecture guards

### Five Whys
1. Why is Workstream 6 still open after the orchestration unification cut?
   - Because console still owns one live outbox claim algorithm locally.
2. Why is that a problem?
   - Because control-plane code still performs durable action-plane state mutation directly.
3. Why move this before worker-loop convergence?
   - Because console is the cleaner boundary seam: one local helper, one caller, and a clear ownership mismatch.
4. Why not keep the helper local and call it “scoped”? 
   - Because scoping is a parameter, not a reason for the control-plane router to own the claim algorithm.
5. Why add guards?
   - Because otherwise console can silently regrow embedded action-plane logic.

### Root Cause Statement
The remaining Workstream 6 control-ownership leak is `console.py`’s embedded scoped outbox claim routine, which should belong to the shared outbox action-plane boundary.

### Fix Mechanism
Move scoped outbox claiming into `outbox_runtime_service`, switch console execute flow to the shared helper, and freeze the boundary with architecture guards.

## Invariant
- No change to scoped claim semantics.
- No change to worker loop behavior.
- Console remains a wrapper/control-plane caller.

## Scope
- Shared scoped-claim owner in `outbox_runtime_service`.
- Console execute path switched to it.
- Thin-console architecture guard.

## Out of Scope
- Worker-loop convergence.
- Full console outbox redesign.
- Wider control-plane changes.

## Touch-list
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Move scoped claim logic into `outbox_runtime_service`.
2. Switch `_run_outbox_process_job(...)` to the shared helper.
3. Update focused console tests.
4. Add architecture guard proving console no longer defines the local claim helper.
5. Run focused deterministic checks and update repo truth.

## DoD
- `console.py` no longer defines `_claim_scoped_outbox_rows(...)`.
- Console execute path uses shared scoped-claim helper.
- Focused deterministic checks are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/outbox_runtime_service.py truffles-api/app/routers/console.py truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "outbox_process"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "console_router_has_no_local_outbox_claim_helper"`
- `git diff --check`

## Evidence
- Focused deterministic test output
- `STATE.md` entry for this family
- Updated architecture guard

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No semantic/runtime-core changes.
- No claim semantics rewrite.
- No worker-loop changes in this block.

## Risks / Blockers
- `console.py` is large; move only the scoped-claim helper.
- Wider architecture suite still has unrelated residuals.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Worker loop scheduling remains local.
- Console still retains dry-run and archive preview logic.

### Why not in this block
- Those are separate residual seams from the scoped claim algorithm itself.

### Risk if deferred
- Durable action-plane ownership improves, but final worker/control-plane convergence remains incomplete.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-worker-loop-boundary-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if console regrows another local outbox mutation helper.

## Next-block Contract (mandatory)
### Next block objective
Shrink the worker loop to a thinner action-plane boundary on top of shared claim/process helpers.

### First deterministic check command
`rg -n "while True:|schedule_inbound_syncs\(|claim_pending_outbox_batches\(" truffles-api/app/workers/outbox.py`

### Blocked-by conditions
- This block must first land with shared scoped-claim ownership and green focused checks.

### Owner role for closure
- Brain / Top Architect
