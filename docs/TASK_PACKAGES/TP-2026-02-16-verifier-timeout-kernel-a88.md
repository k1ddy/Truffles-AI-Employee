# Task Package: LLM Reliability Kernel (TP-1+TP-3)

- Название/цель: Закрыть P0-риск неверных side-effect действий и деградаций по timeout/budget в runtime без архитектурного усложнения: внедрить `verifier lite` + `timeout/budget resilience` в одном цикле.
- Canon refs: `STATE.md` (NOW: policy-core hardening + booking replay gaps), `STRATEGY/REQUIREMENTS.md` (Hard-LAW, reliability, no test-fitting), `AGENTS.md` (Local-first validation law, booking anti-drift loop).

## Invariant
- `FACT/COLLECT/HANDOFF` контракт не ломается на каждом user-turn.
- `_legacy.py` остаётся adapter-only; оркестрацию не переносить в entrypoints.
- Нет client-specific хардкодов и не расширять словари/lexicon для прохождения quality.

## Scope
- Verifier-lite в runtime tool path: строгая проверка args + post-condition для критичных transitions.
- Timeout/budget resilience: управляемый fallback/retry поведение и мета/trace прозрачность деградаций.
- Контрактные тесты и replay evidence на фиксированных сценариях.

## Out of scope
- Полная переработка memory stack (TP-2 отдельно).
- Cross-business suite/pack rollout (TP-4 отдельно).
- Большой архитектурный DEC-уровень рефактор webhook pipeline.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`

## Plan
1. Уточнить текущие деградационные/timeout ветки и точки tool execution в decision path.
2. Добавить verifier-lite: args schema gate + post-condition guard для критичных tool outcomes.
3. Усилить timeout/budget resilience: deterministic fallback path с обязательным decision_meta/trace.
4. Добавить контрактные тесты на verifier + timeout regression.
5. Прогнать локальный контур (targeted pytest + replay на lock scenarios) и собрать evidence.

## DoD
- Невалидные tool args не исполняются и не приводят к side-effect; вместо этого `clarify` или `handoff` по контракту.
- При timeout/budget деградации бот не уходит в пустой/ломающий ответ: фиксируется управляемый fallback с trace/meta.
- `decision_meta` содержит проверяемые поля verifier/degradation на последнем inbound.
- На replay по фиксированным сценариям не растут `missing_bot_reply` и `hard_fail`; strict не ухудшается больше tolerance (<= 0.02) от lock baseline.

## Checks
- `pytest -q truffles-api/tests/test_llm_policy_core.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "tool or timeout or booking"`
- `ruff check truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/intent_service.py truffles-api/app/services/ai_service.py truffles-api/app/schemas/intent.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_llm_policy_core.py truffles-api/tests/test_booking_quality_response_guard.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/offline-replay-20260215-p0-r27/scenarios.json --baseline-summary /tmp/booking_quality/offline-replay-20260215-p0-r27/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --max-failures 20 --run-id offline-replay-20260216-verifier-timeout-a88`

## Evidence
- `summary.json` + `brief.md` + `responses.jsonl` для replay run.
- Счётчики verifier/degradation из `decision_meta` (`tool_decision`, `tool_args`, `llm_degradation_reason`, `router/controller eligibility`).
- Результаты targeted pytest/ruff.

## Rollback
- Revert commit/PR целиком.
- В случае регрессии replay вернуть предыдущие guard-ветки без изменения contracts.

## No-go
- Не трогать memory-архитектуру (TP-2).
- Не трогать cross-business infra (TP-4).
- Не менять БД/trace вручную ради evidence.

## Risks and blockers
- Долгий replay прогон и флуктуации LLM; сравнение только с lock scenarios.
- В рабочем дереве есть параллельные незакоммиченные изменения по console; не включать их в diff этого TP.
