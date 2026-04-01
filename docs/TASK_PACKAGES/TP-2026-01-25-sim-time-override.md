# TP-2026-01-25 — Simulation Time Override for Booking Signals

## Название/цель
Привязать offline datetime‑парсинг (booking signal) к `simulation_time`, чтобы chaos‑sim с `--sim-time` работал
детерминированно и не ловил off‑hours ложные сигналы.

## Invariant
- Никаких изменений прод‑логики без `simulation_time`.
- Hard‑LAW/booking/trace/meta не ухудшаются.
- `_legacy.py` остаётся adapter‑only.

## Scope
- Добавить `relative_base` для offline datetime parsing (только когда есть `simulation_time`).
- Прокинуть `sim_now` в booking signal extractor.
- Обновить `STRUCTURE.md` + `STATE.md` с evidence.

## Out of scope
- Изменения DB/схемы, calendar sync, UI/Console.
- Рефакторинг booking flow или policy/truth_gate логики.

## Touch-list
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/decision.py`
- `docs/TASK_PACKAGES/TP-2026-01-25-sim-time-override.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить `relative_base` в `_resolve_datetime_offline` и прокинуть его из `_extract_datetime`.
2) Передавать `sim_now` в `_evaluate_booking_signal` (только когда `simulation_time` есть).
3) Прогнать `chaos-sim` booking‑only с `--sim-time` (3–5 кейсов), собрать артефакты.
4) Обновить `STATE.md` с evidence.

## DoD
- При `simulation_time` offline datetime‑парсер использует `RELATIVE_BASE=sim_now`.
- При обычном runtime (без sim time) поведение не меняется.
- Есть evidence chaos‑sim артефактов.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/decision.py`
- `python3 ops/diagnose.py chaos-sim --count 3 --kinds booking --min-turns 10 --max-turns 12 --noise high --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" --manager-mode skip --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_booking_simtime_override_3`

## Evidence
- `/tmp/chaos_booking_simtime_override_3` (summary/report/cases/failures)

## Rollback
- Revert PR + redeploy previous image (no DB changes).

## No-go
- Red CI.
- Missing evidence.
- Любая правка core‑логики ради тестов.

## Риски/блокеры
- Нет allowlisted JID (для livecheck не требуется).
- dateparser поведение может отличаться при `RELATIVE_BASE` (ожидается только для sim‑time).

## Branch/Worktree
- Branch: `feat/sim-time-override`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base ref: `origin/main`
- Merge policy: PR + CI green; Brain merges
- Cleanup: удалить ветку после merge
