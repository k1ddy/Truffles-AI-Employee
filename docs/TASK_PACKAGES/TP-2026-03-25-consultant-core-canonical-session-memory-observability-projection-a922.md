# TP-2026-03-25 Consultant Core Canonical Session Memory Observability Projection A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-SESSION-MEMORY-OBSERVABILITY-PROJECTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `9c1e9e87`, `beadc227`
- `UNLOCKS`: one bounded proof that session-memory observability/reset traces report canonical question state instead of legacy `last_question_type`

## Название/цель
Свести remaining session-memory observability dialect к canonical projection: traces/meta/reset snapshots must carry canonical `pending_question_contract` when it exists, while `last_question_type` becomes fallback-only for purely legacy memory payloads.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-compatibility-question-readers-reduction-a922.md`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `git log --oneline -6` shows the latest bounded compatibility-reader reduction commit `9c1e9e87`.
- Remaining question-projection tail is now mostly observability/reporting:
  - `truffles-api/app/routers/webhook/session_memory.py::_session_memory_snapshot(...)` still reports `last_question_type` directly in trace/meta snapshots.
  - `truffles-api/app/services/state_service.py::_reset_session_memory_context(...)` still returns reset snapshot payloads keyed by `last_question_type`.
  - `truffles-api/app/core/consultant_runtime.py::_reset_runtime_context(...)` imports the legacy session-memory snapshot helper, so active runtime reset evidence still carries that legacy field shape.
- Active semantic readers are already canonical-first after `beadc227` and `9c1e9e87`; the remaining issue is observability mismatch, not active semantic ownership.

## One web search (mandatory before implementation)
- **Query (exact):** `JSON Schema annotations official docs`
- **Date/time (local):** `2026-03-25 22:16:02 +0500`
- **Sources opened (from this query):**
  - JSON Schema official docs, `Annotations` — `https://json-schema.org/understanding-json-schema/reference/annotations`
- **Existing solutions found:** annotations are descriptive carriers for UI/tooling/reporting; they do not define validation semantics.
- **Decision:** keep session-memory observability projection as a derived annotation of canonical `pending_question_contract`, and use `last_question_type` only as fallback when no canonical question contract exists in legacy memory.
- **Rejected options:**
  - preserve `last_question_type` as the primary observability field even when canonical question contract exists
  - delete every legacy reporting field in one block without preserving bounded fallback for pure legacy memory payloads
  - add a new trace-only semantic rewrite layer
- **Source quality:** official JSON Schema documentation only

## Root cause (mandatory)
- **Symptom:** even after canonical question-state unification, traces/meta/reset snapshots still describe session memory through `last_question_type` instead of the canonical `pending_question_contract`.
- **Minimal reproduction:** inspect `_session_memory_snapshot(...)` in `truffles-api/app/routers/webhook/session_memory.py` and `_reset_session_memory_context(...)` in `truffles-api/app/services/state_service.py`; both emit legacy `last_question_type` rather than canonical question contract.
- **Evidence:**
  - `truffles-api/app/routers/webhook/session_memory.py:100-137`
  - `truffles-api/app/services/state_service.py:1012-1049`
  - `truffles-api/app/core/consultant_runtime.py:491-500`
- **Root-cause classification (mandatory):**
  - A. session-memory trace/meta projection shape: `observability mismatch` — chosen for this block
  - B. session-memory reset summary shape: `continuity/state mismatch with observability` — chosen for this block
  - C. remaining frozen helper projection/reporting tails outside session memory: `observability mismatch` — deferred
- **Five Whys:**
  1. Why does the old question dialect still appear in evidence? Because session-memory snapshot helpers still emit `last_question_type` directly.
  2. Why is that a problem after canonical question-state landing? Because evidence surfaces still describe a second semantic language.
  3. Why does that matter if readers are already fixed? Because closure proof requires trace/meta/state evidence to speak the same canonical language.
  4. Why is this still architectural debt? Because operators/tests can still observe legacy question meaning as if it were the authoritative contract.
  5. Why is the closure proof not yet honest? Because observability still leaks the old question dialect as a first-class report shape.
- **Root cause statement:** session-memory observability helpers still report legacy `last_question_type` instead of projecting canonical `pending_question_contract`, leaving evidence surfaces on a second question dialect.
- **Fix mechanism:** introduce one canonical session-memory observability snapshot helper, make session-memory traces and reset summaries emit `pending_question_contract` when present, and retain `last_question_type` only as fallback for purely legacy memory payloads.

## Reuse-first plan (mandatory)
- **Internal reuse:** `DialogStateService.normalize_session_memory_payload(...)`, `DialogStateService.project_session_memory_pending_question_contract(...)`
- **External reuse:** JSON Schema annotation guidance
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** canonical projectors already exist, but the observability helpers still assemble legacy snapshot fields by hand.

## Invariant
- `pending_question_contract` remains the semantic owner of question-state evidence.
- `last_question_type` may survive only as fallback for legacy memory payloads without canonical question contract.
- No new semantic reader path based on regex/phrases.
- No frozen webhook rewrite campaign outside the session-memory observability slice.

## Scope
- introduce one canonical session-memory observability snapshot helper in `state_service.py`
- reuse that helper from `webhook/session_memory.py` and reset summaries
- ensure active runtime reset evidence reflects the same canonical session-memory snapshot shape via existing imports
- add targeted regressions for canonical session-memory snapshot reporting

## Out of scope
- deleting all remaining reporting/meta legacy fields outside session-memory snapshots
- rewriting booking/info frozen flows
- final closure proof block
- tool/pack/runtime semantic readers already fixed

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-session-memory-observability-projection-a922.md`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Add one canonical session-memory observability snapshot builder in `state_service.py`.
2. Route `webhook/session_memory.py` trace/meta snapshots and state reset summaries through that helper.
3. Add regressions proving canonical `pending_question_contract` is reported and `last_question_type` is fallback-only.
4. Run targeted + required broader suites and update canon docs if green.

## DoD
- session-memory trace/meta snapshots emit canonical `pending_question_contract` when present
- reset summaries no longer rely on `last_question_type` as the primary question-state report field
- `last_question_type` is retained only as fallback for legacy memory payloads without canonical question contract
- active runtime reset evidence inherits the same snapshot shape through shared helper reuse

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/llm_quality_contracts.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k session_memory_question_set`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff + single commit
- targeted tests proving session-memory trace/reset evidence carries canonical question contract
- required local suite outputs

## Rollback
- `git revert <commit>` for the bounded observability projection commit
- if compatibility evidence consumers break, reopen RCA rather than restoring `last_question_type` as the primary report shape

## No-go
- no new semantic repair layer
- no broad frozen webhook cleanup presented as this block
- no reintroduction of `last_question_type` as primary question-state evidence when canonical contract exists
- no closure claim beyond the session-memory observability slice

## Risks/Blockers
- some tests may still assert exact `last_question_type` snapshot keys
- a few external/frozen helpers may still look for `last_question_type` in reporting payloads
- widening into all frozen reporting surfaces would exceed the bounded block

## Which semantic dialect is being eliminated in this block?
- The session-memory observability dialect where `last_question_type` is reported as the primary question-state evidence instead of canonical `pending_question_contract`.

## Which layers will speak one language after this block?
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/core/consultant_runtime.py` reset evidence through shared session-memory snapshot reuse

## Which semantic dialect still remains afterward, if any, and why?
- Compatibility-only projection/reporting tails remain in other frozen helper/meta surfaces because this block is bounded to session-memory observability and reset evidence.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: frozen non-session-memory reporting/meta surfaces that still mention `expected_reply_*` or `last_question_type`.
- `Why not in this block`: the highest-leverage remaining proof gap is session-memory evidence shape shared by active runtime reset and frozen session-memory traces.
- `Risk if deferred`: final closure proof can still be weakened by mixed evidence formats outside session-memory surfaces.
- `Linked follow-up Task Package(s)`: final closure-proof / residual compatibility-evidence cleanup TP.
- `Expiry/trigger to stop deferral`: before claiming full semantic closure across owner/state/tools/pack/trace.

## Next-block contract (mandatory)
- `Next block objective`: assemble the final bounded closure proof and, if needed, trim the last compatibility-only evidence readers outside session-memory surfaces.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook`
- `Blocked-by conditions`: failing local suites or evidence that session-memory traces/reset summaries still prefer `last_question_type` over canonical question contract
- `Owner role for closure`: Brain / Top Architect
