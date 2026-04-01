# TP-2026-02-07 Integrations Registry + Drift Guard (a15)

## Название/цель
Добавить в Console отдельный Integrations registry (минимум WhatsApp/Telegram per branch) и drift guard для случаев `instance_id mismatch`, `invalid webhook URL`, `no inbound N minutes` с audit/alert и видимым статусом в UI.

## Canon refs
- `AGENTS.md`
- `STATE.md` (GAP: Integrations registry + drift guard)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`

## Invariant
- Не ломаем текущий onboarding/provisioning flow.
- Read-only registry не меняет бизнес-данные branch/client.
- Drift detection прозрачен: status/issue list в API+UI и audit trail для state change.

## Scope
- Backend:
  - `GET /console/v1/admin/integrations`
  - per branch status: WhatsApp binding, Telegram binding, webhook URL validity, last inbound age, drift issues
  - drift signals: audit events (`integration_drift_detected` / `integration_drift_cleared`) + warning alert on detect
- Frontend:
  - новая страница `/integrations`
  - навигация в Console shell
  - таблица branch integration statuses + issues

## Out of scope
- Автоматическое исправление drift (только detect/report).
- Полный provider registry re-architecture/DEC.
- Runbook jobs migration (`sync_client`, `backfill`, etc.).

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_integrations_registry.py` (new)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/integrations/page.tsx` (new)
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить backend schemas и endpoint `/admin/integrations`.
2. Реализовать drift rule evaluation + audit/alert на изменение drift state.
3. Добавить backend unit tests на классификацию и drift signaling.
4. Добавить UI page и nav entry для Integrations.
5. Обновить OpenAPI и regenerate frontend types.
6. Прогнать target checks (pytest + openapi check + frontend lint).

## DoD
- В Console есть отдельная страница Integrations.
- API показывает per-branch binding/status/issues для WhatsApp/Telegram.
- Детектируются минимум 3 drift-сигнала:
  - `instance_id mismatch`
  - `invalid webhook URL`
  - `no inbound N minutes`
- При drift state change пишется audit event; при detect отправляется warning alert.
- Контракт и frontend types синхронизированы.

## Checks
- `PYTEST_ARGS='/app/tests/test_console_integrations_registry.py' scripts/test_api_container.sh`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`

## Evidence
- `git diff --stat` + список измененных файлов.
- Логи pytest/openapi/lint.
- PR checks summary.

## Rollback
- Revert-коммит по endpoint/schemas/ui/nav.

## No-go
- Не добавлять mutating actions в registry endpoint.
- Не менять lifecycle/write semantics из P0.
- Не трогать legacy `/admin/*` в этой задаче.

## Риски/блокеры
- Alert может шуметь без дополнительного cooldown; смягчить локальным state-change сигналом.
- Branches без inbound истории будут помечаться stale — это ожидаемо и должно быть явно видно в UI.
