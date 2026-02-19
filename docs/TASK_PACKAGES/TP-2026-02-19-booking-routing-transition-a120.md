# TP-2026-02-19-booking-routing-transition-a120

## Название/цель
Единый рабочий протокол Firebreak для устранения misroute и expected-reply с сохранением `LLM First Core`: deterministic слой остаётся guard/contract validation и не подменяет семантическое решение LLM.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: booking non-replay manual NO_GO)
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/REPORTS/2026-02-19-booking-nonreplay-manual-a120.md`

## Invariant
- Продуктовый контракт `FACT/COLLECT/HANDOFF` не деградирует.
- `LLM First Core`: смысл запроса определяет LLM, deterministic слой только валидирует/ограничивает unsafe paths.
- Запрещён рост лексикон-хардкода как primary router.
- Для mixed-language и noisy turns routing не должен принудительно сваливаться в `catalog.location` без явного сигнала.

## Scope
- `decision.py`: сужение deterministic override/guards вокруг info interrupt и expected-reply в booking.
- `booking.py`: корректная обработка `time` при уже известной дате (slot continuity).
- `tests/*`: контрактные регрессии + anti-drift покрытия для целевых сценариев.
- Этот документ становится единым протоколом выполнения Firebreak в текущей сессии.

## Out of scope
- Полный rewrite state machine/policy core.
- Изменение owner LAW/policy.
- Массовый рефактор всех эвристик вне подтверждённых failure-path.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `docs/TASK_PACKAGES/TP-2026-02-19-booking-routing-transition-a120.md`
- `docs/SESSIONS/SESSION-2026-02-19-booking-routing-transition-a120.md`
- `docs/SESSION_INDEX.md`

## Единый рабочий протокол
1. `Preflight (обязателен)`:
   - Работать из актуального `main` + целевая feature-ветка.
   - Проверить источник ключа LLM: `truffles-api/.env` (канонический путь в repo: `/home/zhan/truffles-main/truffles-api/.env`).
   - Перед LLM quality-тестами экспортировать ключ в окружение процесса и валидировать непустое значение.
2. `Container freshness gate (обязателен перед тестами)`:
   - Сверить хэш ключевого файла локально и в контейнере (`decision.py` как минимум).
   - При mismatch пересобрать/перезапустить `truffles-api` и повторить сверку.
3. `Code fix`:
   - Убирать deterministic misroute/override только в подтверждённых узлах (`master -> location`, expected-reply info-block).
   - Не добавлять новые словари/лексиконы как основной способ маршрутизации.
4. `Validation`:
   - Local deterministic tests.
   - Local realism/LLM quality контур с `OPENAI_API_KEY` (без ключа статус `BLOCKED`, не `PASS`).
5. `Evidence + handoff`:
   - Зафиксировать тестовые команды, результаты, ключевые decision traces/meta и PR/CI статусы.

## Plan
1. Обновить текущий TP до единого протокола (этот документ).
2. Исправить красный PR (`unit-tests`) целевым код-фиксом без расширения хардкода.
3. Прогнать обязательные целевые тесты + смежные регрессии.
4. Закоммитить/запушить и дождаться CI.
5. Обновить session log с evidence.

## DoD
- Красный `unit-tests` в PR закрыт.
- Подтверждённый misroute-path больше не воспроизводится в тестах.
- Expected-reply time-turn не ломает booking continuity.
- Проверка свежести контейнера и проверка источника `OPENAI_API_KEY` документированы в evidence.
- Никаких новых “словарных” override-веток в core routing.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py`
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply or master or booking"`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py -x`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --run-id booking-firebreak-a120`

## Evidence
- CI run URL + failed/passed job details.
- Локальные команды и результаты pytest/quality run.
- `decision_meta`/`decision_trace` по целевым сценариям.
- Обновление `docs/SESSIONS/SESSION-2026-02-19-booking-routing-transition-a120.md`.

## Rollback
- `git revert HEAD` (или конкретный SHA фикс-коммита из этой ветки)

## No-go
- Не добавлять хардкод-роутинг под конкретные фразы/языки.
- Не расширять словари как primary arbitration.
- Не запускать “pass-only deterministic” как замену LLM quality.
- Не принимать результат без container freshness проверки.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `fix/llm-first-firebreak-2026-02-19`
- Worktree: `/home/zhan/worktrees/fix-llm-first-firebreak-2026-02-19`
- Base ref: `origin/main`
- Merge policy: merge commit (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Локальные deterministic тесты не покрывают все multilingual/chaos траектории без LLM quality.
- Если контейнер не пересобран после кода, возможны ложные падения/ложные pass.
