# TP-2026-03-02-p9-contract-oracle-migration-wave1-a1

## Block identity
- `BLOCK_ID`: SIG-P9-CONTRACT-ORACLE-MIGRATION-W1-A1
- `PARENT_BLOCK_ID`: TP-2026-02-21-consultant-contract-first-remediation-a1
- `DEPENDS_ON`: TP-2026-03-02-contract-test-migration-master-a1
- `UNLOCKS`: P9 closure progression and reduction of text-oracle brittleness

## Название/цель
Продолжить `P9 Contract Test Migration`: убрать часть оставшихся text-oracle asserts из `test_message_endpoint.py` (multi-truth/booking-info-interrupt/consult-recommendation slice) и заменить их на контрактные проверки по `decision_meta/decision_trace/outcome`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONSULTANT.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_knowledge_service.py` (tracked as remaining residual in parent TP)
- `Baseline commands`:
  - `rg -n "assert .* in response\.bot_response|assert any\(token in response_text" truffles-api/tests/test_message_endpoint.py`
  - `rg -n "assert .* in result" truffles-api/tests/test_knowledge_service.py`
- `FACT findings`:
  - В `test_message_endpoint.py` остаются текстовые asserts в P9-related сценариях (consult recommendation, booking info interrupt, multi-truth).
  - В `test_knowledge_service.py` есть текстовые asserts форматирования (будут отдельным follow-up wave, не блокируют этот срез).
- `Detected drift (docs vs code)`: соответствует parent TP статусу `P9 partial`.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI graders guide evaluate outputs beyond exact string match`
- **Date/time (local):** `2026-03-02 14:52, Asia/Almaty`
- **Why this query is precise:** нужен primary reference для migration от brittle string assertions к rubric/contract checks.
- **Sources opened (from this query):**
  - OpenAI docs, Graders guide: `https://platform.openai.com/docs/guides/graders`
  - OpenAI docs, Evals design guide: `https://platform.openai.com/docs/guides/evals-design`
- **Existing solutions found:**
  - Оценка результата по structured criteria/rubric вместо exact text match.
  - Контрактные outcome assertions как устойчивый oracle.
- **Decision:** `integrate`
  - В тестах заменить phrase-based checks на meta/trace/action intent assertions.
- **Rejected options:**
  - Сохранять phrase-level assertions как primary acceptance oracle.
- **Open questions:**
  - Нужен второй wave для utility formatting tests (`test_knowledge_service.py`).

## Root cause (mandatory)
- **Symptom:** `P9` остается partial из-за text-oracle asserts.
- **Minimal reproduction:**
  - `rg -n "assert .* in response\.bot_response|assert any\(token in response_text" truffles-api/tests/test_message_endpoint.py`
- **Evidence to capture:** diff migrated tests + targeted pytest green.
- **Five Whys (or equivalent):**
  1. Почему text-oracle остались? Исторические тесты были ориентированы на формулировку ответа.
  2. Почему это проблема? Legit paraphrase вызывает false-fail.
  3. Почему не закрыто ранее? Приоритет был на runtime firebreak.
  4. Почему миграция нужна сейчас? Parent TP требует contract-first acceptance.
  5. Почему wave approach? Большой объем тестов, нужен безопасный поэтапный перенос.
- **Root cause statement:** тесты используют язык ответа как primary oracle вместо структурного контракта outcome/meta.
- **Fix mechanism:** заменить текстовые проверки в целевом срезе на action/intent/meta/trace invariants.

## Reuse-first plan (mandatory)
- **Internal reuse:** `decision_meta`, `decision_trace`, existing helper assertions в `test_message_endpoint.py`.
- **External reuse:** contract/rubric evaluation pattern from OpenAI graders/evals docs.
- **Why not reinvent the wheel:** необходимые contract signals уже пишутся рантаймом.

## Invariant
- Не меняем runtime behavior.
- Не ослабляем coverage (assertions остаются строгими, но по контракту).
- Не добавляем новые string-oracle asserts.

## Scope
- Мигрировать text-oracles в целевом срезе `test_message_endpoint.py`:
  - `test_consult_recommendation_prefers_pack_service_decision_over_service_matcher`
  - `test_booking_info_interrupt_pricing_with_expected_name_suppresses_booking_prompt`
  - `test_multi_truth_reply_handles_hours_and_price_in_single_segment`
- Обновить parent TP execution status по факту wave1.

## Out of scope
- Полная миграция всех text-oracle asserts во всем репозитории.
- Runtime code changes.
- Acceptance L3 runs.

## Touch-list
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `STATE.md` (optional status note if scope affects NOW summary)

## Plan (1..N)
1. Заменить phrase/text asserts в трех target tests на contract assertions.
2. Проверить, что сценарии все еще подтверждают intended behavior (routing + meta/trace invariants).
3. Прогнать targeted pytest slice.
4. Обновить parent TP status note для P9 wave1.

## DoD
- В трех target tests нет phrase-level business string assertions как primary oracle.
- Тесты проверяют outcome через `decision_meta/decision_trace` и routing behavior.
- Targeted checks green.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "consult_recommendation_prefers_pack_service_decision_over_service_matcher or booking_info_interrupt_pricing_with_expected_name_suppresses_booking_prompt or multi_truth_reply_handles_hours_and_price_in_single_segment"`
- `ruff check truffles-api/tests/test_message_endpoint.py`

## Evidence
- Diff с удалением text-oracle asserts в target tests.
- Outputs `Checks`.
- Parent TP status update.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** 0
- **Fail-fast / scenario lock:** targeted pytest only
- **Stop condition:** any regression in target tests
- **Escalation path:** Brain + Top Architect

## Release safety (mandatory for non-doc changes)
- **Strategy:** test-only migration (no runtime changes).
- **Go/no-go signals:** target tests green, no test coverage regression.
- **Rollback:** `git revert <commit>`.
- **Post-release monitoring window:** next CI unit-tests pass.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`
- `Drift closeout rule`:
  - `P9` status changes only after target test evidence.

## Rollback
- Revert test migration commit.

## No-go
- Нельзя заменять text-oracle на слабые asserts.
- Нельзя менять runtime ради прохождения тестов.
- Нельзя объявлять `P9 done` до следующих wave блоков.

## Risks/Blockers
- Некоторые сценарии могут не иметь достаточного meta signal; тогда нужен runtime meta extension TP.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remaining text-oracles outside target slice (`test_message_endpoint.py` other regions + `test_knowledge_service.py`).
- `Why not in this block`: wave1 intentionally bounded for low-risk migration.
- `Risk if deferred`: partial brittleness remains.
- `Linked follow-up Task Package(s)`: wave2/wave3 migration TP(s).
- `Expiry/trigger to stop deferral`: before declaring parent `P9` fully closed.

## Next-block contract (mandatory)
- `Next block objective`: migrate remaining text-oracles in `test_message_endpoint.py` LLM-policy-core area.
- `First deterministic check command`: `rg -n "assert .* in response\.bot_response|assert any\(token in response_text" truffles-api/tests/test_message_endpoint.py`
- `Blocked-by conditions`: missing stable meta signals for affected scenarios.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: target tests in `test_message_endpoint.py` listed in Scope.
- `Do not touch`: runtime webhook logic.
- `Open risks`: insufficient meta in some scenarios.
- `First command to verify`: target pytest command from `Checks`.
