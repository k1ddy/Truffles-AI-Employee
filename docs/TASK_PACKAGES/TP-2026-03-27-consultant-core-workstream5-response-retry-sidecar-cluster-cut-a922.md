# TP-2026-03-27-consultant-core-workstream5-response-retry-sidecar-cluster-cut-a922

## Title / Goal
Remove the live `response.py -> decision.py` dependency for retry/sidecar/notice primitives by re-homing that shared response cluster into a narrow owner, leaving `decision.py` with compatibility aliases only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "Branch By Abstraction" legacy seam refactoring`
- Date/time: `2026-03-27T20:52:10+05:00`
- Opened sources:
  - `https://www.martinfowler.com/bliki/BranchByAbstraction.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on gradually moving clients off a legacy supplier through a narrow abstraction seam.
- Found reusable idea:
  - move one client cluster to a narrow shared seam first, keep the old supplier as a compatibility alias during migration, and verify behavior through focused tests.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has `runtime_primitives.py` as the shared owner for routing-neutral active-path helpers; the right move is to extend that seam for retry/sidecar/notice primitives instead of adding a new adapter.
- Rejected options:
  - keep `response.py` reading this cluster from `decision.py`: rejected because it preserves `decision.py` as a live response-helper owner.
  - introduce a new parallel helper module just for this cluster: rejected because `runtime_primitives.py` already exists as the narrow shared seam.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/response.py` still reads retry/sidecar/notice primitives from `decision.py`, including `_append_followup`, `MSG_STYLE_REFERENCE_NEED_MEDIA`, `MSG_PENDING_LOW_CONFIDENCE`, `MSG_LOW_CONFIDENCE_RETRY`, `MSG_HANDOVER_CONFIRM`, `LOW_CONFIDENCE_MAX_RETRIES`, `should_offer_low_confidence_retry`, and quiet-hours keys/TTLs.

### Minimal Reproduction
1. Inspect `truffles-api/app/routers/webhook/response.py`.
2. Observe direct `decision_router.*` reads for the retry/sidecar/notice cluster at:
   - `truffles-api/app/routers/webhook/response.py:327-345`
   - `truffles-api/app/routers/webhook/response.py:1756`
   - `truffles-api/app/routers/webhook/response.py:2027-2029`
   - `truffles-api/app/routers/webhook/response.py:2077`
   - `truffles-api/app/routers/webhook/response.py:3101-3202`
   - `truffles-api/app/routers/webhook/response.py:3326-3356`
3. Inspect `truffles-api/app/routers/webhook/decision.py:3953-4091`, `truffles-api/app/routers/webhook/decision.py:7954`, and `truffles-api/app/routers/webhook/decision.py:8485`.
4. Observe that this shared response cluster still lives inside the legacy hotspot.

### Evidence
- `truffles-api/app/routers/webhook/response.py:327-345`
- `truffles-api/app/routers/webhook/response.py:1756`
- `truffles-api/app/routers/webhook/response.py:2027-2029`
- `truffles-api/app/routers/webhook/response.py:2077`
- `truffles-api/app/routers/webhook/response.py:3101-3202`
- `truffles-api/app/routers/webhook/response.py:3326-3356`
- `truffles-api/app/routers/webhook/decision.py:3953-4091`
- `truffles-api/app/routers/webhook/decision.py:7954`
- `truffles-api/app/routers/webhook/decision.py:8485`

### Five Whys
1. Why does `response.py` still depend on `decision.py`?
   - Because shared response-stage constants and helper functions were never re-homed after ambient `_legacy.py` removal.
2. Why are they still in `decision.py`?
   - Because earlier cuts prioritized bigger control seams and left this response helper cluster behind as a compatibility residue.
3. Why is that wrong now?
   - Because `decision.py` still owns live response behavior even though it should be shrinking toward compatibility-only status.
4. Why is that risky?
   - Because response-stage retry and sidecar behavior can still drift when `decision.py` changes, keeping the god-file on the active path.
5. Why does this block Workstream 5?
   - Because Workstream 5 requires the legacy mesh to lose live helper/control ownership, not just ambient import fanout.

### Root Cause Statement
The shared retry/sidecar/notice cluster still lives in `decision.py`, so `response.py` and adjacent consumers continue to use the legacy hotspot as the live owner of response-stage control primitives.

### Fix Mechanism
Move the shared retry/sidecar/notice primitives into `runtime_primitives.py`, switch `response.py` and adjacent consumers to direct imports from that seam, keep compatibility aliases in `decision.py` if needed, and add focused regressions/guards so the seam does not grow back.

## Invariant
- Quiet-hours, low-confidence retry, handover confirmation, and style-reference reply behavior stay unchanged.
- No new semantic routing is added.
- `decision.py` loses live response-helper ownership rather than gaining another wrapper.
- Existing targeted response/message tests stay green.

## Scope
- Remove `response.py` reads of the retry/sidecar/notice helper cluster from `decision.py`.
- Re-home the shared cluster into `runtime_primitives.py`.
- Move adjacent direct consumers (`booking.py`, `context_manager.py`) for the same cluster where it is cheap and bounded.
- Add targeted regressions and architecture guard coverage.

## Out of Scope
- Full removal of all `response.py -> decision.py` dependencies.
- Controller/class-router helper extraction.
- Booking prompt/status constant migration beyond this shared cluster.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_webhook_response.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Re-home the retry/sidecar/notice cluster into `runtime_primitives.py`.
2. Switch `response.py` to direct imports from the new owner.
3. Move bounded adjacent consumers for the same cluster (`context_manager.py`, `booking.py`).
4. Leave compatibility aliases in `decision.py` only if surviving callers still need them.
5. Add focused tests/guards, run deterministic checks, and update repo truth.

## DoD
- `response.py` no longer reads the retry/sidecar/notice cluster from `decision.py`.
- Shared retry/sidecar/notice primitives live in `runtime_primitives.py`.
- Targeted response, message, and architecture checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_webhook_response.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_state_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "low_confidence or handover_confirm or style_reference or quiet_hours"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "low_confidence_retry"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "response or reasoning_core or policy_router or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Targeted pytest output for response/message/state checks
- Targeted architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility layer in front of `decision.py`.
- No semantic regex/phrase routing growth in governed core.
- No behavior-only doc churn without authority reduction.

## Risks / Blockers
- Some compatibility callers may still expect these symbols on `decision.py`; aliases may be required during migration.
- Broader architecture guard still has an unrelated red residual in `dialog_state_service.py`: `test_policy_decision_creation_stays_in_governed_core_boundary` fails on the pre-existing direct `PolicyDecision(...)` constructor in `truffles-api/app/core/dialog_state_service.py`.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `response.py` will still depend on `decision.py` for controller/class-router and booking-detection helpers after this cut.
- `decision.py` remains a large legacy hotspot.

### Why not in this block
- This family is bounded to the shared retry/sidecar/notice cluster; pulling controller or booking-control helpers would turn it into a second family.

### Risk if deferred
- `decision.py` remains the live supplier for other response-stage helper clusters even after retry/sidecar/notice is removed.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream5-response-controller-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this cut lands and `response.py` still reads other generic response-stage helpers from `decision.py` without a bounded owner plan.

## Next-block Contract (mandatory)
### Next block objective
Cut the next `response.py -> decision.py` helper cluster, likely controller/class-router helpers or booking-detection helpers, after the retry/sidecar/notice cluster is re-homed.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "response or policy_router or reasoning_core"`

### Blocked-by conditions
- This block must first prove `response.py` no longer reads the retry/sidecar/notice cluster from `decision.py` and that targeted response tests stay green.

### Owner role for closure
- Brain / Top Architect
