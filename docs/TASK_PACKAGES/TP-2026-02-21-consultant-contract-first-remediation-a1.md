# TP-2026-02-21-consultant-contract-first-remediation-a1

- Название/цель: Contract-first remediation консультанта без костылей: закрыть поведенческие дефекты booking/info диалога (слоты/даты/follow-up/timeout), убрать ложные green-прогоны, и перейти к устойчивому acceptance с целевой надежностью `>=95%` на full critical наборе.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по HQ1/strict), `SPECS/SYSTEM_REFERENCE.md`, `SPECS/CONSULTANT.md`, `STRATEGY/REQUIREMENTS.md`, `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`.
- Supersedes (для текущей remediation wave): operational часть firebreak-гейтов из `TP-2026-02-19-llm-first-firebreak-program.md`.
- Forensic update (обязательно): учтены прогоны за последние 14 часов на `2026-02-22` и полный разбор `scenarios.json`, `responses.jsonl`, `trace_bundle.jsonl`, `brief.md` по каждому run (кроме содержимого `summary.json` по отдельному требованию).

## Problem Snapshot (FACT)
- За последние 14 часов зафиксировано `16` run-директорий.
- Совокупно: `347` observed turn, `judge_fail=7`, `strict_fail=7`, `booking_prompt_leak=8`, `stale_booking_carryover=2`, `requested_date_time_like=3`.
- Два full L1 run неполные:
- `booking-human-nojudge-hq1-l1-contract-first-a1-r6`: `responses=36/112`, отсутствуют `brief.md` и `summary.json`.
- `booking-human-nojudge-hq1-l1-contract-first-a1-r8`: `responses=101/112`, `trace=100/101` (1 message без trace), отсутствуют `brief.md` и `summary.json`.
- В blocking-наборе подтвержден слабый oracle:
- `scenario_weak_expectation_turns=146/434` (`33.64%` turn без сильного контрактного ожидания);
- `reply_type_coverage=24.88%`, `action_coverage=3.23%`.
- Judge покрытие неполное:
- `judge_missing=251/347` (`72.33%` turn не judged), что делает strict-green недостаточным для acceptance.
- Подтверждены дефекты слотов/дат и response-composer drift:
- `requested_date` заполняется временем (`HH:MM`) вместо даты;
- info-turn ответы смешиваются с booking-followup (`"Отлично, время подходит. Как вас зовут?"`, `"На какую дату и время..."`);
- ветки booking_interrupt и tool/info reply не изолируют body ответа от followup-контракта.
- Выявлен процессный дефект run-economy:
- запускались несовместимые/неполные прогоны без валидного завершения и без жесткого gate на completion/parity.

## Confirmed Defect Catalog (FACT, message_id)
- Judge fail / missed booking intent (L2 critical r5):
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-004-10-74b9b7`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-005-07-69060e`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-005-14-29adaa`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-006-14-9fcd2d`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-007-02-f84ddf`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-007-12-2b2046`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-008-10-e51206`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-008-14-f237ad`
- Slot/date contract corruption (`requested_date` time-like):
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-005-07-69060e` (`requested_date=16:30`)
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-008-11-555085` (`requested_date=19:00`)
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-008-14-f237ad` (`requested_date=19:00`)
- `LLM-QUAL-booking-human-micro-critical-slotfix-a1-r6-001-12-ad427a` (`requested_date=16:30`)
- Timeout-degrade generic clarify в booking-turn:
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-005-14-29adaa`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-006-14-9fcd2d`
- Stale booking carryover в фактическом инфо-ответе (проходит strict):
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-001-09-2a01aa`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-003-08-02fb43`
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r5-007-05-f81f05`
- Incomplete run artifact (process defect):
- `booking-human-nojudge-hq1-l1-contract-first-a1-r6` (нет `summary.json`/`brief.md`).

## Invariant
- Продуктовый контракт `FACT/COLLECT/HANDOFF` не меняется.
- Safety/LAW/Policy hard-gates не ослабляются.
- `decision_meta` и `decision_trace` обязаны отражать реальное решение ядра до transport.
- Никаких demo-specific хардкодов в runtime-core.
- `expected_reply_type` управляется из единого канонического reducer.
- Для acceptance запрещены weak-oracle turn: в каждом turn должен быть минимум один проверяемый expectation.
- Ответ по календарным слотам обязан быть truth-consistent с tool outcome:
- нельзя заявлять доступность слота, если слот не присутствует в `available_slots_by_specialist`;
- нельзя писать `requested_date` в формате времени (`HH:MM`);
- нельзя генерировать конфликтное время вне user/tool grounding.
- Run-economy обязателен: повтор full-run без новых code changes и без новых дефект-классов запрещен.

## Scope
- Коррекция runtime-path для относительных дат и date/time сигналов в booking (`decision.py` + `tool_registry_service.py`).
- Завершение slot/date response contract (`requested_date/requested_time/resolved_date/availability_claim/available_slots_by_specialist`).
- Устранение stale booking prompt/carryover через единый reducer expected-reply.
- Фикс timeout-degrade ветки для booking-контекста (без generic clarify).
- Ужесточение quality-oracle в `ops/diagnose.py`:
- fail-классы для `requested_date_time_like`, `stale_booking_carryover`, `timeout_degrade_booking_generic`;
- hard gate на weak-oracle coverage в acceptance;
- hard gate на incomplete run artifacts.
- Введение run-economy gate (стоп повторов без прироста сигнала).
- Обновление сценарного контракта (`blocking_scenarios_human*.json`) для исключения пустых ожиданий.

## Out of scope
- Переписывание всей архитектуры webhook/policy.
- Изменение бизнес-правил и LAW.
- Массовая ревизия всех исторических сценариев вне blocking-набора.

## Target Architecture (обновлено по форензику)
1. Contract-first slot/date path
- В `calendar.list_slots` и `calendar.get_booking` обязательный контракт-слой перед ответом:
- нормализация даты;
- валидация `requested_date` типа;
- синхронизация claim vs slot-map.
- Любой контрактный промах отмечается reason-code в `decision_meta.turn_outcome`.

2. Canonical expected-reply reducer
- Все переходы `expected_reply_type` идут через один reducer.
- Запрещен append stale prompt, если текущий ответ уже завершает intent (info/fact или явный tool-result).

3. Timeout-degrade policy safety
- `policy_core_timeout_degrade` в booking-контексте не имеет права отправлять generic clarify.
- Разрешены только booking-safe fallback ветки (`ask_datetime`, `ask_service`, `ask_name`) с явным reason-code.

4. Quality fail-closed + run-economy
- Acceptance invalid, если:
- `weak_oracle_turn_count > 0`;
- нет `summary.json` или `brief.md`;
- `requested_date_time_like_count > 0`.
- Full-run запускается только если:
- есть code diff по touch-list;
- есть green предыдущего шага;
- есть прирост сигнала или закрытие конкретного defect-class.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/expected_reply_contract.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_booking_relative_date_resolution.py`
- `truffles-api/tests/test_calendar_slot_response_contract.py`
- `truffles-api/tests/test_booking_prompt_leak_guard.py`
- `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv`
- `docs/REPORTS/2026-02-21-firebreak-human-quality-wave-hq1.md`
- `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md`

## Plan (полный, обязательный порядок)
1. Step-0: Freeze + RCA lock (без новых full run)
- Обновить `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv` по фактам из run `r5/r6`.
- Добавить поля: `defect_class`, `owner`, `planned_test`, `status`, `source_run`.
- Зафиксировать weak-oracle turn list и удалить пустые ожидания в blocking-сценариях.
- До закрытия шага запрещены новые full L1/L2.

2. Step-1: Runtime slot/date normalization fix
- Исправить обработку относительных дат в runtime path (`завтрашний день`, `выходные`, `дни недели`).
- Убрать fallback на stale datetime из history, если в текущем turn есть date-signal.
- Добавить hard reject для `requested_date` в формате `HH:MM`.

3. Step-2: Slot response contract enforcement
- Гарантировать согласованность между текстом, `availability_claim` и `available_slots_by_specialist`.
- Запретить followup `service_choice`, если слот-путь не завершен корректно.
- Добавить deterministic тесты на contradiction/fabricated/misaligned requested_date.

4. Step-3: Reducer + prompt leak cleanup
- Централизовать `expected_reply_type` переходы через reducer.
- Ввести response-composer isolation: в info/fact turn запрещено смешивать booking prompt в body ответа.
- Удалить stale append (`"Ещё был вопрос по записи..."`) в info/fact turn без релевантного booking-gap.
- Закрепить тестами leakage/carryover regressions.

5. Step-4: Timeout-degrade remediation
- Для booking-context заменить generic clarify на слот-ориентированный fallback.
- Проставлять `policy_core_guard` reason-code, чтобы QA отличал degradation от behavior bug.
- Добавить тесты на `timeout`/`deadline_exceeded` path.

6. Step-5: Diagnose hardening + run-economy
- Ввести fail-классы:
- `requested_date_time_like`,
- `stale_booking_carryover`,
- `timeout_degrade_booking_generic`,
- `incomplete_run_artifact`.
- В acceptance сводке считать run INVALID при нарушении этих классов.
- Добавить hard Run Integrity Gate:
- `responses_turn_count == scenario_expected_turn_count`;
- `trace_bundle_turn_count == responses_turn_count`;
- mismatch -> `incomplete_run_artifact` + semantic invalid.
- Добавить guard против повторных full-run без code diff и без обновленного сценарного контракта.

7. Step-6: Validation cadence (строго)
- `micro no-judge` -> `micro critical` -> `full L1` -> `full L2 critical`.
- Следующий шаг разрешен только при green предыдущего.
- При fail: stop-the-line, RCA, только потом повтор.

8. Step-7: Acceptance and closure
- Обновить report/evidence,
- сверить закрытие всех message_id из defect catalog,
- сформировать go/no-go пакет для записи в `STATE.md` (Brain/Top Architect).

## DoD
- Full L2 critical: `strict_pass_rate >= 0.95`, `judge.counts.fail=0`, `hq1_bad_turn_count=0`.
- `requested_date_time_like_count=0` на acceptance run.
- `timeout_degrade_booking_generic_count=0`.
- `stale_booking_carryover_count=0`.
- `booking_prompt_leak_count=0`.
- `weak_oracle_turn_count=0` в blocking-сценариях.
- `run_completion_ratio=1.0` (`responses == expected_scenario_turns`).
- `trace_response_delta=0` (`trace_bundle_lines == responses_lines`).
- Нет incomplete run artifacts (`summary.json` и `brief.md` обязательны).
- Все message_id из `Confirmed Defect Catalog` имеют регрессионный тест и переходят в green.
- Финальный evidence-пакет содержит `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl`, обновленный defect catalog.

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/expected_reply_contract.py`
- `ruff check ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/expected_reply_contract.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_booking_relative_date_resolution.py truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_booking_prompt_leak_guard.py`
- `pytest -q truffles-api/tests/test_booking_relative_date_resolution.py truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_booking_prompt_leak_guard.py`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking or expected_reply_type or timeout_degrade"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_interrupt or prompt_leak or style_reference"`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human_dialog6.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode off --allow-judge-off --max-failures 5 --run-id booking-human-micro-nojudge-slotfix-a1-r7`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human_dialog6.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode critical --fail-on-thresholds --max-failures 10 --run-id booking-human-micro-critical-slotfix-a1-r7`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode off --allow-judge-off --max-failures 5 --run-id booking-human-nojudge-hq1-l1-contract-first-a1-r7`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode critical --fail-on-thresholds --max-failures 10 --run-id booking-human-critical-hq1-l2-contract-first-a1-r7`

## Evidence
- Новый форензик:
- `/tmp/booking_quality/analysis_last5h_deep.json`
- `/tmp/booking_quality/analysis_last5h_report.md`
- `/tmp/booking_quality/analysis_last5h_full.json`
- `/tmp/booking_quality/analysis_last14h_report.md`
- `/tmp/booking_quality/analysis_last14h_full.json`
- `/tmp/booking_quality/analysis_last14h_files.tsv`
- `/tmp/booking_quality/analysis_last14h_dialogs.tsv`
- Критический run:
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r5/summary.json`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r5/brief.md`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r5/responses.jsonl`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r5/trace_bundle.jsonl`
- Незавершенный run (process gap):
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r6/responses.jsonl`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r6/trace_bundle.jsonl`
- Обновляемые документы wave closure:
- `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv`
- `docs/REPORTS/2026-02-21-firebreak-human-quality-wave-hq1.md`

## Rollback
- `git revert <sha_step1_step4>`
- `git revert <sha_step5>`
- `git revert <sha_step6_step7>`
- Откат по волнам, без разрушения нецелевых изменений.

## No-go
- Нельзя объявлять acceptance по run с отсутствующим `summary.json`/`brief.md`.
- Нельзя оставлять пустые ожидания в blocking-сценариях.
- Нельзя лечить поведение только oracle-смягчением в `ops/diagnose.py`.
- Нельзя допускать `requested_date` в формате времени.
- Нельзя отправлять generic timeout clarify в booking-context.
- Нельзя делать full повторы без code diff и без закрытого RCA по предыдущему fail.
- Нельзя сравнивать несовместимые run (разный scenario/runtime режим) как единый baseline.

## Risks/блокеры
- Фикс date-signal path может вскрыть скрытые регрессии в calendar.list_slots/book_slot.
- При ужесточении oracle число fail на первом цикле вырастет; это ожидаемая миграция, не повод откатывать гейты.
- Timeout-path чувствителен к latency; нужен контроль budget/degrade порогов вместе с тестами.
- Без дисциплины run-economy команда будет снова терять время на повтор без прироста сигнала.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree path: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`
- Base ref: `origin/main`
- Merge policy: PR waves `A(runtime) -> B(diagnose+tests) -> C(evidence)`, no rebase, merge only.
- Cleanup: Brain/Top Architect после merge (branch/worktree removal).
