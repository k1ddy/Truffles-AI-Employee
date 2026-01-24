# TP-2026-01-24 — Ops Outbox Queue + Retry (P0, contract-first)

- **Название/цель:** дать Ops‑панели прозрачную очередь outbox (pending/processing/failed), возможность ретрая и диагностические поля, без изменения core‑поведения.
- **Canon refs:** `docs/PROCESSES.md` (Ops/Outbox), `SPECS/SYSTEM_REFERENCE.md`, `contracts/console_api/openapi.v1.yaml`, `contracts/console_api/errors.v1.json`, `STATE.md` (OPEN: outbox latency/ops), `AGENTS.md`.

## Invariant
- Единый источник истины: outbox‑статус хранится в БД и не подменяется UI.
- Idempotency + audit на все ops‑действия (retry/filters).
- RBAC: ops доступ только owner/admin/support.
- `_legacy.py` остаётся adapter‑only.

## Scope
- Контракты Console API для ops/outbox: list + retry.
- Backend: list outbox с фильтрами (status, cursor, limit), summary полей без raw payload.
- Backend: retry endpoint (bulk + optional ids) с audit.
- UI Ops: таблица очереди + фильтры + кнопка retry.
- Fix: `GET /console/v1/health` backlog считает PENDING/PROCESSING корректно.
- Документация: Ops‑диагностика + инструкции ретрая.

## Out of scope
- Переписывать outbox worker или менять статус‑машину.
- Новый провайдер / новый transport слой.

## Touch-list
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/outbox_service.py` (helpers, если нужно)
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/types/api.generated.ts` (regen)
- `console-web/src/types/index.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/PROCESSES.md`

## Plan
1) Contract‑first: описать ops/outbox list + retry, схемы response/request.
2) Backend: query + summary + RBAC, audit для retry.
3) UI Ops: таблица и фильтры, безопасный retry.
4) Тесты: unit на summary/filters + smoke.
5) Док‑фиксация (Ops/Outbox steps).

## DoD
- Ops показывает очередь outbox (pending/processing/failed) с ключевыми полями.
- Retry меняет статус и пишет audit.
- `/console/v1/health` возвращает корректный backlog.
- Тесты проходят, CI green.

## Checks
- `pytest -q truffles-api/tests/test_console_outbox_ops.py` (new)
- `npm --prefix console-web run generate:api`
- (CI) `.github/workflows/ci.yml`
  - `console-contract` временно исключает `/ops/outbox` до деплоя endpoint на prod (после деплоя удалить exclude).

## Evidence
- CI run URL + логи тестов.

## Rollback
- Откат PR (без миграций).

## No-go
- Изменения `_legacy.py`.
- Ручные правки БД/trace ради evidence.

## Риски/блокеры
- Большая таблица outbox → нужен ограниченный limit + cursor.
- Неполные данные в payload → summary должен быть устойчивым.

## Branch / Worktree / Merge
- Branch: `feat/ops-outbox-delivery`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
