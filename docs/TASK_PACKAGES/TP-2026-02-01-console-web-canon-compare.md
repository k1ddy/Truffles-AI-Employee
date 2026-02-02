# TP-2026-02-01-console-web-canon-compare

- Название/цель: Сравнить канон/план Web Console с фактической реализацией и зафиксировать расхождения по ролям, страницам и действиям, с ссылками на код и канон.
- Canon refs: `STATE.md` (2026-01-21 Console plan inventory GAP), `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: только документация; без изменений кода/БД/поведения; все утверждения либо канон, либо реализовано в коде.
- Scope:
  - Создать сравнение «Canon vs Implemented» для Web Console (роли, навигация, страницы, ключевые действия).
  - Привязать каждую позицию к канону и к реализации (код/док инвентаря).
  - Обновить индекс `docs/CONSOLE_AUDIT/INDEX.md` и карту документов в `STATE.md`.
- Out of scope:
  - Любые изменения runtime/контрактов/канона.
  - Новые фичи, UI-правки, тесты, живые проверки.
- Touch-list:
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md` (new)
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `STATE.md` (добавить DONE + карту документов)
  - `docs/SESSIONS/SESSION-*.md`, `docs/SESSION_INDEX.md`
- Plan:
  1) Прочитать канон: `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`.
  2) Сопоставить с инвентарём реализации (`docs/CONSOLE_AUDIT/*`) и кодом по ключевым разделам.
  3) Составить `CANON_VS_IMPLEMENTED.md` с метками: match / partial / missing, с ссылками.
  4) Обновить `INDEX.md` и `STATE.md` (DONE + карта документов).
  5) Проверить, что изменения doc-only.
- DoD:
  - Новый документ сравнения покрывает: роли/RBAC, навигацию, Inbox, Calendar, Knowledge, Team, Settings, Ops, Audit, Tenants, Provisioning Wizard.
  - Каждый пункт содержит ссылку на канон и реализацию (код или инвентарь).
  - Явно отмечены расхождения (partial/missing) и список GAP в конце документа.
  - `docs/CONSOLE_AUDIT/INDEX.md` содержит ссылку на сравнение.
  - `STATE.md` обновлен: DONE запись + карта документов.
- Checks:
  - `rg --files docs/CONSOLE_AUDIT`
  - `scripts/session_check.sh`
- Evidence:
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `STATE.md`
- Rollback:
  - Revert коммит с doc-only изменениями.
- No-go:
  - Изменения кода/контрактов/канона; любые runtime-проверки или вмешательство в БД.
- Branch / Worktree:
  - Branch: `feat/2026-02-01-console-web-canon-compare-a4`
  - Worktree: `/home/zhan/worktrees/2026-02-01-console-web-canon-compare-a4`
  - Base ref: `feat/2026-02-01-console-web-inventory-a4`
  - Merge policy: только merge (без rebase); при необходимости — merge `origin/main` в ветку.
  - Cleanup: удалить ветку и worktree после merge.
- Риски/блокеры:
  - Инвентарь реализации ещё не в `main`; работа ведётся от ветки-инвентаря.
