# TP-2026-02-16-owner-admin-ux-simplify-a88

- Название/цель: упростить Console Plane для бизнес-пользователей (owner/admin) через бизнес-first навигацию и понятный action flow без технического шума.
- Canon refs: `STATE.md` (NOW runtime/UX gaps), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-08`, `UX-26`), `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`, `AGENTS.md`.

## Invariant
- Не ломать RBAC и доступность owner/admin маршрутов.
- Не менять контракты API `/console/v1/business/*` и `/console/v1/settings`.
- Не ухудшить существующие owner/admin smoke сценарии.

## Scope
- Упростить owner/admin левое меню: default business-first режим с переключателем "Показать расширенное меню".
- Добавить на `/business` простой блок "Что делать сейчас" с приоритетом и понятным next-step для владельца.
- Упростить copy на бизнес-экранах (убрать технические термины из primary UX surface).
- Зафиксировать изменения в `UX_BACKLOG` и `STATE.md` с evidence.

## Out of scope
- Рефактор backend owner/admin API.
- Полный redesign всех страниц Console.
- Изменение платформенных ролей/прав доступа.

## Touch-list
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/business/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`

## Plan
1. Ввести owner/admin business-first фильтр навигации + toggle для расширенного меню.
2. Добавить на `/business` короткий блок "Что делать сейчас" (3 шага максимум) и упростить метки.
3. Обновить smoke e2e под новый UX-поток (toggle + доступ к hidden routes).
4. Обновить `UX_BACKLOG` и `STATE.md` фактами.
5. Прогнать lint/build/smoke-list checks.

## DoD
- Owner/Admin по умолчанию видит сокращенное business-first меню без перегруза техническими пунктами.
- Любой скрытый пункт остается доступным через toggle "расширенное меню".
- На `/business` есть понятный блок next-actions без технического жаргона.
- `owner-admin-business.spec.ts` отражает новый UX-путь и проходит в списке тестов.
- Доки и `STATE.md` обновлены evidence-форматом.

## Checks
- `npm --prefix console-web run lint -- --file src/components/ConsoleShell.tsx --file src/app/business/page.tsx --file e2e/owner-admin-business.spec.ts`
- `npx --prefix console-web tsc --noEmit --incremental false`
- `npm --prefix console-web run test:e2e:smoke -- --list`
- `./scripts/session_check.sh`

## Evidence
- `git diff --stat`
- Измененные owner/admin UI файлы + e2e spec.
- Вывод lint/tsc/smoke-list команд.
- Обновленные `docs/CONSOLE_AUDIT/UX_BACKLOG.md` и `STATE.md`.

## Rollback
- Откатить commit UX-wave (`git revert` по SHA merge-коммита этого PR; SHA фиксируется в release log).
- Вернуть previous owner/admin nav behavior и copy.
- Перепроверить `owner-admin-business.spec.ts` smoke list.

## No-go
- Не скрывать критичный owner/admin функционал без fallback-toggle.
- Не добавлять новые API/миграции в этой UX-wave.
- Не смешивать UX simplification с platform-admin refactor.

## Риски/блокеры
- Возможные ожидания старых e2e по видимости nav пунктов.
- Риск перегиба в сторону "слишком скрыто" — компенсируется явным toggle и CTA на `/business`.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-16-owner-admin-ux-simplify-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-owner-admin-ux-simplify-a88`
- Base ref: `origin/main`
- Merge policy: PR -> main (no rebase)
- Cleanup: Brain/Top Architect после merge
