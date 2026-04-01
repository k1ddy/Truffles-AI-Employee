# TP-2026-03-28-consultant-core-workstream5-context-guard-runtime-cluster-cut-a922

## Title / Goal
Remove the remaining live `context_manager.py` and `guards.py` dependency on `decision.py` by extracting their shared continuity/session/guard helper cluster into narrow runtime owners and leaving `decision.py` with compatibility aliases only.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_routers_webhook_guards.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_pending.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com branch by abstraction move constants helper cluster out of god class`
- Date/time: `2026-03-28T07:20:30+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/BranchByAbstraction.html`
- High-signal source quality:
  - Martin Fowler primary architecture reference on replacing a legacy supplier by moving all active clients to a narrow abstraction seam while keeping compatibility aliases only during migration.
- Found reusable idea:
  - migrate one cohesive helper family at a time, switch every active caller to the new owner, and keep the old god-file as compatibility aliases until later deletion.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already uses this pattern with `runtime_primitives.py`, `class_router_runtime.py`, `booking_signal_runtime.py`, and `knowledge_runtime.py`; this family should continue the same move for continuity/session and guard helpers.
- Rejected options:
  - keep `context_manager.py` and `guards.py` on direct `decision_router.*` reads: rejected because `decision.py` would keep live continuity/control ownership.
  - cut only `context_manager.py` first and leave `guards.py` on the same helper cluster: rejected because both files still share active authority through the same god-file and the seam would remain live.

## Root Cause (mandatory)
### Symptom
`context_manager.py` and `guards.py` still depend on `decision.py` for their active continuity/session and guard helper cluster: carryover/session keys, confirmation TTLs, memory keys, `_ensure_question_mark(...)`, `_is_refusal_flag_active(...)`, `MULTI_INTENT_LABELS`, `_coerce_batch_messages(...)`, `get_mute_settings(...)`, timeout constants, and guard text constants.

### Minimal Reproduction
1. Inspect direct uses:
   - `truffles-api/app/routers/webhook/context_manager.py:159`
   - `truffles-api/app/routers/webhook/context_manager.py:242`
   - `truffles-api/app/routers/webhook/context_manager.py:403`
   - `truffles-api/app/routers/webhook/context_manager.py:660`
   - `truffles-api/app/routers/webhook/context_manager.py:870`
   - `truffles-api/app/routers/webhook/guards.py:127`
   - `truffles-api/app/routers/webhook/guards.py:398`
   - `truffles-api/app/routers/webhook/guards.py:424`
   - `truffles-api/app/routers/webhook/guards.py:546`
   - `truffles-api/app/routers/webhook/guards.py:886`
2. Inspect sibling consumers:
   - `truffles-api/app/routers/webhook/booking.py:297`
   - `truffles-api/app/routers/webhook/booking.py:1162`
   - `truffles-api/app/routers/webhook/pending.py:384`
   - `truffles-api/app/routers/webhook/__init__.py:18`
3. Inspect definitions in the god-file:
   - `truffles-api/app/routers/webhook/decision.py:3883`
   - `truffles-api/app/routers/webhook/decision.py:3968`
   - `truffles-api/app/routers/webhook/decision.py:4000`
   - `truffles-api/app/routers/webhook/decision.py:4452`
   - `truffles-api/app/routers/webhook/decision.py:7074`
   - `truffles-api/app/routers/webhook/decision.py:7163`
   - `truffles-api/app/routers/webhook/decision.py:7181`
   - `truffles-api/app/routers/webhook/decision.py:7220`

### Evidence
- `rg -n "decision_router\." truffles-api/app/routers/webhook/context_manager.py`
- `rg -n "decision_router\." truffles-api/app/routers/webhook/guards.py`
- `rg -n "MULTI_INTENT_LABELS|MSG_REENGAGE_DECLINED|MSG_REENGAGE_CONFIRM|MSG_MUTED_TEMP|MSG_MUTED_LONG|MSG_FACT_GUARD_CLARIFY|SESSION_TIMEOUT_HOURS|HANDOVER_CONFIRM_WINDOW_MINUTES|REENGAGE_CONFIRM_WINDOW_MINUTES|ASR_CONFIRM_WINDOW_MINUTES|ASR_INFLIGHT_TTL_SECONDS|SERVICE_HINT_WINDOW_MINUTES|MEMORY_PROFILE_TTL_DAYS|MEMORY_PROFILE_KEY|MEMORY_PENDING_KEY|SERVICE_HINT_KEY|SERVICE_HINT_AT_KEY|RE_ENTRY_REQUIRED_KEY|ASR_CONFIRM_KEY|ASR_INFLIGHT_KEY|STYLE_REFERENCE_PENDING_KEY|CONTEXT_MANAGER_KEY|EXPECTED_REPLY_TYPE_KEY|EXPECTED_REPLY_REASON_KEY|SESSION_MEMORY_KEY|CLASS_CARRYOVER_KEY|CLASS_CARRYOVER_TTL_MESSAGES|CLASS_CARRYOVER_CLASSES|SERVICE_CARRYOVER_KEY|CONSULT_CONTEXT_KEY|SERVICE_CARRYOVER_SKIP_INTENTS|_coerce_batch_messages\(|get_mute_settings\(|_ensure_question_mark\(|_is_refusal_flag_active\(" truffles-api/app`

### Five Whys
1. Why do `context_manager.py` and `guards.py` still import `decision.py` at runtime?
   - Because their shared continuity/session/guard helpers were never extracted into narrow owners.
2. Why are sibling modules still tied to the same symbols?
   - Because `booking.py`, `pending.py`, and package exports still read the same constants and helpers from `decision.py`.
3. Why is that wrong now?
   - Because `decision.py` still owns live continuity/control behavior instead of acting as compatibility aliases only.
4. Why is that risky?
   - Because context and guard behavior can still drift whenever the god-file changes, keeping the legacy mesh on the active path.
5. Why does this block Workstream 5?
   - Because Workstream 5 requires legacy helper/control authority to leave the god-file, not merely reduced import fanout in some callers.

### Root Cause Statement
The continuity/session and guard helper cluster was left centralized in `decision.py`, so `context_manager.py`, `guards.py`, and nearby active consumers still use the god-file as the live supplier of context keys, TTLs, carryover contracts, refusal helpers, batch shaping, mute settings, and guard text/control constants.

### Fix Mechanism
Create narrow runtime owners for the continuity/session cluster and the guard cluster, switch every active caller in this family to direct imports from those owners, keep compatibility aliases in `decision.py`, and add deterministic guards so `context_manager.py` and `guards.py` cannot drift back to direct `decision.py` ownership.

## Invariant
- Context carryover, expected-reply continuity, mute/reengage/session-timeout behavior, and guard prompts stay unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live ownership of the moved context/guard cluster.
- Existing targeted deterministic tests remain green.

## Scope
- Extract continuity/session keys, TTLs, and helper functions out of `decision.py`.
- Extract guard/mute/session-timeout helper constants and utility functions out of `decision.py`.
- Switch `context_manager.py`, `guards.py`, `booking.py`, `pending.py`, and `app/routers/webhook/__init__.py` to direct narrow-owner imports where needed.
- Leave compatibility aliases in `decision.py` only for remaining callers.
- Add focused regressions and architecture guards.

## Out of Scope
- Deleting `decision.py`.
- Reworking pending/status product behavior.
- LLM quality acceptance runs.
- Fixing the unrelated `PolicyDecision(...)` residual in `truffles-api/app/core/dialog_state_service.py`.

## Touch-list
- `truffles-api/app/routers/webhook/context_runtime.py`
- `truffles-api/app/routers/webhook/guard_runtime.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Extract the continuity/session helper cluster into a narrow runtime owner.
2. Extract the guard/mute/session-timeout helper cluster into a narrow runtime owner.
3. Switch active consumers to direct imports.
4. Leave compatibility aliases in `decision.py` only for remaining callers.
5. Add focused deterministic tests and architecture guards.
6. Run deterministic checks and update repo truth.

## DoD
- `context_manager.py` no longer reads the moved continuity/session cluster through `decision_router.*`.
- `guards.py` no longer reads the moved guard cluster through `decision_router.*`.
- `booking.py`, `pending.py`, and package exports no longer read the moved symbols through `decision.py`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/context_runtime.py truffles-api/app/routers/webhook/guard_runtime.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "context_manager_expected_reply_getters or mute or reengage or session_timeout or clarify_limit or expected_reply_contract_bypasses_human_request"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "context_and_guard_runtime_clusters_use_narrow_owners or response_decision_helper_residue_uses_narrow_runtime_owners or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused pytest output for context/guard/pending consumers
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
- `decision.py` will still own other helper/control families after this cut.
- `booking.py` and `info.py` will still depend on `decision.py` for unrelated booking/info helpers outside this context/guard family.

### Why not in this block
- This family is bounded to continuity/session and guard helper ownership.

### Risk if deferred
- `decision.py` remains the live supplier of context and guard behavior, keeping the legacy mesh on the active path.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-decision-shared-booking-info-helper-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `context_manager.py` or `guards.py` still have direct `decision_router.*` reads for the moved cluster.

## Next-block Contract (mandatory)
### Next block objective
After this cut, reduce the next surviving direct `decision.py` consumer cluster, likely shared booking/info helper seams still imported by `booking.py` and `info.py`.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "context_and_guard_runtime_clusters_use_narrow_owners or response_decision_helper_residue_uses_narrow_runtime_owners"`

### Blocked-by conditions
- This block must first prove that `context_manager.py` and `guards.py` no longer read the moved helper cluster from `decision.py` and that targeted context/guard tests stay green.

### Owner role for closure
- Brain / Top Architect
