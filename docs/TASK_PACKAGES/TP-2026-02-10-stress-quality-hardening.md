# TP-2026-02-10-stress-quality-hardening

- Название/цель: Закрыть GAP из `STATE.md` NOW по Hybrid LLM-plan chaos-sim (`action_mismatch` / `expected_reply_type_mismatch` / `missing_decision_meta` / `missing_decision_trace` / `ood_false_positive`) через усиление контрактов tool-flow, trace/meta и quality evaluator, без test-fitting и без деградации runtime safety.
- Canon refs: `STATE.md` NOW (Hybrid LLM-plan chaos-sim GAP), `AGENTS.md` (Hard Preflight Gate, Local-first validation law, Anti Test-Fitting Gate, Demo-Neutral Gate), `SPECS/SYSTEM_REFERENCE.md` (trace/meta contracts, quality evidence rules).

## Invariant
- FACT/COLLECT/HANDOFF контракт не меняется.
- Никаких хардкодов словарей/regex как основного oracle для прохождения quality.
- Проверка качества опирается на контрактные сигналы (`decision_meta`, `decision_trace`, tool outcomes), а не на точный текст ответа.
- `demo_salon` остается канарейкой, runtime-core остается pack-agnostic.

## Scope
- Усилить `tool_registry_service` для fail-closed обработки некорректных `appointment_id`.
- Добавить контракт `time_mismatch` для `calendar.get_booking` при проверке "подтверди запись на 14:00".
- Укрепить `ops/diagnose.py llm-quality`:
- booking-progress считать по изменению slot key/value, а не только по количеству слотов;
- suppress false `judge_fail` для check-booking turn, если tool-contract выполнен.
- Добавить/обновить тесты на новые контракты.
- Прогнать local deterministic contour + llm-quality replay/lock-run с evidence.

## Out of scope
- DEC-level архитектурная перестройка runtime.
- Переписывание policy-core и escalation lifecycle.
- Подгонка логики под конкретные фразы или одиночные тест-кейсы.

## Touch-list (files/tables)
- `ops/diagnose.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_booking_quality_progress_gate.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `docs/SESSIONS/SESSION-2026-02-10-stress-quality-a1.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Проанализировать причины strict-fail в llm-quality и связать их с runtime/tool contract.
2. Внести fail-closed фиксы в tool registry для `appointment_id` и check-booking mismatch.
3. Усилить quality evaluator (booking progress + judge suppression по contract evidence).
4. Добавить/обновить unit/regression тесты на новые контракты.
5. Прогнать обязательный local deterministic контур.
6. Прогнать llm-quality с preflight и сохранить `summary/brief/responses` артефакты.

## DoD
- Некорректный `appointment_id` больше не ломает tool-call исключением; возвращается контрактная ошибка.
- Check-booking "не на это время" возвращает `tool_decision=time_mismatch` и корректный user-facing ответ.
- llm-quality не считает turn провальным, если check-booking tool-contract выполнен по trace/meta/tool output.
- booking progress gate учитывает изменение slot значений и ловит фактический прогресс.
- Локальный обязательный тестовый контур по core проходит.

## Checks
- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_booking_quality_progress_gate.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id booking-hard-2026-02-10-r25`

## Evidence
- LLM-quality artifacts: `/tmp/booking_quality/booking-hard-2026-02-10-r25`
- LLM-quality artifacts: `/tmp/booking_quality/booking-hard-2026-02-10-r26`
- Детальные strict failures до фикса: `/tmp/booking_quality/booking-hard-2026-02-10-r21`
- pytest outputs from mandatory contour (local-first).

## Rollback
- `git revert COMMIT_SHA_FROM_THIS_BRANCH` без изменения схемы БД и без ручной правки trace/данных.

## No-go
- Не ослаблять safety/policy ради "зеленого" качества.
- Не добавлять must_include как единственный oracle вместо trace/meta contract checks.
- Не выполнять "доказательства" через ручную чистку БД/trace.
- Не закреплять runtime behavior под demo-only паттерны.

## Риски/блокеры
- LLM latency/timeout может давать шум в `degraded_fallback_rate`; это не отменяет semantic fixes.
- Нужна дисциплина replay по тем же scenarios/baseline, иначе сравнение метрик невалидно.

## Branch / Worktree
- Branch: `feat/2026-02-10-stress-quality-a1`
- Worktree: `/home/zhan/worktrees/2026-02-10-stress-quality-a1`
- Base ref: `origin/main`
- Merge policy: PR в `main`, без rebase.
- Cleanup: после merge закрыть сессию `scripts/session_end.sh --status done` и удалить worktree/branch.
