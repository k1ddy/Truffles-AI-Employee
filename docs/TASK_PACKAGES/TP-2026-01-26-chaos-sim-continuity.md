# TP-2026-01-26 — Chaos-Sim Continuity + Actionable Reporting

## Название/цель
Сделать chaos-sim продолжабельным и объяснимым: run-ledger с resume, авто-бандлы на фейлах, отчёт с причинами и единая инструкция для будущих агентов.

## Invariant
- Никаких изменений в core webhook-логике; только ops/diagnose.py и документация.
- Оценка по `decision_meta/trace`, не по тексту.
- Без ручной правки БД/trace ради evidence.

## Scope
1) Run-ledger + resume:
   - Флаг `--run-id`.
   - `run.json` (seed, jid_base, cases, conversation_id, last_turn, output_dir).
   - `--resume` продолжает тот же run, а не стартует заново.
2) Actionable report:
   - `report.md` с разделением infra vs logic vs evaluator vs data/pack.
   - Для каждого фейла: expected/actual + ссылка на trace-bundle.
3) Auto bundle on fail:
   - `--bundle-on-fail` сохраняет trace-bundle на каждый failure message_id.
4) Док‑фикс:
   - короткая инструкция в `AGENTS.md`,
   - обновление `docs/runbooks/CHAOS_SIM.md` под новые флаги,
   - регистрация в `STRUCTURE.md` и `STATE.md`.

## Out of scope
- Изменение правил канона или evaluator логики для “подгонки”.
- Любые изменения поведения webhook/booking/consult.
- Изменения БД и схем.

## Touch-list
- `ops/diagnose.py`
- `docs/runbooks/CHAOS_SIM.md`
- `AGENTS.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-chaos-sim-continuity.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить `--run-id`, `run.json`, `--resume` (продолжение тех же кейсов/turns).
2) Добавить `--bundle-on-fail` и автоматическое сохранение trace-bundle.
3) Сформировать `report.md` с категоризацией фейлов и ссылками.
4) Обновить `docs/runbooks/CHAOS_SIM.md` и короткую инструкцию в `AGENTS.md`.
5) Smoke-run: один run + resume, проверить артефакты.
6) Записать evidence в `STATE.md`.

## DoD
- `run.json` создаётся и содержит seed/jid_base/case map/last_turn.
- `--resume` продолжает тот же run (тот же jid_base/case_id).
- `report.md` содержит категории фейлов и ссылки на bundles.
- `--bundle-on-fail` создаёт bundle для каждого failure message_id.
- Документация обновлена и понятна новому агенту.

## Checks
- `python3 ops/diagnose.py chaos-sim --run-id demo-run-01 --count 1 --kinds booking --sim-time "2026-01-24T12:00:00+06:00" --mode llm --noise high --min-turns 6 --max-turns 8 --manager-mode skip --console-mode skip --skip-outbox --output-dir /tmp/chaos_continuity_demo`
- `python3 ops/diagnose.py chaos-sim --resume --run-id demo-run-01 --output-dir /tmp/chaos_continuity_demo`

## Evidence
- `/tmp/chaos_continuity_demo/run.json`
- `/tmp/chaos_continuity_demo/report.md`
- `/tmp/chaos_continuity_demo/bundles/*` (если были фейлы)

## Rollback
- Revert коммита.

## No-go
- Красный CI.
- Отсутствует `run.json`/`report.md` после прогона.
- Новые флаги не документированы в runbook.

## Риски/блокеры
- Resume требует стабильных conversation_id; возможны расхождения при долгих паузах.
- Много bundle-артефактов → увеличить диск; чистить только после фиксации evidence.

## Branch/Worktree
- Branch: `feat/booking-signal-llm-align`
- Worktree: `/home/zhan/worktrees/booking-signal-llm-align`
- Base: `origin/main`
- Merge policy: PR + CI green; merge делает Brain
- Cleanup: Brain после merge
