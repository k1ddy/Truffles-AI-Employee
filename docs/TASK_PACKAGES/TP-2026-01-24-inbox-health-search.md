# TP-2026-01-24 — Unified Inbox + Case Health (P0 target, contract-first)

- **Название/цель:** обеспечить единое и надёжное понимание состояния заявки в Console (last inbound/outbound, delivery status, live badges) с быстрым поиском по телефону/ID.
- **Canon refs:** `docs/PROCESSES.md` (Console↔Telegram sync + Inbox health target), `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`, `contracts/console_api/openapi.v1.yaml`, `STATE.md`.

## Invariant
- Единый источник истины: состояния и сообщения фиксируются в БД.
- Idempotency и audit для всех действий (Console/Telegram).
- `manager_active` = бот молчит; клиентские сообщения форвардятся менеджеру.
- Trace/Audit обязателен для каждой операции.

## Scope
- Контракты Inbox/Case Health в OpenAPI (listCases + Case schema).
- Backend: агрегаты `last_inbound_at`, `last_outbound_at`, `last_message_preview`, `unread_count`,
  `has_delivery_error`, `has_pending_outbox`, `last_activity_channel`.
- Поиск/фильтры: `q` (phone/name/id), `phone`, `has_unread`, `has_delivery_error`, `last_activity_since`.
- UI Inbox: сортировка по `last_inbound_at`, бейджи `NEW/LIVE/⚠️`, быстрый поиск.
- Диагностика: Case Health блок в Case View.

## Out of scope
- Полный real‑time (SSE/WS).
- Новые провайдеры или отдельные сервисы.

## Touch-list
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/*` (если потребуется `agent_last_viewed_at`/phone_normalized)
- `truffles-api/migrations/*` (если потребуется)
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/CaseView.tsx`
- `console-web/src/types/api.generated.ts` (regen)
- `docs/CONSOLE_GUIDE.md`

## Plan
1) Контракт‑first: описать новые поля/фильтры в OpenAPI.
2) Реализовать агрегаты и фильтры в `/console/v1/cases`.
3) Добавить индексы для p95 и возможную нормализацию телефона.
4) UI Inbox: сортировка, бейджи, поиск.
5) Case View: Case Health блок (last in/out + delivery flags).
6) Тесты: unit/contract + e2e smoke (Playwright).

## DoD
- Inbox выдаёт агрегаты и фильтры работают (по контракту).
- UI показывает last activity + NEW/LIVE/⚠️.
- Case Health отображает delivery flags.
- Тесты проходят, CI green.

## Checks
- `pytest -q truffles-api/tests/test_console_cases_filters.py` (new)
- `pytest -q truffles-api/tests/test_console_case_health.py` (new)
- `npm --prefix console-web run generate:api`
- (CI) `.github/workflows/ci.yml`

## Evidence
- CI run URL + лог тестов.
- Запись в `STATE.md` после CI.

## Rollback
- Откат PR + миграций (если были).

## No-go
- Любые изменения в `_legacy.py`.
- Ручные правки БД/trace ради evidence.

## Риски/блокеры
- Нагрузка на Inbox при агрегациях без индексов.
- Потребуется хранить `agent_last_viewed_at` для точного `unread_count`.

## Branch / Worktree / Merge
- Branch: `feat/console-inbox-health`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
