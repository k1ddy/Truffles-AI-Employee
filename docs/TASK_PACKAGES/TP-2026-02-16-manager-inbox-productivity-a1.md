# Task Package: Manager Inbox Productivity Bundle (One-shot)

- Название/цель: Убрать ключевые UX-потери менеджера в Inbox одним пакетом: фильтры не сбрасываются при открытии заявки, рабочая сессия удерживается 24 часа, при входе заявки открываются автоматически, ускоряется поток обработки очереди.
- Canon refs: docs/CONSOLE_AUDIT/pages/inbox.md, docs/CONSOLE_AUDIT/roles/manager.md, STATE.md (manager inbox operational gaps)

## Invariant
- Не ломать RBAC и branch-scope для manager/support/admin/owner.
- Не менять контракт backend handover state machine.
- Все изменения в inbox должны быть backward-compatible для API.

## Scope
- Persist manager workspace в Inbox (фильтры, поиск, auto-refresh, выбранная заявка) с TTL 24h.
- Авто-открытие заявки при входе в Inbox (последняя релевантная или первая из очереди).
- Next-case flow для быстрого перехода к следующей заявке без возврата в список.
- SLA countdown в карточке заявки для action-oriented приоритизации.
- Session hardening в console-web (24h session policy + keepalive refresh loop).

## Out of scope
- Изменение backend SLA логики и порогов.
- Новый backend endpoint для message retry/requeue.
- Полный редизайн Inbox layout.

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/src/lib/auth.ts`
- `console-web/src/app/providers.tsx`
- `console-web/src/components/LoginButton.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/e2e/smoke.spec.ts` (targeted test for filter/session persistence)
- `docs/CONSOLE_AUDIT/pages/inbox.md`
- `docs/CONSOLE_AUDIT/roles/manager.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-02-16-manager-inbox-productivity-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить persistence-слой для inbox-фильтров и выбранной заявки (TTL 24h).
2. Добавить авто-выбор/авто-открытие заявки и next-case flow в Inbox.
3. Добавить SLA countdown helper и вывести в шапке диалога.
4. Укрепить manager session: NextAuth 24h policy + SessionProvider keepalive.
5. Обновить e2e smoke и docs, прогнать проверки.

## DoD
- После выбора заявки фильтры/поиск не сбрасываются при навигации `/` -> `/cases/{id}` и при перезагрузке в пределах 24h.
- После открытия Inbox при наличии заявок автоматически открыт диалог (последняя релевантная или первая в очереди).
- В active-заявке есть быстрый переход к следующей заявке.
- В header заявки показан SLA countdown (до breach или перерасход).
- Manager session не отваливается из-за локальной политики раньше 24h при валидном refresh path.
- Доки Inbox/manager отражают новое поведение.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/components/CaseConversation.tsx --file src/utils/labels.ts --file src/lib/auth.ts --file src/app/providers.tsx`
- `cd console-web && npx tsc --noEmit --incremental false`
- `cd console-web && npx playwright test e2e/smoke.spec.ts --grep "filter|cases|inbox" --reporter=line` (targeted)
- `./scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Результаты lint/tsc/playwright.
- Скриншоты UI: persistent filters, auto-open case, next-case CTA, SLA countdown.
- Запись в `STATE.md` (FACT с evidence) перед merge для этого behavior change.

## Rollback
- Revert коммит/PR с возвратом старого inbox state/session поведения.

## No-go
- Никаких client-specific hardcode.
- Никаких silent auth bypass.
- Никаких изменений policy/LAW контрактов.

## Risks and blockers
- Поведение refresh token зависит от Keycloak realm policy; frontend hardening не заменяет серверную lifecycle-политику.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-16-manager-inbox-productivity-a1`
- Worktree path: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR -> main (no rebase)
- Cleanup: после merge удалить branch локально и в origin
