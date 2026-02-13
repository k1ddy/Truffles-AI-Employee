# TP-2026-02-13-provider-binding-hardstop-a34

- Название/цель: Ввести manual Provider Binding Contract для ChatFlow (instance/webhook/paid_until) и включить hard-stop в onboarding scorecard/go-live/autopilot, чтобы исключить запуск без подтвержденной ручной привязки.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` NOW: TODO по automation onboarding/go-no-go (instanceId/phone/webhook/gate) и факт по integrations drift без provider billing SLA
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STRATEGY/REQUIREMENTS.md`

## Invariant
- Не ослаблять текущие go-live gate и onboarding step-order.
- Не ломать текущий контракт `instance_id -> webhook_secret`.
- Сохранить multi-tenant/RBAC поведение (`_require_client_access`/`_require_company_access`).

## Scope
- Добавить в onboarding contract payload обязательные для WA-manual binding поля (provider_binding) с валидацией.
- Подключить provider_binding к scorecard missing list и go-live readiness.
- Добавить UI-поля в Provisioning Wizard для ввода manual binding данных.
- Обновить OpenAPI + generated API types.
- Добавить/обновить тесты backend+frontend unit уровня по новому gate.

## Out of scope
- Интеграция с ChatFlow API (отсутствует по условиям).
- Новый отдельный WhatsApp health endpoint.
- Полный incident workflow rebind (это следующий PR).

## Touch-list
- `truffles-api/app/schemas/onboarding_contract.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/services/onboarding_contract_service.py` (при необходимости сериализации)
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_access_admin_pr2.py` (при необходимости)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Расширить `OnboardingContractPayload` моделью `provider_binding` (chatflow manual fields, валидаторы дат/обязательностей для whatsapp-enabled).
2. В `build_onboarding_inputs` и `missing_prerequisites(GO_NO_GO)` добавить признаки/проверки provider binding (`paid_until`, `webhook_applied_at`, `bound_at`).
3. Обновить autopilot/contract serialization так, чтобы новые поля корректно проходили и возвращались API.
4. Добавить UI-секцию в Provisioning Wizard для редактирования provider binding и сохранения через `patch onboarding contract`.
5. Обновить OpenAPI и `console-web` generated types.
6. Добавить/обновить тесты на fail/pass gate.

## DoD
- При `channels.whatsapp=true` scorecard/go-live/autopilot блокируются без валидного provider binding.
- Missing-list явно показывает новые обязательные поля provider binding.
- Платформенный оператор может ввести данные binding в Console и снять блокировку.
- Тесты backend по onboarding state проходят; frontend lint/typecheck не деградируют.

## Checks
- `pytest -q truffles-api/tests/test_console_onboarding_state.py`
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding or go_live or autopilot"`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint`

## Evidence
- `git diff --stat`
- Outputs of checks above
- Новые/обновленные тест-кейсы с provider binding missing/pass
- Обновление `STATE.md` выполняет Brain/Top Architect до merge (ссылки на evidence)

## Rollback
- `git revert COMMIT_SHA` в ветке PR.
- Если потребуется быстрый rollback поведения: убрать provider binding checks из GO_NO_GO, оставив поля неиспользуемыми.

## No-go
- Не добавлять обходы gate через role exceptions.
- Не писать billing/provider статус в runtime через хардкод.
- Не трогать legacy webhook routing вне нужного scope.

## Branch / Worktree
- Branch: `feat/2026-02-13-provider-binding-hardstop-a34`
- Worktree: `/home/zhan/worktrees/2026-02-13-provider-binding-hardstop-a34`
- Base ref: `origin/main`
- Merge policy: только merge (без rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Нужна аккуратная backward compatibility для старых onboarding contracts без `provider_binding`.
- Возможен контрактный дрейф, если не обновить generated API types после OpenAPI.
