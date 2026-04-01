# TP-2026-03-25 Consultant Core Canonical Question Projection Reduction A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-QUESTION-PROJECTION-REDUCTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `2ff498bf`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-pack-grounding-projection-a922.md`
- `UNLOCKS`: one bounded proof that active question-state continuity, policy-core memory, and trace/meta derive from canonical `pending_question_contract` instead of legacy reply-projection fields

## Название/цель
Свести remaining legacy question-projection dialect к projection-only статусу на active typed runtime path: `pending_question_contract` must remain the only active question-state source, while `expected_reply_type`, `expected_reply_reason`, and `last_question_type` become derived compatibility projections instead of co-equal semantic state.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-pack-grounding-projection-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/reasoning_core.py`

## FACT pre-check (before implementation)
- `git log --oneline -5` shows the latest bounded pack-grounding commit `2ff498bf`.
- `git status --short --branch` is clean on `feat/2026-03-15-consultant-core-governance-lock-a922`.
- Active typed runtime still carries legacy question projections as a parallel dialect:
  - `truffles-api/app/core/consultant_runtime.py` reads `dialog_state.projections.expected_reply_type` / `expected_reply_reason` for memory profile, trace/meta, and `booking_prompt` action derivation.
  - `truffles-api/app/core/dialog_state_service.py` still normalizes and persists top-level `expected_reply_type` / `expected_reply_reason` alongside canonical `pending_question_contract`.
  - `truffles-api/app/core/dialog_state_service.py` still repopulates `session_memory.last_question_type` from canonical question state, keeping a second stored question dialect alive.
- The repo already shows the canonical alternative:
  - `pending_question_contract` is present in planner/runtime/state/trace
  - `project_context_pending_question_contract(...)` already prefers canonical contract over stale projections when both exist
  - `project_session_memory_pending_question_contract(...)` already prefers canonical session-memory contract over `last_question_type`

## One web search (mandatory before implementation)
- **Query (exact):** `JSON Schema annotations official docs`
- **Date/time (local):** `2026-03-25 21:26:46 +0500`
- **Sources opened (from this query):**
  - JSON Schema official docs, `Annotations` — `https://json-schema.org/understanding-json-schema/reference/annotations`
- **Existing solutions found:** annotation fields are descriptive/non-validation carriers; they may exist for tooling or documentation, but they are not the validating source of the schema contract.
- **Decision:** treat `expected_reply_type`, `expected_reply_reason`, and `last_question_type` as derived projection/annotation fields, and keep canonical question meaning in `pending_question_contract`.
- **Rejected options:**
  - keep active runtime reads on `dialog_state.projections.expected_reply_*`
  - keep `session_memory.last_question_type` mirrored from canonical question state on every write
  - delete every projection field immediately across frozen/legacy paths in the same block
- **Source quality:** official JSON Schema documentation only

## Root cause (mandatory)
- **Symptom:** even after canonical question-contract landing, active runtime/state/trace still carry and read `expected_reply_*` and `last_question_type` as a second question-state language.
- **Minimal reproduction:** inspect `truffles-api/app/core/consultant_runtime.py` and `truffles-api/app/core/dialog_state_service.py` for reads of `dialog_state.projections.expected_reply_*`, `runtime_payload.expected_reply_*`, and `session_memory.last_question_type`, then compare that with the already-canonical `pending_question_contract` in the same payloads.
- **Evidence:**
  - `truffles-api/app/core/consultant_runtime.py:388-389`
  - `truffles-api/app/core/consultant_runtime.py:605-657`
  - `truffles-api/app/core/consultant_runtime.py:915-1040`
  - `truffles-api/app/core/dialog_state_service.py:1426-1494`
  - `truffles-api/app/core/dialog_state_service.py:1600-1684`
  - `truffles-api/app/core/dialog_state_service.py:2237-2273`
- **Root-cause classification (mandatory):**
  - A. legacy expected-reply projection fields: `continuity/state` + `semantic protocol/model` mismatch — chosen for this block
  - B. `last_question_type` session-memory carryover: `continuity/state` mismatch — chosen for this block, but only on the active canonical path
  - C. frozen/legacy webhook readers of projection fields: `observability` / compatibility debt — deferred
- **Five Whys:**
  1. Why does a second question dialect still exist? Because runtime/state still persist and read `expected_reply_*` and `last_question_type` beside canonical `pending_question_contract`.
  2. Why is that a semantic mismatch? Because active question meaning is already modeled canonically in `pending_question_contract`.
  3. Why does the mismatch matter after the question-contract slice? Because trace/meta, memory profile, and followup action derivation can still consult projection fields directly.
  4. Why is that risky? Because stale projections can diverge from the canonical contract and silently become runtime truth again.
  5. Why is the architecture still not honestly unified? Because active runtime question state still has two readable dialects, one canonical and one projection-based.
- **Root cause statement:** the remaining active defect is legacy question-projection drift: `expected_reply_type`, `expected_reply_reason`, and `last_question_type` still survive as readable runtime question-state carriers instead of being strictly derived from canonical `pending_question_contract`.
- **Fix mechanism:** make active runtime readers derive question state from canonical `pending_question_contract`, demote `expected_reply_*` to derived transport/meta projections, and stop rehydrating `last_question_type` when canonical question contract already exists.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `pending_question_contract` contract and projection helpers in `DialogStateService`
  - existing canonical runtime loader in `DialogStateService.load_runtime_payload`
  - existing memory-profile normalization in `intent_service`
- **External reuse:** JSON Schema annotation guidance
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** repo already has the canonical contract, but active readers still consult legacy projections directly.

## Invariant
- `pending_question_contract` remains the only active question-state source.
- Deterministic layers may derive projection fields, but they must not let them outrank the canonical contract.
- No new phrase/regex semantic branching.
- No frozen-router cleanup tail inside this block.

## Scope
- shift active runtime reads from `expected_reply_*` projections to canonical `pending_question_contract`
- reduce `last_question_type` to fallback-only behavior when canonical session-memory contract exists
- remove legacy `expected_reply_type` from policy-core memory profile as a semantic carrier
- add targeted tests proving stale projections no longer outrank canonical question contract

## Out of scope
- deleting every projection field from frozen/legacy webhook code
- acceptance replay / quality reruns
- pack/tool semantic changes already landed
- owner-matrix or timeout-boundary semantics beyond projection-source reduction

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Normalize active runtime question reads so `pending_question_contract` outranks projection fields everywhere on the typed runtime path.
2. Reduce session-memory `last_question_type` to fallback-only when canonical question contract exists.
3. Remove legacy `expected_reply_type` from policy-core memory profile and prompt examples so policy-core sees canonical question context instead of a duplicated dialect.
4. Add regressions for `stale projection -> canonical question contract wins` in runtime load, trace/meta, and session-memory normalization.
5. Run required deterministic suites and update `STATE.md` before merge if green.

## DoD
- active typed runtime derives question state from canonical `pending_question_contract`
- stale `expected_reply_*` projections no longer override canonical question state on runtime load/trace/meta
- `last_question_type` is reduced to fallback-only behavior where canonical question contract already exists
- policy-core memory profile no longer carries `expected_reply_type` as a co-equal semantic carrier

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff + single commit
- targeted runtime/state tests proving stale projections no longer win over canonical question contract
- required local suite outputs

## Rollback
- `git revert <commit>` for the bounded projection-reduction commit
- if compatibility regressions surface, reopen RCA instead of reintroducing projection fields as runtime truth

## No-go
- no new semantic repair layer
- no frozen webhook cleanup presented as canonicalization
- no new duplicate question-state carrier
- no closure claim beyond the bounded active typed runtime slice

## Risks/Blockers
- some legacy tests may still assert mirrored `last_question_type` or profile-level `expected_reply_type`
- frozen/legacy webhook surfaces will still read projection fields after this block
- removing too much projection surface inside one block could widen compatibility risk beyond the active typed runtime path

## Which semantic dialect is being eliminated in this block?
- The legacy question-projection dialect: runtime reads of `expected_reply_type`, `expected_reply_reason`, and `last_question_type` as co-equal question-state truth beside canonical `pending_question_contract`.

## Which layers will speak one language after this block?
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- policy-core memory normalization in `truffles-api/app/services/intent_service.py`
- prompt contract in `prompts/llm_policy_core.md`

## Which semantic dialect still remains afterward, if any, and why?
- compatibility-only projection fields may still be emitted in context/trace/meta and frozen/legacy webhook paths, but they should remain derived projections rather than active source-of-truth.
- frozen/legacy webhook readers of `expected_reply_*` and `last_question_type` remain deferred because this block is bounded to the active typed runtime path.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: frozen/legacy webhook readers of `expected_reply_*` and `last_question_type`; transport/meta projections that remain for compatibility.
- `Why not in this block`: this slice is bounded to active typed runtime continuity, policy-core memory, and trace/meta.
- `Risk if deferred`: frozen compatibility paths can still carry the old dialect outside the active runtime path.
- `Linked follow-up Task Package(s)`: one final cleanup block for frozen/legacy projection readers only if needed after active-path closure proof.
- `Expiry/trigger to stop deferral`: before claiming full end-to-end canonical semantic closure across all remaining compatibility surfaces.

## Next-block contract (mandatory)
- `Next block objective`: classify and, if still justified, remove frozen/legacy compatibility readers that still inspect `expected_reply_*` or `last_question_type` outside the active typed runtime path.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/routers/webhook truffles-api/app/services`
- `Blocked-by conditions`: failing required local suites or evidence that active typed runtime still depends on projection fields after this block
- `Owner role for closure`: Brain / Top Architect
