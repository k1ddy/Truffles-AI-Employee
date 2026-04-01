# TP-2026-03-27-consultant-core-workstream3-closeout-proof-pass-a922

- Title/goal: Run the deterministic closeout proof for Workstream 3 and freeze the continuity-writer truth so `TurnJournalV1 + ConversationProjectionV1` can be marked as the only canonical semantic state substrate on the active runtime path.
- Canon refs:
  - `STATE.md` NOW
  - `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `docs/system_forensics/final/TURN_JOURNAL_V1.md`
  - `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
  - `docs/LEGACY_SUNSET.yaml`
- Invariant:
  - Workstream 1 and 2 guarantees stay intact; closure proof must not relax any guard or reintroduce compatibility writer authority.
- Scope:
  - Add one exact architecture guard that the continuity allowlist now points only at governed core.
  - Replay a deterministic proof envelope against the four Workstream 3 completion criteria.
  - Update repo truth and close Workstream 3 if the proof is green.
- Out of scope:
  - Reworking non-guarded direct `conversation.context` writes outside the continuity-guard token set.
  - Starting Workstream 4 implementation.
- Touch-list:
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream3-closeout-proof-pass-a922.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: closure

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com/en-us/azure/architecture/patterns/cqrs CQRS pattern materialized view read model`
- Date/time: 2026-03-27 Asia/Almaty
- Opened sources:
  - Microsoft Learn, `CQRS pattern`: `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Found reusable guidance:
  - the write side should stay the single source of truth
  - read/materialized views can remain for migration but should be query/projection surfaces, not peer mutable stores
  - closure should be based on explicit separation of read/write responsibilities
- Decision: `integrate`
- Why:
  - this closeout pass is exactly about proving the repo now matches a single write substrate plus derived read/compatibility surfaces.
- Rejected variants:
  - close Workstream 3 by narrative only: rejected, closure must be evidence-backed

## Root cause (mandatory)
- Symptom:
  - Workstream 3 implementation is likely complete, but it still lacks an explicit deterministic closeout proof pass and a final guard that the continuity allowlist has collapsed to governed core only.
- Minimal reproduction:
  - `TurnJournalV1` and `ConversationProjectionV1` already exist and are used by runtime/state services, and the continuity allowlist now only contains governed-core entries; however, no single closure artifact yet records that all four completion criteria are green together.
- Evidence:
  - `truffles-api/app/core/dialog_state_service.py:3509`
  - `truffles-api/app/core/dialog_state_service.py:1499`
  - `docs/LEGACY_SUNSET.yaml:371`
  - prior Workstream 3 TPs in `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream3-*`
- Five whys:
  1. Why is Workstream 3 still open? Because the repo truth has not yet recorded a final proof against all four criteria.
  2. Why is that needed? Because architectural closure must be backed by deterministic evidence, not by accumulated narrative.
  3. Why is the guard still slightly weak? Because there is no exact assertion yet that the continuity allowlist now points only to governed core.
  4. Why does that matter? Because a future stale exemption could silently re-expand compatibility writer authority.
  5. Why now? Because the implementation cuts have already collapsed the allowlist and moved projection/journal logic into core.
- Root cause statement:
  - Workstream 3 lacks a final proof artifact and one exact guard that the continuity-writer boundary has fully collapsed to governed core.
- Fix mechanism:
  - Add the exact guard, run the deterministic proof envelope, and record the closeout decision in repo truth.

- Plan:
  1. Add an architecture guard that `continuity_guard.allowed_writer_paths` equals only `truffles-api/app/core/dialog_state_service.py`.
  2. Run the deterministic closure envelope for journal append law, projection-first runtime reads, derived compatibility surfaces, and continuity-writer truth.
  3. Update repo truth and mark Workstream 3 `done` if all checks are green.
- DoD:
  - exact continuity allowlist guard exists
  - deterministic closure envelope is green
  - `STATE.md` records Workstream 3 as `done` if the proof passes
- Checks:
  - `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/state_service.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_state_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "conversation_projection or turn_journal or session_memory or pending_resume"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "turn_journal or conversation_projection or append_only or semantic_state_log"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or preserve_context or simulation"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "conversation_projection or pending_resume or session_memory"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "context_manager_expected_reply_getters"`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer or context_manager or pending_and_state_service or only_dialog_state_service"`
  - `python3 scripts/continuity_writer_guard.py`
  - `git diff --check`
- Evidence:
  - deterministic test output
  - code diff for the exact guard
  - `STATE.md` closure record
- Rollback:
  - revert this TP patchset from branch
- No-go:
  - no reopening of already-removed compatibility writer authority
  - no claim of closure without the proof envelope green
- Risks/blockers:
  - if any closure criterion is still red, Workstream 3 remains `open` and the failure becomes the next bounded block instead of a narrative close

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - non-guarded direct `conversation.context` writes still exist in some services outside the continuity-guard token set
- Why not in this block:
  - Workstream 3 scope is canonical semantic state unification, not every remaining operational context write in the repo
- Risk if deferred:
  - future work may still need a separate hygiene/strangler block for non-semantic direct context writers
- Linked follow-up Task Package(s):
  - Workstream 4 TP, or a final non-guarded context-writer quarantine TP if closure fails
- Expiry/trigger to stop deferral:
  - stop deferral if any of those writers start carrying semantic/current-state authority again

## Next-block contract (mandatory)
- Next block objective:
  - start Workstream 4 if closure passes; otherwise open exactly one bounded final W3 remediation block from the failed criterion
- First deterministic check command:
  - `python3 scripts/continuity_writer_guard.py`
- Blocked-by conditions:
  - closure envelope not fully green
  - exact continuity allowlist guard not in place
- Owner role for closure:
  - Brain / Top Architect
