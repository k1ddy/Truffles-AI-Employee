# TP-2026-02-14-integrations-pagination-readmodel-a1

- Название/цель: Ввести серверную пагинацию и cursor-контракт для `/admin/integrations`, чтобы Fleet Control масштабировался на большие портфели и не требовал выгрузки всех филиалов одним ответом.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по Console Plane UX/scale), `STRATEGY/REQUIREMENTS.md`.

- Invariant:
  - RBAC и tenant access checks не ослабляются.
  - Provider ops queue и статусные вычисления branch integration сохраняются.
  - Существующие фильтры `company_id/client_id/branch_id/stale_after_minutes` сохраняются.

- Scope:
  - Backend: `/admin/integrations` получает `limit` + `cursor` и возвращает `has_more/cursor/total_in_scope`.
  - Schema/contract: обновить `ConsoleIntegrationsListResponse` и типы фронта.
  - Тесты backend на pagination/cursor/limit.

- Out of scope:
  - Переработка визуального UX (будет PR2).
  - Изменение provider lifecycle бизнес-логики.

- Touch-list:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_integrations_registry.py`
  - `console-web/src/types/api.generated.ts` (контрактные типы)
  - `console-web/src/lib/api-client.ts` (при необходимости)
  - `docs/SESSIONS/SESSION-*.md`
  - `docs/SESSION_INDEX.md`

- Plan:
  1. Добавить limit/cursor и pagination в endpoint `/admin/integrations`.
  2. Обновить response schema и типы.
  3. Добавить/обновить тесты backend.
  4. Прогнать целевые проверки и зафиксировать evidence.

- DoD:
  - `/admin/integrations` не возвращает бесконечный список без контроля размера.
  - Для `limit` вне диапазона endpoint возвращает корректную `INVALID_PARAM` (через общий валидатор).
  - Есть тесты на `has_more/cursor` и paging целевого набора.

- Checks:
  - `pytest -q truffles-api/tests/test_console_integrations_registry.py`
  - `pytest -q truffles-api/tests/test_console_fleet_attention.py`
  - `cd console-web && npm run lint`
  - `cd console-web && npm run build`

- Evidence:
  - Вывод целевых тестов + diff + PR URL.

- Rollback:
  - Revert коммита PR1.

- No-go:
  - Не вводить offset-pagination.
  - Не менять semantics provider queue.
  - Не добавлять временные хаки в UI.

- Риски/блокеры:
  - Контрактный дрейф между backend schema и frontend generated types.
