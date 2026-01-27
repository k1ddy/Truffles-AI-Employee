# TP-2026-01-27-session-close-same-commit-a1 — Session close in same commit

- **Название/цель:** убрать цикл "commit только ради закрытия сессии" и зафиксировать правило: статус `done` ставится в финальном коммите работы.
- **Canon refs:** `AGENTS.md` (Session log); `docs/SESSION_START_PROMPT.txt`; `STATE.md` (GAP: бесконечный commit/push без работы).
- **Invariant:** не менять runtime поведение, API/DB, контракты или CI pipeline — только процессные доки.
- **Scope:** правила в `AGENTS.md` и `docs/SESSION_START_PROMPT.txt`.
- **Out of scope:** изменения кода продукта, миграции, тесты core.
- **Touch-list:**
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-close-same-commit-a1.md`
- **Plan:**
  1) Добавить правило: статус `done` ставится в том же коммите, что содержит рабочие изменения.
  2) Закрепить в start‑prompt, что отдельный commit/PR ради закрытия запрещён.
  3) Обновить session log/index и сохранить evidence.
- **DoD:**
  - Правило фиксировано в `AGENTS.md` и `docs/SESSION_START_PROMPT.txt`.
  - `bash -n` не требуется (docs-only).
- **Checks:** не требуется.
- **Evidence:** `git diff --stat`.
- **Rollback:** revert doc changes.
- **No-go:** не трогать runtime код, БД, миграции.
- **Риски/блокеры:** нет.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-close-same-commit-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-close-same-commit-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
