# TP-2026-02-11 Tenants PR-C Schema Forms (a27)

## Название/цель
Сделать onboarding domain-agnostic: schema-driven формы вместо raw JSON как основной путь, с `Advanced JSON` как expert-mode.

## Canon refs
- `AGENTS.md`
- `STATE.md` (domain-agnostic gaps)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Invariant
- Данные в API остаются контрактно валидными.
- Экспертный JSON режим сохраняется как fallback.
- Не ухудшается traceability (reason/action/audit).

## Scope
- Визуальные формы для `billing_info`, `working_hours`, `booking_settings`, `purchased`.
- Явные constraints, placeholder-подсказки, enum-селекты.
- Встроенная валидация до API submit.
- `Advanced JSON` секции, синхронизированные с формами.

## Out of scope
- Переписывание backend схем.
- Миграция существующих tenant данных.

## Touch-list
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/app/tenants/page.tsx` (интеграция)
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Plan
1. Определить минимальный набор schema-driven полей для operator path.
2. Реализовать typed form state + двустороннюю синхронизацию с JSON fallback.
3. Добавить pre-submit validation и понятные ошибки.
4. Добавить e2e smoke на happy path и validation errors.

## DoD
- Оператор может заполнить onboarding без ручного редактирования JSON.
- Ошибки формата ловятся до API запроса.
- Advanced JSON доступен и согласован с визуальной формой.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --grep "Tenants|Onboarding"`

## Evidence
- Скриншоты формы + Advanced JSON
- `git diff --stat`
- Вывод checks

## Rollback
- Revert commit PR-C.

## No-go
- Не удалять JSON fallback без отдельного архитектурного решения.
- Не оставлять двусмысленные поля без format hints.

## Риски/блокеры
- Высокая плотность формы может перегрузить UI.
- Митигация: progressive disclosure + секционирование.
