# TP-2026-02-16-expected-reply-controller-a88

- Название/цель: Закрыть TP#2 и TP#3 на одном фиксированном сценарном наборе: вернуть сопоставимую метрику `expected_reply_deferred` и поднять `controller eligibility/attempted` в non-gated policy-tool ветках с контрактными тестами `decision_meta`.
- Canon refs: `STATE.md` NOW/GAP (booking quality), `AGENTS.md` (local-first, baseline integrity), `/tmp/booking_quality/offline-replay-20260215-p0-r27/scenarios.json`.

## Invariant
- Не менять функциональный контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять safety/policy/law gates.
- Не подгонять тесты через hardcode under-scenario behavior.

## Scope
- `ops/diagnose.py`: совместимая метрика `expected_reply_deferred` для новой таксономии (`expected_reply_blocked_by_info` + controller non-attempt).
- `decision.py`: выставлять observability `controller_eligible/controller_skipped_reason` для non-gated policy-tool path.
- `test_message_endpoint.py`: контрактные проверки `decision_meta` на обновленную observability.

## Out of scope
- Новый planner/controller алгоритм.
- Полная переработка replay/quality framework.
- Любые изменения вне TP#2/#3.

## Touch-list
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-02-16-expected-reply-controller-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-expected-reply-controller-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Обновить evaluator-метрику `expected_reply_deferred` для новой decision_meta таксономии.
2. Обновить observability в policy-tool non-gated ветке.
3. Добавить тесты по decision_meta контракту.
4. Прогнать целевые тесты + replay на тех же scenarios.
5. Открыть PR с evidence.

## DoD
- На том же `scenarios.json` метрика `expected_reply_deferred` считается корректно и сопоставимо.
- `controller_non_eligible` не завышается из-за non-gated policy-tool path (`policy_core_tool` reason вместо `not_run`).
- Контрактные тесты по `decision_meta` зелёные.
- Replay evidence приложен.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k \"policy_verifier or expected_reply_blocked_by_info or controller_skipped_reason\"`
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py ops/diagnose.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --client-slug demo_salon --scenarios-file /tmp/booking_quality/offline-replay-20260215-p0-r27/scenarios.json --count 10 --tool-hooks auto --reset-before-dialog --timeout-profile fast-replay --judge-mode off --allow-judge-off --run-id postmerge-expected-reply-controller-a88 --output-dir /tmp/booking_quality/postmerge-expected-reply-controller-a88 --allow-output-overwrite --skip-outbox`

## Evidence
- `/tmp/booking_quality/postmerge-expected-reply-controller-a88/summary.json`
- `/tmp/booking_quality/postmerge-expected-reply-controller-a88/responses.jsonl`

## Rollback
- Revert commits этой ветки.

## No-go
- Не трогать unrelated файлы.
- Не менять сценарии или baseline файл в этом TP.

## Risks/блокеры
- Разночтение legacy/new taxonomy для `expected_reply_deferred`.
- Потенциальное влияние observability на downstream аналитики (нужно сохранить обратную совместимость).

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-expected-reply-controller-a88`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect after merge.
