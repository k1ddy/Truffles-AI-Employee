# TP-2026-02-19-booking-name-progression-a120

## Название/цель
Закрыть hard-defect #3 из manual non-replay audit: после ввода имени (`Меня зовут Лена`) booking не должен зацикливаться на `calendar.list_slots`, а должен детерминированно продвигаться к confirm/commit.

## Canon refs
- `AGENTS.md`
- `STATE.md` (booking non-replay manual NO_GO)
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/REPORTS/2026-02-19-booking-nonreplay-manual-a120.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-booking-routing-transition-a120.md`

## Invariant
- Не ломать контракт outcomes `FACT/COLLECT/HANDOFF`.
- Не терять уже собранные booking-slots (`service`, `datetime`, `name`).
- После валидного `name` не оставлять пользователя в повторе `list_slots` без прогресса.

## Scope
- Runtime fix в booking transition path (`decision.py` и/или `booking.py`) для детерминированного шага после `name`.
- Контрактные регрессионные тесты в `test_message_endpoint.py`.
- Локальная валидация на затронутых booking suites.

## Out of scope
- Полный rewrite booking state-machine.
- Изменение policy/Law контрактов.
- UX-polish не связанный с name progression.

## Touch-list
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SESSIONS/SESSION-2026-02-19-booking-name-progression-a120.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Поднять новую сессию/worktree от `origin/main`.
2. Воспроизвести текущий path `expected_reply=name` -> tool action / next expected reply.
3. Исправить transition так, чтобы после валидного `name` происходил deterministic progress к confirm/commit, а не повтор `list_slots`.
4. Добавить regression tests на кейс manual audit (`service+datetime` есть, приходит name).
5. Прогнать targeted и смежные booking тесты, зафиксировать evidence.

## DoD
- При `booking.active=true` и заполненных `service+datetime`, вход `name` продвигает сценарий вперед (без stale `list_slots` loop).
- Decision meta/trace отражают корректный transition (booking progress, expected reply/commit state).
- Новые регрессионные тесты проходят.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_message_endpoint.py`
- `ruff check truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "name and booking"`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`

## Evidence
- Diff + pytest results для новых и затронутых сценариев.
- `decision_meta/trace` assertions в тестах на name progression.
- Session log с командами и итогом.

## Rollback
- `git revert HEAD` (или конкретный SHA фикс-коммита) в рабочей ветке.

## No-go
- Не добавлять orchestration в `_legacy.py`.
- Не подгонять логику хардкодом под единичный тест.
- Не менять DB/trace вручную ради evidence.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-19-booking-name-progression-a120`
- Worktree: `/home/zhan/worktrees/2026-02-19-booking-name-progression-a120`
- Base ref: `origin/main`
- Merge policy: merge commit (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Возможны side effects в calendar.list_slots fallback; покрываем смежными booking tests.
