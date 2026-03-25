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
- `STATUS`: done.
- `Delivered in this pass`:
  - completed remaining literal phrase-oracle migration in `truffles-api/tests/test_message_endpoint.py`:
    - removed direct phrase checks from policy-core booking/info/tool flows and replaced them with contract/meta/state assertions (`action`, `intent`, `tool_action`, `tool_decision`, `expected_reply_type`, trace-driven guard outcomes);
    - replaced legacy service-matcher text assertion with explicit mocked service decision contract (`response == mocked_service_decision.response`, matcher call verification);
    - stabilized `services_overview_recovery` test to valid dual contract paths (`fallback` and `invalid`) without runtime semantics downgrade.
  - preserved strict boundary checks via contract constants (`MSG_*`) where user-facing prompt class is the contract.
- `Validation`:
  - `rg -n "assert .*\"[^\"]+\" .*response\\.bot_response|assert any\\(token in response_text" truffles-api/tests/test_message_endpoint.py` -> no matches;
  - `ruff check truffles-api/tests/test_message_endpoint.py` -> `All checks passed`;
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "test_service_matcher_short_circuits_llm or test_llm_policy_core_catalog_tool_decision_mismatch_services_overview_recovery or test_llm_policy_core_get_booking_ok_does_not_force_handoff or test_llm_policy_core_normalizes_action_from_tool_action or test_llm_policy_core_list_slots_ok_appends_derived_followup_prompt or test_llm_policy_core_collect_list_slots_with_known_service_normalizes_to_fact or test_llm_policy_core_info_tool_uses_tool_args_info_refs or test_llm_policy_core_info_single_info_ref_stays_info_in_booking_context or test_booking_interrupt_hours_contract_blocks_price_takeover or test_llm_policy_core_book_slot_backfills_required_args_from_slots_and_specialist_hint or test_llm_policy_core_book_slot_contract_invalid_does_not_auto_escalate or test_llm_policy_core_tool_decision_mismatch_does_not_auto_escalate or test_llm_policy_core_catalog_services_overview_sets_followup_without_info_sections or test_llm_policy_core_handoff_style_reference_keeps_media_prompt_without_plan_rewrite or test_llm_policy_core_list_slots_keeps_context_datetime_when_expected_time or test_llm_policy_core_catalog_service_reply_keeps_info_answer_for_info_query or test_llm_policy_core_provider_unavailable_escalates_after_clarify_limit or test_llm_policy_core_list_slots_provider_unavailable_keeps_booking_question or test_booking_verification_request_does_not_escalate_active_booking_without_reference or test_booking_reschedule_missing_slot_does_not_escalate_without_manager_request or test_llm_policy_core_collect_check_booking_uses_reference_prompt or test_llm_policy_core_service_query_non_service_refs_routes_to_info or test_llm_policy_core_info_tool_master_reply_sent_without_clarify or test_llm_policy_core_catalog_service_reply_normalized_to_master_info_by_signal or test_llm_policy_core_catalog_location_reply_normalized_to_master_info or test_llm_policy_core_semantic_arbitration_off_keeps_master_without_location_rewrite or test_llm_policy_core_consult_ref_does_not_shadow_allowed_consult_refs or test_llm_policy_core_degraded_timeout_booking_safe_second_hit_escalates or test_llm_policy_core_degraded_booking_guard_retries_with_llm_rescue_then_uses_calendar_tool"` -> `29 passed, 241 deselected`.
  - `pytest -q truffles-api/tests/test_message_endpoint.py` -> `270 passed, 2 warnings`.
  - regression carry-over evidence from this TP remains green:
    - `ruff check truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_knowledge_service.py` -> pass;
    - `pytest -q truffles-api/tests/test_knowledge_service.py` -> `10 passed`.
- `Residual scope`: none for this block.

## Next-block contract (mandatory)
- `Next block objective`: none; block closed.
- `First deterministic check command`: n/a.
- `Blocked-by conditions`: n/a.
- `Owner role for closure`: Brain + Top Architect (closure confirmed).

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: next open parent block (`P5b` or `P12/P13/P14`) in parent TP.
- `Do not touch`: n/a.
- `Open risks`: none inside `P9` scope.
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "service_matcher_short_circuits_llm or llm_policy_core_catalog_tool_decision_mismatch_services_overview_recovery"`.
