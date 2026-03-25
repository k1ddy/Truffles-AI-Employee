# TP-2026-01-23 — Agent↔Telegram linking + Console↔Telegram sync + client notify (P0)

- **Название/цель:** привести take/resolve/return к единому state_service, добавить Telegram‑linking для RBAC и клиентские уведомления при подключении/отключении менеджера.
- **Canon refs:** `STATE.md` (NOW: планы Console↔Telegram), `SPECS/ESCALATION.md` (Web‑first + linking + sync), `docs/PROCESSES.md` (Console↔Telegram sync), `contracts/console_api/openapi.v1.yaml`, `contracts/console_api/errors.v1.json`.

## Invariant
- Единый источник истины: все take/resolve/return идут через `state_service` (Console и Telegram — одна логика).
- Один активный handover на диалог, один топик на клиента (`users.telegram_topic_id` — канон).
- `manager_active` = бот молчит, сообщения клиента идут в топик, бот не отвечает.
- Idempotency на take/resolve/return и Telegram callbacks (dedup + audit).
- Media async + signed URL + TTL, не блокировать webhook.
- RBAC: действия в Telegram только у связанного агента (Agent↔Telegram linking).
- Trace/Audit обязателен для каждой операции.

## Scope
- Контракты Console API для linking и sync‑статусов.
- Таблица/модель для link‑token.
- Endpoints: generate link token, list agents + identities, case return.
- Telegram `/start <token>` linking + RBAC check в callback/message.
- Console take/resolve/return → `state_service` + Telegram карточка/топик + уведомление клиенту.
- Audit events: linking + manager_connected/disconnected.
- UI: Settings → Team показывает Telegram‑линк и кнопку «Подключить Telegram».

## Out of scope
- Новый Telegram‑провайдер/бот.
- Перевод на новый UI дизайн или переработка консоли целиком.
- Переписывание state_machine/decision pipeline.
- Миграция legacy `client_settings.telegram_chat_id` → `branches.telegram_chat_id` (отдельная TP).

## Touch-list
- `contracts/console_api/openapi.v1.yaml`
- `contracts/console_api/errors.v1.json`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/telegram_webhook.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/manager_message_service.py`
- `truffles-api/app/services/chatflow_service.py` (notify helpers)
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/agent_identity.py`
- `truffles-api/app/models/*` (new link token model)
- `truffles-api/migrations/008_add_agent_link_tokens.sql`
- `console-web/src/app/settings/page.tsx`
- `console-web/src/types/api.generated.ts` (regen)
- `docs/CONSOLE_GUIDE.md` (linking + sync diagnostics)

## Plan
1) Контракт‑first: обновить OpenAPI + errors registry под linking и case return/sync.
2) Добавить модель/таблицу link‑tokens (TTL, used_at) + миграция.
3) Реализовать Console API: create link token + list agents with telegram identities + return endpoint.
4) Telegram webhook: обработать `/start <token>` (linking) + RBAC check для callback/message.
5) Console take/resolve/return через `state_service` + sync в Telegram (кнопки/топик) + клиентские уведомления.
6) UI: вывести статус Telegram‑линка и кнопку «Подключить».
7) Тесты: pytest для linking + case action sync (unit), regen TS client.
8) Док‑фикс: обновить `docs/CONSOLE_GUIDE.md` (flows + debug).

## DoD
- Контракты обновлены и сгенерирован TS client.
- `POST /console/v1/agents/{id}/telegram/link` возвращает token + deep‑link.
- `GET /console/v1/agents` возвращает telegram identities.
- `POST /console/v1/cases/{id}/take|resolve|return` идут через `state_service` и возвращают sync‑статус.
- Telegram `/start <token>` создаёт `agent_identity(channel=telegram)`.
- RBAC в Telegram: действия доступны только связанным агентам.
- Клиент получает уведомления о подключении/отключении менеджера.
- Audit события пишутся для linking и подключений.
- Есть минимум один тест; CI зелёный.

## Checks
- `pytest -q truffles-api/tests/test_agent_link_service.py`
- `pytest -q truffles-api/tests/test_manager_message_rbac.py`
- `ruff check truffles-api/app truffles-api/tests`
- `npm --prefix console-web run generate:api`
- (CI) `.github/workflows/ci.yml`

## Evidence
- CI run URL + лог тестов.
- Фиксация в `STATE.md` до merge (поведенческие изменения).

## Rollback
- Откат PR + откат миграции `008_add_agent_link_tokens.sql` (DROP TABLE).

## No-go
- Любые изменения в `_legacy.py` и оркестрации webhook.
- Ручные правки БД/trace ради evidence.
- Новые сервисы/очереди.

## Риски/блокеры
- Нет bot username для deep‑link → fallback: показывать токен и инструкцию `/start <token>`.
- TEST_MODE + allowlist может блокировать клиентские уведомления → требуется отдельный live-check.
- Multi‑branch routing по chat_id может потребовать доп. маппинг (если branch chat_id не заполнен).

## Branch / Worktree / Merge
- Branch: `feat/console-telegram-linking`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
