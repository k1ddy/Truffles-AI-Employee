# СПЕЦИФИКАЦИЯ ЭСКАЛАЦИИ TRUFFLES

**Дата:** 2025-12-06
**Обновлено:** 2026-01-09
**Статус:** КРИТИЧЕСКИЙ ДОКУМЕНТ

**Канонические документы (обязательные ссылки):**
- `docs/NORTHSTAR.md` — ценность и инварианты продукта
- `SPECS/ARCHITECTURE.md` — Decision Graph + контракты
- `SPECS/CONSULTANT.md` — поведение консультанта

---

## 0) Статус реализации

| Раздел | Статус |
|--------|--------|
| Состояния диалога (bot/pending/manager_active) | ✅ Реализовано |
| Telegram handover + кнопки | ✅ Реализовано |
| Pending‑SLA ping + auto‑close | ✅ Реализовано |
| Менеджер отвечает через Telegram | ✅ Реализовано |
| Карточка менеджера (summary + next step) | ⚠️ Требует доработки |
| Единый реестр причин эскалации | ⚠️ Частично |
| Learning backlog (через data pack) | ⚠️ Частично |
| Эскалация‑цепочка (multi‑level) | 📋 План |

---

## 1) Зачем и какую ценность даёт

Эскалация — **продуктовый сервис**, а не “отказ” бота.

- **Клиенту:** гарантированный ответ человека в срок без выдумок.
- **Бизнесу:** защита LAW‑зон и сохранение доверия в критических случаях.
- **Системе:** превращает неопределённость в управляемый процесс и источник данных.

**Конечная цель:**
- SLA по эскалациям стабилен.
- Повторные эскалации по одной теме падают за счёт обновления data pack.
- Каждая эскалация оставляет полезный след: trace + карточка + результат.

---

## 2) Определение (что такое эскалация)

Эскалация = переход из автоматического режима в управляемый человеческий режим с SLA.
Она выполняется **по правилам**, а не “по настроению модели”.

**Не является:**
- попыткой “договорить” риск‑зону;
- способом скрыть нехватку фактов;
- каналом бесконечных уточнений.

---

## 3) Роли и сервисы

**Core Roles (канон):**
- **Session Orchestrator** принимает решение об эскалации.
- **Safety/Policy Gate** жёстко блокирует риск‑зоны.
- **Escalation Manager** создаёт handover, следит за SLA, управляет статусом.

**System Services (факт реализации):**
- `truffles-api/app/services/state_service.py` — переходы состояний.
- `truffles-api/app/services/escalation_service.py` — handover + Telegram‑уведомление.
- `truffles-api/app/services/telegram_service.py` — карточка + кнопки.
- `truffles-api/app/services/reminder_service.py` — pending‑SLA + reminders.
- `truffles-api/app/routers/telegram_webhook.py` — take/resolve/return/skip.
- `truffles-api/app/services/manager_message_service.py` — ответ менеджера клиенту.

---

## 4) Контракты (жёсткие)

### 4.1 Handover Contract (DB)
**Источник:** `truffles-api/app/models/handover.py`

**Обязательные поля:**
- `conversation_id`, `client_id`, `trigger_type`, `status`, `created_at`.

**Ключевые поля контекста:**
- `trigger_value`, `user_message`, `context_summary`.

**SLA‑поля:**
- `notified_at`, `first_response_at`, `resolved_at`, `resolution_time_seconds`.

**Назначение:**
- `assigned_to`, `assigned_to_name`, `resolved_by_id`, `resolved_by_name`.

**Канал:**
- `channel`, `channel_ref`, `telegram_message_id`.

**Статусы handover:**
- `pending`, `active`, `resolved` (используются),
- `bot_handling`, `timeout` (зарезервированы, не в активном флоу).

### 4.2 Client Status Contract
**Цель:** клиент всегда знает, что происходит.

**Факт реализации (опорные места):**
- подтверждение: `MSG_ESCALATED` в `truffles-api/app/routers/webhook/_legacy.py`.
- pending‑статусы: `MSG_PENDING_STATUS`, `MSG_PENDING_ACK`, `MSG_PENDING_SLA_PING` (MSG_PENDING_WAIT — legacy).
- auto‑close: `MSG_PENDING_AUTO_CLOSE` в `truffles-api/app/services/reminder_service.py`.

### 4.3 Manager Card Contract
**Сейчас (факт):** имя, телефон, причина, последнее сообщение.
- Формат: `format_handover_message()` в `truffles-api/app/services/telegram_service.py`.

**Должно быть (канон):**
- краткое summary (2–4 факта),
- причина/риск,
- ключевые слоты (филиал/услуга/время),
- предложенный следующий шаг.

**Ценность:** сокращает время до первого ответа и снижает ошибки менеджера.

### 4.4 Trace Contract
- Любая эскалация фиксируется в `decision_trace` + `decision_meta`.
- Trace должен содержать причину (risk/low‑confidence/human_request) и стадию.

---

## 5) Триггеры и приоритет

1) **Hard‑LAW / Policy‑gates** → мгновенная эскалация.
2) **Нет факта после 1–2 уточнений** → эскалация.
3) **Human request / frustration** → эскалация.
4) **Low confidence (RAG < 0.5)** → эскалация.
5) **Тупик** (повторы/фрустрация без прогресса) → эскалация.

**Принцип:** риск выше смысла; семантика не “договаривает” риск‑зону.

---

## 6) Сквозной процесс (как реализовано)

### 6.1 Старт эскалации
**Основной путь (webhook):**
1. Решение об эскалации внутри `_handle_webhook_payload`.
2. `state_service.escalate_to_pending()`:
   - создаёт handover,
   - ставит `conversation.state = pending`,
   - сохраняет `conversation.escalated_at`,
   - создаёт/получает `telegram_topic_id`.
3. `escalation_service.send_telegram_notification()` отправляет карточку.

**Legacy путь (message endpoint):**
- `escalation_service.escalate_conversation()` создаёт handover + отправляет Telegram.

### 6.2 Pending (ожидание менеджера)
- Бот не молчит: работает обычный ответный пайплайн (policy/truth/LLM), но без booking‑flow и без новых handover.
- Команды пользователя: `pending_ack`, `pending_close`, `status` (приоритет).
- Snapshot контекста сохраняется и может быть восстановлен на `pending_ack`.

**Факт реализации:**
- `truffles-api/app/routers/webhook/_legacy.py` (pending‑ветка).
- `truffles-api/app/routers/webhook/pending.py` (normalizers + resume).

### 6.3 Manager Active
- После TAKE: `conversation.state = manager_active`, `handover.status = active`.
- Бот молчит, все сообщения клиента форвардятся менеджеру.

**Факт реализации:**
- TAKE/RESOLVE/RETURN/skip: `truffles-api/app/routers/telegram_webhook.py`.
- Форвард в клиента: `truffles-api/app/services/manager_message_service.py`.

### 6.4 Resolve / Return to bot
- RESOLVE: handover закрыт, бот возвращается в `bot_active`.
- RETURN: handover закрыт + `resolution_notes` = “Returned to bot”.

---

## 7) SLA и таймеры (факт реализации)

- **Pending ping клиенту:**
  - `PENDING_SLA_PING_MINUTES` (15 мин по умолчанию).
  - Реализовано в `reminder_service.process_pending_sla()` и в pending‑ветке `_legacy.py`.
- **Auto‑close ожидания:**
  - `PENDING_AUTO_CLOSE_HOURS` (4 часа по умолчанию).
  - Реализовано в `reminder_service.process_pending_sla()`.
- **Напоминания менеджеру:**
  - `client_settings.reminder_timeout_1/2` (дефолт 30/60 мин).
  - Реализовано в `reminder_service.process_reminders()`.
- **Доп. auto‑close:**
  - `client_settings.auto_close_timeout` → `auto_close_stale_handovers()`.

**GAP:** два источника SLA‑значений (env vs hardcode) требуют унификации.

---

## 8) Telegram workflow (менеджер)

1) Карточка отправляется в Telegram‑топик клиента.
2) Кнопки: **Беру**, **Вернуть боту**, **Не могу**.
3) TAKE → переводит в `manager_active`, кнопки меняются на **Решено**.
4) RESOLVE/RETURN → закрывает handover, удаляет кнопки, снимает закреп.
5) Менеджер пишет в топике → сообщение уходит клиенту.

**Факт реализации:**
- `telegram_service.build_handover_buttons()`
- `telegram_webhook.handle_callback_query()`
- `manager_message_service.process_manager_message()`

---

## 9) Learning / Backlog

**Факт реализации:**
- Ответ менеджера сохраняется в `handover.manager_response`.
- Если отвечает owner (по `client_settings.owner_telegram_id`), ответ добавляется в RAG через `learning_service.add_to_knowledge()`.

**Канонический процесс (нужен):**
- `handover.manager_response` → backlog → review → обновление data pack → sync.
- Без правок логики под конкретный случай.

---

## 10) Метрики и DoD

**Ключевые метрики:**
- Escalation rate
- Time‑to‑take
- Time‑to‑first‑response
- Time‑to‑resolve
- SLA breach rate
- Повторные эскалации по теме
- Полнота карточки менеджера

**DoD:**
- SLA выполняется стабильно
- карточка содержит summary + следующий шаг
- все эскалации с trace/meta

---

## 11) GAP / Задачи (с ценностью)

1) **Карточка менеджера = summary + next step** → быстрее ответы, меньше ошибок.
2) **Единый реестр причин эскалации** → меньше ложных эскалаций, лучше обучение.
3) **Единый источник SLA‑таймеров** → предсказуемость и контроль.
4) **Статус клиенту при TAKE/RESOLVE** → выше доверие, меньше повторов.
5) **Learning backlog через data pack** → масштабируемое обучение без кода.
