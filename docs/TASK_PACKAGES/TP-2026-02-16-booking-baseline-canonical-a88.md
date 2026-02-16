# TP-2026-02-16-booking-baseline-canonical-a88

- Название/цель: Канонизировать baseline quality для booking replay на фиксированных сценариях и подтвердить воспроизводимость через matrix run.
- Canon refs: `STATE.md` NOW/GAP (booking quality anti-drift), `AGENTS.md` (Baseline Integrity Gate, Quality Validity Gate, Local-first validation law), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять runtime-поведение policy/decision/tool.
- Не сравнивать или обновлять baseline на `INVALID` run.
- Оставить тот же `scenarios.json` для lock/replay цепочки.

## Scope
- Обновить canonical baseline (`ops/results/booking_quality.json`) из валидного lock-run.
- Выполнить matrix run на тех же сценариях и подтвердить `infra_valid=true` и `semantic_valid=true`.
- Подготовить session evidence для PR.

## Out of scope
- Любые изменения `truffles-api` runtime-кода.
- Любые новые feature-фиксы по `expected_reply_deferred`/controller.
- Пересборка или смена набора сценариев.

## Touch-list
- `ops/results/booking_quality.json`
- `docs/TASK_PACKAGES/TP-2026-02-16-booking-baseline-canonical-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-booking-baseline-canonical-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Выполнить lock-run на фиксированных сценариях с `judge_mode=all` и `--update-baseline`.
2. Проверить валидность summary и факт обновления canonical baseline.
3. Выполнить matrix run на тех же сценариях с baseline comparison.
4. Зафиксировать evidence и открыть PR.

## DoD
- В `ops/results/booking_quality.json` выставлен актуальный `updated_at` и `config.judge_mode=all`.
- lock-run summary валидный: `infra_valid=true`, `semantic_valid=true`, `comparison_blocked=false`.
- matrix summary валидный: `all_ok=true`, child run с `infra_valid=true` и `semantic_valid=true`.
- PR содержит только baseline + session governance артефакты.

## Checks
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --client-slug demo_salon --scenarios-file /tmp/booking_quality/offline-replay-20260215-p0-r27/scenarios.json --count 5 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --run-id booking-lock-20260216-a88-fast5 --output-dir /tmp/booking_quality/booking-lock-20260216-a88-fast5 --allow-output-overwrite --update-baseline --skip-outbox`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality-matrix --client-slugs demo_salon --run-id-prefix booking-matrix-20260216-a88 --output-dir /tmp/booking_quality/booking-matrix-20260216-a88 --allow-output-overwrite -- --scenarios-file /tmp/booking_quality/booking-lock-20260216-a88-fast5/scenarios.json --count 5 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --fail-on-regression --baseline-summary /home/zhan/truffles-main/ops/results/booking_quality.json --skip-outbox`
- `python3 -m json.tool ops/results/booking_quality.json >/dev/null`
- `scripts/session_check.sh`

## Evidence
- `/tmp/booking_quality/booking-lock-20260216-a88-fast5/summary.json`
- `/tmp/booking_quality/booking-matrix-20260216-a88/matrix_summary.json`
- `/tmp/booking_quality/booking-matrix-20260216-a88/booking-matrix-20260216-a88-01-demo_salon/summary.json`
- `ops/results/booking_quality.json`

## Rollback
- Revert commit c baseline update и session docs.

## No-go
- Не обновлять baseline из run с `infra_valid=false` или `semantic_valid=false`.
- Не менять `scenarios.json` для этого цикла.
- Не добавлять runtime-изменения в этот PR.

## Risks/блокеры
- Сценарные контракты могут дать fail при слишком малом `count` или шуме окружения.
- Длительный runtime lock-run при большом `count`.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `chore/2026-02-16-booking-baseline-canonical-a88`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect после merge.
