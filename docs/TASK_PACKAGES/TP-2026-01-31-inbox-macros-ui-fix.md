# TP-2026-01-31 — Inbox macros UI fix (scroll + immediate list update)

## Название/цель
Исправить UI быстрых ответов в Inbox: обеспечить скролл до кнопки сохранения и отображать новые макросы сразу после сохранения без изменения API/контрактов.

## Canon refs
- `STRATEGY/REQUIREMENTS.md`
- `STATE.md` NOW (GAP: Inbox macros UI — scroll/visibility)

## Invariant
- Inbox take/resolve/send без изменений поведения.
- RBAC и branch scoping (`X-Branch-Id`) остаются как есть.
- Контракты API/БД не меняем.

## Scope
- UI: ограничить высоту панели макросов + скролл в режиме управления.
- UI: сортировка и мгновенное отображение новых макросов после сохранения.

## Out of scope
- Любые изменения backend, миграций, контрактов.
- Редизайн других вкладок.

## Touch-list
- `console-web/src/components/InboxMacros.tsx`
- `docs/SESSIONS/SESSION-2026-01-31-inbox-macros-ui-fix-a3.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1. Создать session log + worktree.
2. Добавить ограничение высоты и scroll для блока управления макросами.
3. Обновить порядок/отображение макросов после create/update (invalidate + local reorder).
4. Проверки и evidence.
5. Обновить `STATE.md` (GAP -> DONE) до merge.

## DoD
- Кнопка "Добавить/Сохранить" достижима скроллом на любом размере экрана.
- Новый макрос появляется в списке сразу после сохранения (без ручного refresh).
- `npm --prefix console-web run lint` проходит.

## Checks
- `npm --prefix console-web run lint`

## Evidence
- Лог lint: `/tmp/console_web_lint_inbox_macros_ui_fix_20260131.txt`
- Запись в `STATE.md` (GAP -> DONE) до merge.

## Rollback
- Откат PR и повторный deploy console-web на предыдущий коммит.

## No-go
- Красный CI.
- Неожиданные файлы в diff.
- Изменения API/БД/контрактов.

## Риски/блокеры
- Недостаточная высота панели в разных viewport.
