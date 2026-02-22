# TP-2026-02-21-consultant-contract-first-remediation-a1

- Название/цель: Contract-first remediation консультанта без костылей: устранить расхождение поведения и измерения качества через единый `TurnOutcome` контракт, единый reducer `expected_reply_type`, transport-изоляцию и fail-closed quality gates.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по HQ1/strict), `SPECS/SYSTEM_REFERENCE.md`, `SPECS/CONSULTANT.md`, `STRATEGY/REQUIREMENTS.md`, `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`.
- Supersedes (для текущей remediation wave): operational часть firebreak-гейтов из `TP-2026-02-19-llm-first-firebreak-program.md`.

## Problem Snapshot (FACT)
- В `fix4..fix8` воспроизводится один и тот же strict-blocker: `dialog=6 turn=1 text="Какой у вас ассортимент услуг?" reason=` `expected_reply_type_mismatch`.
- В `fix8` наблюдаемость плохая: `total=76`, `with_outbox_text=11`, `duplicate_message_id=65`, `turns_without_observed_bot_text=65`.
- Oracle пропускает часть неправильных переходов: `mismatch_but_strict_pass=11`.
- Присутствуют эскалации при слабом контракте ожиданий: `escalate_with_expected_action_null=6`.
- Для ряда run нет `summary.json` (прерывания/невалидный финал), что делает evidence неполным для release acceptance.
- В последних HQ1 артефактах одновременно смешаны behavior и infra/observability причины (одни и те же bad-turn классы и инфраструктурные провалы считаются в одном контуре), что блокирует корректный приоритет фиксов и может искажать acceptance.

## Invariant
- Продуктовый контракт `FACT/COLLECT/HANDOFF` не меняется.
- Safety/LAW/Policy hard-gates не ослабляются.
- `decision_meta` и `decision_trace` обязаны отражать реальное решение ядра до transport.
- Никаких demo-specific хардкодов в runtime-core.
- `expected_reply_type` управляется из единого канонического reducer.
- Quality-run не может давать `PASS`, если ответ не наблюдаем (`unobserved`).

## Scope
- Введение канонического объекта результата хода `TurnOutcome` (contract-first).
- Рефактор expected-reply логики в единый reducer модуль.
- Разделение decision-kernel и transport-send шага.
- Contract-first диагностика в `ops/diagnose.py` с `unobserved` fail-closed gate.
- Ужесточение fallback-логики evaluator (убрать ложные strict-pass).
- Точечная стабилизация `services_overview` booking-followup в runtime через контракт, не через oracle-маскировки.
- Разделение bad-turn форензики на классы: `behavior` vs `infra/observability/oracle` с раздельными очередями исправлений.

## Out of scope
- Переписывание всей архитектуры webhook/policy.
- Изменение бизнес-правил и LAW.
- Массовая ревизия всех исторических сценариев.

## Target Architecture (без обходов)
1. `TurnOutcome` как единственный truth для качества
- Создать типизированный контракт (pydantic/dataclass) с минимумом:
- `action`, `intent`, `tool_action`, `tool_decision`, `expected_reply_type`, `expected_reply_reason`, `contract_status`, `followup_prompt`, `observability`.
- Формировать и сохранять `TurnOutcome` до попытки отправки в провайдер.

2. Единый reducer `expected_reply_contract`
- Вынести переходы `expected_reply_type` в отдельный модуль.
- Все ветки (`calendar.*`, `catalog.service_query/services_overview`, interrupts, handoff) обязаны идти через reducer.
- Инвариант: reply, требующий продолжения диалога, не может завершиться без валидного `expected_reply_type` или явного reason-code очистки.

3. Transport isolation
- Decision-kernel возвращает `TurnOutcome + response_payload`.
- Transport adapter отправляет сообщение отдельно и фиксирует статус доставки отдельно.
- В тестах/quality-run использовать `TestTransportAdapter` (наблюдаемый sink) вместо непредсказуемого внешнего dedupe.

4. Fail-closed quality model
- Добавить `unobserved_turn` (нет наблюдаемого текста ответа + duplicate ack / transport unknown).
- `unobserved_turn_count > 0` => `semantic_valid=false` (run INVALID).
- Убрать broad fallback, где любое `service_choice/time/name` считалось `ok` без доказательства progress.

5. Contract-first acceptance
- L1/L2 валидны только при `infra_valid=true`, `semantic_valid=true`, `unobserved_turn_count=0`.
- Judge-off run не используется для финального acceptance.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/expected_reply_contract.py` (new)
- `truffles-api/app/schemas/turn_outcome.py` (new)
- `truffles-api/app/services/transport_adapter.py` (new)
- `truffles-api/app/services/transport_adapters/chatflow.py` (new or extracted)
- `truffles-api/app/services/transport_adapters/test_sink.py` (new)
- `ops/diagnose.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_reply_type_fallback.py`
- `truffles-api/tests/test_turn_outcome_contract.py` (new)
- `truffles-api/tests/test_expected_reply_contract.py` (new)
- `truffles-api/tests/test_quality_unobserved_gate.py` (new)
- `docs/REPORTS/2026-02-21-firebreak-human-quality-wave-hq1.md` (update evidence status)
- `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv` (update with resolved/unresolved status)

## Plan (PR waves)
1. Step-0: RCA normalization (обязательно до кода)
- Обновить `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv` и добавить столбец класса причины (`behavior`, `infra`, `observability`, `oracle`).
- Зафиксировать owner и трек исправления для каждого bad-turn.
- До завершения Step-0 запрещены новые full L1/L2 прогоны.

2. PR-A: Decision Contract Kernel
- Ввести `TurnOutcome` и единый reducer expected-reply.
- Подключить reducer в critical ветках (`calendar.*`, `catalog.service_query/services_overview`, `reschedule/cancel/check_booking`).
- Добавить trace/meta contract asserts на всех critical и early-return путях.

3. PR-B: Observability + Quality Gates
- Отделить transport adapter, добавить `TestTransportAdapter`.
- В `ops/diagnose.py` перейти на `TurnOutcome` как primary source.
- Добавить `unobserved_turn` и INVALID gate (`unobserved_turn_count > 0 => semantic_valid=false`).
- Убрать мягкие fallback-правила, маскирующие behavior defects (`mismatch_but_strict_pass`).

4. PR-C: Acceptance Closure (жесткий порядок)
- A: unit + targeted pytest (только после green можно идти дальше).
- B: micro replay no-judge на bad-turn наборе.
- C: micro replay critical на том же наборе.
- D: full L1 на `/tmp/booking_quality/blocking_scenarios_human.json`.
- E: full L2 `--judge-mode critical` только если full L1 green.
- Обновить report/evidence и оформить go/no-go пакет.

## DoD
- Поведенческий дефект `dialog 6 turn 1 services_overview` закрыт contract-way: `expected_reply_type=service_choice` фиксируется в outcome/meta/trace.
- Нет `mismatch_but_strict_pass` для booking reply transitions на canonical scenarios.
- `unobserved_turn_count=0` в acceptance run.
- L1: `hq1_bad_turn_count=0`, `expected_action_mismatch=0`, critical blocking set all zero.
- L2 critical: `judge_fail=0` для blocking set.
- Финальный evidence-пакет содержит `summary.json`, `brief.md`, `responses.jsonl`, `trace_bundle.jsonl` и обновлённый bad-turn catalog.
- Acceptance учитывает только сопоставимые и валидные run:
- один и тот же `scenarios-file`,
- одинаковые runtime параметры (`reset-before-dialog`, judge mode, manager/pending режим),
- `infra_valid=true` и `semantic_valid=true`.

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/expected_reply_contract.py truffles-api/app/schemas/turn_outcome.py`
- `ruff check ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/expected_reply_contract.py truffles-api/app/schemas/turn_outcome.py truffles-api/app/services/transport_adapter.py truffles-api/app/services/transport_adapters/chatflow.py truffles-api/app/services/transport_adapters/test_sink.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_reply_type_fallback.py truffles-api/tests/test_turn_outcome_contract.py truffles-api/tests/test_expected_reply_contract.py truffles-api/tests/test_quality_unobserved_gate.py`
- `pytest -q truffles-api/tests/test_turn_outcome_contract.py truffles-api/tests/test_expected_reply_contract.py truffles-api/tests/test_quality_unobserved_gate.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "services_overview or expected_reply_type or booking_interrupt"`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_reply_type_fallback.py`
- `pytest -q truffles-api/tests/test_transport_adapter.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode off --allow-judge-off --max-failures 5 --run-id booking-human-nojudge-hq1-l1-contract-first-a1`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/blocking_scenarios_human.json --count 8 --tool-hooks auto --reset-before-dialog --judge-mode critical --fail-on-thresholds --max-failures 10 --run-id booking-human-critical-hq1-l2-contract-first-a1`

## Evidence
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1/summary.json`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1/brief.md`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1/responses.jsonl`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1/trace_bundle.jsonl`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1/summary.json`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1/brief.md`
- `/tmp/booking_quality/*micro*/summary.json` (bad-turn micro replay no-judge + critical)
- Обновлённые: `docs/REPORTS/2026-02-21-firebreak-human-quality-wave-hq1.md`, `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv`

## Rollback
- `git revert <sha_pr_a>`
- `git revert <sha_pr_b>`
- `git revert <sha_pr_c>`
- Откат по PR-волнам, без разрушения связанных non-scope изменений.

## No-go
- Нельзя лечить behavior только через oracle-смягчение в `ops/diagnose.py`.
- Нельзя объявлять acceptance при `unobserved_turn_count > 0`.
- Нельзя запускать L2/L3 до закрытия micro-replay дефекта.
- Нельзя добавлять client/demo-specific хардкоды в runtime-core.
- Нельзя смешивать `infra_invalid` и behavior-решения в одном acceptance-вердикте без явной классификации причин в bad-turn catalog.
- Нельзя сравнивать несовместимые run (разные scenario/runtime режимы) как одно baseline решение.

## Risks/блокеры
- Рефактор reducer может затронуть много веток `decision.py`; нужен wave-by-wave merge.
- Без transport test adapter проблема `duplicate_message_id` будет продолжать размывать сигнал качества.
- Возможны новые strict-fails после ужесточения oracle; это ожидаемо и требует точечных исправлений поведения.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree path: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`
- Base ref: `origin/main`
- Merge policy: PR waves `A -> B -> C`, no rebase, merge only.
- Cleanup: Brain/Top Architect после merge (branch/worktree removal).
