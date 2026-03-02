# TP-2026-03-02-p9-contract-oracle-full-closure-a1

## Block identity
- `BLOCK_ID`: SIG-P9-CONTRACT-ORACLE-FULL-CLOSURE-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: none
- `UNLOCKS`: `P9 Contract Test Migration` -> `done`

## Название/цель
Полностью закрыть `P9`: убрать оставшиеся бизнес text-oracle проверки из deterministic test suites и заменить их на contract/meta/trace asserts без снижения строгости.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p9-contract-oracle-migration-wave1-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_knowledge_service.py`
  - `truffles-api/tests/test_info_master_long_hair.py` (regression check only)
- `Baseline commands`:
  - `rg -n "assert .* in response\.bot_response|assert any\(token in response_text|assert .* in result" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`
  - `rg -n "decision_meta|decision_trace|contract|resolver_contract" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`
- `FACT findings`:
  - `P9 wave1` выполнен (3 целевых теста в `test_message_endpoint.py` уже на contract-oracle).
  - В других участках `test_message_endpoint.py` и `test_knowledge_service.py` остаются text assertions.
- `Detected drift (docs vs code)`: parent TP корректно фиксирует `P9 partial`.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI evals design structured grading vs exact string match`
- **Date/time (local):** `2026-03-02 15:25, Asia/Almaty`
- **Why this query is precise:** нужен source для migration от brittle text matching к structured contract evaluation.
- **Sources opened (from this query):**
  - OpenAI Evals design guide: `https://platform.openai.com/docs/guides/evals-design`
  - OpenAI Graders guide: `https://platform.openai.com/docs/guides/graders`
- **Existing solutions found:** rubric/structured criteria as primary oracle; exact text optional and non-primary.
- **Decision:** `integrate` contract/meta/trace oracle во всех оставшихся P9-участках.
- **Rejected options:** оставлять phrase-based checks как primary acceptance.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** тесты падают на легитимных перефразах и затрудняют развитие policy-core.
- **Minimal reproduction:**
  - `rg -n "assert .* in response\.bot_response|assert any\(token in response_text|assert .* in result" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`
- **Evidence to capture:** diff удаленных text-oracle asserts + targeted/full deterministic suite pass.
- **Five Whys (or equivalent):**
  1. Исторически тесты писались на конкретные фразы.
  2. Фразы неустойчивы к нормальным перефразам модели.
  3. Это создает false-fail и pressure на hardcode.
  4. Contract signals уже доступны, но не везде используются.
  5. Без полной миграции `P9` остается partial.
- **Root cause statement:** primary oracle привязан к тексту, а не к структурному контракту outcome/meta/trace.
- **Fix mechanism:** заменить оставшиеся business text asserts на структурные контрактные проверки.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `decision_meta/decision_trace`, contract assertion patterns из wave1.
- **External reuse:** OpenAI eval design principles.
- **Why not reinvent the wheel:** инструменты и patterns уже есть внутри тестов.

## Invariant
- Runtime поведение не меняется.
- Строгость тестов не снижается.
- Новые business text-oracle asserts не добавляются.

## Scope
- Полная миграция оставшихся business text-oracle asserts в `test_message_endpoint.py` и `test_knowledge_service.py`.
- Унификация helper assertions по contract/meta/trace.
- Обновление parent TP/STATE по завершению.

## Out of scope
- UI formatting-only checks, если они не про business semantics.
- Runtime code refactor.

## Touch-list
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_knowledge_service.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md`

## Plan (1..N)
1. Инвентаризация всех remaining text-oracle asserts.
2. Замена assertions на contract/meta/trace invariants.
3. Удаление дублирующих phrase-check helpers.
4. Прогон targeted suites.
5. Прогон полного deterministic test scope для затронутых файлов.
6. Обновление parent TP и `STATE.md` с фактами.

## DoD
- В `test_message_endpoint.py` и `test_knowledge_service.py` нет business text-oracle как primary check.
- Все мигрированные тесты проверяют outcome через contract/meta/trace.
- `P9` в parent TP переведен в `done`.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_knowledge_service.py`
- `pytest -q truffles-api/tests/test_info_master_long_hair.py`
- `ruff check truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`
- `rg -n "assert .* in response\.bot_response|assert any\(token in response_text|assert .* in result" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py`

## Evidence
- Diff migration asserts.
- `Checks` outputs.
- Parent TP + `STATE.md` update.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic tests only
- **Stop condition:** any regression in migrated suites
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** test-only rollout.
- **Go/no-go signals:** all target suites green, no runtime file changes.
- **Rollback:** `git revert <commit>`.
- **Post-release monitoring window:** next CI unit-tests.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
  - `STATE.md`
- `Drift closeout rule`:
  - `P9` меняется на `done` только при полном отсутствии business text-oracle leftovers.

## Rollback
- Revert test migration commit(s).

## No-go
- Ослаблять assertions до пустых sanity-check.
- Менять runtime код для «подгона» тестов.
- Добавлять новые phrase-based business checks.

## Risks/Blockers
- В некоторых сценариях может не хватать meta поля; тогда добавляется минимальный meta signal без semantic rewrite.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none.
- `Why not in this block`: n/a.
- `Risk if deferred`: n/a.
- `Linked follow-up Task Package(s)`: none.
- `Expiry/trigger to stop deferral`: n/a.

## Execution Status Update (2026-03-02)
- `STATUS`: in_progress.
- `Delivered in this pass`:
  - migrated a deterministic slice in `truffles-api/tests/test_message_endpoint.py` away from hardcoded business phrases toward contract/state checks for:
    - `test_consult_recommendation_prefers_pack_service_decision_over_service_matcher`
    - `test_consult_recommendation_forces_consult_intent_for_pack_service_decision`
    - `test_booking_info_interrupt_keeps_info_reply_without_prompt_leak`
    - `test_booking_info_interrupt_with_expected_reply_type_keeps_info_reply`
    - `test_booking_time_service_question_keeps_time_contract`
    - `test_booking_info_interrupt_without_policy_handler_uses_service_hint_for_pricing`
    - `test_intent_queue_sets_context_and_prompt`
    - `test_intent_queue_info_limit_skips_booking`
    - `test_intent_queue_choice_pricing_replies_and_updates_queue`
    - `test_intent_queue_choice_hours_matches_time_phrase`
    - `test_llm_policy_core_service_query_non_service_refs_routes_to_info`
    - `test_multi_truth_reply_handles_hours_and_service_without_booking`
  - converted `truffles-api/tests/test_knowledge_service.py` formatting asserts to structural line-based checks.
- `Validation`:
  - `ruff check truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py` -> pass;
  - `pytest -q truffles-api/tests/test_knowledge_service.py` -> `10 passed`;
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "consult_recommendation_prefers_pack_service_decision_over_service_matcher or consult_recommendation_forces_consult_intent_for_pack_service_decision or booking_info_interrupt_keeps_info_reply_without_prompt_leak or booking_info_interrupt_with_expected_reply_type_keeps_info_reply or booking_time_service_question_keeps_time_contract or booking_info_interrupt_without_policy_handler_uses_service_hint_for_pricing or intent_queue_sets_context_and_prompt or intent_queue_info_limit_skips_booking or intent_queue_choice_pricing_replies_and_updates_queue or intent_queue_choice_hours_matches_time_phrase or llm_policy_core_service_query_non_service_refs_routes_to_info or multi_truth_reply_handles_hours_and_service_without_booking or llm_policy_core_catalog_tool_decision_mismatch_contract_error_escalates_handoff or llm_policy_core_consult_duration_signal_sets_info_meta"` -> `12 passed, 258 deselected`.
- `Remaining scope`:
  - literal phrase-oracle asserts still exist in other `test_message_endpoint.py` sections (inventory command from this block still returns non-zero), therefore `P9` remains open.

## Next-block contract (mandatory)
- `Next block objective`: continue `P9` migration on remaining literal phrase-oracle assertions in `test_message_endpoint.py`.
- `First deterministic check command`: `rg -n "assert .*\"[^\"]+\" .*response\\.bot_response" truffles-api/tests/test_message_endpoint.py`
- `Blocked-by conditions`: regressions in migrated deterministic slice.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `rg` inventory command in FACT pre-check.
- `Do not touch`: webhook runtime code.
- `Open risks`: hidden text assertions in helper functions.
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py`.
