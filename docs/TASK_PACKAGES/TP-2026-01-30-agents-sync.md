# TP-2026-01-30 — AGENTS sync + workspace anchor

## Название/цель
Синхронизировать `/home/zhan/AGENTS.md` с репозиторием и добавить workspace‑anchor блок в `AGENTS.md` внутри репо для устранения дрейфа инструкций.

## Invariant
- Канон: repo‑доки приоритетнее локальных файлов.
- Только doc‑изменения, без кода.

## Scope
- Добавить workspace‑anchor блок в `AGENTS.md` (repo).
- Синхронизировать `/home/zhan/AGENTS.md` с обновлённым репо‑файлом.

## Out of scope
- Любые изменения в `SPECS/*`, `STATE.md`, коде и тестах.
- Обновления других локальных файлов.

## Touch-list
- `AGENTS.md`
- `/home/zhan/AGENTS.md`
- `docs/SESSIONS/SESSION-2026-01-30-agents-sync-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить workspace‑anchor блок в repo `AGENTS.md`.
2. Скопировать обновлённый `AGENTS.md` в `/home/zhan/AGENTS.md`.
3. Обновить session log + SESSION_INDEX.

## DoD
- Repo `AGENTS.md` содержит workspace‑anchor блок.
- `/home/zhan/AGENTS.md` полностью соответствует repo‑версии.
- Док‑изменения только.

## Checks
- `diff -u /home/zhan/AGENTS.md AGENTS.md` (из worktree)

## Evidence
- Диффы `AGENTS.md` + подтверждение sync.

## Rollback
- `git revert COMMIT_SHA`

## No-go
- Кодовые правки.

## Branch/worktree
- Branch: `docs/2026-01-30-agents-sync-a1`
- Worktree: `/home/zhan/worktrees/2026-01-30-agents-sync-a1`
- Base: `origin/main`
- Merge policy: PR (doc-only)
- Cleanup: Brain

## Риски/блокеры
- Несовпадение локальной и repo‑версии после sync.
