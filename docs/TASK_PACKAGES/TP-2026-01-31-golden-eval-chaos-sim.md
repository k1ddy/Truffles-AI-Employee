- Название/цель: golden eval + booking chaos-sim по trace/meta (без сравнения текстов) как базовая регрессия для DEC-018.
- Canon refs: `STATE.md` (OPEN chaos-sim residuals), `docs/runbooks/CHAOS_SIM.md`, `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/IMPERIUM_DECISIONS.yaml` (DEC-018).
- Invariant:
  - decision_meta/decision_trace пишутся на каждом user-message и раннем возврате.
  - Entry points и `_legacy.py` остаются adapter-only; оркестрация не добавляется.
  - Stage order snapshot не меняется.
- Scope:
  - добавить golden eval набор с проверкой decision_meta/trace-only (без текстовых assert).
  - добавить golden eval тест в существующий `test_demo_salon_eval.py`.
  - прогнать booking-only chaos-sim (logic mode) и сохранить артефакты.
- Out of scope:
  - LLM промпты/контракты, pack-index/versioning, live-outbound, миграции БД.
- Touch-list:
  - `truffles-api/app/knowledge/demo_salon/EVAL_GOLDEN.yaml`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `docs/SESSIONS/SESSION-2026-01-31-golden-eval-chaos-sim-a4.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1) Создать golden eval cases (trace/meta expectations).
  2) Добавить pytest, который валидирует decision_meta/trace без текстовых сравнений.
  3) Запустить pytest и зафиксировать output.
  4) Запустить booking-only chaos-sim (logic mode) и сохранить artifacts.
  5) Обновить `STATE.md` с evidence.
- DoD:
  - Golden eval test проходит и проверяет decision_meta/trace-only.
  - Chaos-sim run завершён, есть `summary.json`/`report.md`/`failures.jsonl`.
  - Evidence записан в `STATE.md` (Brain/Top Architect) до merge.
- Checks:
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py -k \"golden_eval\"`
  - `python3 ops/diagnose.py chaos-sim --count 3 --kinds booking --mode logic --skip-outbox --console-mode skip --manager-mode skip --sim-time "2026-01-24T12:00:00+06:00" --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_golden_eval_booking_20260131`
- Evidence:
  - pytest output: `/tmp/pytest_golden_eval_20260131.txt`
  - chaos-sim artifacts: `/tmp/chaos_golden_eval_booking_20260131`
  - запись в `STATE.md`.
- Rollback:
  - `git revert HEAD`.
- No-go:
  - Любые текстовые assert для LLM.
  - Изменения в `_legacy.py`/entrypoints.
  - Правки БД ради evidence.
- Риски/блокеры:
  - Chaos-sim требует живой локальный API и env; если недоступно — фиксировать BLOCKED с логами.
- Branch/worktree:
  - Branch: `feat/2026-01-31-golden-eval-chaos-sim-a4`
  - Worktree: `/home/zhan/worktrees/2026-01-31-golden-eval-chaos-sim-a4`
  - Base ref: `origin/main`
  - Merge policy: PR + CI
  - Cleanup: Brain/Top Architect
