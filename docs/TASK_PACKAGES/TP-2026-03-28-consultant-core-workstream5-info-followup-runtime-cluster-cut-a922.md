# TP-2026-03-28-consultant-core-workstream5-info-followup-runtime-cluster-cut-a922

## Title / Goal
Remove the remaining live `info.py -> decision.py` dependency by extracting the info followup helper cluster into a narrow runtime owner and switching `info.py` to direct runtime primitives for shared response text helpers.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com extract helper methods to module refactoring`
- Date/time: `2026-03-28T07:39:32+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/class-too-large.html`
- High-signal source quality:
  - Martin Fowler primary refactoring article on pulling cohesive method groups out of an oversized owner while keeping behavior stable through small, test-backed moves.
- Found reusable idea:
  - identify one coherent responsibility slice, move just that slice to a new owner, redirect live callers first, and leave the large legacy file with aliases only.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo is already using this move-one-cluster pattern against `decision.py`; the info followup helpers are another cohesive slice.
- Rejected options:
  - leave `info.py` on direct `decision_router.*` reads until booking/media are handled: rejected because it preserves a live legacy helper seam.
  - fold info followup work into the much larger booking helper family: rejected because it mixes separate domains and weakens closure evidence.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/info.py` still imports `decision.py` at runtime for a small but live helper cluster: `_looks_like_hours_followup(...)`, `_looks_like_carryover_followup(...)`, `MSG_ESCALATED`, `MSG_EXPECTED_SERVICE_OFF_TOPIC`, and `_combine_sidecar(...)`.

### Minimal Reproduction
1. Inspect direct reads in `truffles-api/app/routers/webhook/info.py`.
2. Confirm `MSG_ESCALATED`, `MSG_EXPECTED_SERVICE_OFF_TOPIC`, and `_combine_sidecar(...)` already have narrow owners in `runtime_primitives.py`.
3. Confirm `_looks_like_hours_followup(...)` and `_looks_like_carryover_followup(...)` are still defined only in `decision.py`.

### Evidence
- `rg -n "decision_router\.(MSG_ESCALATED|MSG_EXPECTED_SERVICE_OFF_TOPIC|_combine_sidecar|_looks_like_hours_followup|_looks_like_carryover_followup)" truffles-api/app/routers/webhook/info.py`
- `rg -n "def _looks_like_hours_followup|def _looks_like_carryover_followup|MSG_EXPECTED_SERVICE_OFF_TOPIC|def _combine_sidecar" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/runtime_primitives.py`

### Five Whys
1. Why does `info.py` still import `decision.py`?
   - Because the info followup helpers were never extracted into a narrow owner.
2. Why is that wrong now?
   - Because `decision.py` still supplies live info followup behavior on the active path.
3. Why is that risky?
   - Because info followup logic can still drift with unrelated `decision.py` changes.
4. Why does this block Workstream 5?
   - Because Workstream 5 requires live helper/control authority to leave the god-file.
5. Why handle this family separately?
   - Because the info followup cluster is cohesive, small, and should let `info.py` drop direct `decision.py` dependency entirely.

### Root Cause Statement
The info followup helper cluster stayed in `decision.py`, so `info.py` still uses the god-file as a live supplier for followup detection and shared response helpers instead of narrow runtime owners.

### Fix Mechanism
Create an `info_followup_runtime.py` owner for the followup helpers, switch `info.py` to import shared response primitives from `runtime_primitives.py` directly plus the new followup owner, keep compatibility aliases in `decision.py`, and add deterministic guards.

## Invariant
- Info followup detection and user-visible replies stay unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live ownership of the moved info followup cluster.

## Scope
- Extract `_looks_like_hours_followup(...)` and `_looks_like_carryover_followup(...)` plus any exact support helpers/constants they require into `info_followup_runtime.py`.
- Switch `info.py` to direct imports from `runtime_primitives.py` and `info_followup_runtime.py`.
- Leave compatibility aliases in `decision.py` only.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Deleting `decision.py`.
- Refactoring the larger booking helper family.
- Media/dedup/outbox cleanup.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/info_followup_runtime.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Extract the info followup helper cluster into `info_followup_runtime.py`.
2. Switch `info.py` to direct runtime owner imports.
3. Keep compatibility aliases in `decision.py` only.
4. Add focused deterministic coverage and architecture guard updates.
5. Update repo truth.

## DoD
- `info.py` no longer reads `MSG_ESCALATED`, `MSG_EXPECTED_SERVICE_OFF_TOPIC`, `_combine_sidecar(...)`, `_looks_like_hours_followup(...)`, or `_looks_like_carryover_followup(...)` through `decision_router.*`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/info_followup_runtime.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "strict_ood or routing_policy or style_reference"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "info_followup_runtime_cluster_uses_narrow_owner or pending_runtime_cluster_uses_narrow_owner or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused pytest output for info behavior
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
- `booking.py`, `media.py`, `dedup.py`, and `outbox.py` will still depend on `decision.py` for unrelated helper clusters after this cut.

### Why not in this block
- This family is bounded to the live `info.py -> decision.py` seam.

### Risk if deferred
- `decision.py` keeps live ownership of info followup helper behavior.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-booking-info-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `info.py` still has direct `decision_router.*` reads for the moved cluster.

## Next-block Contract (mandatory)
### Next block objective
After this cut, reduce the next surviving `decision.py` helper family in `booking.py` or `media.py`.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "info_followup_runtime_cluster_uses_narrow_owner or pending_runtime_cluster_uses_narrow_owner"`

### Blocked-by conditions
- This block must first prove that `info.py` no longer reads the moved helper cluster from `decision.py` and that focused info tests stay green.

### Owner role for closure
- Brain / Top Architect
