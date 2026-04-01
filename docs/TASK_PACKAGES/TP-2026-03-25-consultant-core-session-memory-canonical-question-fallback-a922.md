# TP-2026-03-25 Consultant Core Session Memory Canonical Question Fallback A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-SESSION-MEMORY-CANONICAL-QUESTION-FALLBACK-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `a85241d6`
- `UNLOCKS`: webhook expected-reply fallback and reasoning snapshot stop reading active question from legacy `session_memory.last_question_type` when canonical `session_memory.pending_question_contract` already exists

## Название/цель
Убрать следующий semantic protocol mismatch: active webhook fallback logic и reasoning snapshot до сих пор читают session-memory question continuity из legacy `last_question_type`, хотя canonical `pending_question_contract` уже хранится в `session_memory`. Из-за этого один и тот же pending question может расходиться между runtime canon и session-memory fallback consumers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-pending-resume-canonical-question-projection-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- Worktree was clean after `a85241d6`.
- `DialogStateService.normalize_session_memory_payload()` already preserves canonical `pending_question_contract`, but downstream consumers still read `last_question_type` directly.
- `decision.py:_apply_expected_reply_contract()` restores active expected-reply fallback from `session_memory.last_question_type` only.
- `reasoning_core._build_conversation_snapshot()` restores `reply_slot` from `session_memory.last_question_type` only.
- This means session-memory carryover can still speak a second question dialect even after pending-resume and router canonicalization.

## One web search (mandatory before implementation)
- **Query (exact):** `Python functools cached_property official docs`
- **Date/time (local):** 2026-03-25 12:41:00 +05
- **Sources opened:**
  - Python standard library documentation, `functools.cached_property` — `https://docs.python.org/3/library/functools.html#functools.cached_property`
- **Existing solutions found:** `cached_property` is appropriate only for stable instance-derived values, not for projections over mutable per-call payloads.
- **Decision:** keep the session-memory canonical projector as a pure helper on `DialogStateService`, not as cached mutable state on router/runtime objects.
- **Rejected options:**
  - memoizing session-memory semantic projection on mutable webhook context objects
  - continuing to treat `last_question_type` as semantic source-of-truth when `pending_question_contract` exists
  - adding a router-only session-memory rewrite layer
- **Source quality:** official Python documentation

## Root cause (mandatory)
- **Classification:** `semantic protocol/model` plus `continuity/state mismatch`; not retrieval, transport, or evaluation/process.
- **Symptom:** webhook expected-reply fallback and reasoning snapshot can recover a different active question than the canonical question contract already persisted in session memory.
- **Minimal reproduction:** inspect `decision.py:_apply_expected_reply_contract()` and `reasoning_core._build_conversation_snapshot()` when `session_memory.last_question_type` disagrees with `session_memory.pending_question_contract.expected_reply_type`.
- **Evidence:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_reasoning_core.py`
- **Five Whys:**
  1. Why does session-memory fallback drift? Because consumers restore active question from `last_question_type` only.
  2. Why is that wrong? Because session memory already stores richer canonical `pending_question_contract`.
  3. Why is meaning lost? Because `last_question_type` carries only the resume axis, not the full question contract and reason.
  4. Why does this matter? Because webhook fallback and reasoning snapshot can observe stale or contradictory active-question meaning.
  5. Why is this a protocol defect? Because session memory still exposes two semantic languages and active consumers choose the lossy one first.
- **Root cause statement:** session memory canonically stores `pending_question_contract`, but active webhook and reasoning consumers still treat legacy `last_question_type` as the authoritative question-state contract.
- **Fix mechanism:** add one session-memory canonical-question projector and route webhook fallback / reasoning snapshot through it, keeping `last_question_type` only as projection fallback.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_pending_question_contract(...)`
  - `DialogStateService.normalize_session_memory_payload(...)`
  - existing router getters and runtime canonical question-contract seam
- **External reuse:** Python standard library guidance on `cached_property`
- **Why not reinvent the wheel:** the canonical pending-question projector already exists; this block only routes session-memory fallback consumers through it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity/consumer alignment for session-memory fallback without touching booking/info/response flow logic broadly.

## Invariant
- Policy-core remains the semantic owner.
- Session memory may persist canonical pending-question state, but webhook/runtime consumers must not reinterpret user meaning beyond contractual fallback.
- `last_question_type` remains a projection, not the source-of-truth, when `session_memory.pending_question_contract` exists.
- No new router phrase branching or semantic repair layer.

## Scope
- add a canonical session-memory pending-question projector
- route `decision.py` expected-reply fallback through that projector
- route `reasoning_core` conversation snapshot through that projector
- update focused tests

## Out of scope
- deleting all remaining top-level webhook `expected_reply_*` fields
- booking/info/response flow rewrites
- acceptance baseline refresh
- retrieval or transport changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-session-memory-canonical-question-fallback-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Add one `DialogStateService` helper that projects canonical pending-question state from session memory, with `last_question_type` only as fallback projection.
2. Replace direct `session_memory.last_question_type` source-of-truth reads in webhook expected-reply fallback and reasoning snapshot with that helper.
3. Update focused tests proving canonical session-memory contract wins over stale legacy projection.
4. Run the required local suite set and commit only after exact closure evidence exists.

## DoD
- webhook expected-reply fallback reads session-memory canonical question contract first
- reasoning snapshot reads session-memory canonical question contract first
- stale `last_question_type` no longer overrides canonical `session_memory.pending_question_contract`
- tests prove the same session-memory semantic contract is seen across consumers

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- focused session-memory fallback test output
- required local suite outputs

## Rollback
- `git revert <commit>` for this bounded session-memory canonical-question fallback commit
- if webhook fallback regresses, reopen RCA instead of restoring `last_question_type` as the semantic source-of-truth

## No-go
- no new semantic regex branches
- no session-memory-only semantic schema
- no cached mutable semantic projection on webhook/runtime objects
- no continued direct `last_question_type` source-of-truth reads where canonical pending question contract exists

## Risks/Blockers
- some older tests intentionally assert `last_question_type` presence and may need adjustment to reflect its downgraded role as projection
- if legacy sessions lack `pending_question_contract`, fallback must still preserve current behavior via `last_question_type`

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remaining webhook flows in `booking.py` / `info.py` / `response.py` still use top-level expected-reply projections on various behavior paths.
- `Why not in this block`: this slice closes the session-memory semantic mismatch first; broader webhook surface cleanup remains separate.
- `Risk if deferred`: some active flows can still carry top-level expected-reply projection debt even after session-memory consumers are canonicalized.
- `Linked follow-up Task Package(s)`: next block should remove or projection-limit remaining direct webhook expected-reply consumers in `booking.py` / `info.py` / `response.py`.
- `Expiry/trigger to stop deferral`: before claiming full webhook expected-reply dialect closure.

## Next-block contract (mandatory)
- `Next block objective`: remove or projection-limit remaining direct webhook expected-reply consumers outside session-memory fallback.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/response.py`
- `Blocked-by conditions`: any failing suite that proves session-memory fallback still reads stale `last_question_type` over canonical pending-question state.
- `Owner role for closure`: Brain / Top Architect
