# TP-2026-01-25 — Chaos P0 Cleanup + Live Booking E2E Suite

## Название/цель
Снять шум в chaos-sim (P0) и добавить live E2E suite для полного бронирования с подтверждением,
handover и outbox, чтобы получить доказательства "живого" диалога.

## Invariant
- Hard-LAW: мед/юридические/жалобы/возвраты → только escalation, без офферов.
- decision_meta/decision_trace пишутся на каждом inbound.
- Не менять production booking/consult/policy логику ради прохождения тестов.
- `_legacy.py` остаётся adapter-only.

## Scope
- P0: устранить ложные срабатывания chaos-sim (manager state/handover, OOD false positives, clarify_limit).
- P1: добавить live suite `ca12-booking-full` (WA → booking_confirm → booking_commit → outbox → manager take/resolve).
- Документация: runbook + STATE обновляются evidence по прогонам.

## Out of scope
- Изменения DB схемы, calendar sync, CA06, UI/Console изменения.
- Рефакторинг core pipeline.

## Touch-list
- `ops/diagnose.py`
- `docs/runbooks/CHAOS_SIM.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-chaos-live-e2e.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1) P0 evidence: повторить booking-only chaos-sim (1–3 кейса) с `--debug`, собрать причины
   manager/ood/expected_reply_type/500.
2) Исправить evaluator/manager checks (только если это false-positive), не трогая core-логику.
3) Прогнать booking-only chaos-sim 5–10 кейсов, сохранить summary/report/failures.
4) Добавить live suite `ca12-booking-full` в `ops/diagnose.py` + описать в runbook.
5) Прогнать live suite и собрать evidence (appointments/appointment_audit/outbox + trace stages).
6) Обновить `STATE.md` и закрыть GAP по живым диалогам.

## DoD
- Chaos-sim booking-only даёт стабильные результаты без ложных manager/ood фейлов.
- `ca12-booking-full` выполняется end-to-end (WA→booking_confirm→booking_commit→outbox→take/resolve).
- Evidence сохранена: conv_id, decision_trace (booking_confirm/booking_commit), appointment_audit, outbox status.

## Checks
- `python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_booking_simtime_eval_5`
- `python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full`

## Evidence
- chaos-sim artifacts (`summary.json`, `failures.jsonl`, `report.md`) + command line.
- livecheck artifacts + SQL snippets:
  - `appointments`, `appointment_audit`, `outbox_messages`
  - `decision_trace` stages `booking_confirm`, `booking_commit`

## Rollback
- Revert PR + redeploy previous image (no DB changes).

## No-go
- Red CI.
- Отсутствует evidence (logs/SQL/trace).
- Любые изменения в production logic ради тестов.

## Риски/блокеры
- Нет allowlisted JID / токенов Telegram/Console.
- LLM/RAG ключи недоступны для live suite.
- Периодические 500 на `/webhook` (нужно локализовать до E2E).

## Branch/Worktree
- Branch: `feat/chaos-live-e2e`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base ref: `origin/main`
- Merge policy: PR + CI green, Brain merges
