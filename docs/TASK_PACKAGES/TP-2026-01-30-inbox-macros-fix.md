# TP-2026-01-30 — Inbox macros load + chat frame fix

## Название/цель
Исправить ошибку загрузки быстрых ответов в Inbox и убрать двойной бордер/скругления у чата, не ломая RBAC и веточные контексты.

## Canon refs
- `STRATEGY/REQUIREMENTS.md`
- `STATE.md` NOW (GAP: Inbox macros load error + double chat border)

## Invariant
- Inbox take/resolve/send без изменений поведения.
- RBAC и branch scoping (`X-Branch-Id`) остаются как есть.

## Scope
- UI: исправить двойной бордер/скругления в чате.
- UI: сделать ошибку загрузки макросов диагностируемой (retry) без изменения контракта.
- Ops: проверить наличие `console_macros` таблицы; при отсутствии применить миграцию `017_add_console_macros.sql`.

## Out of scope
- Новые фичи макросов/контента.
- Любые изменения схемы/контрактов, кроме применения существующей миграции.

## Touch-list
- `console-web/src/components/InboxMacros.tsx`
- `console-web/src/components/ChatInterface.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/InboxView.tsx`
- `truffles-api/migrations/017_add_console_macros.sql` (apply if missing on prod)
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-30-inbox-macros-fix-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать GAP в `STATE.md` до правок.
2. Проверить наличие `console_macros` в БД; при отсутствии применить миграцию.
3. Убрать двойной бордер: добавить режим без рамки для `ChatInterface`, включить его в Inbox card.
4. Улучшить UX ошибки макросов: retry и ясное сообщение при API ошибке.
5. Проверки (lint) + evidence; обновить `STATE.md` на DONE.

## DoD
- Быстрые ответы не падают при наличии таблицы; ошибка отображается с кнопкой повтора.
- Чат в Inbox имеет одну рамку/скругление.
- `npm --prefix console-web run lint` проходит.

## Checks
- `npm --prefix console-web run lint`

## Evidence
- CI run URL.
- SQL proof `to_regclass('public.console_macros')` (до/после при миграции).
- Запись в `STATE.md` (GAP -> DONE).

## Rollback
- Откат PR. Миграцию не откатываем без отдельного запроса.

## No-go
- Красный CI.
- Неожиданные файлы в diff.
- Любые изменения контрактов без согласования.

## Риски/блокеры
- Отсутствие `console_macros` таблицы на проде.
