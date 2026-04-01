# TP-2026-03-25 Consultant Core Router Canonical Question Projection A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-ROUTER-CANONICAL-QUESTION-PROJECTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `fe5f76bf`
- `UNLOCKS`: router-level expected-reply compatibility can read one canonical question contract instead of a separate webhook-local dialect

## Название/цель
Убрать следующий semantic protocol mismatch: активный router compatibility path в `decision.py` и `context_manager.py` всё ещё читает question continuity из legacy `expected_reply_type/reason` и старого `canonical_dialog_state.pending_question_contract{slot,message_count,value}` вместо того, чтобы читать один канонический active question contract с `next_question/open_questions/reason`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_webhook_booking.py`

## FACT pre-check (before implementation)
- Worktree is clean after `fe5f76bf`.
- `decision.py` still routes the compatibility path off `_get_expected_reply_type/_get_expected_reply_reason` and `_should_use_expected_reply_collect_fast_path(...)`, so router semantics still depend on legacy projected fields.
- `context_manager._get_expected_reply_type()` and `_get_expected_reply_reason()` currently read only top-level context fields, not the canonical question contract.
- `DialogStateService.normalize_context_manager_canonical_state()` still normalizes a second pending-question dialect with `slot/message_count/value` instead of the richer canonical `next_question/open_questions/...` shape.
- `decision.py:_resolve_semantic_referent()` still reads `pending_question_contract.slot` directly from canonical dialog state.

## One web search (mandatory before implementation)
- **Query (exact):** `Pydantic AliasChoices validation_alias official docs`
- **Date/time (local):** 2026-03-25 23:03:00 +05
- **Sources opened:**
  - Pydantic official docs, Fields API — `https://docs.pydantic.dev/latest/api/fields/`
- **Existing solutions found:** Pydantic supports alias-based validation (`validation_alias`, `AliasChoices`) so one typed model can accept legacy field names while emitting one canonical shape.
- **Decision:** reuse the existing canonical projection seam instead of keeping router-local field dialects; accept old `slot` as input alias but normalize router-visible question state to `next_question/open_questions`.
- **Rejected options:**
  - keeping the context-manager canonical state on `slot/message_count/value` and adding more router glue
  - adding another router-only question contract object
  - leaving `_get_expected_reply_type/reason` blind to canonical dialog state
- **Source quality:** official Pydantic documentation

## Root cause (mandatory)
- **Classification:** `semantic protocol/model` plus `continuity/state mismatch`; not retrieval, transport, or evaluation/process.
- **Symptom:** webhook router still has a separate active-question language from the runtime canonical question contract.
- **Minimal reproduction:** inspect `truffles-api/app/routers/webhook/context_manager.py` getters, `DialogStateService.normalize_canonical_pending_question_contract()`, and `decision.py:_resolve_semantic_referent()`.
- **Evidence:**
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
- **Five Whys:**
  1. Why does router question logic still drift? Because it reads top-level `expected_reply_*` fields and an older canonical-state sub-schema instead of the richer canonical question contract.
  2. Why is that a separate dialect? Because context-manager canonical state still stores `slot/message_count/value`, while active runtime stores `next_question/open_questions/reason/...`.
  3. Why is that lossy? Because router code can only recover slot-level meaning and not the same canonical question payload used by runtime memory and trace/meta.
  4. Why does it matter? Because a pending question can mean different things depending on whether code is reading runtime continuity or router compatibility state.
  5. Why is this a semantic protocol defect? Because the active question is still represented by two different schemas across adjacent active layers.
- **Root cause statement:** the webhook compatibility path still owns a legacy question-contract dialect; canonical dialog state and router getters have not been migrated onto the richer canonical pending-question projection.
- **Fix mechanism:** make context-manager canonical pending-question state normalize to the runtime canonical shape, make router getters/projectors read that shape first, and remove direct `slot`-based semantic reads from `decision.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_pending_question_contract(...)`
  - existing context-manager canonical dialog state plumbing
  - existing top-level `expected_reply_*` fields as compatibility projections only
- **External reuse:** Pydantic alias-driven validation guidance from official docs
- **Why not reinvent the wheel:** the codebase already has one projector that understands both legacy `slot` and canonical `next_question`; this block should route router compatibility through that seam instead of building new parsing logic.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** bounded router/context-manager contract alignment on top of the previously landed canonical question substrate.

## Invariant
- Policy-core remains the semantic owner.
- Router compatibility logic may project canonical question state for gating, but it must not invent new question meaning.
- `expected_reply_type/reason` stay compatibility projections, not the canonical source of truth.
- `pending_question_contract` in canonical dialog state speaks the same slot/semantic language as runtime continuity.

## Scope
- align context-manager canonical pending-question normalization with the runtime canonical shape
- make webhook context getters prefer canonical pending-question state
- update active `decision.py` reads that still depend on `pending_question_contract.slot`
- update focused router/context-manager tests

## Out of scope
- removing top-level `expected_reply_*` fields from public context
- acceptance baseline refresh
- retrieval, transport, or pack behavior changes
- full deletion of all legacy webhook compatibility helpers

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-router-canonical-question-projection-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_webhook_booking.py`

## Plan (1..N)
1. Migrate context-manager canonical pending-question normalization/builders to the canonical `next_question/open_questions/...` shape while still accepting legacy aliases on input.
2. Make router getters/projectors read canonical pending-question state first and keep top-level `expected_reply_*` as projections only.
3. Remove direct `slot`-based question-contract reads from `decision.py` and replace them with canonical projection reads.
4. Update focused tests and run the required local suite set.

## DoD
- context-manager canonical pending-question state normalizes to the same question-contract shape as runtime continuity
- router `_get_expected_reply_type/reason` derive from canonical pending-question state when it exists
- `decision.py` no longer depends on `pending_question_contract.slot` in the active path
- tests prove router compatibility consumes the canonical question contract, not a separate dialect

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
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
- focused router/context-manager test output
- required local suite outputs

## Rollback
- `git revert <commit>` for this bounded router/canonical-question alignment commit
- if router compatibility regresses, reopen RCA instead of restoring slot-based shadow schema

## No-go
- no new semantic regex branches
- no router-side semantic repair layer
- no new question-contract schema
- no continued writes of `slot/message_count/value` as the router canonical question contract

## Risks/Blockers
- direct tests may assert the old context-manager canonical pending-question payload
- router code that clears only top-level expected-reply fields may need coordinated canonical-state clearing to avoid stale state

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: top-level `expected_reply_type/reason` still remain in webhook context as compatibility projections for non-migrated surfaces.
- `Why not in this block`: this slice aligns the canonical source and active router consumers first; deleting the public/top-level projections is a separate cleanup once all consumers are proven migrated.
- `Risk if deferred`: context snapshots can still expose legacy projection fields even after router semantics are canonicalized.
- `Linked follow-up Task Package(s)`: next block should either remove or formally project top-level `expected_reply_*` from canonical question state across remaining webhook surfaces.
- `Expiry/trigger to stop deferral`: before claiming full closure of webhook question-contract dialect drift.

## Next-block contract (mandatory)
- `Next block objective`: delete or strictly projection-limit top-level webhook `expected_reply_*` state once all remaining consumers are moved to canonical pending-question state.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason" truffles-api/app/routers/webhook truffles-api/tests/test_message_endpoint.py`
- `Blocked-by conditions`: any failing suite that still proves active router logic depends on the old top-level fields as source-of-truth.
- `Owner role for closure`: Brain / Top Architect
