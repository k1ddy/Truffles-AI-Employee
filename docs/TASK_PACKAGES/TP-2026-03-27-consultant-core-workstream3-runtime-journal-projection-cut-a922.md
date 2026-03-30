# TP-2026-03-27-consultant-core-workstream3-runtime-journal-projection-cut-a922

- Title/goal: Introduce `TurnJournalV1` + `ConversationProjectionV1` as the primary runtime state substrate on the active `consultant_runtime` path, while keeping `dialog_state` and `context_manager` as derived compatibility views.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- Invariant:
  - Workstream 1 and 2 guarantees stay intact: one semantic owner, typed binding boundary, no post-owner semantic rewrite on the active path.
- Scope:
  - Add runtime-local `TurnJournalV1` and `ConversationProjectionV1` artifacts.
  - Make runtime reads prefer `ConversationProjectionV1` over peer compatibility carriers.
  - Keep `dialog_state`, `canonical_dialog_state`, top-level expected-reply fields, and `pending_resume` as derived migration surfaces in this block.
- Out of scope:
  - Full legacy mesh strangler.
  - DB-backed journal persistence.
  - Full removal of `session_memory` / `pending_resume`.
  - Full Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/__init__.py`
  - `truffles-api/app/core/turn_journal.py`
  - `truffles-api/app/core/conversation_projection.py`
  - `contracts/runtime/turn_journal.v1.jsonschema`
  - `contracts/runtime/conversation_projection.v1.jsonschema`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com CQRS event sourcing materialized view projection append-only journal`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - write model and read model should stay separated
  - materialized view can serve as the read model
  - event store can be the single source of truth, with projection rebuilt from events
  - snapshots/projections reduce replay cost
- Decision: `integrate/build`
- Why:
  - The repo already has a runtime-local append-only semantic log and compatibility projections, but no first-class journal/projection artifacts. Reuse the current state writer logic and formalize it into explicit journal/projection contracts instead of importing a new framework.
- Rejected variants:
  - external event-sourcing framework: rejected, too large for this bounded block
  - keeping `dialog_state` as the primary read model: rejected, preserves peer truth-carriers

## Root cause (mandatory)
- Symptom:
  - canonical state unification is still blocked after Workstream 1 and 2.
- Minimal reproduction:
  - `DialogStateService.project_context_pending_question_contract(...)` and `DialogStateService.project_context_current_goal(...)` still resolve state through fallback chains across runtime payload, `context_manager.canonical_dialog_state`, `session_memory`, top-level expected-reply fields, and top-level `current_goal`.
- Evidence:
  - `truffles-api/app/core/dialog_state_service.py:1260`
  - `truffles-api/app/core/dialog_state_service.py:1389`
  - `truffles-api/app/routers/webhook/context_manager.py:57`
  - `docs/LEGACY_SUNSET.yaml:371`
- Five whys:
  1. Why is W3 blocked? Because the runtime has multiple live current-state carriers.
  2. Why do multiple carriers stay live? Because `dialog_state` is not a first-class canonical projection and `canonical_dialog_state` remains an independent continuity store.
  3. Why is `dialog_state` not enough? Because it is both a runtime payload and a compatibility payload, and readers still fall back outside it.
  4. Why do readers fall back outside it? Because no explicit `TurnJournalV1` / `ConversationProjectionV1` artifacts exist on the active path.
  5. Why do those artifacts not exist? Because prior cuts focused on semantic ownership and binding, not state substrate extraction.
- Root cause statement:
  - The active runtime still lacks explicit canonical journal/projection artifacts, so state readers continue to consult multiple peer continuity surfaces.
- Fix mechanism:
  - Introduce explicit runtime `TurnJournalV1` and `ConversationProjectionV1`, write them in the canonical state writer, and switch runtime/context projections to read projection-first while deriving compatibility surfaces from that projection.

- Plan:
  1. Add typed `TurnJournalV1` and `ConversationProjectionV1` models plus runtime schemas.
  2. Extend the canonical state writer to append bounded journal events and emit a primary projection.
  3. Make runtime loads and context projections read projection-first.
  4. Keep legacy carriers derived-only on this path.
  5. Add deterministic contract/regression coverage.
- DoD:
  - `consultant_runtime` payload contains typed `turn_journal` and `conversation_projection`.
  - Runtime loads and projections prefer `conversation_projection` over peer legacy carriers.
  - `dialog_state` remains present only as a derived compatibility view on that path.
  - Deterministic tests prove append-only journal growth and projection-first reads.
- Checks:
  - `python3 -m py_compile truffles-api/app/core/turn_journal.py truffles-api/app/core/conversation_projection.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "turn_journal or conversation_projection or projection_first or canonical_state"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "turn_journal or conversation_projection or projection_first or append_only"`
  - `git diff --check`
- Evidence:
  - code diff
  - deterministic test output
  - `STATE.md` update after checks
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no new peer current-state store
  - no semantic hardcode in runtime core
  - no demotion of Workstream 1/2 invariants
- Risks/blockers:
  - large compatibility surface around `context_manager`, `session_memory`, and `pending_resume`
  - projection drift if compatibility views are not explicitly derived from the new projection

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `context_manager.canonical_dialog_state` still exists
  - `session_memory` and `pending_resume` still exist
  - legacy webhook readers still consume compatibility views
- Why not in this block:
  - this block only establishes the primary runtime substrate and primary read path
- Risk if deferred:
  - peer-carrier residue continues outside the active runtime path until follow-up migration cuts land
- Linked follow-up Task Package(s):
  - follow-up W3 compatibility-reader demotion TP (to be opened after this block)
- Expiry/trigger to stop deferral:
  - stop deferral if any new runtime read path consumes legacy state before projection-first read

## Next-block contract (mandatory)
- Next block objective:
  - demote `context_manager` / `reasoning_core` / timeout boundary readers to derived `ConversationProjectionV1` reads only
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "projection_first or context_projection"`
- Blocked-by conditions:
  - no explicit `ConversationProjectionV1` written on active runtime path
  - no append-only `TurnJournalV1` evidence
- Owner role for closure:
  - Brain / Top Architect
