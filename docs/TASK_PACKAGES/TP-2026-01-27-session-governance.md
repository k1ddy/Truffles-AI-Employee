# TP-2026-01-27 — Session governance: worktree дисциплина + session log + gates

- **Название/цель:** закрепить обязательный session log + правила worktree/branch и добавить скрипты/гейты, чтобы исключить дрейф после context compaction.
- **Canon refs:** `AGENTS.md`; `docs/SESSION_START_PROMPT.txt`; `STATE.md` (GAP: session drift + worktree мусор после compaction).
- **Invariant:** не менять runtime поведение, API/DB, контракты или прод‑процессы; только docs + инструменты процесса.
- **Scope:** session log (docs/SESSIONS + SESSION_INDEX), скрипты session_start/check/end/audit/gate, git hooks, обновления AGENTS/STRUCTURE/SESSION_START_PROMPT.
- **Out of scope:** изменения бизнес‑логики, тестов core, CI пайплайна приложений, прод‑настроек.
- **Touch-list:**
  - `AGENTS.md`
  - `STRUCTURE.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `docs/SESSIONS/SESSION_TEMPLATE.md`
  - `docs/SESSIONS/SESSION-2026-01-27-session-governance.md`
  - `docs/SESSION_INDEX.md`
  - `scripts/session_start.sh`
  - `scripts/session_check.sh`
  - `scripts/session_end.sh`
  - `scripts/session_audit.sh`
  - `scripts/session_gate.sh`
  - `scripts/install_hooks.sh`
  - `.githooks/pre-commit`
  - `.githooks/pre-push`
  - `.github/workflows/session-gate.yml`
- **Plan:**
  1) Добавить канон session log (SESSIONS + INDEX + template).
  2) Реализовать session scripts (start/check/end/audit/gate) и install_hooks.
  3) Добавить git hooks для обязательного session_check и doc‑only gate.
  4) Обновить AGENTS/STRUCTURE/SESSION_START_PROMPT под новый протокол.
  5) Зафиксировать текущую сессию в session log + index.
  6) Прогнать минимальные проверки (bash -n) и собрать evidence.
- **DoD:**
  - Session log и index существуют и описаны в AGENTS/STRUCTURE.
  - Скрипты session_* реализованы и проходят `bash -n`.
  - Hooks подключаются через install_hooks и блокируют работу вне протокола.
  - Doc‑only fast path разрешён только для `docs/**`, `STATE.md`, `STRUCTURE.md`, `AGENTS.md`.
  - Текущая сессия зарегистрирована в `docs/SESSIONS` и `docs/SESSION_INDEX.md`.
- **Checks:**
  - `bash -n scripts/session_start.sh`
  - `bash -n scripts/session_check.sh`
  - `bash -n scripts/session_end.sh`
  - `bash -n scripts/session_audit.sh`
  - `bash -n scripts/session_gate.sh`
  - `bash -n scripts/install_hooks.sh`
- **Evidence:** `git diff --stat`, вывод `bash -n`.
- **Rollback:** удалить добавленные файлы и откатить изменения в docs/scripts/hooks.
- **No-go:** не трогать runtime код, БД, миграции, `_legacy.py`, инфраструктуру.
- **Риски/блокеры:** нет.
- **Branch/Worktree/Base/Merge/Cleanup:**
  - Branch: `feat/session-governance-2026-01-27`
  - Worktree: `/home/zhan/worktrees/session-governance-2026-01-27`
  - Base: `origin/main`
  - Merge: `merge --no-ff` (без rebase)
  - Cleanup: удалить worktree + ветку после merge (Brain/Top Architect).
