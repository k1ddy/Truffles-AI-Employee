# INBOX HUMAN LOCK — Техническое задание (TЗ)

**Версия:** 1.0  
**Дата:** 2026-02-21  
**Статус:** Draft (implementation-ready)

## 1) Контекст и проблема
В Console «Заявки» реализованы:
- ручные сообщения клиенту (manual reply);
- ручной outreach (сообщение по номеру/JID);
- пауза бота (human lock) для исключения конфликтных ответов.

Сейчас UX и backend дают скрытые состояния (пауза неочевидна), несогласованность UI/контракта (минуты игнорируются), и есть сценарии, когда бот остаётся немым после «Вернуть боту».

## 2) Цели и критерии качества
**Цель:** сделать управление ручными сообщениями и паузой бота предсказуемым, наблюдаемым и безопасным.

**Критерии качества (SLO):**
1. 95%+ случаев: менеджер понимает, почему бот молчит, и может снять паузу за 1 действие.
2. 0 случаев: бот остаётся немым после явного «Вернуть боту».
3. 0 случаев: выбранная длительность паузы игнорируется.
4. 100% inbound при активной паузе фиксируются в `decision_trace` и `decision_meta`.
5. Нет кросс‑эффекта паузы между разными заявками.

## 3) Термины
- **Manual Reply** — ответ менеджера в рамках открытой заявки.
- **Outreach** — ручное сообщение клиенту по номеру/JID, но строго в контексте существующей заявки.
- **Human Lock** — запрет ответа бота на время (TTL), управляемый менеджером.

## 4) Область и ограничения
- **In scope:** UI/UX «Заявки», API отправки сообщений, Human Lock, trace/meta, RBAC.
- **Out of scope:** холодный outreach без заявки (для этого использовать Campaigns / Marketing).

## 5) UX требования (visual)
### 5.1 Шапка заявки
- Индикатор состояния: `Бот на паузе: 12 мин` / `Бот активен`.
- Показывать: `Кто поставил`, `Причина`, `Источник`.

### 5.2 Список заявок
- Badge `Пауза` рядом со статусом/SLA.
- Фильтр: `На паузе`.

### 5.3 Блок ручных действий
- Переключатель: `Ставить паузу после отправки`.
- Поле минут активно только при включённой паузе.
- Предустановки минут: 15 / 30 / 60 / 120.
- Кнопка `Снять паузу` всегда активна при активном lock.

### 5.4 Ошибки
- Ошибки должны возвращаться с конкретной причиной (например, `INTEGRATION_UNAVAILABLE`, `CONVERSATION_REQUIRED`, `INVALID_PARAM`).
- UI показывает их конкретным текстом, без “общих тостов”.

## 6) Backend — контракты и логика
### 6.1 ConsoleManagerMessageRequest
Расширить запрос:
- `pause_enabled: bool = true`
- `pause_minutes: int = 30`
- `pause_reason: str | null`

Если `pause_enabled=false` или `pause_minutes=0` → lock не создаётся.

### 6.2 ConsoleOutreachMessageRequest
- `conversation_id` обязателен. Если отсутствует → ошибка `CONVERSATION_REQUIRED`.
- `pause_bot_minutes` поддерживает 0.

### 6.3 Human Lock API
- `GET /conversations/{id}/human-lock` → статус (active, until, remaining, source, reason, locked_by).
- `POST /conversations/{id}/human-lock/pause` → создать/обновить lock.
- `DELETE /conversations/{id}/human-lock` → release.

### 6.4 Авто‑release
- `return_case` и `resolve_case` обязаны снимать active lock для этой conversation.

## 7) Data Model
### 7.1 conversation_human_locks
**Изменения:**
- добавить `lock_scope` (`conversation` | `remote_jid`), default `conversation`.
- уникальный индекс: `(client_id, conversation_id)` where conversation_id is not null.
- для legacy (если есть): частичный уникальный индекс `(client_id, remote_jid)` where `lock_scope='remote_jid'`.

### 7.2 ConsoleCase
Добавить поля:
- `human_lock_active: bool`
- `human_lock_until: datetime | null`
- `human_lock_remaining_seconds: int | null`
- `human_lock_source: string | null`
- `human_lock_reason: string | null`
- `human_lock_by: string | null`

## 8) Trace/Meta
- `decision_trace`: stage `routing`, decision `human_lock_silent`, fields `lock_until`, `source`.
- `decision_meta.human_lock`: active/until/source/reason/locked_by.

## 9) RBAC
- `outreach:write` только `manager`, `admin`, `owner`, `platform_admin`.

## 10) Тесты
- Unit: `human_lock_service` (conversation-first lookup, release).
- Integration: send_manager_message с pause toggle.
- Integration: send_outreach_message требует conversation_id.
- UI: badge “Пауза”, фильтр, auto‑release после return.
- Trace: `human_lock_silent` сохраняется в DB‑trace.

## 11) Rollout
- Feature flag: `HUMAN_LOCK_V2_ENABLED`.
- Миграция данных: legacy locks получают `lock_scope='remote_jid'`.
- Поэтапный релиз: staging → 1 tenant → full.

## 12) No‑go
- Любые silent состояния без UI индикатора.
- Любые lock без возможности release.
- Любые автоматические паузы без явного управления.

