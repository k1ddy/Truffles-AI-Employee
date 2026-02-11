# TP-2026-02-11 Tenants PR-A Stabilization (a27)

## Название/цель
Закрыть Wave 1 для вкладки `Tenants`: стабилизировать UX и контрактные валидации без изменения продуктовой архитектуры.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants / Console audit findings)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-02-11-tenants-admin-full-audit/audit-summary.json`

## Invariant
- RBAC/tenant isolation не ослабляются.
- Деструктивные действия требуют явного подтверждения.
- API-контракты `/console/v1/admin/*` обратно совместимы для валидных payload.

## Scope
- Backend: строгие validators (`timezone`, `phone`, `telegram_chat_id`, `knowledge_tag`) в branch flows + autopilot.
- Frontend: убрать browser `prompt/confirm`; inline confirm-блок lifecycle клиента.
- UX copy: заменить критичные англоязычные/непрозрачные CTA на понятные оператору.
- E2E smoke: безопасные проверки Tenants lifecycle/branch-change controls.
- Canon sync: обновить docs по фактическому UI/API-поведению.

## Out of scope
- Полный редизайн информационной архитектуры Tenants.
- Новые сущности/миграции БД.
- Полный перевод всех тех-терминов backend-domain.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_branch_changes.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Plan
1. Ужесточить backend-валидации и покрыть тестами.
2. Перевести lifecycle клиента на inline подтверждение.
3. Упростить ключевые CTA/тексты на Tenants.
4. Добавить non-mutating e2e smoke для новых UI-контролов.
5. Обновить аудит-документацию и зафиксировать evidence.

## DoD
- Невалидные значения `timezone/phone/telegram_chat_id/knowledge_tag` отклоняются с `INVALID_PARAM`.
- Lifecycle клиента не использует browser prompt/confirm.
- Ключевые действия branch-change понятны в UI и покрыты smoke.
- Локальные проверки проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_console_admin_provisioning.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --grep "Tenants"`

## Evidence
- `git diff --stat`
- Вывод checks
- `docs/CONSOLE_AUDIT/artifacts/2026-02-11-tenants-admin-full-audit/*`

## Rollback
- Revert commit PR-A по touch-list.

## No-go
- Не менять `_legacy.py` и core message pipeline.
- Не делать destructive live-mutations в production-контуре без явного разрешения.
- Не подгонять тесты хардкодом под конкретный tenant.

## Риски/блокеры
- Разные окружения (`localhost` vs `console.truffles.kz`) могут давать различное фронтенд-поведение.
- UI-локализация может затронуть e2e-селекторы по тексту (решение: data-testid).
