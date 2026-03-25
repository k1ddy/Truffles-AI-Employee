# TP-2026-01-31-state-scn-multiturn-evidence

- Название/цель: Обновить STATE.md NOW с DONE-фиксацией soft-pending + multi-turn SCN1–SCN5 oracle/eval и доказательствами после merge.
- Canon refs: `STATE.md` NOW (DEC-018 related P0 items), `docs/SESSION_START_PROMPT.txt`, `AGENTS.md`.
- Invariant: Документы отражают только фактические изменения с evidence; никаких кодовых правок.
- Scope: Только doc-only изменения в STATE.md + session log/index.
- Out of scope: Любые изменения кода/данных/конфигурации, запуск тестов, новые evidence.
- Touch-list: `STATE.md`, `docs/TASK_PACKAGES/TP-2026-01-31-state-scn-multiturn-evidence.md`, `docs/SESSIONS/SESSION-2026-01-31-state-scn-multiturn-evidence-a4.md`, `docs/SESSION_INDEX.md`.
- Plan:
  1) Создать сессию и session log.
  2) Добавить DONE в NOW с evidence по soft-pending + SCN1–SCN5 multi-turn.
  3) Закрыть сессию, пройти session_check, закоммитить и запушить doc-only.
- DoD: STATE.md обновлён; session log + SESSION_INDEX обновлены; doc-only commit в main.
- Checks: `scripts/session_check.sh`, `git status -sb`, `git diff --stat`.
- Evidence: `/tmp/pytest_scn_multiturn_soft_pending_20260201e.txt` + указание на пути `truffles-api/app/routers/webhook/pending.py`, `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/info.py`, `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml`.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Никаких кодовых правок, тестов или изменений веток.
- Branch/Worktree/Base/Merge/Cleanup: `feat/2026-01-31-state-scn-multiturn-evidence-a4` / `/home/zhan/worktrees/2026-01-31-state-scn-multiturn-evidence-a4` / `origin/main` / doc-only fast-forward в `main` / удалить локальный worktree после.
- Риски/блокеры: Нет; использовать существующее evidence.
