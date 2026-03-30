# TP-2026-03-27-consultant-core-workstream5-response-controller-class-router-cluster-cut-a922

## Title / Goal
Remove the live `response.py` / `booking.py` / `info.py` dependency on `decision.py` for controller/class-router result shaping, moving that shared helper cluster into a narrow runtime owner and leaving `decision.py` with compatibility aliases only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "Branch By Abstraction" gradual replacement abstraction layer`
- Date/time: `2026-03-27T21:03:00+05:00`
- Opened sources:
  - `https://www.martinfowler.com/bliki/BranchByAbstraction.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on gradually moving clients to a narrow abstraction seam while keeping the old supplier as compatibility during migration.
- Found reusable idea:
  - extract one supplier-facing helper cluster behind a narrow abstraction, move all current clients to that seam, then leave the legacy module as an alias-only compatibility surface.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has multiple narrowed webhook runtime owners; this family should add one explicit class-router owner module and move all current clients to it instead of keeping `decision.py` as the live supplier.
- Rejected options:
  - keep `response.py` / `booking.py` / `info.py` reading class-router helpers from `decision.py`: rejected because it preserves `decision.py` as a live helper bus.
  - move only `response.py` and leave the same cluster in `booking.py` / `info.py`: rejected because the same helper cluster would remain live in `decision.py` and authority would not actually be reduced.

## Root Cause (mandatory)
### Symptom
`response.py`, `booking.py`, and `info.py` still read controller/class-router helper symbols from `decision.py`, including `_build_controller_meta_output`, `_ensure_controller_output_meta`, `CONTROLLER_CONFIDENCE_THRESHOLD`, `_resolve_controller_signal_class`, `_resolve_class_router_result`, `_controller_meta_updates_from_class_router`, `_router_observability_updates_from_class_router`, and `CONSULT_INTERRUPT_INTENTS`.

### Minimal Reproduction
1. Inspect:
   - `truffles-api/app/routers/webhook/response.py:878-1001`
   - `truffles-api/app/routers/webhook/booking.py:1577-1669`
   - `truffles-api/app/routers/webhook/info.py:1120-1269`
   - `truffles-api/app/routers/webhook/info.py:1607-1717`
   - `truffles-api/app/routers/webhook/info.py:2009-2038`
2. Observe direct `decision_router.*` calls for controller/class-router shaping.
3. Inspect `truffles-api/app/routers/webhook/decision.py:7127-7849`.
4. Observe that the shared controller/class-router result-shaping cluster still lives in the legacy hotspot.

### Evidence
- `truffles-api/app/routers/webhook/response.py:878-1001`
- `truffles-api/app/routers/webhook/booking.py:1577-1669`
- `truffles-api/app/routers/webhook/info.py:1120-1269`
- `truffles-api/app/routers/webhook/info.py:1607-1717`
- `truffles-api/app/routers/webhook/info.py:2009-2038`
- `truffles-api/app/routers/webhook/decision.py:7127-7849`

### Five Whys
1. Why do three active routers still depend on `decision.py`?
   - Because controller/class-router result shaping was never extracted into its own narrow owner.
2. Why is that cluster still in `decision.py`?
   - Because earlier Workstream 5 cuts removed simpler helper clusters first and left the controller/class-router shaping logic behind.
3. Why is that wrong now?
   - Because `decision.py` still owns a live helper/control cluster used by multiple active modules.
4. Why is that risky?
   - Because controller/class-router behavior can still drift whenever `decision.py` changes, keeping the god-file on the hot path.
5. Why does this block Workstream 5?
   - Because Workstream 5 requires the legacy mesh to lose live helper/control authority, not just ambient import fanout.

### Root Cause Statement
The shared controller/class-router result-shaping cluster still lives in `decision.py`, so active router modules continue to use the legacy hotspot as the live supplier of controller confidence thresholds, class-router envelopes, and controller observability metadata.

### Fix Mechanism
Create a narrow class-router runtime owner for this shared cluster, switch all current active consumers to direct imports from that owner, keep compatibility aliases in `decision.py`, and add deterministic guards so the cluster does not drift back into the legacy hotspot.

## Invariant
- Controller/class-router behavior stays unchanged.
- No new semantic routing is added.
- `decision.py` loses live controller/class-router helper ownership.
- Existing targeted class-router tests remain green.

## Scope
- Extract the shared controller/class-router helper cluster out of `decision.py`.
- Switch `response.py`, `booking.py`, and `info.py` to direct narrow-owner imports.
- Keep compatibility aliases in `decision.py` only if surviving callers still need them.
- Add focused regressions and architecture guard coverage.

## Out of Scope
- RAG helper extraction.
- Booking-request detection extraction.
- Knowledge backlog extraction.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/class_router_runtime.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_webhook_response.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Extract the shared controller/class-router helper cluster into a narrow runtime owner.
2. Switch `response.py`, `booking.py`, and `info.py` to direct imports from that owner.
3. Leave compatibility aliases in `decision.py` only for surviving callers.
4. Add focused tests and architecture guards.
5. Run deterministic checks and update repo truth.

## DoD
- Active router modules no longer read the controller/class-router helper cluster from `decision.py`.
- Shared controller/class-router shaping lives in a narrow owner.
- Targeted response/booking/info/architecture checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/class_router_runtime.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_webhook_response.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "strict_ood or signal_snapshot_written_on_class_router"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "controller_class_router_cluster_uses_narrow_runtime_owner or response_retry_sidecar_cluster_uses_narrow_runtime_primitives or policy_router_has_no_direct_decision_router_import or reasoning_core_has_no_direct_decision_router_import or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Targeted pytest output for class-router consumers
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
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `truffles-api/tests/test_webhook_booking.py` already has a pre-existing export-surface failure around `app.routers.webhook.EXPECTED_REPLY_NAME`; if it stays red, it cannot be used as closure evidence unless this block directly fixes that export seam.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `response.py` will still depend on `decision.py` for RAG, booking-request detection, backlog recording, and service-hint helpers after this cut.
- `decision.py` remains a large legacy hotspot.

### Why not in this block
- This family is bounded to the controller/class-router helper cluster; pulling RAG, backlog, and booking-detection helpers would open separate families.

### Risk if deferred
- `decision.py` remains the live supplier for other response-stage helper clusters after controller/class-router shaping is removed.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream5-response-rag-booking-detection-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this cut lands and `response.py` still reads more than one unrelated generic helper cluster from `decision.py` without a bounded owner plan.

## Next-block Contract (mandatory)
### Next block objective
Cut the next remaining `response.py -> decision.py` helper cluster, likely RAG or booking-detection helpers, after controller/class-router shaping is re-homed.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "class_router or response or policy_router"`

### Blocked-by conditions
- This block must first prove that active router modules no longer read controller/class-router shaping helpers from `decision.py` and that targeted class-router tests stay green.

### Owner role for closure
- Brain / Top Architect
