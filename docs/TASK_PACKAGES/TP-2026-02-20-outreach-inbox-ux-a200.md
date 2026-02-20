# TP-2026-02-20-outreach-inbox-ux-a200

## Название/цель
Улучшить UX вкладки «Заявки» для outreach/human-lock: сделать действие заметным и понятным, убрать необходимость `zoom out`, сохранить текущие API/контракты.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Не менять backend-контракты outreach/human-lock.
- Не ломать текущую RBAC-логику для `outreach`.
- Не ухудшать существующий flow inbox/chat/details.

## Scope
1. Адаптивная высота inbox-layout без жёсткого `min-h/calc(...)`.
2. Улучшение discoverability ручного сообщения клиенту.
3. Снижение визуальной нагрузки: сворачиваемый outreach-panel.

## Out of scope
- Новые backend endpoint-ы.
- Изменения в data model/migrations.
- Массовые рассылки/marketing flow.

## Touch-list
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/ConsoleShell.tsx`

## Plan
1. Убрать жёсткие высоты и перевести контейнеры на `flex/min-h-0`.
2. Добавить явный CTA «Связаться с клиентом» в шапку заявки.
3. Сделать outreach блок сворачиваемым, переименовать тексты на понятный оператору русский.
4. Прогнать lint/build для изменённых компонентов.

## DoD
- На странице «Заявки» контент помещается по высоте без принудительного `zoom out`.
- В карточке заявки есть явный вход в ручное сообщение клиенту.
- Outreach-панель разворачивается/сворачивается и не перегружает экран.
- `npm lint` и `npm build` проходят.

## Checks
- `npm --prefix console-web run lint -- --file src/components/InboxView.tsx --file src/components/CaseConversation.tsx --file src/components/ConsoleShell.tsx`
- `npm --prefix console-web run build`

## Evidence
- Локальный lint/build output в сессии.

## Rollback
- `git revert` коммита UX-правок.

## No-go
- Не менять backend/API контракты.
- Не добавлять новые RBAC исключения.

## Риски/блокеры
- Требуется реальный визуальный smoke на целевом разрешении после деплоя.
- Локальный скрин не заменяет live-check на прод-подобном окружении.

## Branch / Worktree
- Branch: `fix/2026-02-20-outreach-inbox-ux-a200`
- Worktree: `/home/zhan/worktrees/2026-02-20-outreach-inbox-ux-a200`
- Base ref: `origin/main`
- Merge policy: merge-only
- Cleanup: после merge удалить branch/worktree
