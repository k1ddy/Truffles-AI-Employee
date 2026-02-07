# TP-2026-02-07 Runbook-to-Console Jobs (P1-B, slice 1, a15)

## Название/цель
Поднять в Console минимальный Jobs-контур для ops-runbook операций без CLI: dry-run/execute, история запусков и артефакты результата для Platform Admin.

## Canon refs
- `AGENTS.md`
- `STATE.md` (GAP: runbook lift / split admin surface)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`

## Invariant
- Ops-операции остаются детерминированными и auditable: каждый запуск имеет входные параметры, статус и результат.
- RBAC не ослабляется: execute только для `ops:write`, list/get для `ops:read`.
- Не ломаем существующие `/console/v1/ops/outbox*`, `/metrics/daily`, `/telegram/health`.
- Legacy `/admin/*` не удаляется в этом срезе.

## Scope
- Backend:
  - `GET /console/v1/ops/jobs/catalog` (доступные job types и поддержка dry-run).
  - `GET /console/v1/ops/jobs` (history list с лимитом).
  - `GET /console/v1/ops/jobs/{job_id}` (детали одного запуска).
  - `POST /console/v1/ops/jobs/run` (dry-run/execute).
  - Job types в slice 1:
    - `outbox_process` (обертка вокруг текущей обработки outbox).
    - `heal` (обертка вокруг health heal).
    - `metrics_snapshot` (обертка metrics snapshot для текущего client).
  - Таблица истории запусков jobs (`console_ops_jobs`) + модель + миграция.
  - Audit events для запуска jobs.
- Frontend (`Ops`):
  - секция Console Jobs: выбор job type, dry-run/execute, история последних запусков, просмотр результата.

## Out of scope
- Перенос `sync_client` и `backfill_branch_rag` в этот PR.
- Асинхронный воркер/очередь для jobs (выполнение синхронное в рамках запроса).
- Деплой/рестарт/миграции/бэкапы через UI.
- Полная депрекация legacy `/admin/*`.

## Touch-list
- `truffles-api/app/models/console_ops_job.py` (new)
- `truffles-api/app/models/__init__.py`
- `truffles-api/migrations/026_add_console_ops_jobs.sql` (new)
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_ops_jobs.py` (new)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить backend model/migration для `console_ops_jobs`.
2. Реализовать jobs catalog/run/history endpoints c RBAC и audit.
3. Добавить unit tests для dry-run/execute/history + permission guards.
4. Обновить OpenAPI и сгенерировать frontend API-типы.
5. Добавить в `OpsPage` UI для запуска и просмотра job history.
6. Прогнать target checks и собрать evidence.

## DoD
- Platform Admin может выполнить `dry-run` и `execute` для `outbox_process|heal|metrics_snapshot` из Console.
- Каждый запуск сохраняется в `console_ops_jobs` со статусом и payload результата.
- История запусков доступна через list/get endpoints.
- UI `Ops` показывает jobs и позволяет запуск из интерфейса.
- OpenAPI/types синхронизированы.
- Есть тесты backend на новый контур.

## Checks
- `PYTEST_ARGS='/app/tests/test_console_ops_jobs.py /app/tests/test_console_outbox_ops.py' scripts/test_api_container.sh`
- `python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`

## Evidence
- `git status -sb`
- `git diff --stat`
- Логи target checks (pytest/openapi/lint)
- PR CI summary (core-eval красный допускается по текущему правилу)

## Rollback
- Revert-коммит изменений `console_ops_jobs` (router/schema/model/ui/types).
- Временный fallback на текущие ops endpoints (`/ops/outbox/*`, legacy `/admin/*` runbook).

## No-go
- Не переносить SRE операции в Console.
- Не удалять legacy `/admin/*`.
- Не менять core decision pipeline и `_legacy.py`.

## Риски/блокеры
- Синхронное выполнение jobs может быть долгим на больших данных; лимиты и минимальные safe defaults обязательны.
- `metrics_snapshot` в multi-tenant контуре должен быть строго ограничен client scope текущего контекста.
