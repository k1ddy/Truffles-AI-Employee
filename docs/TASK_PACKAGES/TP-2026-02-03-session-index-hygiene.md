# TP-2026-02-03-session-index-hygiene

- Название/цель: Стабилизировать работу с `docs/SESSION_INDEX.md` и `docs/SESSIONS/*` (уменьшить дрейф и незакомиченные артефакты) через скрипт пересборки индекса и опциональный авто-коммит на старте сессии.
- Canon refs: `AGENTS.md`, `STRUCTURE.md`, `STATE.md` (GAP: дрейф session-артефактов), `docs/SESSION_START_PROMPT.txt`.
- Invariant: правила session-gate не меняем; doc-only gate на `main` сохраняем; формат session-файлов не ломаем.
- Scope:
  - Новый скрипт `scripts/session_index_rebuild.sh` (пересборка `docs/SESSION_INDEX.md` из `docs/SESSIONS/*`).
  - Опциональный авто-коммит session log + index в `scripts/session_start.sh`.
  - Обновление `AGENTS.md` и `STRUCTURE.md` (инструкция и карта файлов).
  - Обновление `STATE.md` (фиксируем дрейф как закрытую проблему).
- Out of scope: чистка существующих dirty worktrees, изменение session_end/resume, изменение doc-only политики.
- Touch-list:
  - `scripts/session_start.sh`
  - `scripts/session_index_rebuild.sh` (new)
  - `AGENTS.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1) Зафиксировать GAP в `STATE.md` (дрейф session-артефактов).
  2) Добавить `scripts/session_index_rebuild.sh`.
  3) Добавить авто-коммит в `scripts/session_start.sh` (ENV/flag).
  4) Обновить `AGENTS.md` и `STRUCTURE.md`.
  5) Проверки (bash -n).
  6) Обновить session log + `docs/SESSION_INDEX.md`.
- DoD:
  - `scripts/session_index_rebuild.sh` пересобирает индекс из session-файлов.
  - `scripts/session_start.sh` поддерживает авто-коммит session log + index.
  - Процесс задокументирован в `AGENTS.md`, скрипт добавлен в `STRUCTURE.md`.
  - `STATE.md` обновлён с evidence.
- Checks:
  - `bash -n scripts/session_start.sh scripts/session_index_rebuild.sh`
- Evidence:
  - Изменения в `scripts/session_start.sh`, `scripts/session_index_rebuild.sh`, `AGENTS.md`, `STRUCTURE.md`, `STATE.md`.
- Rollback: revert commit; удалить новый скрипт; вернуть старое поведение `session_start.sh`.
- No-go: правки doc-only gate и session_id формата; правки `_legacy.py`.
- Риски/блокеры: конфликт по `docs/SESSION_INDEX.md` при параллельных сессиях.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-session-index-hygiene-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-03-session-index-hygiene-a1`
  - Base: `origin/main`
  - Merge: PR → `main`
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
