# TP-2026-03-27-consultant-core-workstream3-state-service-writer-allowlist-collapse-a922

- Title/goal: Remove the remaining guarded continuity-writer status from `state_service.py` and `pending.py` by pushing pending-resume snapshot/write shape rules into governed core and shrinking the continuity allowlist.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
  - `docs/LEGACY_SUNSET.yaml`
- Invariant:
  - Workstream 1/2 guarantees stay intact, and Workstream 3 keeps the primary runtime substrate stronger than compatibility snapshot writers.
- Scope:
  - Move state-service pending-resume snapshot/context-write shape rules into `DialogStateService`.
  - Rework `state_service.py` to use governed-core snapshot/write helpers instead of directly authoring guarded continuity tokens.
  - Remove `pending.py` and `state_service.py` from the continuity-writer allowlist if deterministic proof shows they no longer own guarded writes.
- Out of scope:
  - Removing `context_manager.py` as a compatibility entrypoint.
  - Reworking handover business flow beyond continuity write ownership.
  - Workstream 3 closeout.
- Touch-list:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `docs/LEGACY_SUNSET.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com/en-us/azure/architecture/patterns/cqrs CQRS pattern materialized view read model`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - the write model should own updates while read/compatibility models stay derived/materialized
  - write/read bridging should be explicit instead of spread across multiple adapters/services
  - materialized views are useful during migration, but should not act like peer mutable stores
- Decision: `integrate/build`
- Why:
  - the repo already has governed core state seams in `DialogStateService`; this block moves remaining continuity snapshot/write rules there and demotes compatibility services to delegates.
- Rejected variants:
  - keep `state_service.py` on the continuity allowlist: rejected, preserves compatibility-writer authority
  - delete pending-resume helpers outright: rejected, too broad for this bounded block

## Root cause (mandatory)
- Symptom:
  - `Workstream 3` remains open because `state_service.py` still counts as an allowed guarded continuity writer, and `pending.py` remains allowlisted despite no longer owning direct guarded writes.
- Minimal reproduction:
  - removing `truffles-api/app/services/state_service.py` from `docs/LEGACY_SUNSET.yaml` currently trips `continuity_writer_guard` on four lines: two direct `conversation.context = ...` assignments bound to pending-resume helpers and two direct `snapshot_context["expected_reply_*"] = ...` writes in `_build_pending_resume_snapshot_payload(...)`.
  - removing `truffles-api/app/routers/webhook/pending.py` from the allowlist yields zero guard violations, which means it is stale allowlist residue.
- Evidence:
  - `truffles-api/app/services/state_service.py:616`
  - `truffles-api/app/services/state_service.py:652`
  - `truffles-api/app/services/state_service.py:677`
  - `truffles-api/app/services/state_service.py:678`
  - temporary guard evaluation without allowlist entries: `state_service.py -> 4 violations`, `pending.py -> 0 violations`
- Five whys:
  1. Why is the writer allowlist still larger than desired? Because `state_service.py` still authors pending-resume snapshot/context shape locally.
  2. Why is that a problem? Because a compatibility service remains part of the guarded continuity write authority instead of delegating fully to governed core.
  3. Why does `pending.py` still appear there? Because the allowlist was not narrowed after prior refactors removed its direct guarded writes.
  4. Why does `state_service.py` still violate the guard? Because it still builds snapshot payloads with direct guarded token writes and assigns helper-returned contexts to `conversation.context`.
  5. Why has that not been removed yet? Because earlier Workstream 3 blocks first established projection-first state, then reader/session-memory/context-manager demotions.
- Root cause statement:
  - Pending-resume compatibility write shape is still partially authored in `state_service.py`, and the continuity allowlist still carries stale entries that no longer reflect real guarded writer ownership.
- Fix mechanism:
  - Move pending-resume snapshot/context-write shape helpers into `DialogStateService`, route `state_service.py` through those governed seams, and shrink the continuity allowlist to reflect the actual remaining writer surface.

- Plan:
  1. Add governed-core helpers for pending-resume snapshot context building and normalized state-service context writes.
  2. Rework `state_service.py` to use those helpers instead of direct guarded token writes / helper-bound context assignments.
  3. Remove stale `pending.py` and, if the guard is clean, `state_service.py` from `docs/LEGACY_SUNSET.yaml`.
  4. Add deterministic regressions for the new governed seams and allowlist shrink.
  5. Run continuity/architecture checks and update repo truth.
- DoD:
  - `state_service.py` no longer needs to be in `continuity_guard.allowed_writer_paths`
  - `pending.py` is removed from the allowlist
  - pending-resume snapshot payload semantics are preserved
  - deterministic checks pass and repo truth reflects the narrowed writer surface
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or preserve_context or simulation"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
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
  - `test_state_service.py` covers old helper boundaries heavily; helper names may need to stay stable while internals move
  - allowlist removal must be backed by the guard, not by narrative

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `context_manager.py` still remains an allowed continuity writer
  - handover/reminder services still perform direct `conversation.context` writes outside this block
- Why not in this block:
  - this family is limited to pending-resume compatibility writer collapse and allowlist truth
- Risk if deferred:
  - remaining compatibility writers stay wider than the target single primary substrate
- Linked follow-up Task Package(s):
  - follow-up W3 TP for final continuity writer narrowing outside governed core
- Expiry/trigger to stop deferral:
  - stop deferral if a new continuity writer is added to the allowlist or `state_service.py` regains guarded writes

## Next-block contract (mandatory)
- Next block objective:
  - narrow the last remaining compatibility writer entrypoints outside governed core, starting with `context_manager.py` allowlist removal or explicit quarantine of the remaining direct writers
- First deterministic check command:
  - `python3 scripts/continuity_writer_guard.py`
- Blocked-by conditions:
  - `state_service.py` still trips the continuity guard without allowlist exemptions
  - no deterministic proof that `pending.py` and `state_service.py` can be removed from the allowlist
- Owner role for closure:
  - Brain / Top Architect
