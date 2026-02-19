# TP-2026-02-19-booking-routing-transition-a120

## Название/цель
Исправить два подтверждённых hard-defect из ручного non-replay аудита booking: (1) misroute `master/specialist -> catalog.location`, (2) некорректный booking transition на time-turn (`19:00`) с загрязнением `intent_choice` и потерей прогресса.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: booking non-replay manual NO_GO)
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md` (core behavior evidence contract)
- `docs/REPORTS/2026-02-19-booking-nonreplay-manual-a120.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-booking-nonreplay-manual-a120.md`

## Invariant
- Не ломаем продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не допускаем silent fallback `master/specialist -> catalog.location` без явного location/hours запроса.
- После валидного expected-reply slot-match booking должен двигаться вперёд без возврата в stale `intent_choice`.

## Scope
- `decision.py`: routing/guard для master/specialist и transition cleanup для expected-reply booking-flow.
- `booking.py`: корректное применение `time` expected-reply, когда дата уже есть, а время приходит отдельным turn.
- `test_message_endpoint.py`: регрессионные контрактные тесты для обоих дефектов.

## Out of scope
- Полный rewrite policy core / state-machine.
- Изменение owner policy/LAW.
- Косметический cleanup intent_choice текстов (`[по записи]`) и consult/media drift (отдельные пункты).

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SESSIONS/SESSION-2026-02-19-booking-routing-transition-a120.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Поднять отдельную сессию/worktree через `scripts/session_start.sh`.
2. Внести routing guard для master/specialist: при master-сигнале и отсутствии явного location/hours запроса запрещать уход в `catalog.location`.
3. Исправить transition path expected-reply(time): корректно объединять date+time и очищать stale `intent_queue` при возврате в booking slot-flow.
4. Добавить regression tests, воспроизводящие оба найденных hard-defect.
5. Прогнать целевые и смежные pytest, собрать evidence в session log.

## DoD
- Master-вопрос не маршрутизируется в `catalog.location` при отсутствии явного location/hours запроса.
- На `expected_reply=time` при уже выбранной дате и входе `19:00` слот datetime корректно обновляется (без потери date).
- После валидного booking expected-reply match stale `intent_queue` не оставляет `expected_reply_type=intent_choice`.
- Все новые/затронутые тесты зелёные.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "master or expected_reply or intent_queue"`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- Diff + passing pytest output для новых регрессий.
- Фактические значения `decision_meta.expected_reply_type/intent/tool_action` в тестах.
- Запись в `docs/SESSIONS/SESSION-2026-02-19-booking-routing-transition-a120.md`.

## Rollback
- `git revert HEAD` (или конкретный SHA фикс-коммита) для кода и тестов в этой ветке.

## No-go
- Не трогать `_legacy.py` оркестрацией.
- Не подгонять поведение хардкодом под один пример.
- Не править БД/trace вручную ради evidence.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-19-booking-routing-transition-a120`
- Worktree: `/home/zhan/worktrees/2026-02-19-booking-routing-transition-a120`
- Base ref: `origin/main`
- Merge policy: merge commit (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Возможны смежные регрессии в info-bundle/intent-queue ветках; покрываем targeted тестами и полным `test_message_endpoint.py`.
- `test_demo_salon_eval.py` имеет исторический риск (`E542`), фиксируем как residual если не связан с текущим diff.
