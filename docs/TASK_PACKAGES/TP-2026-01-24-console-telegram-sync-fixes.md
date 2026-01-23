# TP-2026-01-24 — Console↔Telegram live sync + desktop deep link (P0)

- **Название/цель:** восстановить практическую синхронизацию Console↔Telegram: live‑обновление сообщений/статусов, корректный deep‑link для Desktop, эхо сообщений из Console в Telegram topic.
- **Canon refs:** `STATE.md` (Console↔Telegram P0), `SPECS/ESCALATION.md`, `docs/PROCESSES.md`, `contracts/console_api/openapi.v1.yaml`, `docs/CONSOLE_GUIDE.md`.

## Invariant
- Единый источник истины: все take/resolve/return идут через `state_service`.
- Один активный handover на диалог, один топик на клиента (`users.telegram_topic_id` — канон).
- `manager_active` = бот молчит, сообщения клиента идут в топик, бот не отвечает.
- Idempotency на take/resolve/return и Telegram callbacks (dedup + audit).
- Media async + signed URL + TTL, не блокировать webhook.
- RBAC: действия в Telegram только у связанного агента (Agent↔Telegram linking).
- Trace/Audit обязателен для каждой операции.

## Scope
- Добавить `telegram_desktop_link` в Console API (Contract + schema + response).
- В Case View добавить авто‑обновление сообщений/статуса (polling).
- Эхо сообщений из Console в Telegram topic (при доставке в WhatsApp).
- Уточнить проверку назначенного агента по `assigned_to` (id), а не только имени.
- Обновить `docs/CONSOLE_GUIDE.md` (ссылки/ожидаемое поведение).

## Out of scope
- Новый Telegram‑бот/провайдер.
- Полный real‑time (WebSocket/SSE).
- Миграции схемы БД.

## Touch-list
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_telegram_helpers.py`
- `console-web/src/components/CaseView.tsx`
- `console-web/src/components/ChatInterface.tsx`
- `console-web/src/types/index.ts`
- `console-web/src/types/api.generated.ts` (regen)
- `docs/CONSOLE_GUIDE.md`

## Plan
1) Обновить контракт `TelegramTrail` и схемы API под `telegram_desktop_link`.
2) Добавить helper для Desktop deep‑link и вернуть его в `telegram_trail`.
3) В Console send_message: проверка `assigned_to` по agent_id + echo в Telegram topic.
4) В UI Case View: polling + показ `tg://` и web‑ссылок.
5) Обновить тесты helper‑функций и regen TS client.
6) Проверки + фиксация evidence.

## DoD
- `telegram_trail` возвращает `telegram_desktop_link`.
- Desktop‑ссылка открывает Telegram app, web‑ссылка открывает топик в браузере.
- Сообщения клиента/менеджера появляются в Console без ручного refresh (polling).
- Сообщения из Console дублируются в Telegram topic.
- Тесты helper‑функций проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_telegram_helpers.py`
- `npm --prefix console-web run generate:api`

## Evidence
- Логи тестов + CI run URL (если запускался).

## Rollback
- Откат PR.

## No-go
- Любые изменения в `_legacy.py`.
- Ручные правки БД/trace ради evidence.

## Риски/блокеры
- `tg://` deep‑link зависит от клиента (Desktop/OS) — для fallback даём web‑ссылку.
- Polling 5–10s увеличит load; при нагрузке перевести на SSE/WS.

## Branch / Worktree / Merge
- Branch: `fix/console-telegram-sync-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
