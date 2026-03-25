# TP-2026-02-11 Tenants PR-B IA v2 (a27)

## Название/цель
Пересобрать вкладку `Tenants` в понятный lifecycle-centered интерфейс: `Portfolio`, `Onboarding`, `Change Management`, `Decommission`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants findings + UX gaps)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Invariant
- Нельзя ухудшить существующие provisioning возможности platform_admin.
- Нельзя ломать API-совместимость backend.
- Нельзя прятать audit-critical действия без подтверждаемого следа.

## Scope
- Перекомпозиция layout и навигации внутри Tenants.
- Явные зоны: портфель, онбординг, изменения, деактивация.
- Понятные пользовательские тексты, contextual help, action-first controls.
- Обновление e2e smoke/navigation для новой IA.

## Out of scope
- Новый backend доменный слой.
- Массовые bulk-операции и авто-оркестрация за пределами текущих API.

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/ConsoleShell.tsx` (если нужен nav refactor)
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Plan
1. Снять IA-map текущего экрана и определить блоки по lifecycle.
2. Вынести action-first секции с читаемым hierarchy.
3. Сохранить текущие API вызовы, меняя только presentation слой.
4. Обновить e2e smoke и документацию.

## DoD
- Оператор может пройти onboarding/change/decommission без чтения исходного кода.
- Все ключевые действия доступны за <= 2 перехода на странице.
- Smoke-tests по Tenants navigation и key-actions зелёные.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --grep "Tenants|Navigation"`

## Evidence
- Скриншоты до/после
- `git diff --stat`
- Вывод checks

## Rollback
- Revert commit PR-B.

## No-go
- Не вносить backend изменения без отдельного TP.
- Не смешивать IA-рефактор и бизнес-логику в одном PR.

## Риски/блокеры
- Риск UX-регрессии из-за перестройки layout.
- Митигация: feature-flag или поэтапное включение секций.
