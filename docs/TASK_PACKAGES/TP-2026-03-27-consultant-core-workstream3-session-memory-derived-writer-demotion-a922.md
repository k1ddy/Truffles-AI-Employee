# TP-2026-03-27-consultant-core-workstream3-session-memory-derived-writer-demotion-a922

- Title/goal: Narrow the remaining pre-runtime compatibility writer surface by making active `session_memory` mutations rebuild from projection-first state and by removing dormant session-memory writer helpers from app runtime.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
  - `docs/LEGACY_SUNSET.yaml`
- Invariant:
  - Workstream 1 and 2 guarantees stay intact, and Workstream 3 keeps `ConversationProjectionV1` as the strongest active/runtime-derived continuity source.
- Scope:
  - Rebuild active `session_memory` answer/goal/clear mutations from projection-first context instead of letting `session_memory` keep writing duplicated `active_goal`, `goal_stack`, `pending_question_contract`, and `interaction_state` ad hoc.
  - Remove dormant app-runtime session-memory writer helpers that are only used by tests.
  - Shrink the continuity-writer allowlist if `session_memory.py` no longer owns guarded continuity writes.
- Out of scope:
  - Removing `pending_resume` or `context_manager` writer paths.
  - Full `decision.py` strangler work.
  - Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `docs/LEGACY_SUNSET.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com materialized view derived compatibility read model CQRS write model migration`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - write-side state should remain the single authority
  - read/compatibility models should be materialized from the authoritative substrate instead of acting like peer mutable stores
  - compatibility projections can stay during migration, but they should be derived views
- Decision: `integrate/build`
- Why:
  - The repo already has `conversation_projection`; this block converts `session_memory` into a more purely derived compatibility view rather than a peer continuity author.
- Rejected variants:
  - keep active session-memory writes ad hoc: rejected, preserves peer continuity authority
  - delete `session_memory` in one cut: rejected, too broad for this bounded block

## Root cause (mandatory)
- Symptom:
  - Workstream 3 remains open because `session_memory` still writes continuity fields that should be projection-derived, and dormant writer helpers still live in app runtime.
- Minimal reproduction:
  - `session_memory.py` updates `active_goal`, `goal_stack`, answer state, and expected-reply cleanup by mutating `session_memory` directly after other context writes.
  - `build_context_session_memory_snapshot(...)` already knows how to derive `active_goal`, `pending_question_contract`, and `interaction_state` from runtime/context projection, but active writer paths do not reuse that seam.
  - dormant helpers `_reset_session_memory(...)` / `_sync_session_memory_interaction_state(...)` still live under `app/routers/webhook/session_memory.py` even though app runtime does not call them.
- Evidence:
  - `truffles-api/app/routers/webhook/session_memory.py:59`
  - `truffles-api/app/routers/webhook/session_memory.py:125`
  - `truffles-api/app/routers/webhook/session_memory.py:180`
  - `truffles-api/app/routers/webhook/session_memory.py:215`
  - `truffles-api/app/core/dialog_state_service.py:1977`
- Five whys:
  1. Why is writer-surface narrowing still open? Because `session_memory` continues to author continuity fields after projection-first reader cuts.
  2. Why is that a problem? Because `session_memory` remains a peer continuity store instead of a derived compatibility view.
  3. Why can it drift? Because active writer paths mutate memory payloads directly instead of rebuilding them from current projection/state.
  4. Why do dormant helpers matter? Because they preserve additional writer entrypoints inside app runtime, which keeps the writer surface larger than necessary.
  5. Why has it not been fixed yet? Because prior W3 blocks focused on primary substrate introduction, reader demotion, and pending-resume derivation first.
- Root cause statement:
  - Active and dormant `session_memory` helpers still let compatibility memory behave like a peer writer instead of a derived projection of the primary runtime/state substrate.
- Fix mechanism:
  - Add a projection-first session-memory rebuild seam in `DialogStateService`, route active session-memory updates through it, move dormant writer helpers out of app runtime, and shrink the continuity-writer allowlist if the file no longer owns guarded writes.

- Plan:
  1. Add a `DialogStateService` helper that rebuilds `session_memory` from context/projection plus bounded local deltas.
  2. Rework active `session_memory` answer/goal/clear helpers to use that rebuild seam.
  3. Move dormant `_reset_session_memory(...)` / `_sync_session_memory_interaction_state(...)` helpers to test-only support and drop unused imports from `decision.py`.
  4. Narrow `docs/LEGACY_SUNSET.yaml` writer allowlist if `session_memory.py` is no longer a live guarded writer.
  5. Add deterministic regressions and update repo truth.
- DoD:
  - active `session_memory` updates rebuild from projection-first state
  - stale `session_memory.active_goal` / `pending_question_contract` do not win when context projection disagrees
  - dormant session-memory writer helpers are no longer in app runtime
  - continuity-writer guard can drop `truffles-api/app/routers/webhook/session_memory.py` from the allowlist without regressions
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "session_memory or expected_reply or pending_resume"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
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
  - targeted tests may encode stale session-memory shape assumptions
  - some dormant helper expectations may need to move into test-only support

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `context_manager.py` and `pending.py` still own continuity writes outside the primary runtime substrate
  - `state_service.py` still owns active `pending_resume` write paths
- Why not in this block:
  - this block is limited to the session-memory writer family
- Risk if deferred:
  - compatibility continuity writes remain spread across multiple files
- Linked follow-up Task Package(s):
  - follow-up W3 TP for `context_manager` / `state_service` writer-surface narrowing
- Expiry/trigger to stop deferral:
  - stop deferral if any new session-memory-like compatibility writer appears outside `DialogStateService`

## Next-block contract (mandatory)
- Next block objective:
  - narrow `context_manager` and `state_service` writers so only bounded derived compatibility snapshots remain outside the primary runtime substrate
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or context_manager or session_memory"`
- Blocked-by conditions:
  - `session_memory.py` still owns guarded continuity writes
  - no deterministic proof that active session-memory writes rebuild from projection-first state
- Owner role for closure:
  - Brain / Top Architect
