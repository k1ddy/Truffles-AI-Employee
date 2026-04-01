# TP-2026-02-10 — Integrations: Platform Admin Fleet Control (a25)

- Название/цель: перестроить вкладку `Integrations` в platform-level control plane: только `platform_admin`, fleet cross-tenant обзор, безопасные per-branch действия через `dry_run -> confirmation -> execute`.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` (NOW: `Integrations registry + drift guard` сделан, но read-path содержит side-effects; enterprise fleet PR-4 требует actionable control)
  - `SPECS/CONTROL_PLANE.md`
  - `SPECS/MULTI_TENANT.md`
  - `docs/REPORTS/2026-02-08-enterprise-fleet-program.md`
  - `contracts/console_api/openapi.v1.yaml`
  - `docs/TASK_PACKAGES/TP-2026-02-07-integrations-registry-drift-a15.md`
  - `docs/TASK_PACKAGES/TP-2026-02-09-pr4a-active-fleet-cockpit-a21.md`

## Invariant
- Доступ к вкладке и API `Integrations` только для `platform_admin`.
- Fleet-first: основной режим — cross-tenant (без скрытого auto-select tenant).
- Первый этап только per-branch mutate actions (без bulk execute).
- Любой mutate action — строго `dry_run -> confirmation -> execute`.
- Read API для интеграций не имеет side-effects (без `commit`/`audit`/`alert`).
- Tenant isolation/fail-closed не ослабляются.

## Scope
- Backend P0:
  - убрать side-effects из `GET /console/v1/admin/integrations`.
  - зафиксировать строгий platform-admin guard для integrations read path.
  - устранить ambiguity helper'ов доступа (`_require_platform_admin` дублируется в `console.py`).
  - синхронизировать схемы API для integration status полей (включая `integration_state/*`).
- Frontend P0:
  - RBAC/nav gating для `Integrations`: только `platform_admin`.
- Backend/UI P1:
  - fleet cross-tenant integrations registry (список branch across доступные clients).
  - per-branch action flow: `dry_run` preview + `execute` только с `confirmation_id`.

## Out of scope
- Bulk operations по нескольким branch за один execute.
- Incident ownership/ack/snooze.
- Новая модель инцидентов/таблицы без отдельного TP.
- Полная миграция legacy `/admin/*`.

## Touch-list (файлы/таблицы)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `truffles-api/tests/test_console_rbac.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Зафиксировать TP (этот документ) и стартовые инварианты.
2. Внедрить P0 в backend: strict RBAC + read-only integrations endpoint без side-effects.
3. Внедрить P0 в frontend: nav/page доступ только для `platform_admin`.
4. Обновить OpenAPI + generated frontend types.
5. Добавить/обновить тесты на RBAC и отсутствие read side-effects.
6. Прогнать целевые проверки и собрать evidence.

## DoD
- `Integrations` недоступна ролям кроме `platform_admin` (UI + API).
- `GET /admin/integrations` не выполняет мутаций БД и не шлёт alerts/audit.
- Контракт и generated types синхронизированы с реальным response.
- Тесты на RBAC/endpoint behavior проходят.

## Checks
- `PYTEST_ARGS='/app/tests/test_console_integrations_registry.py /app/tests/test_console_rbac.py' scripts/test_api_container.sh`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`

## Evidence
- `git status -sb`
- `git diff --stat`
- Логи checks (pytest/openapi/lint)
- Ссылка на PR/CI после push
- Обновление `STATE.md` с FACT + evidence (до merge для core/behavior)

## Rollback
- Revert коммит(ы) этого TP-среза.
- Временно вернуть read-only старый UI режим без action flow.

## No-go
- Не оставлять mutate логику в read endpoint.
- Не делать fallback на implicit tenant auto-select для platform fleet view.
- Не внедрять bulk execute в этом этапе.
- Не обходить confirmation flow для mutate действий.

## Branch / Worktree / Base / Merge / Cleanup
- Branch: `feat/2026-02-10-tenants-platform-admin-fixes`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: merge commit via PR (no rebase)
- Cleanup: после merge удалить ветку/рабочую ветку по runbook

## Риски/блокеры
- Риск contract drift между backend schema и OpenAPI/typegen.
- Риск скрытых side-effects, если сигналинг останется в read path.
- Риск UX-регрессии для non-platform ролей (ожидаемый deny, но нужны явные сообщения).
