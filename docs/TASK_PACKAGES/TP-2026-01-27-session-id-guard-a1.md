# TP-2026-01-27-session-id-guard-a1 — Session id guard

- **Название/цель:** запретить коллизии session_id/worktree/branch и закрепить требование суффикса агента в session_id.
- **Canon refs:** `AGENTS.md` (Session log); `docs/SESSION_START_PROMPT.txt`; `STATE.md` (GAP: коллизии сессий при параллельной работе).
- **Invariant:** не менять runtime поведение, API/DB или контракты — только процессные скрипты/доки.
- **Scope:** `scripts/session_start.sh` + правила `AGENTS.md` и `docs/SESSION_START_PROMPT.txt`.
- **Out of scope:** любые изменения кода продукта, CI пайплайна, миграций.
- **Touch-list:**
  - `scripts/session_start.sh`
  - `AGENTS.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-id-guard-a1.md`
- **Plan:**
  1) Зафиксировать правило `session_id` = `YYYY-MM-DD-{slug}-{agent}` в `AGENTS.md` и старт‑промпте.
  2) Усилить `scripts/session_start.sh`: требовать session_id, проверять индекс, branch и worktree.
  3) Обновить session log/index и сохранить evidence.
- **DoD:**
  - `scripts/session_start.sh` падает при дубликате session_id/branch/worktree.
  - Документация требует суффикс агента.
  - `bash -n scripts/session_start.sh` проходит.
- **Checks:** `bash -n scripts/session_start.sh`
- **Evidence:** `git diff --stat`, вывод `bash -n`.
- **Rollback:** `git revert 0c64eeb4` или удаление правок из docs/scripts.
- **No-go:** не трогать runtime код, БД, миграции.
- **Риски/блокеры:** нет.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: feat/2026-01-27-session-id-guard-a1
  - Worktree: /home/zhan/worktrees/2026-01-27-session-id-guard-a1
  - Base: origin/main
  - Merge: merge --no-ff (no rebase)
  - Cleanup: delete worktree + branch after merge.
