# TP-2026-02-14-universal-consultant-p0-contract-kernel-a1

- Название/цель: стабилизировать core-поведение до контрактного уровня `99%` для ответов и использования инструментов через fail-closed контуры (`policy_core -> tool -> verify`), убрать системные причины ложных booking-prompt, и ввести tenant/branch-aware tool permission policy без нишевых хардкодов.
- Canon refs: `STATE.md` (NOW/GAP: degraded fallback и нестабильный strict pass), `AGENTS.md` (P0/P1 fitness, Anti Test-Fitting Gate, Demo-Neutral Gate, Lexicon/Regex Delta Gate), `SPECS/SYSTEM_REFERENCE.md` (decision_meta/trace/tool evidence contracts), `STRUCTURE.md` (размещение артефактов).

## Invariant
- FACT/COLLECT/HANDOFF продуктовый контракт не ломается.
- Safety-контур (LAW/policy/pending/manager_active) остается приоритетом выше pass-rate.
- Никаких расширений словарей/лексиконов/regex как основного способа исправления.
- Никакой подгонки под `demo_salon` или любую конкретную нишу.
- На каждом user-turn сохраняются валидные `decision_meta` и `decision_trace`.

## Scope
- Ввести детальную таксономию причин LLM деградации вместо агрегированного `error`.
- Переписать degraded path в `policy_core_guard` на intent-aware rescue matrix:
- если вопрос info-класса, отвечать по truth/tool path, а не автоматически `booking_prompt`.
- Ввести capability policy для инструментов (`allow/deny` на client/branch scope) и enforce перед execution.
- Усилить schema/args validation для tool-вызовов до исполнения side effects.
- Добавить контрактные тесты и replay-гейты под новые инварианты.

## Out of scope
- DEC-level переписывание всей архитектуры.
- Замена LLM-провайдера или миграция на новый стек моделей.
- Массовая перепаковка knowledge packs.

## Touch-list (files/tables)
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/schemas/capabilities.py`
- `truffles-api/app/services/capabilities_runtime.py`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Добавить error taxonomy в `intent_service` и прокинуть детальные причины в `decision_meta.policy_core_degrade_reason`.
2. Реализовать intent-aware degraded rescue matrix в `decision.py` с приоритетом info truth/tool контрактов.
3. Расширить capability schema полем инструментальных разрешений (client + branch override).
4. Добавить runtime enforcement: блок неразрешенного `tool_action` до `execute_tool_action`.
5. Усилить precondition/postcondition валидацию tool args/outcomes и trace-stage при каждом отказе.
6. Добавить regression tests (no lexicon changes) и replay checks по frozen scenarios.

## DoD
- `policy_core_degrade_reason` больше не агрегируется в общий `error` для типовых причин.
- В деградации info-вопросы не уходят в ложный `booking_prompt` (контрактно подтверждено trace/meta).
- Неразрешенный по capabilities инструмент не вызывается и дает контролируемый ответ + trace evidence.
- `contract_success_rate >= 0.99` на frozen replay по контрактным метрикам.
- `missing_bot_reply = 0`.

## Checks
- `pytest -q truffles-api/tests/test_llm_policy_core.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_core or degraded or capabilities"`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/booking-lock-42/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-42/summary.json --count 10 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression`

## Evidence
- `summary.json` + `brief.md` replay-run с frozen scenarios.
- фрагменты `decision_trace`/`decision_meta` для info-vs-booking conflict cases.
- evidence по blocked tool policy (`tool_not_allowed`) с trace stage.
- логи pytest для таргетных suites.

## Rollback
- `git revert SHA_FROM_THIS_BRANCH` в ветке реализации.
- Feature-flag rollback:
- отключение tool policy enforcement в runtime config.
- отключение нового degraded rescue matrix в runtime config.

## No-go
- Запрещено расширять словари/regex для прохождения quality как основной фикс.
- Запрещено использовать текстовые `must_include` как основной oracle вместо trace/meta/tool contracts.
- Запрещено изменять runtime-поведение под конкретный pack/клиента.

## Риски/блокеры
- Возможен временный рост escalation при fail-closed policy до стабилизации capability профилей.
- Ужесточение validation может вскрыть скрытые дефекты tool args в текущих сценариях.

## Branch / Worktree
- Branch: `feat/2026-02-14-universal-consultant-p0-contract-kernel-a1`
- Worktree: `/home/zhan/worktrees/2026-02-14-universal-consultant-p0-contract-kernel-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main`, no rebase
- Cleanup: `scripts/session_end.sh --status done` + cleanup worktree/branch после merge
