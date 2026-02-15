# Owner/Admin + Platform Admin Wave-8 Report (Incident Control Loop)

Date
- 2026-02-15

Goal
- Убрать blind operations при проблемах outbox/provider и дать role-scoped incident control loop в Console Plane:
  - `platform_admin`: fleet incidents (все компании),
  - `owner/admin`: incidents только своего business scope.

Delivered
- Backend incident API:
  - `GET /business/incidents`:
    - scope-aware incidents (`client`/`branch`),
    - причина (`reason_code` + `reason_label`),
    - метрики (`outbox_backlog`, `failed_24h`, `integration_degraded_branches`, `pending_handovers`),
    - безопасные шаги remediation (`dry_run` first).
  - `GET /admin/incidents`:
    - fleet incident feed для platform admin,
    - приоритизация по severity + operational risk.
- Root-cause classification:
  - `provider_unavailable`,
  - `provider_auth`,
  - `provider_rate_limited`,
  - `integration_degraded`,
  - `outbox_backlog`,
  - `handover_backlog`,
  - `unknown`.
- Suggested actions contract:
  - `open_ops`,
  - `outbox_process (dry_run)`,
  - `integration_reconcile (dry_run)`,
  - интеграционные переходы (`/integrations`, `/tenants`) и операционные переходы (`/`, `/business/team-performance`).
- Frontend:
  - `Ops` (platform_admin): новый блок `Критичные инциденты` с фактами и next-step actions.
  - `Business` (owner/admin): новый блок `Ключевые инциденты` с понятной причиной и последовательными действиями.

Contract
- OpenAPI contract updated:
  - paths:
    - `/business/incidents`
    - `/admin/incidents`
  - schemas:
    - `IncidentAction`
    - `IncidentItem`
    - `IncidentSummary`
    - `IncidentListResponse`

Validation
- Backend:
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/console_owner_admin.py truffles-api/tests/test_console_owner_business.py` -> OK
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_fleet_attention.py` -> `73 passed`
  - `python3 truffles-api/scripts/generate_openapi.py --check` -> OK
- Frontend:
  - `npm --prefix console-web run generate:api` -> OK
  - `npm --prefix console-web run lint` -> OK
  - `npm --prefix console-web run build` -> OK
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> OK

Result
- Platform Admin и Owner/Admin получили единый понятный формат инцидента:
  - что сломано,
  - почему вероятно сломано,
  - что делать безопасно сейчас,
  - какие шаги выполнять дальше без спама/ошибочных массовых действий.
