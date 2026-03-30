# TP-2026-03-28-consultant-core-workstream6-worker-loop-boundary-cut-a922

## Title / Goal
Move the remaining worker-loop outbox release/schedule/claim cadence into `outbox_runtime_service`, so `workers/outbox.py` stays an operational loop shell instead of owning durable action-plane flow.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 6 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 6 — Durable Action Plane`
- `docs/system_forensics/files/app_workers_outbox.md`
- `docs/system_forensics/files/app_services_outbox_service.md`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`

## One Web Search (mandatory before implementation)
- Query: `site:microservices.io polling publisher transactional outbox`
- Date/time: `2026-03-28T18:35:00+05:00`
- Opened sources:
  - `https://microservices.io/patterns/data/polling-publisher.html`
- High-signal source quality:
  - Chris Richardson primary-source pattern reference for polling publisher / transactional outbox.
- Found reusable idea:
  - the polling worker should be a thin poller over one outbox publishing boundary, not a second place that embeds claim/release/publish orchestration.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has a shared durable action-plane owner in `outbox_runtime_service`; the wrong authority is the worker’s remaining embedded cadence logic.
- Rejected options:
  - keeping the worker’s release/schedule/claim logic local and only adding comments: rejected because it preserves duplicate action-plane ownership.
  - redesigning metrics-daily scheduling in the same block: rejected because it is a separate residual family from outbox execution cadence.

## Root Cause (mandatory)
### Symptom
`workers/outbox.py` still performs `release_stale_processing(...)`, `schedule_inbound_syncs(...)`, `claim_pending_outbox_batches(...)`, and the inner batch cadence loop locally.

### Minimal Reproduction
1. `rg -n "release_stale_processing\(|schedule_inbound_syncs\(|claim_pending_outbox_batches\(" truffles-api/app/workers/outbox.py`
2. Inspect `run_worker()` and observe the direct low-level calls plus the local batch loop.

### Evidence
- `truffles-api/app/workers/outbox.py`
- focused deterministic tests/guards for the outbox runtime boundary

### Five Whys
1. Why is `Workstream 6` still open after extracting `outbox_runtime_service`?
   - Because the worker still owns live durable action-plane cadence locally.
2. Why is that a problem?
   - Because there are still two places orchestrating outbox release/schedule/claim/process flow.
3. Why is the worker the next seam?
   - Because request wrappers and console already delegate to the shared owner; the worker is the remaining active duplicate orchestration path.
4. Why not leave the worker as a “special case”?
   - Because polling cadence is still action-plane behavior, not worker-shell behavior.
5. Why add architecture guards?
   - Because otherwise the worker can silently regrow direct low-level outbox mutations.

### Root Cause Statement
The remaining durable-action ownership leak is the worker loop’s embedded release/schedule/claim/process cadence, which should belong to the shared outbox runtime boundary instead of `workers/outbox.py`.

### Fix Mechanism
Add one shared worker-cycle helper in `outbox_runtime_service`, switch `workers/outbox.py` to call it, and freeze the boundary with focused tests and architecture guards.

## Invariant
- No change to outbox delivery semantics.
- No change to metrics-daily scheduling.
- Worker remains the outer loop/OTel/startup shell only.

## Scope
- Shared worker-cycle helper in `outbox_runtime_service`.
- `workers/outbox.py` switched to the shared helper.
- Focused tests and architecture guards.

## Out of Scope
- Metrics-daily orchestration redesign.
- New queue/backoff semantics.
- Wider worker framework changes.

## Touch-list
- `truffles-api/app/services/outbox_runtime_service.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/tests/test_outbox_worker_settings.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add a shared outbox worker-cycle helper to `outbox_runtime_service`.
2. Switch `workers/outbox.py` to that helper and remove direct low-level outbox imports.
3. Update/add focused worker runtime tests.
4. Add architecture guards proving the worker no longer calls low-level outbox helpers directly.
5. Run focused deterministic checks and update repo truth.

## DoD
- `workers/outbox.py` no longer calls `release_stale_processing(...)`, `schedule_inbound_syncs(...)`, or `claim_pending_outbox_batches(...)` directly.
- Worker uses one shared outbox runtime cycle helper.
- Focused deterministic checks are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/outbox_runtime_service.py truffles-api/app/workers/outbox.py truffles-api/tests/test_outbox_worker_settings.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_worker_settings.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "outbox_worker_loop_uses_shared_runtime_cycle or outbox_worker_and_console_use_shared_runtime_settings"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_console_ops_jobs.py -k "outbox_process"`
- `git diff --check`

## Evidence
- Focused deterministic test output
- Updated architecture guard
- `STATE.md` entry for this family

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No semantic/runtime-core changes outside durable action plane.
- No metrics-daily redesign.
- No queue semantics rewrite.

## Risks / Blockers
- Worker file also contains metrics-daily logic; keep that untouched.
- Wider architecture suite still has unrelated residuals.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Metrics-daily scheduling remains local to the worker.
- Workstream 6 closeout proof is not done in this block.

### Why not in this block
- They are separate residual seams from the outbox worker cadence itself.

### Risk if deferred
- Durable action-plane ownership improves, but final Workstream 6 closure still needs proof that remaining worker/control-plane code is compatibility shell only.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if `workers/outbox.py` regrows new direct outbox mutation helpers.

## Next-block Contract (mandatory)
### Next block objective
Run Workstream 6 closeout proof against the shared outbox runtime boundary and remaining worker/control-plane shells.

### First deterministic check command
`rg -n "release_stale_processing\(|schedule_inbound_syncs\(|claim_pending_outbox_batches\(" truffles-api/app/workers/outbox.py truffles-api/app/routers/console.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py`

### Blocked-by conditions
- This block must first land with green focused worker tests and architecture guards.

### Owner role for closure
- Brain / Top Architect
