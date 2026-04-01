# TP-2026-03-25 Consultant Core Canonical Question Contract Substrate A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-QUESTION-CONTRACT-SUBSTRATE-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `646c0183`, `9636381f`
- `UNLOCKS`: removal of one more semantic dialect by making `pending_question_contract` the canonical question-state payload across planner, continuity, policy-core memory, execution meta, and runtime trace/meta

## Название/цель
Закрыть следующий системный semantic mismatch: active question continuity is still split between `pending_question_contract`, `expected_reply_type/reason`, `interaction_target`, and `semantic_contract`, and one of those fields (`pending_question_target`) is still partially overloaded with slot names. This block makes the question contract itself a richer canonical substrate and stops writing slot meaning into semantic-axis fields.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-query-substrate-booking-prompt-owner-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/intent_service.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `contracts/runtime/dialog_state.v1.jsonschema`

## FACT pre-check (before implementation)
- Current worktree is clean after `646c0183`.
- `PendingQuestionContract` in `truffles-api/app/core/turn_planner.py` currently stores only `expected_reply_type`, `pending_question_target`, `active_question_relation`, `next_question`, `open_questions`.
- `DialogStateService.build_collect_owner_state()` currently falls back from `interaction_target` to `next_question`, which overloads semantic-axis state with slot names (`service`, `datetime`, `name`, `phone`).
- `IntentService._normalize_policy_core_memory_profile()` accepts `pending_question_contract` but currently normalizes only `slot/expected_reply_type/reason/value`; semantic question axes remain split elsewhere.
- `ConsultantRuntime._build_policy_core_memory_profile()` reconstructs a partial `pending_question_contract` dict instead of projecting the typed runtime contract directly.

## One web search (mandatory before implementation)
- **Query (exact):** `Pydantic model_validate official docs`
- **Date/time (local):** 2026-03-25 21:02:00 +05
- **Sources opened:**
  - Pydantic official docs, `BaseModel` API — `https://docs.pydantic.dev/2.7/api/base_model/`
- **Existing solutions found:** Pydantic `BaseModel.model_validate(...)` is the direct validation seam for evolving a richer nested contract payload without ad hoc post-parse repair.
- **Decision:** reuse the existing `PendingQuestionContract` Pydantic model as the single typed question-contract substrate and project richer canonical payloads through `model_validate(...)` instead of maintaining parallel dict dialects.
- **Rejected options:**
  - leaving `pending_question_contract` partial and reconstructing missing meaning ad hoc in each runtime layer
  - introducing a second sidecar question-contract schema outside the active runtime models
  - preserving slot-name overload in `pending_question_target` / `interaction_target`
- **Source quality:** official Pydantic documentation

## Root cause (mandatory)
- **Symptom:** question continuity is represented differently across layers; `pending_question_contract` is partial, `expected_reply_reason` lives outside it, and generic collect state writes slot names into semantic-axis fields (`pending_question_target`, `interaction_target`).
- **Minimal reproduction:** inspect `PendingQuestionContract` in planner, `build_collect_owner_state()` / `_build_booking_followup_dialog_state()` in `dialog_state_service`, `ConsultantRuntime._build_policy_core_memory_profile()`, and `IntentService._normalize_policy_core_memory_profile()`.
- **Evidence:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/services/intent_service.py`
  - `prompts/llm_policy_core.md`
- **Five Whys:**
  1. Why does question meaning drift? Because the system stores slot collection state and semantic interaction state in different partially overlapping fields.
  2. Why is that lossy? Because `pending_question_contract` omits `reason` / `pending_question_act`, while `expected_reply_reason` and semantic axes live elsewhere.
  3. Why is it ambiguous? Because generic collect logic also writes slot names into `pending_question_target` / `interaction_target`, overloading semantic-axis fields.
  4. Why does that matter? Because policy-core memory, runtime state, execution meta, and trace/meta no longer reflect the same question contract.
  5. Why is this a semantic protocol defect? Because the same active question is spoken in multiple dialects rather than one canonical question contract.
- **Root cause statement:** the system still lacks one canonical question-contract substrate; runtime layers split question meaning across partial pending-question payloads, legacy expected-reply projections, and overloaded interaction fields.
- **Fix mechanism:** enrich `PendingQuestionContract` into the canonical question payload, stop overloading semantic-axis fields with slot names, and project that same payload consistently through continuity, policy-core memory, execution meta, and runtime trace/meta.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PendingQuestionContract` Pydantic model
  - `DialogStateService` as continuity writer/normalizer seam
  - `ConsultantRuntime` memory-profile builder
  - current `semantic_contract.v1` as semantic-owner output
- **External reuse:** Pydantic `BaseModel.model_validate(...)`
- **Why not reinvent the wheel:** the required change is a contract migration inside the existing typed runtime path, not a new model stack.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** this is a bounded runtime contract migration across already-existing typed seams.

## Invariant
- Policy-core remains the only semantic owner.
- Deterministic layers do not infer user meaning from raw text; they only persist, project, and expose the canonical question contract.
- `next_question/open_questions` remain slot-collection fields.
- `pending_question_act/pending_question_target/active_question_relation` remain semantic interaction axes and are not overloaded with slot names.

## Scope
- enrich `PendingQuestionContract` so it can carry the canonical active question payload
- stop writing slot names into semantic-axis fields in dialog-state continuity
- project the same canonical question contract into policy-core memory profile
- expose the same canonical question contract in execution meta and runtime trace/meta
- update prompt/schema/tests to speak that same question-contract language

## Out of scope
- router-level legacy `decision.py` expected-reply deletion
- retrieval or transport work
- acceptance baseline refresh
- pack-specific behavior changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/intent_service.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `contracts/runtime/dialog_state.v1.jsonschema`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Enrich `PendingQuestionContract` and its runtime schema so question reason/act are first-class and slot fields are kept separate from semantic axes.
2. Update `DialogStateService` to persist and restore the canonical question contract without overloading `pending_question_target` / `interaction_target` with slot names.
3. Update `ConsultantRuntime`, `TurnExecutor`, and `booking_prompt_owner` to project the same question contract into memory, execution meta, and trace/meta.
4. Update `IntentService` normalization and `prompts/llm_policy_core.md` so policy-core sees one canonical question-contract shape.
5. Add/update focused tests and run required local checks.

## DoD
- `PendingQuestionContract` carries the active question payload more completely than before
- generic collect continuity no longer stores slot names in semantic-axis fields
- policy-core memory, runtime state, execution meta, and trace/meta expose the same question-contract shape
- tests prove the contract is canonicalized rather than repaired ad hoc

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/turn_executor.py truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- targeted contract test output
- required local suite outputs

## Rollback
- `git revert <commit>` for the bounded question-contract migration commit
- if runtime continuity regresses, reopen RCA instead of reintroducing overloaded fields

## No-go
- no new semantic regex branching
- no second semantic owner
- no runtime semantic repair layer
- no slot-name stuffing into semantic-axis fields
- no keeping `pending_question_contract` partial once the richer typed contract exists

## Risks/Blockers
- old tests may assert overloaded `pending_question_target=datetime|service`
- runtime/meta snapshots may depend on the previous partial pending-question shape
- some compatibility layers may still read top-level `expected_reply_type/reason`

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: legacy router `decision.py` still has its own expected-reply/question-contract dialect outside the active consultant-runtime continuity writer.
- `Why not in this block`: this block canonicalizes the typed active runtime question contract first; the legacy router migration remains a separate bounded compatibility deletion/alignment slice.
- `Risk if deferred`: old router branches can still surface a second question-contract language outside the active runtime path.
- `Linked follow-up Task Package(s)`: next block should align or delete the legacy `decision.py` expected-reply compatibility path using the now richer canonical question contract.
- `Expiry/trigger to stop deferral`: before claiming full consultant-core question-contract closure.

## Next-block contract (mandatory)
- `Next block objective`: migrate the remaining legacy expected-reply compatibility consumers in `truffles-api/app/routers/webhook/decision.py` onto the richer canonical question contract or delete them if dead.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|pending_question_contract" truffles-api/app/routers/webhook/decision.py`
- `Blocked-by conditions`: failing required local suites or evidence that active runtime still depends on overloaded question fields.
- `Owner role for closure`: Brain / Top Architect
