# TP-2026-03-27-consultant-core-workstream3-context-manager-allowlist-removal-a922

- Title/goal: Remove stale continuity-writer allowlist status from `context_manager.py` now that guarded continuity tokens are already authored through governed core seams.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
  - `docs/LEGACY_SUNSET.yaml`
- Invariant:
  - Workstream 3 keeps governed core as the only active owner of guarded continuity token shaping, and no compatibility file regains direct guarded-write authority.
- Scope:
  - Remove `truffles-api/app/routers/webhook/context_manager.py` from `continuity_guard.allowed_writer_paths`.
  - Add deterministic proof that the guard remains clean without that exemption.
  - Record repo truth for the narrowed allowlist.
- Out of scope:
  - Removing the `_set_conversation_context(...)` compatibility entrypoint itself.
  - Reworking non-guarded `conversation.context` writes in other services.
  - Workstream 3 closeout.
- Touch-list:
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com CQRS read model derived compatibility migration single writer`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - write operations should stay on the write side
  - read/compatibility models can remain during migration, but should be derived/materialized and not treated as peer writers
  - once a compatibility surface stops owning writes, its special write exemption should be removed
- Decision: `integrate`
- Why:
  - this block is exactly an allowlist-truth correction after prior governed-core extractions
- Rejected variants:
  - keep `context_manager.py` on the allowlist “just in case”: rejected, leaves stale authority metadata and weakens the guard

## Root cause (mandatory)
- Symptom:
  - `context_manager.py` still appears in `continuity_guard.allowed_writer_paths` even though the current continuity guard no longer detects any guarded-token writes in that file when the exemption is removed.
- Minimal reproduction:
  - remove `truffles-api/app/routers/webhook/context_manager.py` from the allowlist in a temporary config copy and evaluate `scripts/continuity_writer_guard.py`; result is zero violations for that path.
- Evidence:
  - temporary guard evaluation without the allowlist entry -> `count 0`
  - `truffles-api/app/routers/webhook/context_manager.py` now delegates context-write preservation to `DialogStateService.prepare_conversation_context_write(...)`
- Five whys:
  1. Why is the allowlist still larger than desired? Because it still carries an old exemption for `context_manager.py`.
  2. Why is that wrong? Because the guard should describe real guarded-writer authority, not historical status.
  3. Why is the exemption stale now? Because prior Workstream 3 cuts moved expected-reply/session-memory/context-shape rules into `DialogStateService`.
  4. Why does this matter? Because stale exemptions weaken the continuity guard and hide regression risk.
  5. Why has it not been removed yet? Because the previous blocks focused on moving the write logic first, not on cleaning the metadata after the move.
- Root cause statement:
  - The continuity allowlist was not reduced after `context_manager.py` stopped owning guarded continuity-token writes.
- Fix mechanism:
  - Remove the stale allowlist entry, add a regression that keeps it removed, and re-run the continuity guard as proof.

- Plan:
  1. Remove `context_manager.py` from `docs/LEGACY_SUNSET.yaml`.
  2. Add an architecture regression asserting it is no longer allowlisted.
  3. Run the continuity guard and focused architecture tests.
  4. Update repo truth.
- DoD:
  - `context_manager.py` is no longer in `continuity_guard.allowed_writer_paths`
  - deterministic proof shows the guard stays green without that exemption
  - repo truth reflects that only governed core remains on the allowlist
- Checks:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer or context_manager"`
  - `python3 scripts/continuity_writer_guard.py`
  - `git diff --check`
- Evidence:
  - code diff
  - deterministic test output
  - `STATE.md` update after checks
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no new compatibility exemption
  - no semantic/state authority moved out of governed core
- Risks/blockers:
  - if the guard starts reporting new `context_manager.py` violations, the block stops and the exemption stays until the actual root cause is fixed

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - many services still perform direct `conversation.context` writes outside the continuity-guard token set
  - compatibility entrypoints still exist even after their guarded-write status is removed
- Why not in this block:
  - this block is limited to allowlist truth, not to every remaining direct context write in the app
- Risk if deferred:
  - stale exemptions keep the architecture guard weaker than the actual code state
- Linked follow-up Task Package(s):
  - follow-up W3 closeout/proof pass or final direct-context-writer quarantine block
- Expiry/trigger to stop deferral:
  - stop deferral if any new compatibility file requests an allowlist exemption without fresh guard evidence

## Next-block contract (mandatory)
- Next block objective:
  - decide whether Workstream 3 can close on continuity-guard truth or whether a final block is needed to quarantine remaining non-guarded direct `conversation.context` writers
- First deterministic check command:
  - `python3 scripts/continuity_writer_guard.py`
- Blocked-by conditions:
  - the guard reports new `context_manager.py` violations once the exemption is removed
  - no deterministic proof that the allowlist now matches actual guarded writer ownership
- Owner role for closure:
  - Brain / Top Architect
