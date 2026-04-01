# TP-2026-03-27-consultant-core-workstream5-policy-decision-helper-cluster-cut-a922

## Title / Goal
Remove the live `policy.py -> decision.py` helper/control dependency by re-homing shared routing/sidecar/escalation primitives and policy-handler ownership out of `decision.py`, leaving policy gates to consume narrow owners only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_policy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `martinfowler branch by abstraction refactoring legacy seam`
- Date/time: `2026-03-27T20:37:41+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/BranchByAbstraction.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on gradual replacement through an abstraction seam
- Found reusable idea:
  - move clients of the old supplier to an abstraction/shared seam first, then gradually replace the old supplier while keeping delivery green.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has `runtime_primitives.py` as a shared seam; the correct move is to move shared control/response primitives there and let `policy.py` own its local policy-handler cluster instead of reaching into `decision.py`.
- Rejected options:
  - keep `policy.py` importing `decision.py` for helper constants/functions: rejected because it preserves `decision.py` as a live helper bus.
  - introduce a new extra adapter layer just for policy helpers: rejected because it adds transitional architecture without reducing ownership.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/policy.py` still imports `decision.py` indirectly and pulls live helper/control symbols from it: `_contains_any`, `_POLICY_HANDLERS`, `_is_hygiene_context_text`, `MSG_ESCALATED`, `_combine_sidecar`.

### Minimal Reproduction
1. Inspect `truffles-api/app/routers/webhook/policy.py:414-834`.
2. Observe `decision_router._contains_any(...)`, `decision_router._POLICY_HANDLERS`, `decision_router._is_hygiene_context_text(...)`, `decision_router.MSG_ESCALATED`, and `decision_router._combine_sidecar(...)`.
3. Inspect `truffles-api/app/routers/webhook/decision.py:3958-3968`, `truffles-api/app/routers/webhook/decision.py:4590`, and `truffles-api/app/routers/webhook/decision.py:7954-8013`.
4. Observe that the shared helper/control cluster still lives in the legacy hotspot.

### Evidence
- `truffles-api/app/routers/webhook/policy.py:414-834`
- `truffles-api/app/routers/webhook/decision.py:3958-3968`
- `truffles-api/app/routers/webhook/decision.py:4590`
- `truffles-api/app/routers/webhook/decision.py:7954-8013`

### Five Whys
1. Why does `policy.py` still depend on `decision.py`?
   - Because shared policy-side helpers and constants still live inside the legacy god-file.
2. Why are those symbols still there?
   - Because earlier cuts removed ambient `_legacy.py` fanout first, but did not finish re-homing the direct helper clusters.
3. Why is that wrong now?
   - Because `decision.py` remains a live authority center as long as policy gates must read helper/control symbols from it.
4. Why is that dangerous?
   - Because policy behavior can still drift whenever `decision.py` changes, even though the policy seam should be narrow and explicit.
5. Why does this block Workstream 5?
   - Because Workstream 5 requires legacy modules to become adapter-only/shadow-only, which is impossible while `decision.py` still owns shared helper/control primitives for policy routing.

### Root Cause Statement
Policy routing still reads a shared helper/control cluster from `decision.py`, so the legacy god-file remains the effective owner of escalation messaging, sidecar composition, policy-handler lookup, and normalized keyword matching for the policy gate.

### Fix Mechanism
Move shared routing/response primitives to `runtime_primitives.py`, move policy-handler ownership into `policy.py`, keep compatibility aliases in `decision.py` only if required, and add freeze coverage so `policy.py` no longer imports `decision.py` directly.

## Invariant
- Policy gate behavior stays unchanged for routing, escalation text, and sidecar composition.
- No new semantic routing is added.
- `decision.py` loses live helper/control ownership rather than gaining another wrapper.
- Existing policy handler tests and routing-policy tests stay green.

## Scope
- Remove the remaining direct `policy.py -> decision.py` helper dependency.
- Re-home shared policy/routing primitives out of `decision.py`.
- Keep compatibility aliases in `decision.py` only if needed for surviving callers.
- Add deterministic tests/guards covering the severed seam.

## Out of Scope
- Full removal of `decision.py` imports from `booking.py` / `response.py`.
- Global `_combine_sidecar` migration for every legacy module.
- Workstream 6 durable action plane work.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Re-home shared helper/control primitives needed by `policy.py`.
2. Move policy-handler ownership into `policy.py`.
3. Remove the direct `decision.py` dependency from `policy.py`.
4. Add deterministic regressions and architecture guard coverage.
5. Run deterministic checks and update repo truth.

## DoD
- `policy.py` no longer imports or depends on `decision.py` for helper/control primitives.
- Shared primitives used by policy routing live in narrow owners.
- Existing policy handler behavior stays green.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "routing_policy or policy"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy_router_has_no_direct_decision_router_import or final_legacy_residue_first_wave_uses_direct_owners or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Targeted policy/runtime pytest output
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
- Some compatibility callers may still expect symbols on `decision.py`; aliases may be required during the migration.
- Broader architecture guard still has an unrelated red residual in `dialog_state_service.py`: `test_policy_decision_creation_stays_in_governed_core_boundary` fails on the pre-existing direct `PolicyDecision(...)` constructor in `truffles-api/app/core/dialog_state_service.py`.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `response.py`, `booking.py`, and `info.py` still depend on `decision.py` for other helper clusters.
- `decision.py` remains a large legacy hotspot.

### Why not in this block
- This family is bounded to the policy seam; collapsing the whole importer graph would exceed one authority-reduction block.

### Risk if deferred
- `decision.py` remains a shared helper center for other legacy modules even after the policy cut lands.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream5-response-booking-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if policy cut lands and another runtime-adjacent module still imports `decision.py` for the same helper/control cluster.

## Next-block Contract (mandatory)
### Next block objective
Cut the next direct helper cluster from `decision.py`, likely in `response.py` or `booking.py`, using the same narrow shared primitives strategy.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy or legacy"`

### Blocked-by conditions
- This block must first prove `policy.py` no longer depends on `decision.py` and the routing/escalation behavior remains stable.

### Owner role for closure
- Brain / Top Architect
