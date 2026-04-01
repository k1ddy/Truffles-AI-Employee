# TP-2026-03-28-consultant-core-workstream6-closeout-proof-pass-a922

## Title / Goal
Prove whether `Workstream 6 — Durable Action Plane` is actually closed by freezing the remaining outbox execution boundary: one shared runtime owner, thin worker/control-plane shells, and no live low-level outbox orchestration outside `outbox_runtime_service`.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 6 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_services_outbox_service.md`
- `docs/system_forensics/files/app_workers_outbox.md`
- `docs/system_forensics/files/app_routers_console.md`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com strangler boundary proof refactoring`
- Date/time: `2026-03-28T18:52:00+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/OriginalStranglerFigApplication.html`
- High-signal source quality:
  - Martin Fowler primary source for the Strangler Fig pattern and gradual boundary replacement.
- Found reusable idea:
  - closure should be decided at the active boundary: once traffic depends on the new shell/owner and the old orchestration edges are gone, the strangler phase for that boundary is complete.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - Workstream 6 closeout is a boundary-proof problem, not a new runtime feature.
- Rejected options:
  - keeping Workstream 6 open without proof after the worker cut: rejected because it hides actual completion if the active boundary is already frozen.
  - declaring Workstream 6 done without machine-checked guards: rejected because the outbox control surface could silently regrow.

## Root Cause (mandatory)
### Symptom
After the worker-loop cut, `Workstream 6` may already be functionally complete, but it cannot close honestly until we prove that the active app/runtime boundary no longer performs low-level outbox orchestration outside `outbox_runtime_service`.

### Minimal Reproduction
1. Scan app/runtime files for direct imports/calls of low-level outbox orchestration helpers.
2. Confirm request wrappers and worker shells only use the shared runtime boundary.
3. Run focused architecture proof guards.

### Evidence
- `rg -n "release_stale_processing\(|claim_pending_outbox_batches\(|schedule_inbound_syncs\(" truffles-api/app/routers truffles-api/app/workers`
- `rg -n "from app\.services\.outbox_service import|from app\.services\.calendar_sync_service import" truffles-api/app`
- focused architecture guard results

### Five Whys
1. Why is Workstream 6 still open after the worker-loop cut?
   - Because closure proof has not yet frozen the remaining boundary.
2. Why is that proof necessary?
   - Because Workstream 6 is about removing duplicated durable-action orchestration authority, not just moving functions around.
3. Why focus on imports and helper calls?
   - Because those are the concrete edges that would keep a second action-plane owner alive.
4. Why can thin shells remain after closure?
   - Because wrappers/workers can remain as transport or scheduling shells as long as orchestration authority lives only in the shared runtime owner.
5. Why add architecture guards?
   - Because otherwise low-level outbox control logic can silently regrow outside the owner.

### Root Cause Statement
The remaining uncertainty in Workstream 6 is closure proof: we need a frozen guarantee that low-level outbox orchestration helpers are imported and executed only through `outbox_runtime_service`, while worker/control-plane files remain thin shells.

### Fix Mechanism
Add final architecture guards for low-level outbox import/call ownership, rerun the deterministic closeout envelope, and update repo truth with the explicit close decision.

## Invariant
- No behavior changes on the outbox execution path.
- No new queue semantics.
- Closeout must be evidence-based.

## Scope
- Final architecture proof for Workstream 6 closure.
- Explicit close decision in repo truth.

## Out of Scope
- New runtime behavior changes.
- Metrics-daily redesign.
- Starting Workstream 7 implementation in this block.

## Touch-list
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add final low-level outbox ownership guards.
2. Run focused closeout envelope.
3. Update repo truth with the close decision.

## DoD
- Architecture guards prove low-level outbox orchestration imports stay in `outbox_runtime_service`.
- Architecture guards prove worker/control-plane shells use only shared runtime helpers.
- Focused deterministic closeout envelope passes.
- Repo truth records an explicit Workstream 6 close decision.

## Work Mode
- `closure`

## Checks
- `python3 -m py_compile truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "outbox_execution_low_level_imports_stay_in_shared_runtime_owner or outbox_worker_loop_uses_shared_runtime_cycle or outbox_request_wrappers_are_thin or console_router_has_no_local_outbox_claim_helper"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "outbox_process"`
- `git diff --check`

## Evidence
- Focused architecture guard output
- Focused deterministic wrapper/worker output
- `STATE.md` closeout entry

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No premature `done` without passing closeout evidence.
- No new wrapper/helper duplication outside `outbox_runtime_service`.
- No doc-only closeout without frozen guards.

## Risks / Blockers
- Some outbox helper imports remain legitimate inside source owners (`outbox_service.py`, `calendar_sync_service.py`); guards must distinguish definitions from runtime callsites.
- Wider architecture suite still has unrelated residuals.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Metrics-daily scheduling remains local to `workers/outbox.py`.
- Workstream 7 control-plane governance remains untouched.

### Why not in this block
- They are outside durable outbox execution ownership.

### Risk if deferred
- Workstream 6 can close, but control-plane and ops governance work still remains in later workstreams.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-governed-registry-entry-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if a new app/runtime file starts importing low-level outbox orchestration helpers directly.

## Next-block Contract (mandatory)
### Next block objective
Start `Workstream 7 — Minimum Control Plane` by identifying the first governed registry/policy pack entrypoint that still lives as scattered runtime branches/constants.

### First deterministic check command
`rg -n "registry|policy pack|context recipe|capability registry|tool registry" truffles-api/app docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`

### Blocked-by conditions
- This block must first land with green focused closeout guards and an explicit Workstream 6 close decision.

### Owner role for closure
- Brain / Top Architect
