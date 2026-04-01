# TP-2026-03-28-consultant-core-workstream5-pending-runtime-cluster-cut-a922

## Title / Goal
Remove the remaining live `pending.py -> decision.py` dependency by extracting the pending-status / SLA helper cluster into a narrow runtime owner and leaving `decision.py` with compatibility aliases only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_pending.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com move group of related methods to new class refactoring`
- Date/time: `2026-03-28T07:32:58+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/class-too-large.html`
- High-signal source quality:
  - Martin Fowler primary refactoring article describing how to move one cohesive method group into a new owner while keeping tests green and leaving the original large class slimmer.
- Found reusable idea:
  - extract one coherent responsibility slice, switch active callers first, and keep the original large module as a temporary compatibility surface only.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - this repo is already strangling `decision.py` one cohesive helper family at a time; the pending-status/SLA slice matches that pattern cleanly.
- Rejected options:
  - leave `pending.py` on direct `decision_router.*` reads until later: rejected because it preserves a live legacy helper seam on the active path.
  - bundle pending with booking/info helper families in one cut: rejected because it would mix unrelated behavior and weaken closure evidence.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/pending.py` still imports `decision.py` at runtime for pending-status detection, pending SLA constants, and pending-status response texts.

### Minimal Reproduction
1. Inspect remaining reads in `truffles-api/app/routers/webhook/pending.py`:
   - `decision_router.MSG_HANDOVER_DECLINED`
   - `decision_router.MSG_PENDING_ACK`
   - `decision_router.is_handover_status_question(...)`
   - `decision_router.MSG_PENDING_STATUS`
   - `decision_router.MSG_PENDING_WAIT`
   - `decision_router.PENDING_SLA_PING_MINUTES`
   - `decision_router.PENDING_SLA_PING_SENT_KEY`
   - `decision_router.MSG_PENDING_SLA_PING`
2. Inspect current definitions in `truffles-api/app/routers/webhook/decision.py`:
   - `is_handover_status_question(...)`
   - `MSG_HANDOVER_DECLINED`
   - `MSG_PENDING_STATUS`
   - `MSG_PENDING_WAIT`
   - `MSG_PENDING_SLA_PING`
   - `MSG_PENDING_ACK`
   - `PENDING_SLA_PING_MINUTES`
   - `PENDING_SLA_PING_SENT_KEY`
3. Confirm `pending.py` still carries `_decision_runtime()` and a live direct import seam.

### Evidence
- `rg -n "decision_router\.(MSG_HANDOVER_DECLINED|MSG_PENDING_ACK|MSG_PENDING_STATUS|MSG_PENDING_WAIT|MSG_PENDING_SLA_PING|PENDING_SLA_PING_MINUTES|PENDING_SLA_PING_SENT_KEY|is_handover_status_question)" truffles-api/app/routers/webhook/pending.py`
- `rg -n "def is_handover_status_question|MSG_HANDOVER_DECLINED|MSG_PENDING_ACK|MSG_PENDING_STATUS|MSG_PENDING_WAIT|MSG_PENDING_SLA_PING|PENDING_SLA_PING_MINUTES|PENDING_SLA_PING_SENT_KEY" truffles-api/app/routers/webhook/decision.py`

### Five Whys
1. Why does `pending.py` still import `decision.py`?
   - Because the pending-status/SLA helper cluster was never extracted into its own owner.
2. Why is that wrong now?
   - Because `decision.py` remains the live supplier of pending control texts and status helper logic.
3. Why does that matter?
   - Because pending continuity/control behavior can still drift when the god-file changes.
4. Why is this still a Workstream 5 blocker?
   - Because Workstream 5 requires live helper/control authority to leave the legacy mesh, not just reduce import count elsewhere.
5. Why fix this as a separate family?
   - Because the pending-status/SLA helper cluster is cohesive, directly testable, and has a narrow active consumer set.

### Root Cause Statement
The pending-status / SLA helper cluster stayed centralized in `decision.py`, so `pending.py` still depends on the god-file for status-question detection, pending responses, and SLA ping constants instead of a narrow runtime owner.

### Fix Mechanism
Create a `pending_runtime.py` owner for the pending-status / SLA helper cluster, switch `pending.py` and any adjacent active consumer needed for this cluster to direct imports, keep compatibility aliases in `decision.py`, and freeze the seam with deterministic guards.

## Invariant
- Pending/handover status behavior stays unchanged.
- Pending SLA ping timing and context-key semantics stay unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live ownership of the moved pending helper cluster.

## Scope
- Extract pending-status / SLA helpers and messages into `pending_runtime.py`.
- Switch `pending.py` to direct imports from the new narrow owner.
- Move any adjacent active consumer of the exact same cluster if needed.
- Leave compatibility aliases in `decision.py` only for remaining callers.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Deleting `decision.py`.
- Reworking reminder-service auto-close behavior.
- Refactoring unrelated booking/info helper clusters.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/pending_runtime.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Extract the pending-status / SLA helper cluster into `pending_runtime.py`.
2. Switch `pending.py` to direct imports and remove `_decision_runtime()` if it becomes dead.
3. Move any adjacent same-cluster consumer needed for closure.
4. Keep compatibility aliases in `decision.py` only.
5. Add focused deterministic checks and update repo truth.

## DoD
- `pending.py` no longer reads the moved pending helper cluster through `decision_router.*`.
- `pending.py` no longer needs `_decision_runtime()`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/pending_runtime.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "pending or handover_status"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "pending_runtime_cluster_uses_narrow_owner or context_and_guard_runtime_clusters_use_narrow_owners or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused pytest output for pending behavior
- Focused architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility facade in front of `decision.py`.
- No semantic regex/phrase growth in governed core.
- No doc-only closure without authority reduction.

## Risks / Blockers
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `Canon Sync Gate` remains red because worktree `AGENTS.md` diverges from `/home/zhan/AGENTS.md`; this block cannot claim session gate closure.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `booking.py` and `info.py` will still depend on `decision.py` for unrelated booking/info helper clusters after this cut.
- Reminder/state-service duplicates for pending constants remain out of scope here.

### Why not in this block
- This family is bounded to the live `pending.py -> decision.py` helper seam.

### Risk if deferred
- `decision.py` keeps live ownership of pending status control text and SLA helper logic.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-booking-info-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `pending.py` still has direct `decision_router.*` reads for the moved pending helper cluster.

## Next-block Contract (mandatory)
### Next block objective
After this cut, reduce the next surviving `decision.py` helper family in `booking.py` / `info.py`.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "pending_runtime_cluster_uses_narrow_owner or context_and_guard_runtime_clusters_use_narrow_owners"`

### Blocked-by conditions
- This block must first prove that `pending.py` no longer reads the moved pending cluster from `decision.py` and that focused pending tests stay green.

### Owner role for closure
- Brain / Top Architect
