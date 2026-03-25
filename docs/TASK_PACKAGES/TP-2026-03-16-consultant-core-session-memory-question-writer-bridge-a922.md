# TP-2026-03-16-consultant-core-session-memory-question-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-QUESTION-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-QUESTION-CONTRACT-WRITER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после question-contract writer bridge: session-memory question bookkeeping must stop living in `truffles-api/app/routers/webhook/session_memory.py`. `DialogStateService` should become the owner of normalized writes for `last_question_type`, `unanswered_questions`, `pending_slots`, and `goal_stack`/`active_goal`, while `session_memory.py` stays a thin orchestration layer around context mutation, timestamps, trace/meta side effects, and reset gates.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '140,430p' truffles-api/app/routers/webhook/session_memory.py`
  - `sed -n '1,220p' truffles-api/app/core/dialog_state_service.py`
  - `rg -n "unanswered_questions|pending_slots|goal_stack|last_question_type|active_goal" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py`
  - `sed -n '8690,8765p' truffles-api/tests/test_message_endpoint.py`
  - `sed -n '9028,9112p' truffles-api/tests/test_message_endpoint.py`
  - `sed -n '28050,28220p' truffles-api/tests/test_message_endpoint.py`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns session-memory interaction-state projection but does not yet own question bookkeeping writes for `last_question_type`, `unanswered_questions`, `pending_slots`, `goal_stack`, or `active_goal`.
  - `session_memory.py` still shapes those fields directly in `_update_session_memory_on_question(...)`, `_update_session_memory_on_answer(...)`, `_clear_session_memory_expected_reply(...)`, and `_update_session_memory_goal(...)`.
  - The current session-memory write path is bounded and self-contained enough to move without touching frozen router files.
  - Message-endpoint compatibility tests already assert the externally visible effects of this seam for expected-reply clear, slot mismatch capture, and booking-check success paths.
- `Detected drift (docs vs code)`: strategy lock now points to single continuity writer completion, but session-memory question bookkeeping still has a local writer outside `DialogStateService`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python list copy method official documentation`
- **Date/time (local):** `2026-03-16 21:22 +0500`
- **Why this query is precise:** this block moves list/dict-backed question bookkeeping into `DialogStateService` and must preserve detached update semantics for `goal_stack`, `unanswered_questions`, and `pending_slots` without aliasing caller-owned containers.
- **Sources opened (from this query):**
  - `Built-in Types — list.copy()` — `https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types`
- **Source quality:** official Python documentation.
- **Existing solutions found:** shallow list copying is the standard baseline for detached list updates when the elements are immutable strings; combined with dict copies, it is sufficient for this bounded writer slice.
- **Decision:** `reuse + integrate` — keep detached copy semantics in service helpers for list/dict question bookkeeping instead of custom mutation helpers.
- **Rejected options:**
  - leaving question bookkeeping writes in `session_memory.py`
  - widening this block into reset orchestration or broader state-restore ownership
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** session-memory question bookkeeping is still shaped directly in `session_memory.py`, so `DialogStateService` is not yet the single writer for this live continuity seam.
- **Minimal reproduction:**
  1. Call `_update_session_memory_on_question(...)` with `expected_reply_type="time"` and `active_goal="booking"`.
  2. Observe that `session_memory.py` appends `unanswered_questions`, updates `goal_stack`, `active_goal`, and `last_question_type` locally.
  3. Call `_update_session_memory_on_answer(...)` or `_clear_session_memory_expected_reply(...)` and observe that `pending_slots` and `unanswered_questions` are also shaped locally instead of via `DialogStateService`.
- **Evidence to capture:**
  - `DialogStateService` directly shapes normalized session-memory question bookkeeping payloads.
  - `session_memory.py` becomes orchestration-only for these writes.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented here? Because only interaction-state projection was moved into `DialogStateService`; question bookkeeping stayed local.
  2. Why is that a problem? Because one live continuity surface still has multiple shaping authorities.
  3. Why can this block be bounded? Because the affected writes are local to `session_memory.py` and operate on simple list/dict fields with existing compatibility tests.
  4. Why not widen into reset/state-restore logic? Because that mixes a clean writer-collapse seam with broader orchestration semantics and risks another partial cut.
  5. Why fix this now? Because the current strategy lock prefers real writer deletion over new semantic seams when the next semantic slice would widen.
- **Root cause statement:** the session-memory question lifecycle still lets `session_memory.py` shape `last_question_type`, `unanswered_questions`, `pending_slots`, and `goal_stack`/`active_goal` directly, so `DialogStateService` is not yet the single shaping authority for this continuity seam.
- **Fix mechanism:**
  - add bounded session-memory question-bookkeeping helpers to `DialogStateService`
  - replace local shaping in `session_memory.py` with thin delegation
  - prove parity with focused unit tests and targeted message-endpoint compatibility checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_get_session_memory(...)` / `_set_session_memory(...)` orchestration in `session_memory.py`
  - existing `DialogStateService` detached-copy patterns and normalization helpers
  - existing message-endpoint compatibility tests that assert this seam’s visible effects
- **External reuse:**
  - official Python list-copy semantics from the standard library docs
- **Why not reinvent the wheel:** this block is ownership consolidation, not a new memory subsystem.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity-writer collapse with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- External session-memory behavior stays unchanged for existing booking/info flows.
- Detached update semantics for lists/dicts are preserved.

## Scope
- Add bounded session-memory question-bookkeeping helpers to `DialogStateService`.
- Make `session_memory.py` delegate these writes to the service.
- Add regression tests for the new service ownership and reuse existing compatibility tests.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- broader reset/state-restore logic
- new semantic owner cutovers
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-question-writer-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add bounded session-memory question-bookkeeping helpers to `DialogStateService`.
3. Replace local shaping in `session_memory.py` with thin delegation.
4. Add focused service tests and rerun targeted message-endpoint compatibility checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns normalized writes for session-memory question bookkeeping in this seam.
- `session_memory.py` stays orchestration-only for these writes.
- tests prove parity for question, answer, clear, and goal updates.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'expected_reply_contract_bypasses_human_request or expected_reply_time_slot_mismatch_captures_alternate_name_without_clearing_time or test_llm_policy_core_get_booking_ok_clears_expected_reply_contract_without_escalation'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- unit tests showing service-owned session-memory question bookkeeping writes
- targeted message-endpoint checks showing booking/info compatibility is unchanged
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires reset/state-restore widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helpers, session-memory delegation, tests, and doc sync
- **Post-release monitoring window:** next block should continue writer collapse or return to owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the session-memory question writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, session-memory delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into reset/state-restore orchestration
- no counting this block as done unless `session_memory.py` loses local question-bookkeeping shaping authority

## Risks / blockers
- if service helpers mutate caller-owned list/dict payloads in place, the block introduces aliasing regressions.
- if the block accidentally changes timestamp/orchestration behavior instead of only shaping ownership, compatibility drift can leak into booking/info flows.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this session-memory question seam
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded writer-collapse slice; widening further would mix session-memory question bookkeeping with broader reset/state-restore semantics
- **Risk if deferred:**
  - session-memory drift remains possible because question-bookkeeping authority stays split
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-next-seam-a922` (planned)
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next block needs another session-memory-local writer workaround for question bookkeeping fields

## Next-block contract (mandatory)
- **Next block objective:** either delete the next bounded continuity writer seam after session-memory question bookkeeping or return to richer owner-replacement work only if it deletes an old semantic authority without new bridge growth.
- **First deterministic check command:** `python3 scripts/continuity_writer_guard.py`
- **Blocked-by conditions:** reset/state-restore widening, frozen-router edits, or any need to grow generic semantic bridge families
- **Owner role for closure:** `Top Architect`
