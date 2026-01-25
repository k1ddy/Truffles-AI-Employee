# TP-2026-01-25 — Chaos-Sim Resilience + Artifacts

## Название/цель
Стабилизировать chaos-sim для ночных прогонов: preflight, retry/backoff, continue-on-infra, per-turn events и частичные чекпоинты.

## Invariant
- Никаких изменений в прод-логике webhook; только ops/diagnose.py.
- Решения оцениваются по decision_meta/trace, не по тексту.

## Scope
- Preflight /admin/health + /admin/version.
- Retry/backoff на сетевых сбоях.
- Continue-on-infra с фиксацией ошибок и bundle артефактов.
- Пер-ходовый events.jsonl и summary.partial.json.

## Out of scope
- Изменение evaluator логики.
- Изменение core pipeline.

## Touch-list
- `ops/diagnose.py`
- `docs/TASK_PACKAGES/TP-2026-01-25-chaos-sim-resilience.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить preflight и infra retry/backoff в chaos-sim.
2) Добавить events.jsonl + summary.partial.json + failure bundles.
3) Smoke-run 1 case с sim-time.

## DoD
- Preflight артефакт создаётся.
- Ошибки infra не роняют прогон (по умолчанию).
- Есть events.jsonl + summary.partial.json.

## Checks
- `python3 ops/diagnose.py chaos-sim --count 1 --kinds booking --sim-time "2026-01-24T12:00:00+06:00" --mode logic --manager-mode skip --console-mode skip --skip-outbox --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --timeout 15 --max-runtime 90 --output-dir /tmp/chaos_booking_simtime_improved_1a`

## Evidence
- `/tmp/chaos_booking_simtime_improved_1a/preflight.json`
- `/tmp/chaos_booking_simtime_improved_1a/events.jsonl`
- `/tmp/chaos_booking_simtime_improved_1a/summary.json`

## Rollback
- Revert коммита.

## No-go
- Красные тесты.
- Нет артефактов по итогам прогона.

## Риски/блокеры
- Долгие опросы decision_meta; контролируется max-runtime.

## Branch/Worktree
- Branch: `feat/chaos-sim-resilience`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base: `origin/main`
- Merge policy: PR + CI green; merge делает Brain
- Cleanup: Brain после merge
