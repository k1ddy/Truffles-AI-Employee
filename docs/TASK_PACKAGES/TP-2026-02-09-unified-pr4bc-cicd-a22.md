# TP-2026-02-09-unified-pr4bc-cicd-a22

- Название/цель: Unified PR для CI/CD anti-repeat + PR-4B Jobs + PR-4C Branch Change Management в Console Plane.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW: enterprise control plane rollout), `STRATEGY/REQUIREMENTS.md`, `SPECS/SYSTEM_REFERENCE.md`, `contracts/console_api/openapi.v1.yaml`.

## Invariant
- Не ломаем tenant isolation, go-live gate, destructive confirmation flow, и текущие ops/jobs сценарии.

## Scope
- CI/CD: добавить deploy parity gate (`merged SHA == deployed API SHA == console SHA`) и обязательный console deploy в main pipeline.
- PR-4B: добавить `integration_reconcile` job с `dry_run/execute/history/artifacts`.
- PR-4C: добавить branch change management (`draft -> validate -> preview diff -> publish -> rollback`) API + UI.

## Out of scope
- Полный onboarding conveyor PR-3.
- Fleet KPI/data migration (PR-1).
- SRE/deploy orchestration beyond parity checks.

## Touch-list (файлы/таблицы)
- `.github/workflows/ci.yml`
- `scripts/restart_console_web.sh`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/integration_guardrails_service.py`
- `truffles-api/app/models/console_branch_change.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/migrations/029_add_console_branch_changes.sql`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/tenants/page.tsx`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_console_branch_changes.py`

## Plan
1. Закрыть CI/CD anti-repeat и parity gate.
2. Реализовать backend PR-4B (`integration_reconcile` + artifacts).
3. Реализовать backend PR-4C (branch change model/migration/endpoints).
4. Обновить OpenAPI + TS types + UI (`OpsPage`, `Tenants`).
5. Добавить/обновить тесты и прогнать проверки.

## DoD
- После merge/main deploy pipeline валится при SHA mismatch API/Console.
- Ops Jobs поддерживают `integration_reconcile` (dry-run/execute), в истории есть artifact metadata.
- В Tenants для branch edit работает: draft+validate, preview diff, publish, rollback.
- OpenAPI/TS types синхронизированы.
- Console test-suite зелёный.

## Checks
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd truffles-api && pytest -q tests/test_console_*`
- `cd console-web && npx --yes openapi-typescript ../contracts/console_api/openapi.v1.yaml -o src/types/api.generated.ts`
- `cd console-web && npm run build`

## Evidence
- Локальные test/build логи и diff.
- CI run URL после push (фиксируется в PR).

## Rollback
- Git revert PR commit.
- Откат migration `029_add_console_branch_changes.sql` по стандартному runbook rollback.

## No-go
- Не менять прод-данные вручную ради evidence.
- Не обходить confirmations для destructive branch изменений.
- Не оставлять contract drift между кодом и `openapi.v1.yaml`.

## Риски/блокеры
- Риск разъезда contract/typegen: закрывается обязательным `generate_openapi --check` и TS typegen в том же PR.
- Риск UI flow regressions: закрывается `npm run build` + `pytest test_console_*`.
