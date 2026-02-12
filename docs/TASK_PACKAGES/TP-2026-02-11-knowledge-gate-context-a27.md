# TP-2026-02-11 Knowledge Gate Context UX (a27)

## Название/цель
Упростить UX вкладки Knowledge для Platform Admin: убрать дублирующий branch gate, стабилизировать tenant/branch context при переходах в связанные разделы и сделать поведение предсказуемым.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSIONS/SESSION-2026-02-11-knowledge-ux-hotfix-a27.md`

## Invariant
- Контракты `/console/v1/knowledge/*` и RBAC не меняются.
- Branch-change publish по-прежнему требует diff + reason.
- Cross-tenant безопасность заголовков `X-Company-Id/X-Client-Id/X-Branch-Id` не ослабляется.

## Scope
- `console-web/src/app/knowledge/page.tsx`
  - убрать двойной UX-gate выбора branch;
  - унифицировать apply context для кнопок fleet panel;
  - исключить визуальный "провал" в состояние disabled после успешного branch select.

## Out of scope
- backend API изменения;
- deploy/CI изменения;
- redesign других вкладок.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `docs/TASK_PACKAGES/TP-2026-02-11-knowledge-gate-context-a27.md`
- `docs/SESSIONS/SESSION-2026-02-11-knowledge-gate-context-a27.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Убрать вторичный gate (`Продолжить`) в пользу единой точки `Открыть филиал`.
2. Исправить переходы fleet actions так, чтобы branch context сохранялся где ожидается.
3. Добавить явные UX-подсказки по состоянию контекста.
4. Прогнать `lint/build` для `console-web`.

## DoD
- После выбора branch через fleet panel страница Knowledge не требует повторного `Продолжить`.
- Переходы `Команда и мастера`/`Управлять в Team` сохраняют branch context.
- Переходы client-level (`Интеграции`/`Заявки`) явно маркированы как client scope.
- `npm run lint` + `npm run build` зеленые.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && npm run build`

## Evidence
- `git diff --stat`
- консольный вывод lint/build
- PR URL

## Rollback
- revert commit со страницей Knowledge.

## No-go
- не менять API роуты/миграции;
- не обходить hooks.

## Риски/блокеры
- e2e не покрывает все сценарии context drift; локальный UI аудит обязателен после правок.
