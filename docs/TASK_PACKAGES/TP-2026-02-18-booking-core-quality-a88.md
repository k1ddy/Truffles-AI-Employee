# TP-2026-02-18-booking-core-quality-a88

## Название/цель
Стабилизировать booking core-поведение после ручного аудита: убрать повторные переспросы, лишние эскалации, провалы confirm-flow и деградации `degraded_collect`, затем подтвердить результат детерминированными тестами и manual line-by-line аудитом `responses.jsonl` без judge.

## Canon refs
- Owner docs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/SYSTEM_REFERENCE.md`.
- STATE NOW/GAP: manual audits по `/tmp/booking_quality/*` с проблемами `redundant_*_reask`, `booking_confirm_flow_gap`, `escalate_without_explicit_manager_request`, `deadline_exceeded`.

## Invariant
- Не ухудшить LAW/policy safety: эскалация только по явному сигналу менеджера/фрустрации или hard-law.
- Не нарушить booking contract: при наличии слотов не переспрашивать уже известные `service/datetime/name`.
- Не вводить хардкод клиентских фактов в core-логику.

## Scope
- Правки в policy/booking decision flow для follow-up, booking_interrupt, confirm recovery, degraded_collect.
- При необходимости корректировка pipeline budget для уменьшения `deadline_exceeded` без ослабления safety.
- Обновление сценарного медиапути на канонический `/home/zhan/TrufflesLogoClear.png`.

## Out of scope
- Большие архитектурные переписывания и DEC-level перестройка.
- Изменение бизнес-политик/LAW контракта.
- Изменения unrelated Console UI.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-02-18-booking-core-quality-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать session/worktree и baseline состояния ветки.
2. Внести правки в `decision.py`/`booking.py` по 4 проблемным зонам (reask, interrupt, confirm, degraded_collect) + budget.
3. Добавить/обновить тесты контрактов на новые ветки поведения.
4. Прогнать обязательные deterministic тесты.
5. Прогнать `llm-quality` с `judge_mode=off` на runtime из текущего кода.
6. Выполнить manual line-by-line аудит каждого `responses.jsonl`, сохранить `manual_dialog_audit.tsv` и `logic_gaps.tsv`.
7. Обновить `STATE.md`, подготовить PR с evidence.

## DoD
- `redundant_service_reask` и `redundant_datetime_reask` устранены на целевых цепочках.
- Confirm-flow даёт guided recovery и не уходит в лишний handoff без явного manager signal.
- `degraded_collect` не отдает generic fallback при полноте booking slots.
- Фиксация media reference path на `/home/zhan/TrufflesLogoClear.png`.
- Все обязательные проверки ниже зелёные или задокументирован BLOCKED с причиной/evidence.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py scripts/booking_dialog_scenarios.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode off --run-id booking-core-quality-a88`

## Evidence
- Пути артефактов quality run: `responses.jsonl`, `summary.json`, `trace_bundle.jsonl`, `manual_dialog_audit.tsv`, `logic_gaps.tsv`.
- Выдержки `decision_trace/decision_meta` по ранее проблемным ходам.
- `git status -sb`, `git diff --stat`, команды проверок и результат.
- Запись в `STATE.md` до merge.

## Rollback
- `git revert HEAD` для отката последнего merge-коммита PR.
- Если деградация runtime: вернуть предыдущий commit в ветку и повторить deterministic + replay checks.

## No-go
- Хардкод клиентских фактов/словарей под тест.
- Изменение `_legacy.py` под оркестрацию.
- Редактирование БД/trace ради косметического evidence.
- Merge без полного локального контура и manual line-by-line аудита.

## Branch / Worktree
- Branch: `fix/2026-02-18-booking-core-quality-a88`
- Worktree path: `/home/zhan/worktrees/2026-02-18-booking-core-quality-a88`
- Base ref: `origin/main`
- Merge policy: merge commit (no rebase)
- Cleanup: Brain/Top Architect после merge (branch + worktree)

## Риски/блокеры
- Возможен BLOCKED по LLM quality при runtime/env дрейфе или отсутствующем ключе/инфра.
- Возможен шум по provider availability (calendar/provider_error), требуется отдельная пометка infra vs logic.
