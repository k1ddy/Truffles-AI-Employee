# TP-2026-03-27-consultant-core-workstream3-context-manager-context-write-owner-cut-a922

- Title/goal: Move conversation-context preservation and decision-trace merge ownership out of `context_manager.py` into governed core so `context_manager` becomes a thin compatibility delegate for conversation-context writes.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
  - `docs/LEGACY_SUNSET.yaml`
- Invariant:
  - `ConversationProjectionV1` stays the strongest active continuity source, and this block must not reintroduce peer semantic/state authority outside governed core.
- Scope:
  - Extract `_set_conversation_context(...)` preservation/merge behavior from `context_manager.py` into `DialogStateService`.
  - Make `context_manager._set_conversation_context(...)` a thin delegate over the governed core helper.
  - Add deterministic coverage for simulation-field preservation and decision-trace merge behavior through the new core seam.
- Out of scope:
  - Removing `context_manager.py` from the continuity-writer allowlist.
  - `state_service.py` / `pending.py` writer-surface narrowing.
  - Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com CQRS single write model materialized view migration compatibility writer`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - the write model should stay the single authority for updates
  - read and compatibility models can remain during migration, but should be materialized/derived from the write-side authority
  - separation works best when read/update bridging logic is explicit instead of being spread across adapters
- Decision: `integrate/build`
- Why:
  - the repo already has a governed core state service; this block rehomes context-write merge logic there instead of leaving it in a webhook adapter
- Rejected variants:
  - keep merge/preservation logic in `context_manager.py`: rejected, preserves adapter-side write authority
  - delete `_set_conversation_context(...)` outright: rejected, too broad while many compatibility callers still use the seam

## Root cause (mandatory)
- Symptom:
  - `context_manager.py` still owns the conversation-context preservation and trace-merge rules for active compatibility writes, so the writer boundary is not yet centered in governed core.
- Minimal reproduction:
  - `context_manager._set_conversation_context(...)` preserves simulation keys from existing conversation context and merges decision trace entries before assigning `conversation.context`.
  - many compatibility callers route all context writes through this adapter, so adapter-local logic remains the effective authority for write-shape preservation.
- Evidence:
  - `truffles-api/app/routers/webhook/context_manager.py:182`
  - `truffles-api/app/routers/webhook/context_manager.py:194`
  - `truffles-api/app/routers/webhook/context_manager.py:215`
  - `truffles-api/app/routers/webhook/context_manager.py:366`
  - `truffles-api/app/routers/webhook/context_manager.py:514`
- Five whys:
  1. Why is writer-surface narrowing still open? Because an adapter still decides how conversation context is preserved and merged on write.
  2. Why is that a problem? Because compatibility-layer adapters remain part of the active state-write authority instead of delegating write rules to governed core.
  3. Why does this persist? Because `_set_conversation_context(...)` still implements merge policy itself.
  4. Why does that matter after the projection-first cuts? Because every compatibility caller that updates conversation context still relies on adapter-local preservation behavior.
  5. Why has it not moved yet? Because prior Workstream 3 blocks first established the runtime journal/projection substrate and reader/session-memory demotions.
- Root cause statement:
  - Conversation-context write preservation still lives in `context_manager.py`, leaving a webhook adapter as the practical owner of compatibility write-shape rules.
- Fix mechanism:
  - Add a governed-core helper in `DialogStateService` that applies conversation-context preservation/trace-merge rules, then route `context_manager._set_conversation_context(...)` through that helper and cover the seam with deterministic regressions.

- Plan:
  1. Add a `DialogStateService` helper that applies conversation-context preservation and decision-trace merge rules.
  2. Replace adapter-local `_trace_*` / `_merge_decision_trace(...)` logic in `context_manager.py` with a thin delegate to the new core seam.
  3. Add deterministic regressions for simulation-field preservation and trace dedupe/merge behavior.
  4. Run focused writer/continuity checks and update repo truth.
- DoD:
  - adapter-local conversation-context merge logic is removed from `context_manager.py`
  - `DialogStateService` owns the preservation/merge rules
  - existing behavior for simulation keys and decision-trace dedupe is preserved
  - deterministic checks pass and `STATE.md` records the authority reduction truthfully
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "conversation_context or decision_trace or simulation"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "context_manager_expected_reply_getters"`
  - `python3 scripts/continuity_writer_guard.py`
  - `git diff --check`
- Evidence:
  - code diff
  - deterministic test output
  - `STATE.md` update after checks
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no new peer writer path
  - no semantic hardcode in core
  - no weakening of Workstream 1/2 guarantees
- Risks/blockers:
  - existing tests may implicitly depend on adapter-local helper names
  - other files may still import `_set_conversation_context(...)`, so the seam must stay backward-compatible while authority moves inward

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `context_manager.py` still exposes active compatibility write entrypoints
  - `state_service.py` and `pending.py` still own remaining continuity writes outside primary runtime substrate
- Why not in this block:
  - this family is limited to moving the write-shape rules, not deleting the compatibility entrypoints yet
- Risk if deferred:
  - compatibility writers stay spread across multiple files even after this authority move
- Linked follow-up Task Package(s):
  - follow-up W3 TP for `state_service.py` / `pending.py` writer narrowing
- Expiry/trigger to stop deferral:
  - stop deferral if new adapter-local context-write policy is added outside `DialogStateService`

## Next-block contract (mandatory)
- Next block objective:
  - narrow `state_service.py` and remaining compatibility writers so they emit only derived snapshots over the primary runtime substrate
- First deterministic check command:
  - `python3 scripts/continuity_writer_guard.py`
- Blocked-by conditions:
  - `context_manager.py` still owns conversation-context merge policy
  - no deterministic proof that core owns the preservation/trace-merge rules
- Owner role for closure:
  - Brain / Top Architect
