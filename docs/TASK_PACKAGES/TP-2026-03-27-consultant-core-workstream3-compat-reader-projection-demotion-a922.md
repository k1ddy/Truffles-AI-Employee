# TP-2026-03-27-consultant-core-workstream3-compat-reader-projection-demotion-a922

- Title/goal: Demote the remaining compatibility readers so they consume `ConversationProjectionV1` / projection-derived runtime views first, instead of treating `canonical_dialog_state`, `session_memory`, and other legacy carriers as peer current-state stores.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- Invariant:
  - Workstream 1 and 2 guarantees stay intact, and Workstream 3 keeps one primary runtime read model on the active path.
- Scope:
  - Rebind compatibility readers in `context_manager`, `reasoning_core`, and timeout-boundary helpers to projection-first/runtime-derived reads.
  - Keep legacy carriers as fallback-only migration surfaces where explicit runtime projection is absent.
- Out of scope:
  - Removing `canonical_dialog_state`, `session_memory`, or `pending_resume` writers.
  - DB-backed journal/projection persistence.
  - Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/timeout_owner_boundary_service.py`
  - `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com CQRS materialized view read model derived view migration compatibility view`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - one write model may feed a materialized read model
  - compatibility or downstream consumers should read the materialized view instead of consulting multiple peer state stores
  - migration can keep compatibility views derived from the primary read model during cutover
- Decision: `integrate/build`
- Why:
  - The repo now has runtime-local `TurnJournalV1` and `ConversationProjectionV1`; the missing cut is to force legacy readers through that projection seam instead of reading `canonical_dialog_state` / `session_memory` directly.
- Rejected variants:
  - keep direct `canonical_dialog_state` reads: rejected, preserves peer truth-carriers
  - introduce external CQRS framework: rejected, too large for this bounded block

## Root cause (mandatory)
- Symptom:
  - Workstream 3 still has live compatibility readers that can observe stale legacy state before the new projection seam.
- Minimal reproduction:
  - `context_manager._get_pending_question_contract(...)` reads `canonical_dialog_state` directly.
  - `reasoning_core._build_conversation_snapshot(...)` can still resurrect continuity from `session_memory` / `canonical_dialog_state` even when runtime projection exists.
  - timeout-boundary helpers read `interaction_state` back from `canonical_dialog_state` instead of a projection-derived runtime view.
- Evidence:
  - `truffles-api/app/routers/webhook/context_manager.py:267`
  - `truffles-api/app/services/reasoning_core.py:320`
  - `truffles-api/app/services/reasoning_core.py:383`
  - `truffles-api/app/services/timeout_owner_boundary_service.py:173`
  - `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py:104`
- Five whys:
  1. Why is the primary runtime projection not enough yet? Because several compatibility readers still bypass it.
  2. Why do they bypass it? Because they were written before `ConversationProjectionV1` existed and still read legacy carriers directly.
  3. Why is that harmful? Because stale `canonical_dialog_state` or `session_memory` can shadow the new primary read model.
  4. Why can stale compatibility state still win? Because these readers do not go through one governed projection-first helper.
  5. Why has that not been removed yet? Because the first W3 block introduced the substrate but did not rebind the outer compatibility readers.
- Root cause statement:
  - Compatibility readers still treat legacy state carriers as peer truths instead of reading through the new projection-derived runtime seam.
- Fix mechanism:
  - Add projection-first reader helpers in `DialogStateService` where needed, route compatibility consumers through them, and keep legacy carriers fallback-only when no explicit runtime projection exists.

- Plan:
  1. Add projection-first helper(s) for compatibility reader needs that still read legacy state directly.
  2. Rebind `context_manager` expected-reply readers to projection-first helpers.
  3. Rebind `reasoning_core` snapshot reads to projection-first helpers and prevent explicit runtime projection from being shadowed by stale `session_memory`.
  4. Rebind timeout-boundary helpers to projection-derived interaction-state reads.
  5. Add deterministic regressions and update repo truth.
- DoD:
  - `context_manager` no longer reads pending-question state directly from `canonical_dialog_state` when runtime projection exists.
  - `reasoning_core` snapshot prefers runtime projection/service referents over stale compatibility carriers.
  - timeout-boundary helpers read projection-derived interaction state instead of reading `canonical_dialog_state` directly.
  - deterministic tests prove projection-first precedence and no silent resurrection of stale compatibility state when explicit projection exists.
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "conversation_projection or expected_reply_getters or canonical_dialog_state"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "conversation_snapshot and (projection or session_memory or canonical)"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "conversation_projection or interaction_state"`
  - `git diff --check`
- Evidence:
  - code diff
  - deterministic test output
  - `STATE.md` update after checks
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no new peer state store
  - no semantic hardcode in runtime core
  - no weakening of Workstream 1/2 invariants
- Risks/blockers:
  - compatibility readers may still depend on fallback-only legacy behavior when explicit projection is absent
  - timeout-boundary helpers may rely on derived runtime loads after context_manager mutation

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `canonical_dialog_state`, `session_memory`, and `pending_resume` writers still exist
  - `state_service` still treats `pending_resume` and `session_memory` as live compatibility stores
- Why not in this block:
  - this block only demotes readers; writer-surface reduction is the next W3 cut
- Risk if deferred:
  - multiple write paths continue to exist even after reader precedence is cleaned up
- Linked follow-up Task Package(s):
  - follow-up W3 writer-surface narrowing TP (to be opened after this block)
- Expiry/trigger to stop deferral:
  - stop deferral if any new reader or writer bypasses `conversation_projection` on the active runtime path

## Next-block contract (mandatory)
- Next block objective:
  - narrow the continuity writer surface so `canonical_dialog_state`, `session_memory`, and `pending_resume` become derived-only or explicitly bounded compatibility writers
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or session_memory or context_manager"`
- Blocked-by conditions:
  - compatibility readers still bypass projection-first helpers
  - no deterministic proof that explicit runtime projection wins over stale legacy state
- Owner role for closure:
  - Brain / Top Architect
