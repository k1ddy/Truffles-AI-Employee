# TP-2026-03-25 Consultant Core Canonical Compatibility Question Readers Reduction A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-COMPATIBILITY-QUESTION-READERS-REDUCTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `beadc227`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md`
- `UNLOCKS`: one bounded proof that the remaining active/frozen expected-reply bootstrap readers derive from canonical `pending_question_contract` before any legacy projection fallback

## Название/цель
Убрать следующий remaining semantic-reader seam: reasoning and frozen webhook bootstrap code must read question meaning from canonical `pending_question_contract` first, while top-level `expected_reply_*` stays compatibility projection only.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `git log --oneline -5` shows the latest bounded question-projection reduction commit `beadc227`.
- `git status --short --branch` is clean on `feat/2026-03-15-consultant-core-governance-lock-a922`.
- Remaining active compatibility readers still exist outside the typed runtime path:
  - `truffles-api/app/services/reasoning_core.py` bootstraps `reply_slot/resume_reason` from top-level context `expected_reply_type` / `expected_reply_reason` before consulting canonical context question state.
  - `truffles-api/app/routers/webhook/decision.py` bootstraps `expected_reply_type` / `expected_reply_reason` from legacy top-level context getters before any canonical context question contract.
- `truffles-api/app/services/state_service.py` already prefers canonical `pending_question_contract` in pending-resume restore paths; surviving `last_question_type`/projection surfaces there are mostly compatibility transport and observability, not the highest-leverage live reader seam.

## One web search (mandatory before implementation)
- **Query (exact):** `JSON Schema annotations official docs`
- **Date/time (local):** `2026-03-25 21:47:16 +0500`
- **Sources opened (from this query):**
  - JSON Schema official docs, `Annotations` — `https://json-schema.org/understanding-json-schema/reference/annotations`
- **Existing solutions found:** annotation fields are descriptive/non-validation carriers; they document or hint, but they do not define the validating contract.
- **Decision:** keep legacy top-level `expected_reply_*` only as annotation/projection carriers and make remaining bootstrap readers consume canonical `pending_question_contract` first.
- **Rejected options:**
  - keep reasoning/webhook bootstrap starting from top-level `expected_reply_*`
  - remove every compatibility projection field in one block, including frozen reporting/meta surfaces
  - add a post-hoc semantic repair layer that rewrites stale projection fields after bootstrap
- **Source quality:** official JSON Schema documentation only

## Root cause (mandatory)
- **Symptom:** even after active typed runtime question canonicalization, remaining ingress/bootstrap readers can still treat top-level `expected_reply_type` / `expected_reply_reason` as runtime truth before canonical `pending_question_contract`.
- **Minimal reproduction:** seed context with canonical `pending_question_contract.expected_reply_type=time` and stale top-level `expected_reply_type=name`; inspect `reasoning_core._build_conversation_snapshot(...)` and `webhook.decision._apply_expected_reply_contract(...)` to see which value wins.
- **Evidence:**
  - `truffles-api/app/services/reasoning_core.py:362-433`
  - `truffles-api/app/routers/webhook/decision.py:1220-1299`
  - `truffles-api/app/services/state_service.py:716-764`
- **Root-cause classification (mandatory):**
  - A. reasoning bootstrap from top-level `expected_reply_*`: `semantic protocol/model` + `runtime` mismatch — chosen for this block
  - B. frozen webhook expected-reply bootstrap from top-level `expected_reply_*`: `semantic protocol/model` mismatch — chosen for this block
  - C. `state_service`/`session_memory` compatibility reporting fields such as `last_question_type`: `observability` mismatch — deferred
- **Five Whys:**
  1. Why can stale projections still affect behavior? Because some readers bootstrap from top-level `expected_reply_*` before canonical question contract.
  2. Why is that wrong after the prior block? Because active question meaning already lives in `pending_question_contract`.
  3. Why does this matter if projections are “just compatibility”? Because these readers run before later canonical typed runtime layers can correct them.
  4. Why is that an architecture risk? Because stale transport fields can silently regain source-of-truth status on ingress/fallback paths.
  5. Why is the semantic substrate still not fully unified? Because bootstrap readers in reasoning/frozen webhook still read a second dialect first.
- **Root cause statement:** remaining ingress/bootstrap compatibility readers still consult top-level expected-reply projection fields as primary question-state input instead of deriving from canonical `pending_question_contract` first.
- **Fix mechanism:** route reasoning/webhook bootstrap through `DialogStateService.project_context_pending_question_contract(...)`, use top-level `expected_reply_*` only as fallback when canonical question fields are absent, and add regression coverage for stale-projection override attempts.

## Reuse-first plan (mandatory)
- **Internal reuse:** `DialogStateService.project_context_pending_question_contract(...)`, `DialogStateService.project_session_memory_pending_question_contract(...)`, existing pending-resume boundary helpers.
- **External reuse:** JSON Schema annotation guidance.
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** the canonical projector already exists, but the remaining readers still initialize from legacy getters instead of that projector.

## Invariant
- `pending_question_contract` remains the only semantic source of active question state.
- Deterministic bootstrap readers may project compatibility fields, but they must not let them outrank canonical question state.
- No phrase/regex semantic repair.
- No tool/pack scope expansion in this block.

## Scope
- make `reasoning_core._build_conversation_snapshot(...)` prefer canonical context question contract over stale top-level projections
- make `webhook.decision._apply_expected_reply_contract(...)` prefer canonical context question contract over stale top-level projections
- add bounded regressions proving stale top-level projections no longer win in those readers

## Out of scope
- deleting every compatibility projection field from `state_service.py` or frozen reporting helpers
- full frozen webhook cleanup tail outside the expected-reply bootstrap seam
- new quality replay runs
- pack/tool semantic changes already landed

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-compatibility-question-readers-reduction-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Inspect remaining bootstrap readers and route them through canonical `pending_question_contract` projection before compatibility fallback.
2. Add regressions for stale top-level `expected_reply_*` being overridden by canonical question contract in reasoning snapshot and frozen webhook expected-reply handling.
3. Run targeted contract suites first, then required broader suites if green.
4. Update `STATE.md` / `STRUCTURE.md` before merge if the bounded block closes cleanly.

## DoD
- reasoning snapshot bootstrap derives reply slot/reason from canonical context question contract first
- frozen webhook expected-reply bootstrap derives from canonical context question contract first
- stale top-level `expected_reply_*` no longer override canonical `pending_question_contract` in the touched readers
- remaining projection fields are compatibility-only in these paths

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff + single commit
- targeted tests proving canonical question contract outranks stale top-level expected-reply projections in reasoning/webhook bootstrap
- required local suite outputs

## Rollback
- `git revert <commit>` for the bounded compatibility-reader reduction commit
- if frozen compatibility regressions surface, reopen RCA instead of restoring top-level projections as primary truth

## No-go
- no new semantic repair layer
- no broad frozen webhook cleanup campaign hidden inside this block
- no reintroduction of top-level expected-reply projections as source-of-truth
- no closure claim beyond the touched reasoning/webhook bootstrap seam

## Risks/Blockers
- frozen tests may still assume top-level projections are read first
- some fallback-only reporting helpers will still mention `last_question_type` after this block
- widening into all frozen webhook readers would exceed the bounded slice

## Which semantic dialect is being eliminated in this block?
- The remaining bootstrap dialect where top-level `expected_reply_type` / `expected_reply_reason` are read before canonical `pending_question_contract` in reasoning and frozen webhook bootstrap.

## Which layers will speak one language after this block?
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`

## Which semantic dialect still remains afterward, if any, and why?
- Compatibility-only projection/reporting surfaces remain in `state_service.py`, `webhook/session_memory.py`, and frozen trace/meta helpers because this block is bounded to bootstrap readers, not every reporting field.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: compatibility-only `expected_reply_*` / `last_question_type` reporting and frozen helper surfaces.
- `Why not in this block`: the highest-leverage remaining risk is bootstrap source-of-truth ordering, not every reporting field.
- `Risk if deferred`: compatibility metadata can still look like a second dialect even if it no longer drives the touched readers.
- `Linked follow-up Task Package(s)`: one final closure/cleanup TP for remaining compatibility-only projection/reporting surfaces and closure proof.
- `Expiry/trigger to stop deferral`: before claiming full end-to-end semantic closure across all remaining runtime and frozen compatibility edges.

## Next-block contract (mandatory)
- `Next block objective`: remove or fence the remaining compatibility-only projection/reporting readers in `state_service.py` and frozen webhook helper surfaces, then produce the final bounded closure proof.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|last_question_type" truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook`
- `Blocked-by conditions`: failing required local suites or evidence that bootstrap readers still prefer stale top-level projections after this block
- `Owner role for closure`: Brain / Top Architect
