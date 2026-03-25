# TP-2026-03-25 Consultant Core Canonical Question Evidence Closure A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-QUESTION-EVIDENCE-CLOSURE-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `a83a7ff4`, `9c1e9e87`, `beadc227`
- `UNLOCKS`: final bounded closure proof that question-state observability/proof surfaces speak canonical `pending_question_contract`

## Название/цель
Закрыть remaining observability/proof tail по question-state: frozen webhook evidence and quality proof helpers must project canonical `pending_question_contract` first, while legacy `expected_reply_*` stays only as compatibility projection.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-compatibility-question-readers-reduction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-session-memory-observability-projection-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/services truffles-api/app/routers/webhook` shows the active typed runtime path is already canonical-first; the remaining hotspots are frozen question-contract observability and proof helpers.
- `truffles-api/app/routers/webhook/decision.py` still writes question-contract/session-memory/intent-decomposition evidence keyed by legacy `expected_reply_type` / `expected_reply_reason` without always attaching the canonical `pending_question_contract` that actually governed the turn.
- `truffles-api/app/routers/webhook/info.py` truth-gate override evidence still publishes legacy expected-reply fields as primary override evidence.
- `truffles-api/app/services/llm_quality_contracts.py` still extracts booking-progress/resume reply kind from top-level `expected_reply_type` before canonical `pending_question_contract` in several proof helpers.

## One web search (mandatory before implementation)
- **Query (exact):** `JSON Schema annotations official docs`
- **Date/time (local):** `2026-03-25 22:32:52 +0500`
- **Sources opened (from this query):**
  - JSON Schema official docs, `Annotations` — `https://json-schema.org/understanding-json-schema/reference/annotations`
- **Existing solutions found:** annotation/projection fields may describe data for tooling/reporting, but they do not own validation semantics.
- **Decision:** keep legacy `expected_reply_*` evidence only as annotation/projection, and make frozen webhook evidence plus proof helpers consume canonical `pending_question_contract` first.
- **Rejected options:**
  - continue treating top-level `expected_reply_*` as the primary proof/evidence key when canonical question contract already exists
  - delete every compatibility evidence field in one block and break frozen helpers instead of projecting canonical-first
  - add a post-hoc semantic repair layer in proof tooling
- **Source quality:** official JSON Schema documentation only

## Root cause (mandatory)
- **Symptom:** after canonical question-state landing, some trace/meta/proof surfaces still describe active question meaning through legacy `expected_reply_type` / `expected_reply_reason` instead of canonical `pending_question_contract`.
- **Minimal reproduction:** inspect `_apply_expected_reply_contract(...)` in `truffles-api/app/routers/webhook/decision.py` and `has_resume_meta_trace_allowance(...)` in `truffles-api/app/services/llm_quality_contracts.py`; both still derive or emit evidence using legacy expected-reply fields as the first visible contract.
- **Evidence:**
  - `truffles-api/app/routers/webhook/decision.py:1243-1322,1357-1450,1898-1954,2110-2119`
  - `truffles-api/app/routers/webhook/info.py:2147-2203`
  - `truffles-api/app/services/llm_quality_contracts.py:536-575,601-748`
- **Root-cause classification (mandatory):**
  - A. frozen webhook question evidence shape: `observability mismatch with canonical protocol` — chosen for this block
  - B. proof helper reply-kind extraction order: `observability/evaluation mismatch with canonical protocol` — chosen for this block
  - C. legacy transport projections inside runtime payloads: `projection-only compatibility` — deferred
- **Five Whys:**
  1. Why does the legacy question dialect still appear in closure evidence? Because several frozen trace/meta writers still emit only top-level expected-reply fields.
  2. Why is that a problem if runtime readers are canonical-first? Because proof/observability still speak a second semantic language.
  3. Why does that block honest closure? Because the closure claim requires `trace/meta` and quality proof to observe the same canonical contract as runtime/state.
  4. Why hasn’t the dialect disappeared by itself? Because the frozen webhook helpers were preserving compatibility evidence shapes without explicitly projecting canonical question state alongside them.
  5. Why do residual failures keep looking like “one more expected-reply issue”? Because operators and proof helpers can still reason over the legacy projection fields instead of the canonical contract.
- **Root cause statement:** frozen webhook evidence writers and llm-quality proof helpers still privilege legacy expected-reply projections over canonical `pending_question_contract`, leaving observability on a second question-state dialect even though runtime/state are canonical-first.
- **Fix mechanism:** project canonical `pending_question_contract` into the remaining frozen question-evidence traces/meta, teach llm-quality proof helpers to extract reply kind from canonical contract first, and add one explicit end-to-end closure test that binds semantic contract + question contract + tool/pack trace evidence together.

## Reuse-first plan (mandatory)
- **Internal reuse:** `DialogStateService.project_pending_question_contract(...)`, `DialogStateService.project_context_pending_question_contract(...)`
- **External reuse:** JSON Schema annotation guidance
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** canonical projectors exist, but frozen evidence writers and proof helpers still assemble/consume legacy fields directly.

## Invariant
- `pending_question_contract` remains the semantic owner of question-state evidence.
- `expected_reply_*` may survive only as annotation/projection or compatibility fallback.
- No new regex/phrase semantic owner.
- No new runtime repair layer.

## Scope
- canonicalize remaining question-evidence writers in frozen webhook `decision.py` / `info.py`
- make llm-quality proof helpers read canonical `pending_question_contract` before legacy expected-reply projections
- add one bounded closure test proving canonical semantic + question contracts survive through trace/meta on the active runtime path

## Out of scope
- deleting every legacy expected-reply projection field from payloads or history
- rewriting booking/info business flow logic
- new tool or pack protocol work
- acceptance replay / live run execution

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-evidence-closure-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add canonical pending-question evidence projection helpers to the remaining frozen question-contract trace/meta writes.
2. Switch llm-quality reply-kind extraction/proof allowance helpers to canonical `pending_question_contract` first.
3. Add targeted regressions plus one bounded runtime closure test.
4. Run required local checks, update canon docs, and commit only if the closure claim is exact.

## DoD
- frozen webhook question-evidence traces/meta carry canonical `pending_question_contract` whenever that contract governs the turn
- llm-quality proof helpers can prove booking-progress/resume contracts from canonical question evidence without requiring legacy top-level expected-reply fields
- one explicit bounded test proves `semantic_contract + pending_question_contract + tool/pack trace/meta` align on one turn family
- legacy `expected_reply_*` remain projection-only in the touched surfaces

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/services/llm_quality_contracts.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "resume_contract_meta_trace_fallback or session_memory_question_set"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff + one final bounded commit for question-evidence closure
- targeted tests showing canonical question evidence in frozen webhook traces/meta and llm-quality proof helpers
- explicit closure test covering semantic contract + question contract + trace/meta

## Rollback
- `git revert <commit>` for the bounded evidence-closure commit
- if proof/evidence consumers still break, reopen RCA instead of restoring legacy expected-reply fields as primary truth

## No-go
- no scenario-specific booking patching
- no new semantic owner outside policy-core
- no proof-only semantic rewrite layer detached from runtime evidence
- no broad claim that every frozen compatibility surface is deleted

## Risks/Blockers
- some tests may assert exact legacy trace/meta shapes
- truth-gate/frozen evidence paths may carry slightly different metadata than active runtime turns
- if more than question-evidence/proof helpers need changes, the block is no longer bounded

## Which semantic dialect is being eliminated in this block?
- The remaining question-evidence dialect where frozen traces/meta/proof helpers still privilege top-level `expected_reply_*` over canonical `pending_question_contract`.

## Which layers will speak one language after this block?
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/app/core/consultant_runtime.py` closure proof path in tests

## Which semantic dialect still remains afterward, if any, and why?
- Compatibility transport projections (`expected_reply_*`, `last_question_type`) can still remain in payloads/history as derived fields, because this block only closes the remaining evidence/proof ownership gap and does not rewrite every historical compatibility surface.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: compatibility projection fields may still appear in payload/history for old readers.
- `Why not in this block`: deleting every transport projection is a broader cleanup than the remaining closure requirement.
- `Risk if deferred`: low if those fields remain projection-only; high only if a new reader starts treating them as primary truth again.
- `Linked follow-up Task Package(s)`: none required for semantic ownership if closure proof is green; future cleanup can be a transport-only debt block.
- `Expiry/trigger to stop deferral`: any new reader that consumes legacy question projections before canonical contract.

## Next-block contract (mandatory)
- `Next block objective`: only if this block lands cleanly, produce the final closure summary / merge handoff with no additional runtime semantic work.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/routers/webhook truffles-api/app/services/llm_quality_contracts.py`
- `Blocked-by conditions`: failing required suites or evidence that proof helpers still require legacy expected-reply fields when canonical contract exists
- `Owner role for closure`: Brain / Top Architect
