# TP-2026-03-27-consultant-core-workstream3-pending-resume-derived-writer-cut-a922

- Title/goal: Narrow the remaining compatibility writer surface by making pending-resume snapshots/restores derive `context_manager` and `session_memory` from the primary runtime projection/state instead of copying peer legacy carriers as-is.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- Invariant:
  - Workstream 1 and 2 guarantees stay intact, and Workstream 3 keeps `ConversationProjectionV1` as the strongest read model on the active/runtime-derived path.
- Scope:
  - Rework pending-resume capture/restore so `context_manager` and `session_memory` snapshots are derived from runtime projection/state when available.
  - Preserve legacy fallback behavior only when no explicit runtime projection/state exists.
- Out of scope:
  - Removing `context_manager`, `session_memory`, or `pending_resume` writers completely.
  - Reworking all pre-runtime compatibility writers in one block.
  - Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_pending_pack_lexicons.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com CQRS single write model materialized view derived compatibility migration write model`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - a single write model should feed the read model
  - compatibility/read consumers should be materialized/derived from the primary model instead of acting like peer mutable truths
  - projections/materialized views can preserve compatibility during migration
- Decision: `integrate/build`
- Why:
  - The repo already has runtime `conversation_projection`; this block converts pending-resume snapshots/restores into derived compatibility artifacts rather than another peer continuity truth surface.
- Rejected variants:
  - keep pending-resume snapshots as raw copies of `context_manager` / `session_memory`: rejected, preserves peer writer debt
  - remove pending-resume entirely in one step: rejected, too large for this bounded block

## Root cause (mandatory)
- Symptom:
  - Workstream 3 still has live compatibility writer debt in `pending_resume` capture/restore.
- Minimal reproduction:
  - `DialogStateService.capture_pending_resume_payload(...)` copies `context_manager` / `session_memory` snapshots directly.
  - `DialogStateService.restore_pending_resume_payload(...)` restores those legacy stores directly.
  - If explicit runtime projection exists, stale compatibility state can still become the stored continuity snapshot.
- Evidence:
  - `truffles-api/app/core/dialog_state_service.py:3848`
  - `truffles-api/app/core/dialog_state_service.py:3925`
  - `truffles-api/app/services/state_service.py:590`
  - `truffles-api/app/services/state_service.py:608`
- Five whys:
  1. Why is writer-surface narrowing still open? Because pending-resume still snapshots and restores peer compatibility stores.
  2. Why is that a problem? Because it preserves a second continuity-writing plane beside runtime projection/state.
  3. Why can stale state leak in? Because capture/restore copy legacy carriers directly instead of deriving them from runtime state.
  4. Why do those copies matter? Because pending-resume is later used to reactivate continuity and can reintroduce stale fields.
  5. Why has it not been fixed yet? Because earlier W3 cuts established projection-first reads, not writer derivation.
- Root cause statement:
  - Pending-resume capture/restore still writes compatibility state as raw peer snapshots instead of deriving those compatibility views from the primary runtime projection/state.
- Fix mechanism:
  - Add derived snapshot builders for `context_manager` and `session_memory`, use them in pending-resume capture/restore, and only fall back to raw legacy carriers when no explicit runtime projection/state exists.

- Plan:
  1. Add derived compatibility snapshot helpers in `DialogStateService` for `context_manager` and `session_memory`.
  2. Rework pending-resume capture to store derived compatibility views.
  3. Rework pending-resume restore to rebuild compatibility views from the stored derived snapshot.
  4. Add deterministic regressions for projection-first pending-resume capture/restore.
  5. Update repo truth.
- DoD:
  - pending-resume capture prefers runtime projection/state over stale compatibility carriers.
  - pending-resume restore rebuilds `context_manager` / `session_memory` from derived compatibility snapshots.
  - legacy fallback remains only when explicit runtime projection/state is absent.
  - deterministic tests prove projection-first snapshot/restore behavior.
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_pending_pack_lexicons.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or session_memory or context_manager"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
  - `git diff --check`
- Evidence:
  - code diff
  - deterministic test output
  - `STATE.md` update after checks
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no new peer state store
  - no weakening of Workstream 1/2 invariants
  - no semantic hardcode in runtime core
- Risks/blockers:
  - pending-resume tests may rely on legacy copy semantics
  - some compatibility-only paths may still not carry explicit runtime projection

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `build_expected_reply_context_sync_result(...)` still writes compatibility stores directly on some pre-runtime paths
  - `context_manager` and `session_memory` still exist as live compatibility writers
- Why not in this block:
  - this block is limited to the `pending_resume` writer family
- Risk if deferred:
  - other compatibility write paths can still bypass the primary runtime substrate
- Linked follow-up Task Package(s):
  - follow-up W3 compatibility-writer narrowing TP for pre-runtime expected-reply/session-memory writers
- Expiry/trigger to stop deferral:
  - stop deferral if any new pending-resume or continuity snapshot bypasses the derived helpers

## Next-block contract (mandatory)
- Next block objective:
  - narrow pre-runtime compatibility writers (`context_manager` / `session_memory`) so expected-reply mutations are also derived or explicitly bounded
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "pending_resume or expected_reply_contract or session_memory"`
- Blocked-by conditions:
  - pending-resume snapshot/restore still copies stale compatibility state when explicit runtime projection exists
  - no deterministic proof that derived snapshot/restore works
- Owner role for closure:
  - Brain / Top Architect
