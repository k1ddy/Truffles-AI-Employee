# TP-2026-01-29 — Dialog Report Tool (one-command analysis)

- Название/цель: сделать каноничный one-command инструмент анализа диалогов (таймлайн + decision_meta/outbox + media/ASR) для любых агентов и сессий.
- Canon refs: `AGENTS.md`, `STATE.md`, `SPECS/SYSTEM_REFERENCE.md`, `docs/SESSION_START_PROMPT.txt`, `STRUCTURE.md`.
- Invariant: read-only; не менять core-пайплайн/LLM/decision graph; не трогать `_legacy.py`.
- Scope:
  - Новый subcommand `dialog-report` в `ops/diagnose.py`.
  - Runbook: `docs/runbooks/DIALOG_REPORT.md`.
  - Документация: `SPECS/SYSTEM_REFERENCE.md`, `docs/SESSION_START_PROMPT.txt`, `STRUCTURE.md`.
  - Обновить `STATE.md` с evidence после прогона.
- Out of scope: изменения core-логики, RBAC, миграции БД, CI.
- Touch-list:
  - `ops/diagnose.py`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `docs/SESSION_START_PROMPT.txt`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/runbooks/DIALOG_REPORT.md`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-01-29-dialog-report-a1.md`
- Plan:
  1) Реализовать `ops/diagnose.py dialog-report` (read-only).
  2) Обновить канон-доки + runbook с инструкцией.
  3) Прогнать команду и сохранить отчёт (evidence).
  4) Зафиксировать DONE в `STATE.md`.
- DoD:
  - Команда выдаёт понятный отчёт (таймлайн, решения, outbox, медиа/ASR).
  - Документы отражают новый primary-tool.
  - Evidence сохранён и указан в `STATE.md`.
- Checks:
  - `python3 ops/diagnose.py dialog-report --help`
  - Прогон на реальных параметрах (read-only).
- Evidence:
  - Путь к отчёту (например `/tmp/dialog-report-*.md`) + команды запуска.
- Rollback: revert merge commit.
- No-go: любые записи в БД, изменение core/LLM, `docker exec` с write-операциями.
- Риски/блокеры: если указан неправильный receiver phone/таймзона — отчёт будет пуст.
- Branch / Worktree / Base:
  - Branch: `feat/2026-01-29-dialog-report-a1`
  - Worktree: `/home/zhan/worktrees/2026-01-29-dialog-report-a1`
  - Base ref: `origin/main`
  - Merge policy: merge commit
  - Cleanup: удалить ветку и worktree после merge
