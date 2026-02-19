# TP-2026-02-19-console-context-banner-dedupe-a130

- Название/цель: убрать визуальный перегруз в верхней зоне Console Plane, сохранив ценность контекстной прозрачности и быстрых действий Ops/Tenants.
- Canon refs: `AGENTS.md`, `STATE.md` (GAP по UX/понятности console контекста), `STRUCTURE.md`, `docs/CONSOLE_GUIDE.md`.

## Invariant
- Контекст `Компания/Клиент/Филиал` остаётся явным и всегда видимым в header.
- Права доступа (`canReadOps`, `canReadTenants`) не ослабляются.
- `ContextHealthStrip` остаётся источником health-сигналов при предупреждениях/ошибках.

## Scope
- Перенастроить отображение `ContextHealthStrip`, чтобы постоянный info-баннер не дублировал контекст при нормальном состоянии.
- Сохранить идею "только активные" через более лёгкий UI-паттерн (чип/tooltip) без постоянной плашки.
- Убрать desktop-дублирование быстрых ссылок `Ops`/`Тенанты` при наличии боковой навигации.

## Out of scope
- Перестройка IA/навигации Console целиком.
- Изменения backend API/контрактов.
- Изменения RBAC-матрицы.

## Touch-list (allowed)
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/globals.css` (только если потребуется минимальный стиль tooltip/chip)
- `console-web/e2e/*.spec.ts` (только если потребуется обновить/добавить UI-assert)

## Plan
1. Разделить в `ContextHealthStrip` health-сообщения и информационные подсказки, оставить предупреждения приоритетом.
2. Заменить постоянный текст `platform_active_filter` на компактный чип с пояснением по hover/focus.
3. Ограничить `Открыть Ops`/`Открыть Тенанты` для mobile-контекста, чтобы не дублировать sidebar на desktop.
4. Прогнать lint + targeted e2e/screenshot check для фактической верификации UX.

## DoD
- При нормальном состоянии в header нет длинной дублирующей плашки про активные сущности.
- Пользователь всё ещё видит, что действует фильтр "только активные" (компактно и читаемо).
- Предупреждения (`no_active_branches`, `no_clients_for_company`, `company_missing`) остаются заметными.
- Быстрые ссылки в health-strip не создают desktop-дубль с левой навигацией.

## Checks
- `npm --prefix console-web run lint -- --file src/components/ConsoleShell.tsx`
- `cd console-web && npx playwright screenshot --device="Desktop Chrome" https://console.truffles.kz /tmp/console-context-after.png` (или эквивалентный локальный Playwright script с login)
- `./scripts/session_check.sh`

## Evidence
- Скриншот до/после верхней зоны с контекстом.
- `git diff --stat` + целевые фрагменты `ConsoleShell.tsx`.
- Логи lint/проверок.

## Rollback
- `git revert MERGE_COMMIT_SHA` после merge PR (или `git revert HEAD` в ветке до merge).

## No-go
- Не удалять и не ослаблять контекстный control bar (`Компания/Клиент/Филиал`).
- Не убирать health предупреждения в silent-режим.
- Не добавлять новую сложную навигацию или modal flow.

## Риски/блокеры
- Возможны ожидания e2e по старому `data-testid`/copy.
- Разные роли (platform_admin vs owner/admin/manager) показывают разные варианты header.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-19-console-context-banner-dedupe-a130`
- Worktree: `/home/zhan/worktrees/2026-02-19-console-context-banner-dedupe-a130`
- Base ref: `origin/main`
- Merge policy: PR -> main (no rebase)
- Cleanup: Brain/Top Architect после merge
