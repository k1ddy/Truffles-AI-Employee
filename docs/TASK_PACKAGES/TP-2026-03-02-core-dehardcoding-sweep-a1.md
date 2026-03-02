# TP-2026-03-02-core-dehardcoding-sweep-a1

- Название/цель: Полностью закрыть `P7 Core De-hardcoding Sweep` для `info/booking/tool_registry`: убрать phrase/regex‑маршрутизацию из core‑файлов, перенести сигнал‑матчинг в pack/runtime слой и опереться на data‑lexicons. Цель: убрать бизнес‑семантику из core, сохранить LLM‑first ownership и contract‑first оркестр.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- Parent TP: `docs/TASK_PACKAGES/TP-2026-02-21-consultant-contract-first-remediation-a1.md` (`P7 Core De-hardcoding Sweep`).
- Branch: `fix/llm-first-firebreak-2026-02-19`.
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`.
- Base ref: `origin/main`.
- Merge policy: merge only (rebase запрещен).
- Cleanup: Brain/Top Architect после merge удаляет branch + worktree.

## Root cause (mandatory)

- Symptom: phrase/regex‑маршрутизация остаётся в core‑файлах, что нарушает `Semantic Ownership Gate` и `Pack/tenant as data` и делает доменное поведение зависимым от кода.
- Minimal reproduction:
  - `rg -n "_signal_phrase_list|RELATIVE_DAY_TOKEN_PATTERNS|BOOKING_HOUR_FALLBACK_PATTERN|_DATE_TOKEN_PATTERNS" truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/tool_registry_service.py`
- Evidence:
  - `truffles-api/app/routers/webhook/info.py` содержит `_signal_phrase_list` и прямые `any(phrase in normalized ...)`.
  - `truffles-api/app/routers/webhook/booking.py` содержит `RELATIVE_DAY_TOKEN_PATTERNS`, `DAYPART_TOKEN_PATTERNS`, `BOOKING_HOUR_FALLBACK_PATTERN`, `PHONE_PATTERN`.
  - `truffles-api/app/services/tool_registry_service.py` содержит `_DATE_TOKEN_PATTERNS` и прямой phrase‑match для `services_overview_phrases`.
- Five whys:
  - Почему core содержит phrase/regex маршрутизацию? — Локальные фиксы шли быстрее, чем перенос в pack/runtime слой.
  - Почему это проблема? — Доменные правила оказались в core, нарушая LLM‑first и data‑driven принципы.
  - Почему нельзя оставить как есть? — Рост ниш/тенантов усиливает дрейф и риск тест‑фиттинга.
  - Почему не вынесли раньше? — Фокус был на стабилизации quality chain и safety‑гейтах.
  - Почему сейчас? — `P7` остаётся missing; без него контрактные гейты не закрывают архитектурный дрейф.
- Root cause statement: core‑модули содержат доменные phrase/regex‑правила, которые должны жить в data/pack resolver слое.
- Fix mechanism: вынести сигнал‑матчинг и regex‑паттерны в runtime/pack‑сервис, а core‑файлы переключить на вызовы этих сервисов и lexicon‑данные.

## One web search (mandatory before implementation)

- Query: `Open Policy Agent policy as data decouple policy from application code`
- Date/time: `2026-03-02T08:09:40+05:00`
- Opened sources:
  - `https://www.openpolicyagent.org/docs/philosophy` (primary)
  - `https://www.openpolicyagent.org/docs/latest/` (primary)
- Ready solutions found:
  - Policy decoupling: правила должны жить отдельно от кода, а код должен запрашивать решение у policy/data слоя.
- Decision: `reuse/integrate`
  - Использовать принцип policy/data decoupling для переноса phrase/regex из core в pack/runtime слой.
- Rejected options:
  - Переписать оркестратор полностью (избыточно, противоречит no‑refactor‑all).

## Reuse-first (mandatory)

- Reuse: существующие `get_signal_lexicon_list`, `get_system_lexicon_list`, `get_system_anchor_groups`, `_normalize_text` из pack runtime.
- Integrate: new signal runtime service (тонкий слой) для переноса regex/phrase матчеров.
- Configure: lexicon‑ключи в `SYSTEM_LEXICONS.yaml` и pack‑data.
- Build: только минимальные wrapper‑функции и перенос существующей логики без изменения semantics.

## Release safety (mandatory)

- Rollout strategy: canary в рамках стандартного release‑потока (по правилам TP).
- Go/No-go: локальные deterministic тесты зелёные; no‑regression по targeted suites.
- Rollback: revert commit.

## Invariant

- Не менять контракт `FACT/COLLECT/HANDOFF`.
- Не добавлять новые phrase/regex ветки в core‑файлы.
- Не менять LLM‑first семантику; только перенос логики.

## Scope

- Вынести phrase/regex‑матчинг из:
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/services/tool_registry_service.py`
- Создать runtime‑сервис для сигнал‑матчинга и переключить core‑файлы на него.

## Out of scope

- Изменение поведения LLM policy core.
- Изменение acceptance lane или quality chain.
- Массовая миграция всех regex в кодовой базе.

## Touch-list

- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_service.py` (если потребуется)
- Новый файл `truffles-api/app/services/*_signal_*.py`
- `STRUCTURE.md`

## Plan

1. Вынести signal/regex‑матчинг в отдельный runtime‑сервис (минимальные wrapper‑функции).
2. Переподключить info/booking/tool_registry на новый сервис без изменения семантики.
3. Удалить phrase/regex‑паттерны из core‑файлов.
4. Прогнать targeted deterministic tests.
5. Обновить `Execution Status` в parent TP (P7).

## DoD

- В info/booking/tool_registry нет phrase/regex‑паттернов и прямых phrase‑match веток.
- Семантика не изменилась (контрактные тесты зелёные).
- Targeted tests из `Checks` зелёные.

## Checks

- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_master_info_flow.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "info_intents or booking_info_intents or expected_reply"`

## Evidence

- Вывод `Checks`.
- Diff, показывающий перенос phrase/regex‑матчеров в runtime‑сервис.

## Rollback

- `git revert <commit>`.

## No-go

- Нельзя добавлять новую phrase/regex‑маршрутизацию в core‑файлы.
- Нельзя менять продуктовые ответы.

## Риски/блокеры

- Возможный дрейф поведения при переносе matcher‑логики; нужен тест‑контур.

## Fitness Functions impacted

- P0 (Semantic Ownership): улучшение — core больше не содержит доменных phrase‑веток.
- P1 (Deterministic Boundaries): без изменений.
- P2 (Evidence Integrity): сохраняется, т.к. проверки deterministic.

### Execution Status Update (2026-03-02)

- Done: phrase/regex матчеры вынесены в `truffles-api/app/services/info_signal_service.py` и `truffles-api/app/services/booking_signal_service.py`; `info/booking/tool_registry` теперь вызывают signal helpers и lexicon‑данные без core‑паттернов.
- Checks: `pytest -q truffles-api/tests/test_booking_appointments.py` (60 passed).
- Checks: `pytest -q truffles-api/tests/test_master_info_flow.py` (29 passed).
- Checks: `pytest -q truffles-api/tests/test_message_endpoint.py -k "info_intents or booking_info_intents or expected_reply"` (18 passed, 252 deselected).
