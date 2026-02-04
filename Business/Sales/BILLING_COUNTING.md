# Billing — Правила подсчета сообщений и доказательства

**Статус:** DRAFT (для согласования)
**Owner:** Жанбол
**Обновлено:** 2026-02-04
**Scope:** как считаем сообщения для выставления счетов и как это доказываем.
**Out of scope:** изменение тарифов/цен, новые каналы, UI-аналитика.

---

## 1) Что считается платным ответом

**Платный ответ** = исходящее сообщение бота клиенту, которое:
- отправлено Truffles (не менеджером и не системой напоминаний),
- не является тестом/симуляцией,
- имеет подтверждение доставки (provider status) или валидный fallback.

**Каналы:** сейчас учитываем WhatsApp (ChatFlow). Telegram — канал менеджеров, не считается.

**Исключаем из счета:**
- ответы менеджеров (Telegram/Console),
- напоминания и системные уведомления (reminder_jobs, calendar_sync и т.п.),
- симуляции/тестовые прогоны,
- сообщения с ошибкой доставки.

---

## 2) Источник истины для биллинга

Для оплаты используем **outbox** (фактически отправленные исходящие сообщения), а не UI-аналитику:
- таблица: `outbox_messages`
- фильтр: `payload_json.tenant_context.source` == `system` (бот)
- статус доставки:
  - **primary:** `meta.provider_status.status` ∈ {sent, delivered, read}
  - **fallback:** если provider_status отсутствует, `status = 'SENT'`
- исключаем симуляции: `meta.simulation.mode = true`

**Почему так:** outbox — это техническая цепочка доставки; это единственное место, где есть факт отправки и (если доступно) provider ack.

---

## 3) Единица учета

**1 billable message = 1 outbox запись.**
- Если провайдер дробит сообщение на несколько частей, это **не** увеличивает счет.
- Идемпотентность: `client_id + inbound_message_id` предотвращает двойной счет при ретраях.

---

## 4) Формула счета (пример тарифа)

**Пример (Starter):** включено до 1000 сообщений/мес на клиента.

```
billable = count(billable_messages)
quota = 1000
overage = max(0, billable - quota)
```

**Период:** по таймзоне клиента (tenant timezone).

---

## 5) Доказательства (что можно показать клиенту)

Для каждой оплаченной единицы можно показать:
- `outbox_messages.id` — уникальный идентификатор отправки
- `outbox_messages.created_at` — время отправки
- `outbox_messages.status` — статус отправки
- `outbox_messages.meta.provider_status.status` — подтверждение провайдера
- `outbox_messages.meta.provider_status.provider_message_id` — ID у провайдера
- `outbox_messages.conversation_id` — связка с диалогом
- `outbox_messages.inbound_message_id` — связка с входящим сообщением

Это обеспечивает доказуемость “отправлено/доставлено” по каждой единице.

---

## 6) Пример SQL для сверки

**Итог за период:**

```sql
SELECT COUNT(*) AS billable_messages
FROM outbox_messages
WHERE client_id = :client_id
  AND created_at >= :date_from
  AND created_at < :date_to
  AND payload_json->'tenant_context'->>'source' = 'system'
  AND COALESCE(meta->'simulation'->>'mode', 'false') <> 'true'
  AND (
    (meta->'provider_status'->>'status') IN ('sent','delivered','read')
    OR (meta->'provider_status' IS NULL AND status = 'SENT')
  );
```

**Детализация для споров:**

```sql
SELECT
  id,
  conversation_id,
  inbound_message_id,
  created_at,
  status,
  meta->'provider_status'->>'status' AS provider_status,
  meta->'provider_status'->>'provider_message_id' AS provider_message_id
FROM outbox_messages
WHERE client_id = :client_id
  AND created_at >= :date_from
  AND created_at < :date_to
  AND payload_json->'tenant_context'->>'source' = 'system'
  AND COALESCE(meta->'simulation'->>'mode', 'false') <> 'true'
ORDER BY created_at;
```

---

## 7) Что не используем для счета

- `metrics_daily` и UI Insights — **только аналитика**, не биллинг.
- `messages` без outbox/provier ack — не источник оплаты.

---

## 8) Границы и риски

- Если provider status недоступен, используем fallback (`outbox.status = SENT`).
- Если клиент требует “строго delivered”, можно переключить правила на `delivered/read`.
- Исторические периоды без provider_status — счет считаем по fallback, либо отдельно согласуем.

---

## 9) Связанные документы

- Тарифы и лимиты: `STRATEGY/PRODUCT.md`
- Внешние обещания: `docs/SELLING_TRUTHS.md`
- Архитектура доставки: `SPECS/ARCHITECTURE.md`
