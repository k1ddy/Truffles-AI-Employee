# TP-2026-02-01-pack-compiler-pending-gap

- Название/цель: Закрыть GAP по chaos-sim (pending_action_mismatch/state_mismatch/action_mismatch/ood_false_positive) после Pack-Compiler; все pending-решения — через pack-лексиконы, без словарей в коде.
- Canon refs: `STATE.md` (GAP Pack-Compiler DoD not green), `docs/REPORTS/2026-02-01-pack-compiler-implementation.md`, `docs/runbooks/CHAOS_SIM.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: никаких бизнес-лексиконов/фраз в коде; pending soft-pass сохраняет in-domain ответы; trace/meta обязательны; stage order без изменений; `_legacy.py` adapter-only.
- Scope:
  - Триаж chaos-sim артефактов и фиксация причин pending mismatches.
  - Исправить pack-compiler schema lookup в контейнере (repo-root detection + contracts в image).
  - Перенос pending ack/close/status фраз в packs (SYSTEM_LEXICONS) и использование их в pending gate.
  - Обновление pending gate/decision resolve без `unknown_state` при валидном pending.
  - Добавление/обновление тестов на pending gate и decision_meta.
  - Рерун chaos-sim с теми же параметрами и evidence.
- Out of scope: Pack-Compiler/DSL изменения, миграции БД, изменения stage order, новые LLM промпты/контракты.
- Touch-list:
  - `truffles-api/app/services/pack_compiler_service.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/Dockerfile`
  - `truffles-api/docker-compose.yml`
  - `truffles-api/tests/test_pending_pack_lexicons.py`
  - `docs/REPORTS/2026-02-01-pack-compiler-implementation.md`
  - `docs/TASK_PACKAGES/TP-2026-02-01-pack-compiler-pending-gap.md`
  - `docs/SESSIONS/SESSION-2026-02-01-pack-compiler-pending-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md` (обновление только Brain/Top Architect)
- Plan:
  1) Триаж `/tmp/chaos_pack_compiler_rerun` и группировка pending mismatches (decision_meta/trace).
  2) Добавить/обновить pending ack/close/status фразы в `SYSTEM_LEXICONS`.
  3) Обновить pending gate/decision resolve для корректного pending_action через pack-лексиконы.
  4) Добавить тест(ы) на pending gate и decision_meta.
  5) Рерун chaos-sim и обновление evidence + `STATE.md`.
- DoD:
  - Chaos-sim rerun (same params) без pending_action_mismatch.
  - Remaining chaos-sim failures (action_mismatch/state_mismatch/ood_false_positive) зафиксированы как GAP и принимаются как baseline в `STATE.md`.
  - Pending решения используют pack-лексиконы; в коде нет словарей/фраз.
  - decision_meta/trace корректны на pending путях.
  - Тесты проходят.
- Checks:
  - `pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
  - `python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" --manager-mode skip --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_pack_compiler_pending_fix4`
- Evidence:
  - `/tmp/chaos_pack_compiler_pending_fix4` (summary/report/failures)
  - `/tmp/pytest_pending_gate_20260201.txt`
  - Обновление `docs/REPORTS/2026-02-01-pack-compiler-implementation.md`
  - Запись в `STATE.md` (Brain/Top Architect) с путями evidence
- Rollback: `git revert HEAD` (or revert the merge commit in main).
- No-go:
  - Словари/ключевые слова в коде.
  - Изменение порядка стадий без DEC + snapshot-test.
  - Добавление логики в `_legacy.py`.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-01-pack-compiler-pending-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-01-pack-compiler-pending-a1`
  - Base: `origin/main`
  - Merge: PR -> main
  - Cleanup: `scripts/session_end.sh` + remove worktree/branch
- Риски/блокеры: pending фразы могут не покрыть все вариации; возможен рост false-positive pending_status.
