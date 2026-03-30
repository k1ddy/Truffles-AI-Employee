# TP-2026-03-28-consultant-core-workstream5-response-decision-helper-residue-cut-a922

## Title / Goal
Remove the remaining live `response.py` dependency on `decision.py` by extracting the residual helper clusters still owned by the god-file: booking-signal / service-hint / consult-clarify thresholds and RAG / backlog helpers. Move active consumers to narrow runtime owners and leave `decision.py` with compatibility aliases only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_routers_webhook_guards.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com move behavior from god class to module branch by abstraction`
- Date/time: `2026-03-28T06:38:33+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/BranchByAbstraction.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on moving client behavior off a legacy supplier by introducing a narrow abstraction seam and gradually switching all consumers before leaving compatibility aliases.
- Found reusable idea:
  - move one cohesive helper family at a time into a narrow owner, switch every active consumer to the new owner, then leave the legacy hotspot as alias-only compatibility until later deletion.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has `runtime_primitives.py` and `class_router_runtime.py` as narrowed owners; this family should continue that pattern instead of keeping `decision.py` as the supplier of response-stage helper behavior.
- Rejected options:
  - cut only `response.py` and leave `booking.py` / `context_manager.py` / `guards.py` on the same `decision.py` helpers: rejected because the helper cluster would remain live in the god-file.
  - do a tiny RAG-only cut first: rejected because the larger residue is the shared booking-signal / service-hint / consult-threshold cluster, and continuing tiny cuts would preserve the wrong authority distribution.

## Root Cause (mandatory)
### Symptom
`response.py` still depends on `decision.py` for all of its remaining `decision_router.*` reads, and sibling active routers still read the same god-file for booking-signal/service-hint helpers and consult/clarify thresholds.

### Minimal Reproduction
1. Inspect remaining `response.py` calls:
   - `truffles-api/app/routers/webhook/response.py:591`
   - `truffles-api/app/routers/webhook/response.py:601`
   - `truffles-api/app/routers/webhook/response.py:694`
   - `truffles-api/app/routers/webhook/response.py:770`
   - `truffles-api/app/routers/webhook/response.py:1553`
   - `truffles-api/app/routers/webhook/response.py:2112`
   - `truffles-api/app/routers/webhook/response.py:2565`
   - `truffles-api/app/routers/webhook/response.py:2792`
2. Inspect sibling consumers:
   - `truffles-api/app/routers/webhook/booking.py:556`
   - `truffles-api/app/routers/webhook/info.py:1481`
   - `truffles-api/app/routers/webhook/context_manager.py:174`
   - `truffles-api/app/routers/webhook/guards.py:220`
3. Inspect definitions in the god-file:
   - `truffles-api/app/routers/webhook/decision.py:3679`
   - `truffles-api/app/routers/webhook/decision.py:3896`
   - `truffles-api/app/routers/webhook/decision.py:4103`
   - `truffles-api/app/routers/webhook/decision.py:4713`
   - `truffles-api/app/routers/webhook/decision.py:4759`
   - `truffles-api/app/routers/webhook/decision.py:4852`
   - `truffles-api/app/routers/webhook/decision.py:6984`

### Evidence
- `rg -n "decision_router\." truffles-api/app/routers/webhook/response.py`
- `rg -n "_merge_rag_scores|_derive_rag_status|_record_knowledge_backlog|_is_booking_request|_extract_service_hint|_looks_like_time_only_request|CONSULT_CONTEXT_TTL_MESSAGES|CLARIFY_MAX_ATTEMPTS" truffles-api/app`
- `truffles-api/app/routers/webhook/decision.py:3679-3908`
- `truffles-api/app/routers/webhook/decision.py:4103-4178`
- `truffles-api/app/routers/webhook/decision.py:4595-4886`
- `truffles-api/app/routers/webhook/decision.py:6984-7035`

### Five Whys
1. Why does `response.py` still depend on `decision.py`?
   - Because the last response-stage helper residue was never re-homed after earlier class-router and retry-sidecar extractions.
2. Why is the same helper residue still live in sibling routers?
   - Because booking-signal/service-hint detection and consult/clarify thresholds stayed grouped inside `decision.py` and active consumers kept reading them there.
3. Why is that wrong now?
   - Because the god-file still owns live response/booking/control helper behavior instead of compatibility aliases only.
4. Why is that risky?
   - Because response-stage behavior can still drift when `decision.py` changes, and the legacy mesh remains the supplier of consult TTL, clarify limits, booking detection, service hints, and backlog writes.
5. Why does this block Workstream 5?
   - Because Workstream 5 requires the legacy mesh to lose live helper/control authority, not merely ambient import fanout.

### Root Cause Statement
The remaining response-stage helper residue was left concentrated in `decision.py`, so active consumers still use the god-file as the live supplier of booking-signal detection, service-hint extraction, consult/clarify thresholds, RAG status merging, and backlog recording.

### Fix Mechanism
Create narrow runtime owners for the residual helper families, switch all active consumers to those owners, keep compatibility aliases in `decision.py`, and add deterministic guards so the moved clusters cannot drift back into the god-file.

## Invariant
- Response / booking / info / guard behavior stays unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live ownership of the moved helper clusters.
- Existing targeted deterministic tests stay green.

## Scope
- Extract the booking-signal/service-hint/time-only/consult-threshold helper cluster out of `decision.py`.
- Extract RAG/backlog helper residue out of `decision.py`.
- Switch active consumers to direct narrow-owner imports.
- Leave compatibility aliases in `decision.py` only for surviving callers.
- Add focused tests and architecture guards.

## Out of Scope
- Deleting `decision.py`.
- Reworking unrelated booking slot/state-machine logic.
- LLM quality acceptance runs.
- Fixing the unrelated `PolicyDecision(...)` residual in `truffles-api/app/core/dialog_state_service.py`.

## Touch-list
- `truffles-api/app/routers/webhook/booking_signal_runtime.py`
- `truffles-api/app/routers/webhook/knowledge_runtime.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_webhook_response.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Extract booking-signal/service-hint/time-only helpers and consult/clarify thresholds into a narrow runtime owner.
2. Extract RAG/backlog helpers into a narrow runtime owner.
3. Switch `response.py`, `booking.py`, `info.py`, `context_manager.py`, and `guards.py` to direct imports.
4. Leave compatibility aliases in `decision.py` only for remaining callers.
5. Add focused regressions and architecture guards.
6. Run deterministic checks and update repo truth.

## DoD
- `response.py` no longer reads any `decision_router.*` helper from the moved clusters.
- Active consumers of booking-signal/service-hint/consult-threshold helpers no longer read them from `decision.py`.
- Active consumers of RAG/backlog helpers no longer read them from `decision.py`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/booking_signal_runtime.py truffles-api/app/routers/webhook/knowledge_runtime.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_webhook_response.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "style_reference or quiet_hours or routing_policy or expected_reply or booking_interrupt or strict_ood or low_confidence"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "routing_policy or pending_booking_reactivation"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "response or policy_router or reasoning_core or controller_class_router_cluster or final_legacy_residue_first_wave"`
- `git diff --check`

## Evidence
- Updated TP
- Focused pytest output for response/booking/info consumers
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
- `decision.py` will still own other legacy helper families after this cut.
- Some active modules may still import `decision.py` for unrelated constants or helpers outside the moved clusters.

### Why not in this block
- This family is bounded to the last response-stage helper residue plus its directly shared booking-signal/consult and RAG/backlog clusters.

### Risk if deferred
- `decision.py` remains the live supplier for response-stage behavior and keeps the legacy mesh on the active path.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-decision-shared-booking-info-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `response.py` still has any direct `decision_router.*` helper dependency.

## Next-block Contract (mandatory)
### Next block objective
After this cut, reduce the next surviving direct `decision.py` consumer cluster, likely shared booking/info helper seams still imported by `booking.py` and `info.py`.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "response or policy_router or reasoning_core"`

### Blocked-by conditions
- This block must first prove that `response.py` no longer reads the moved helper clusters from `decision.py` and that targeted response/architecture checks stay green.

### Owner role for closure
- Brain / Top Architect
