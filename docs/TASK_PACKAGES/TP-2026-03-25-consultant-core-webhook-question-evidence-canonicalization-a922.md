# TP-2026-03-25 Consultant Core Webhook Question Evidence Canonicalization A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-WEBHOOK-QUESTION-EVIDENCE-CANONICALIZATION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `b2c60974`
- `UNLOCKS`: webhook trace/meta surfaces stop reporting pending-question state as split legacy projections after canonical question state has already been written

## Название/цель
Закрыть следующий системный slice: webhook compatibility layer уже пишет canonical `pending_question_contract` в context/state, но trace/meta evidence после `_set_expected_reply_context(...)` по-прежнему отражает только split `expected_reply_type` / `expected_reply_reason`. Из-за этого observability слой живёт на более бедном semantic dialect, чем active continuity.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-session-memory-canonical-question-fallback-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`

## FACT pre-check (before implementation)
- Worktree is clean after `b2c60974`.
- Deterministic scan of remaining webhook surfaces shows the true remaining mismatch is narrower than the earlier rough residual note: active getters already prefer canonical question contract, but `_set_expected_reply_context(...)` still records lossy evidence.
- `context_manager._set_expected_reply_context(...)` writes canonical state first and then records `question_contract` trace plus message `decision_meta` with only `expected_reply_type` / `expected_reply_reason`.
- `response.py`, `info.py`, and `booking.py` rely on `_set_expected_reply_context(...)` for many follow-up flows, so this lossy evidence leaks across multiple families even though state is already canonical.
- This is an `observability mismatch with the canonical protocol`, not retrieval, routing, or a new semantic owner.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses frozen official docs`
- **Date/time (local):** 2026-03-25 17:32:00 +05
- **Sources opened:**
  - Python standard library documentation, `dataclasses` — `https://docs.python.org/3/library/dataclasses.html`
- **Existing solutions found:** frozen dataclasses remain the correct pattern for immutable handoff payloads; extending a frozen result object with an additional field is preferable to mutating ad-hoc dict state after the fact.
- **Decision:** keep `ExpectedReplyContextSyncResult` immutable and extend it with one canonical `pending_question_contract` projection produced at the sync seam.
- **Rejected options:**
  - post-hoc trace/meta reconstruction from local constants after `_set_expected_reply_context(...)`
  - a second router-only evidence builder detached from the actual context sync result
  - continuing to expose only split `expected_reply_*` projections in `question_contract` trace/meta
- **Source quality:** official Python documentation

## Root cause (mandatory)
- **Classification:** `observability mismatch with the canonical protocol`; specifically, webhook trace/meta still expose a lossy question dialect after state/continuity already moved to the canonical question contract.
- **Symptom:** `question_contract` trace entries and message `decision_meta` can show only `expected_reply_type` / `expected_reply_reason`, while the same turn already has a richer canonical `pending_question_contract` in continuity.
- **Minimal reproduction:** call `_set_expected_reply_context(...)` with a booking context where `booking.last_question=datetime`; the context ends up with canonical `pending_question_contract.next_question=datetime`, but the emitted trace/meta do not carry that contract.
- **Evidence:**
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/booking.py`
- **Five Whys:**
  1. Why is webhook evidence lossy? Because `_set_expected_reply_context(...)` records only split legacy projections.
  2. Why is that wrong? Because the same sync seam already computed and stored richer canonical pending-question state.
  3. Why does meaning drift? Because trace/meta are built from local projection fields instead of the canonical pending-question contract.
  4. Why does this matter? Because debugging and downstream evidence consumers can see execution leftovers instead of the actual canonical question state.
  5. Why is this systemic? Because `_set_expected_reply_context(...)` is the shared seam used by booking/info/consult follow-up flows across webhook compatibility surfaces.
- **Root cause statement:** webhook context sync writes canonical pending-question state, but the shared evidence seam still serializes only legacy `expected_reply_*` projections, leaving trace/meta one dialect behind continuity.
- **Fix mechanism:** extend the shared sync result with a canonical projected `pending_question_contract` and route `question_contract` trace/message metadata through that projection.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_context_pending_question_contract(...)`
  - `DialogStateService.project_pending_question_contract(...)`
  - existing `_set_expected_reply_context(...)` shared webhook seam
- **External reuse:** Python standard library `dataclasses` guidance for frozen result carriers
- **Why not reinvent the wheel:** the canonical question projector already exists; this block only wires webhook evidence to the same projector instead of creating a second question schema.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** bounded protocol/evidence alignment at the shared webhook seam with focused regression tests.

## Invariant
- Policy-core remains the only semantic owner.
- Webhook compatibility layers may project question state, but they must not invent a second semantic language for evidence.
- No new regex/phrase branching.
- No runtime semantic repair layer.
- Top-level `expected_reply_*` remain projections only.

## Scope
- extend the shared expected-reply sync result with canonical pending-question projection
- record canonical pending-question contract in webhook `question_contract` trace and message `decision_meta`
- add focused regression tests proving evidence follows canonical question state

## Out of scope
- deleting all remaining top-level `expected_reply_*` transport projections
- refactoring booking/info/response decision logic broadly
- retrieval or transport changes
- acceptance baseline refresh

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-webhook-question-evidence-canonicalization-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`

## Plan (1..N)
1. Extend `ExpectedReplyContextSyncResult` so the sync seam returns one canonical `pending_question_contract` projection together with normalized split projections.
2. Route `_set_expected_reply_context(...)` trace/meta evidence through that canonical contract.
3. Add regression tests proving webhook evidence reflects canonical `next_question/open_questions/reason` rather than only split projections.
4. Run focused plus mandatory regression suites and commit only after exact closure evidence exists.

## DoD
- `_set_expected_reply_context(...)` emits `question_contract` trace entries with canonical `pending_question_contract`
- message `decision_meta` stores the same canonical `pending_question_contract`
- booking follow-up evidence preserves `next_question/open_questions` through the shared webhook seam
- no new semantic owner or phrase branching is introduced

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- focused trace/meta evidence tests
- required local suite outputs

## Rollback
- `git revert <commit>` for this bounded webhook question-evidence canonicalization commit
- if evidence consumers regress, reopen RCA instead of restoring split `expected_reply_*` as the only webhook evidence surface

## No-go
- no new semantic regex branches
- no second webhook-only question schema
- no post-hoc trace repair layer
- no broad booking/info/response rewrites unrelated to the shared seam

## Risks/Blockers
- some tests may implicitly assume message metadata contains only split `expected_reply_*` fields and will need precise updates
- trace retention must still keep payload size bounded; the contract projection must remain the already-normalized compact slice

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: top-level `expected_reply_type` / `expected_reply_reason` still exist as transport/projection fields in webhook context and some remaining traces still explicitly mention them alongside the canonical contract.
- `Why not in this block`: this slice only aligns the shared evidence seam; deleting the projections entirely requires a separate consumer sweep.
- `Risk if deferred`: some compatibility surfaces may still over-index on split projections even though evidence becomes truthful.
- `Linked follow-up Task Package(s)`: next block should sweep remaining webhook/public consumers and prove top-level `expected_reply_*` are projection-only.
- `Expiry/trigger to stop deferral`: before claiming full webhook question-dialect closure.

## Next-block contract (mandatory)
- `Next block objective`: remove or hard-limit remaining active consumers of top-level `expected_reply_*` outside the shared evidence seam, so projections remain transport-only.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason" truffles-api/app/routers/webhook truffles-api/app/services/state_service.py | head -n 200`
- `Blocked-by conditions`: any failing suite proving webhook evidence still omits canonical `pending_question_contract` after `_set_expected_reply_context(...)`.
- `Owner role for closure`: Brain / Top Architect
