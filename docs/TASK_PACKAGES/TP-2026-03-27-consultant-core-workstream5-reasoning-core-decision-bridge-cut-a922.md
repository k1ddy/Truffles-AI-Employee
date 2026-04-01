# TP-2026-03-27-consultant-core-workstream5-reasoning-core-decision-bridge-cut-a922

## Title / Goal
Cut the live `reasoning_core -> webhook/decision.py` bridge so the compatibility shim stops treating `decision.py` as an ambient helper bus and instead reads narrow shared primitives and direct helper seams.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, overall program `open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_services_reasoning_core.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `martinfowler strangler fig application branch by abstraction adapter anti corruption layer`
- Date/time: `2026-03-27T20:28:24+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on incremental legacy modernization
- Found reusable idea:
  - introduce seams and move small pieces of behavior out of the legacy host gradually; use transitional architecture only to coexist during the migration, not as a permanent authority center.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has narrow helper owners (`runtime_primitives`, `info`, `policy`, `http`); the correct move is to route `reasoning_core` through those seams and shrink `decision.py` ownership instead of inventing a new wrapper layer.
- Rejected options:
  - leave `reasoning_core` importing `decision.py`: rejected because it preserves `decision.py` as a live ambient helper bus.
  - add another compatibility facade in front of `decision.py`: rejected because it widens transitional architecture instead of shrinking live authority.

## Root Cause (mandatory)
### Symptom
`reasoning_core.py` is nominally a thin compatibility shim, but it still imports `app.routers.webhook.decision` directly and reads helper functions, constants, routing policy, and DB lookup helpers from the largest legacy hotspot.

### Minimal Reproduction
1. Inspect `truffles-api/app/services/reasoning_core.py:21`.
2. Observe direct `decision_router` import.
3. Inspect `truffles-api/app/services/reasoning_core.py:387-439` and `truffles-api/app/services/reasoning_core.py:516`.
4. Observe direct reads of `_is_short_reply`, `_extract_datetime`, `_looks_like_info_query`, `_looks_like_policy_topic`, `EXPECTED_REPLY_*`, `ROUTING_MATRIX`, and `_find_message_by_message_id`.

### Evidence
- `truffles-api/app/services/reasoning_core.py:21`
- `truffles-api/app/services/reasoning_core.py:387-439`
- `truffles-api/app/services/reasoning_core.py:516`
- `truffles-api/app/routers/webhook/decision.py:4090-4129`

### Five Whys
1. Why does `reasoning_core` still keep a live legacy-mesh dependency?
   - Because it still imports `decision.py` directly for shared primitives and helper logic.
2. Why is it reading those symbols from `decision.py`?
   - Because shared routing/expected-reply/datetime helpers were never re-homed to narrower owners during earlier core extraction.
3. Why is that now wrong?
   - Because `reasoning_core` is already demoted to a shadow compatibility shim, so keeping it coupled to the biggest legacy hotspot preserves a live control seam into the mesh.
4. Why is that dangerous?
   - Because any new helper or state/control logic added to `decision.py` remains immediately reachable from the governed runtime through `reasoning_core`.
5. Why does this block `Workstream 5`?
   - Because `decision.py` cannot become adapter-only or shadow-only while direct compatibility shims still treat it as an ambient owner for routing and continuity behavior.

### Root Cause Statement
Shared routing and expected-reply helper ownership is still smeared into `decision.py`, so `reasoning_core` remains a live bridge into the legacy mesh instead of consuming narrow, explicit seams.

### Fix Mechanism
Re-home or consume shared helpers from narrow modules (`runtime_primitives`, `policy`, `info`, `http`, direct service constants), remove the direct `decision.py` import from `reasoning_core`, and add a freeze guard so that bridge cannot silently return.

## Invariant
- `reasoning_core` remains a thin compatibility delegate; it does not regain semantic ownership.
- No behavior regression in snapshot building, duplicate lookup, or secret-preflight trace resolution.
- `decision.py` loses live helper-bus authority; no new wrapper layer is introduced.
- Deterministic boundary artifacts and governed core paths stay unchanged.

## Scope
- Remove direct `decision.py` import from `reasoning_core.py`.
- Re-home any shared routing primitive that still only lives in `decision.py` and is needed by `reasoning_core`.
- Switch `reasoning_core` to direct narrow helper owners for expected-reply heuristics, routing policy, and message lookup.
- Add deterministic regressions and architecture guard coverage for the severed bridge.

## Out of Scope
- Full `decision.py` strangler or deletion.
- Removing all `decision.py` imports from `booking.py`, `response.py`, or other legacy modules.
- Workstream 6 durable action plane changes.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Inspect each `reasoning_core` use of `decision_router` and map it to the narrowest existing owner.
2. Re-home any missing shared primitive required for that cut.
3. Remove the direct `decision.py` import from `reasoning_core` and update tests.
4. Add an architecture guard proving `reasoning_core` no longer imports `decision.py`.
5. Run deterministic checks and update repo truth.

## DoD
- `reasoning_core.py` has no direct `decision.py` import.
- Shared routing/expected-reply helpers used by `reasoning_core` come from narrow owners.
- `decision.py` no longer owns the moved primitive.
- Deterministic tests covering `reasoning_core` snapshot/preflight behavior stay green.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "routing_policy"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "reasoning_core_has_no_app_runtime_importers or reasoning_core_has_no_direct_decision_router_import or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Targeted reasoning-core pytest output
- Targeted architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility facade in front of `decision.py`.
- No new regex/phrase semantic routing in governed core.
- No widening of `reasoning_core` responsibilities.
- No doc-only progress without removing a live legacy-mesh bridge.

## Risks / Blockers
- Some helper ownership may still live only inside `decision.py`; if so, one narrow primitive may need to be re-homed before the import can be removed.
- Broader `test_legacy_freeze_guard.py` still contains an unrelated residual failure outside this block: `test_policy_decision_creation_stays_in_governed_core_boundary` remains red on the pre-existing `PolicyDecision(...)` constructor in `truffles-api/app/core/dialog_state_service.py`.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `decision.py` remains a large live legacy hotspot with many direct importers.
- `policy.py`, `booking.py`, and `response.py` still use `decision.py` internally.

### Why not in this block
- This block is bounded to the `reasoning_core` bridge seam. Collapsing all `decision.py` importers at once would exceed the first Workstream 5 family.

### Risk if deferred
- `decision.py` remains a live compatibility center even after `reasoning_core` is cut off.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream5-decision-importer-family-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if a second runtime-adjacent shim still imports `decision.py` for shared primitives after this block lands.

## Next-block Contract (mandatory)
### Next block objective
Cut the next direct `decision.py` importer family (`policy.py` / `response.py` / `booking.py`) by re-homing another shared primitive cluster out of the legacy hotspot.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "decision_bridge or legacy"`

### Blocked-by conditions
- This block must first prove `reasoning_core` no longer imports `decision.py` and snapshot/preflight behavior remains stable.

### Owner role for closure
- Brain / Top Architect
