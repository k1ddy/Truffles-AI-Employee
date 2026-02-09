# TP-2026-02-09-postmerge-strict-replay-evidence-a19

- Название/цель: Выполнить post-merge strict replay (`count=10`) с judge hard-gate и зафиксировать сравнение метрик до/после для policy-core runtime hardening + route-llm-plan retire.
- Canon refs: `AGENTS.md`; `STATE.md` NOW (policy-core runtime hardening и follow-up evidence GAP); `docs/TASK_PACKAGES/TP-2026-02-08-policy-core-runtime-hardening-a19.md`; `docs/TASK_PACKAGES/TP-2026-02-09-route-llm-plan-legacy-a19.md`.

- Invariant:
  - Replay выполняется только по frozen scenarios (`--scenarios-file`), без генерации и без изменения исходных артефактов.
  - Judge в strict replay обязательно включен (`judge.enabled=true`) без debug-waiver.
  - Никаких изменений runtime-кода/БД ради «улучшения» метрик.

- Scope:
  - Запустить strict replay `count=10` на frozen seed=1337 сценариях с включенным judge.
  - Сравнить baseline vs post-merge по требуемым метрикам.
  - Зафиксировать evidence в `STATE.md` + сессионных доках.

- Out of scope:
  - Новые кодовые изменения в runtime.
  - Изменения сценариев в `/tmp/booking_quality/*/scenarios.json`.
  - Тюнинг judge prompt/модели в рамках этого шага.

- Touch-list (files/tables):
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-09-postmerge-strict-replay-evidence-a19.md`
  - `docs/SESSION_INDEX.md`
  - `docs/TASK_PACKAGES/TP-2026-02-09-postmerge-strict-replay-evidence-a19.md`
  - `/tmp/booking_quality/20260209-postmerge-main-seed-1337-replay-count10/*` (artifacts)

- Plan (1..N):
  1. Старт сессии/worktree и валидация baseline frozen artifacts.
  2. Запуск strict replay `count=10` с `--scenarios-file`, `--baseline-summary`, `--judge-mode all`.
  3. Извлечение метрик до/после (включая derived where needed) и проверка judge.enabled.
  4. Обновление `STATE.md` (FACT + evidence paths/commands).
  5. Подготовка commit/push/PR с doc evidence.

- DoD:
  - Получен новый `summary.json` и `responses.jsonl` для post-merge strict replay count=10.
  - В новом summary `judge.enabled=true`.
  - Зафиксировано сравнение baseline vs post-merge по `false_ok_rate`, `fallback_rate`, `deadline_exceeded_rate`, `booking_commit_without_*` (явно указать метод расчета).
  - `STATE.md` обновлен с evidence и командой воспроизведения.

- Checks:
  - `python3 ops/diagnose.py llm-quality --scenarios-file ... --baseline-summary ... --count 10 --tool-hooks auto --reset-before-dialog --max-failures 20 --judge-mode all --judge-api-key ... --output-dir ...`
  - `python3 - <<'PY'` (extract metrics from baseline/post summaries and responses)

- Evidence:
  - `/tmp/booking_quality/20260209-postmerge-main-seed-1337-replay-count10/summary.json`
  - `/tmp/booking_quality/20260209-postmerge-main-seed-1337-replay-count10/responses.jsonl`
  - `/tmp/booking_quality/20260209-postmerge-main-seed-1337-replay-count10/brief.md`
  - diff/update in `STATE.md`
  - PR URL

- Rollback:
  - Revert doc-only commit if evidence запись некорректна.

- No-go:
  - Не использовать `--allow-judge-off`.
  - Не менять существующие frozen scenario/baseline файлы.
  - Не скрывать деградации в отчете.

- Риски/блокеры:
  - Возможный runtime timeout/outbox polling stall в replay; при зависании зафиксировать стоп-линию и infra evidence.
  - Judge API недоступен/без ключа; mitigated через secure extraction key из runtime container env без логирования значения.

- Branch + Worktree path + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-02-09-postmerge-strict-replay-evidence-a19`
  - Worktree: `/home/zhan/worktrees/2026-02-09-postmerge-strict-replay-evidence-a19`
  - Base ref: `origin/main`
  - Merge policy: PR в `main`, без rebase
  - Cleanup: после merge удалить ветку и worktree
