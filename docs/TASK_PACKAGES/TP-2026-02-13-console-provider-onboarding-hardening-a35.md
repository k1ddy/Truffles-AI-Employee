# TP-2026-02-13-console-provider-onboarding-hardening-a35

- Название/цель: Закрыть три P0 направления для Console Plane после merge: (1) довести autopilot UI до полного `provider_binding` контракта, (2) добавить Console-first SLA контур для ручного ChatFlow lifecycle, (3) завершить переход к domain-first MDC v2 и вынести salon-legacy в compatibility mapper.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` NOW/GAP (Console-first onboarding/support, quality gates)
  - `STRATEGY/REQUIREMENTS.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `TECH.md`

## Invariant
- Не ослаблять GO/NO-GO/scorecard hard-stop и tenant RBAC.
- Не ломать существующий `instance_id -> webhook_secret` контракт.
- Не вводить обходы через legacy/admin surface вместо Console plane.

## Scope
- Autopilot UI: добавить provider binding поля в форму и отправку payload.
- Provider lifecycle SLA: backend + UI поля `owner`, `next_renewal_at`, `last_rebind_at`, `rebind_required`, `alert_state`; hard-stop для activate/go-live/autopilot при `expired` или `rebind_required`.
- MDC v2 domain-first: перейти на canonical `client_pack.business/location/operations/catalog/communication`; salon-legacy оставить только в адаптере совместимости.

## Out of scope
- Автоматизация ChatFlow через внешний API/polling (если API отсутствует).
- Изменение webhook runtime логики вне onboarding/integrations scope.
- Изменение LLM runtime/booking policy за пределами readiness/onboarding.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/schemas/onboarding_contract.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/services/onboarding_intake_service.py`
- `truffles-api/app/services/knowledge_validation.py`
- `truffles-api/app/services/onboarding_contract_service.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/types/api.generated.ts`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_onboarding_contract_service.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_knowledge_validation.py`
- `truffles-api/tests/test_onboarding_intake_service.py`

## Plan
1. Autopilot UI: добавить `provider_binding.whatsapp` поля и отправку в `OnboardingAutopilotRequest`.
2. Provider SLA contract: расширить onboarding contract + integrations lifecycle модель новыми SLA полями.
3. Hard-stop gates: блокировать activate/go-live/autopilot при `paid_until_expired` или `rebind_required`.
4. Console Integrations UI: вывести SLA статус, owner, due dates, alert-state.
5. MDC v2 domain-first: перенести парсинг/валидацию на canonical paths, salon оставить в mapper aliases.
6. Обновить OpenAPI + regenerate frontend types.
7. Прогнать целевые backend/UI проверки и зафиксировать evidence.

## DoD
- Autopilot UI отправляет `provider_binding` и сервер сохраняет без ручного patch.
- Go-live/activate/autopilot fail-closed при `rebind_required` или `paid_until_expired`.
- Integrations page показывает lifecycle SLA поля и actionable drift statuses.
- MDC v2 readiness выдаёт canonical missing keys; salon-legacy проходит только через explicit compatibility mapping.
- OpenAPI/types синхронизированы; целевые тесты green.

## Checks
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "autopilot or go_live or waive"`
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_onboarding_state.py`
- `pytest -q truffles-api/tests/test_onboarding_contract_service.py truffles-api/tests/test_console_onboarding_contract_api.py`
- `pytest -q truffles-api/tests/test_knowledge_validation.py truffles-api/tests/test_onboarding_intake_service.py`
- `pytest -q truffles-api/tests/test_console_*.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/app/integrations/page.tsx`

## Evidence
- `git status -sb`
- `git diff --stat`
- Вывод команд из раздела Checks
- Ссылки на изменённые API/UI contracts и тесты
- Запись в `docs/SESSIONS/SESSION-...` и при необходимости в `STATE.md` (Brain/Top Architect до merge для core behavior)

## Rollback
- `git revert COMMIT_SHA_FROM_THIS_PR`
- Быстрый rollback поведения: отключить новые SLA-hard-stop проверки (rebind/expiry) отдельным revert-коммитом, сохранив поля данных.

## No-go
- Не добавлять обходы hard-stop по ролям.
- Не подменять truth status ручными статусами без source data.
- Не возвращать salon-specific keys как canonical output контракта.

## Branch / Worktree
- Branch: `feat/2026-02-13-console-provider-onboarding-hardening-a35`
- Worktree: `/home/zhan/worktrees/2026-02-13-console-provider-onboarding-hardening-a35`
- Base ref: `origin/main`
- Merge policy: merge only (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Объёмный diff по API/UI/typegen, нужен строгий контрактный контроль.
- Возможен регресс intake parsing для legacy payload без отдельного compatibility слоя.
- Потребуется аккуратная миграция тест-фикстур с salon keys на canonical keys.
