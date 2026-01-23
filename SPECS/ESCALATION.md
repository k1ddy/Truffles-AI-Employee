# СПЕЦИФИКАЦИЯ ЭСКАЛАЦИИ TRUFFLES

**Статус:** CANON (critical)  
**Owner:** Жанбол  
**Обновлено:** 2026-01-23  
**Scope:** эскалация, состояния, роли, Telegram‑workflow, SLA.  
**Out of scope:** реализация кода, внешние обещания.  
**Links:** `SPECS/ACTIVE_LEARNING.md`, `SPECS/ARCHITECTURE.md`, `STATE.md`.

**Создано:** 2025-12-06  
**Автор:** Жанбол + Droid

> ⚠️ **Эскалация — второй столп проекта после мозгов бота.**
> Без этого Active Learning не работает. Бот не учится. Продукт мёртв.

---

## СТАТУС РЕАЛИЗАЦИИ (DERIVED, НЕ ИСТОЧНИК ИСТИНЫ)

_Актуальный статус и evidence — в `STATE.md`._
_Любые статусы ниже — DERIVED; единственный источник истины — `STATE.md`._

| Раздел | Статус |
|--------|--------|
| Состояния диалога | ✅ РЕАЛИЗОВАНО |
| Цепочка эскалации (multi-level) | 📋 ПЛАН |
| Роли и идентичности | ⚠️ ЧАСТИЧНО (схема/модели есть, wiring pending) |
| Менеджер отвечает через Telegram | ✅ РЕАЛИЗОВАНО |
| Очередь обучения + модерация | ⚠️ ЧАСТИЧНО (схема есть, флоу/moderation pending) |
| Telegram per branch (форум) | 📋 ПЛАН |
| Console↔Telegram sync (take/resolve + client notify) | 📋 ПЛАН |
| Метрики | ⚠️ ЧАСТИЧНО |
| База данных | ✅ РЕАЛИЗОВАНО (handovers + agents/agent_identities/learned_responses) |
| Конфигурация | ⚠️ ЧАСТИЧНО |

---

## СВЯЗЬ С АРХИТЕКТУРОЙ (что где реализовано)

- **State Machine:** `truffles-api/app/services/state_service.py` + `state_machine.py` (все переходы `bot_active/pending/manager_active`).
- **Escalation flow:** `truffles-api/app/services/escalation_service.py` (handover + Telegram notify).
- **Telegram UI:** `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/services/manager_message_service.py`.
- **Pending‑SLA:** `truffles-api/app/services/reminder_service.py` + pending‑ветка в `truffles-api/app/routers/webhook/_legacy.py`.
- **Trace‑evidence:** `truffles-api/app/routers/webhook/trace.py` (stages: `escalation`, `pending_sla`, `pending_status`, `pending_resume`, `re_entry`, `state_transition`).

---

## ЗАЧЕМ ЭТОТ ДОКУМЕНТ

Эскалация — это **продукт внутри продукта**:
- Система уведомлений
- Интерфейс менеджера
- Интерфейс модерации
- Pipeline обучения
- Метрики

**Цель:** Каждая эскалация = возможность научить бота. Escalation Rate падает со временем.

---

# РЕШЕНИЕ (2026-01-23): WEB CONSOLE = PRIMARY, TELEGRAM = PAGING/FALLBACK

**Новый канон:**
- **Web‑Console** — основной профессиональный UI (RBAC, аудит, очередь, контроль процесса).
- **Telegram** — пейджинг и fallback (уведомления + быстрые действия), не “место, где живёт процесс”.
- Любое действие (Console/Telegram) проходит **один и тот же сервисный слой** и пишет audit/trace.

**Почему:**
- Консоль обеспечивает аудит/роль‑контроль/масштабируемость.
- Telegram остаётся быстрым каналом реакции, не ломая управление и аналитику.

**Обязательные последствия (P0 target):**
- **Console↔Telegram синхронизация**: take/resolve/return в консоли обновляют Telegram‑карточку и топик.
- **Клиентские уведомления**: “менеджер подключился” и “бот снова отвечает” идут в WhatsApp при take/resolve.
- **Agent↔Telegram linking** обязателен для RBAC (telegram_id → agent_id).
- **Единый Inbox/Case Health в Console**: последняя активность, статус доставки, ошибки каналов — видны без переключений.

_Статус реализации и evidence — в `STATE.md`._

---

# РЕШЕНИЕ (2025-12-24): РОЛИ + ОЧЕРЕДЬ ОБУЧЕНИЯ + TELEGRAM КАК UI

**Боли, от которых уходим:**
- Роль владельца завязана на Telegram ID → ломает омниканальность и масштаб.
- Нет явной очереди обучения → нет контроля, нет отката, нет метрик.
- Один чат на клиента → не поддерживает филиалы.
- Обучение происходит “тихо” → владелец не видит, что попадает в KB.

**Что меняем:**
- Вводим роли и идентичности (agent + agent_identity). Канал ≠ роль.
- Очередь обучения в БД: pending → approved/rejected. Owner auto-approve.
- Telegram = операционный UI. Источник истины — БД/сервис.
- Telegram-группа на каждый филиал (branch.telegram_chat_id).

**Почему это стабильно:**
- Ядро становится channel-agnostic → легко добавлять новые каналы.
- Owner контролирует качество → меньше “хуйню в KB”.
- Филиалы масштабируются линейно → меньше путаницы у менеджеров.

---

# ЧАСТЬ 1: СОСТОЯНИЯ ДИАЛОГА [РЕАЛИЗОВАНО]

## Когда говорит бот, когда человек?

```
┌─────────────────────────────────────────────────────────────────┐
│                    СОСТОЯНИЯ ДИАЛОГА                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BOT_ACTIVE ──────────────────────────────────────────────┐     │
│      │                                                    │     │
│      │ Бот не знает / клиент просит менеджера             │     │
│      ▼                                                    │     │
│  PENDING ─────────────────────────────────────────────┐   │     │
│      │                                                │   │     │
│      │ Менеджер нажал [Беру]                          │   │     │
│      ▼                                                │   │     │
│  MANAGER_ACTIVE ──────────────────────────────────────┤   │     │
│      │                                                │   │     │
│      │ Менеджер нажал [Решено]                        │   │     │
│      ▼                                                │   │     │
│  BOT_ACTIVE ◄─────────────────────────────────────────┘   │     │
│                                                           │     │
└───────────────────────────────────────────────────────────┘     │
```

**Реализация:** `truffles-api/app/services/state_machine.py`

---

## Таблица состояний

| Состояние | Кто отвечает | Бот делает | Триггер выхода |
|-----------|--------------|------------|----------------|
| `bot_active` | Бот | Отвечает на всё | — |
| `pending` | Ждём менеджера | Только статус/подтверждение, не принимает новые решения | Менеджер [Беру] или клиент отменил |
| `manager_active` | Менеджер | **МОЛЧИТ** | Менеджер [Решено] |

**Реализация:** `truffles-api/app/models/conversation.py` — поле `state`

---

## Правила поведения бота [РЕАЛИЗОВАНО]

### Когда `bot_active`:
- Бот отвечает на все сообщения
- Нормальная работа

**Реализация:** `truffles-api/app/routers/webhook/_legacy.py` (основной путь), `truffles-api/app/routers/message.py` (legacy)

### Когда `pending`:
- Бот УЖЕ ответил клиенту ("Передал менеджеру")
- Создан handover в БД
- Уведомление в Telegram с кнопками [Беру] [Вернуть боту] [Не могу]
- Бот отвечает только статусными/подтверждающими сообщениями (pending_ack/pending_close/status)
- После `pending_ack` — восстановление контекста + **re‑entry** (старые слоты требуют подтверждения)

**Реализация:** `truffles-api/app/services/state_service.py` (`escalate_to_pending`) + `truffles-api/app/services/escalation_service.py` (`send_telegram_notification`)

### Pending‑SLA lifecycle (ожидание менеджера)
- **SLA ping** клиенту через **15 минут** в `pending` без ответа менеджера: просим подтвердить актуальность.
- Ответ клиента:
  - `pending_ack` → закрываем handover, `state=bot_active`, короткое подтверждение + re‑entry.
  - `pending_close` → закрываем handover, `state=bot_active`, бот замьючен, короткое подтверждение.
- Классификация `pending_ack/pending_close`: **детерминированные фразы** подтверждения/закрытия.
- **Auto‑close:** через **4 часа** ожидания без подтверждения — системное закрытие (handover → resolved, state → bot_active).

### Когда `manager_active`:
- **БОТ ПОЛНОСТЬЮ МОЛЧИТ**
- Все сообщения клиента форвардятся менеджеру в Telegram
- Менеджер отвечает → ответ идёт в WhatsApp клиенту
- Выход: менеджер нажимает [Решено]

**P0 target (Web‑first sync):**
- Take (Console/Telegram) → уведомить клиента “менеджер подключился”, обновить карточку и топик в Telegram, записать audit.
- Resolve/Return → уведомить клиента “бот снова отвечает”, обновить карточку/топик, контекст сохраняется/сбрасывается по флагу.

**Реализация:** 
- `telegram_webhook.py` — `handle_manager_message()`
- `manager_message_service.py` — `process_manager_message()`

### Медиа (фото/аудио/документы)
- Фото/аудио/документы принимаем, видео запрещено.
- В `bot_active`: 
  - если есть текст/транскрипт → обрабатываем как обычное сообщение (intent/RAG), заявки не открываем автоматически.
  - если нет текста → бот просит описать запрос текстом, заявки не открывает.
  - если запрос “как на фото/референс/в стиле” → эскалация + форвард в Telegram.
- если запрос “как на фото/референс” без фото → просим прислать фото, без эскалации.
- В `pending`: медиа форвардится в Telegram; бот может уточнять детали по тексту/транскрипту, но без финальных решений.
- В `manager_active`: бот полностью молчит.
- Голосовые: транскрибируем только короткие PTT; длинные аудио/видео — просим текст.
- Документы: только пересылка (обработка позже).
- Ограничения по размеру и rate‑limit до обработки.

**Реализация:** `truffles-api/app/routers/webhook/_legacy.py` (media guardrails + forward), `truffles-api/app/services/telegram_service.py` (sendPhoto/sendAudio/sendDocument/sendVoice).

---

## Контракт поведения (приоритеты и матрица) [P0]

Если в одном сообщении несколько сигналов/интентов, применяется самый сильный по приоритету.
Это правило сильнее любых локальных эвристик.

**Приоритеты (сильнее → слабее):**
1. **Hard‑LAW** (оплата: подтверждение/проверка/возвраты, медицинка, жалобы, переносы, тех. сбои) → эскалация.
2. **Policy‑gates (скидки/способы оплаты)** → ответ **только** по правилам из `client_pack.policy`; если правил нет — эскалация.
3. **Opt-out / rejection** → мьют. Если в сообщении есть запись/цена/адрес/время — запросить re-engage и не выполнять действие до ответа.
4. **Human request / frustration** → эскалация.
5. **Booking flow** → сбор слотов записи (важнее цены/общих вопросов).
6. **Question (in-domain)** → ответ через truth/RAG, при низкой уверенности — уточнение/эскалация.
7. **Greeting / thanks** → короткий ответ, без заявки.
8. **Out-of-domain / other** → вежливый отказ/перенаправление.

**Re-engage:**
- `reengage_confirmation` в `conversation.context` ставится, если есть opt-out + бизнес-запрос.
- Пока ждём подтверждения, остальные интенты игнорируются.
- "Да" → снять мьют и продолжить; "Нет" → оставить мьют.
- В `pending/manager_active` opt-out = отмена заявки, не мьют.

**Booking interrupt (expected_reply_type активен):**
- In-domain вопрос во время сбора слота → дать факт‑ответ и в том же сообщении вернуть booking‑prompt (без эскалации).
- Если сообщение не относится к записи и нет booking‑сигнала → booking ставится на паузу до явного запроса записи.

**Info‑bundle (инвариант):**
- Комбинации “где/когда/парковка/гости/дети/ранний приход” не должны эскалировать — дают факт‑ответ (адрес+часы+нужные секции).
- Эскалация допустима только при явных Hard‑LAW/policy‑триггерах, не из‑за порядка слов.

**Policy‑gates: скидки**
- Скидки — **не Hard‑LAW**. Отвечаем **только** по явным правилам в `client_pack.policy.discounts`.
- Если правил нет/не совпали — эскалация (без попытки торга/обещаний).

**Policy‑gates: способы оплаты (info)**
- Перечисление способов оплаты разрешено **только** при `client_pack.policy.payment_info.allow=true`.
- Если правил/списка нет — эскалация.
- Подтверждение оплаты/возвраты/проверка транзакции — всегда Hard‑LAW.

### Матрица state × intent → action

| State | human_request / frustration | rejection / opt_out | booking (slots) | question (in-domain) | greeting / thanks | out_of_domain / other |
|-------|-----------------------------|--------------------|-----------------|----------------------|-------------------|-----------------------|
| bot_active | Эскалация (handover) + ответ шаблоном | Мьют + re-engage при смешении | Сбор слотов, 1 вопрос за раз | Ответ через truth/LLM; low → уточнение/эскалация | Коротко, без заявки | Вежливый отказ |
| pending | Без нового handover, подтвердить что менеджер подключён | Отменить заявку, без мьюта | Сбор слотов, без нового handover | Короткий ответ, без handover | Коротко | Вежливый отказ |
| manager_active | Бот молчит, форвард менеджеру | Отменить заявку, без мьюта | Бот молчит, форвард менеджеру | Бот молчит, форвард менеджеру | Бот молчит, форвард менеджеру | Бот молчит, форвард менеджеру |

---

## Мьют бота [РЕАЛИЗОВАНО]

| Ситуация | Действие |
|----------|----------|
| Первый "нет" в bot_active | Мьют 30 мин (настраивается) |
| Второй "нет" в bot_active | Мьют 24 часа (настраивается) |
| 24 часа без сообщений | Сброс счётчика |
| Явный запрос записи/цены/адреса после мьюта | Размьютить и продолжить диалог |
| Opt‑out + запись в одном сообщении | Запросить подтверждение “да/нет” |

**Реализация:** 
- `truffles-api/app/routers/webhook/_legacy.py` / `truffles-api/app/routers/message.py` — `is_rejection(intent)`
- `conversation.bot_muted_until`, `conversation.no_count`
- `client_settings.mute_duration_first_minutes`, `mute_duration_second_hours`

**ВАЖНО:** "нет" при открытой заявке (pending/manager_active) — это отмена заявки, НЕ мьют.
**ВАЖНО:** re‑engage подтверждение хранится в `conversation.context` (ключ `reengage_confirmation`).

---

# ЧАСТЬ 2: ЦЕПОЧКА ЭСКАЛАЦИИ [ПЛАН]

> ⚠️ **Этот раздел НЕ реализован. Сейчас только один уровень уведомления.**

## Кто отвечает и когда (план)

```
ЭСКАЛАЦИЯ НАЧАЛАСЬ
        │
        ▼
┌───────────────────────────────────────┐
│ 1. PRIMARY MANAGER                    │
│    Уведомление в Telegram             │
│    Таймаут: 5 минут                   │
└───────────────┬───────────────────────┘
                │ Не ответил
                ▼
┌───────────────────────────────────────┐
│ 2. OTHER MANAGERS (все в списке)      │
│    Уведомление всем                   │
│    Таймаут: 5 минут                   │
└───────────────┬───────────────────────┘
                │ Никто не ответил
                ▼
┌───────────────────────────────────────┐
│ 3. LEADERSHIP (владелец/директор)     │
│    Красный алерт                      │
│    Таймаут: 10 минут                  │
└───────────────┬───────────────────────┘
                │ Никто не ответил
                ▼
┌───────────────────────────────────────┐
│ 4. BOT FALLBACK                       │
│    "Требуется время, вернусь"         │
│    Создать задачу в системе           │
└───────────────────────────────────────┘
```

**Текущая реализация:** Только один уровень — уведомление в Telegram группу. Напоминания через 30 и 60 минут.

---

## Таймауты

| Уровень | План | Текущая реализация |
|---------|------|-------------------|
| Primary Manager | 5 мин | ❌ Нет |
| Other Managers | 5 мин | ❌ Нет |
| Leadership | 10 мин | ❌ Нет |
| Reminder 1 | — | ✅ 30 мин (настраивается) |
| Reminder 2 | — | ✅ 60 мин + тег owner (настраивается) |

**Реализация напоминаний:** `reminder_service.py`

---

# ЧАСТЬ 3: РОЛИ, ИДЕНТИЧНОСТИ, ОБУЧЕНИЕ [РЕШЕНИЕ]

## Роли в системе

| Роль | Кто | Права | Обучение |
|------|-----|-------|----------|
| `owner` | Владелец бизнеса | Всё | Авто-approve в KB |
| `admin` | Управляющий | Почти всё | В очередь на модерацию owner |
| `manager` | Менеджер | Отвечать, видеть диалоги | В очередь на модерацию |
| `support` | Поддержка | Только отвечать | В очередь на модерацию |

**Текущая реализация:** Таблицы ролей/идентичностей существуют, но wiring не подключён. Используется `client_settings.owner_telegram_id` как временный костыль.

---

## Идентичности (agent_identities)

**Принцип:** один человек = один `agent`, у него может быть несколько идентичностей в разных каналах.

Примеры идентичностей:
- `channel=telegram`, `external_id=123456789`, `username=owner_user`
- `channel=email`, `external_id=owner@company.kz`

**Зачем:** роль определяется в БД, а не “по Telegram”. Это снимает привязку к одному каналу.

---

## Скоуп ролей (филиал vs глобально)

- `branch_id = NULL` → роль действует на все филиалы клиента
- `branch_id = <branch>` → роль действует только в этом филиале

**Пример:** админы по филиалам, owner глобальный.

---

## Чей ответ — золото? (решение)

```
Owner ответил → сразу в KB (auto-approve)
Admin ответил → pending → approve owner (или auto-approve, если включено)
Manager/Support ответил → pending → approve owner
```

**Конфиг:** `auto_approve_roles` (по умолчанию `owner,admin`). При включении `admin` — ограничить филиалом.

**Текущая реализация:** ⚠️ Частично. Ответ менеджера сохраняется в `handover.manager_response`. Если отвечает owner (по `client_settings.owner_telegram_id`) — ответ может авто-добавляться в KB (Qdrant).

---

## Очередь обучения (learned_responses)

**Задача:** у owner всегда есть контроль и откат.

Статусы:
- `pending` — ждём решения owner
- `approved` — добавлено в KB
- `rejected` — отклонено

**Auto-approve:** только если роль `owner`.

---

## Порядок эскалации (план)

```sql
-- Таблица: escalation_chain (НЕ СОЗДАНА)
client_id | priority | role      | user_id | contact
----------|----------|-----------|---------|------------------
1         | 1        | manager   | 101     | @manager_tg
1         | 2        | manager   | 102     | @manager2_tg
1         | 3        | admin     | 103     | @admin_tg
1         | 4        | owner     | 104     | @owner_tg
```

---

# ЧАСТЬ 4: КАК МЕНЕДЖЕР ОТВЕЧАЕТ [ЧАСТИЧНО РЕАЛИЗОВАНО]

## Варианты

### Вариант A: Telegram бот [РЕАЛИЗОВАНО]
```
Менеджер получает в Telegram:
┌─────────────────────────────────────┐
│ 🚨 НОВАЯ ЗАЯВКА                     │
│                                     │
│ 📱 Клиент: +7 701 570 5555          │
│ 👤 Имя: Анна                        │
│ 💬 Сообщение: "Хочу узнать цены"    │
│                                     │
│ [Беру] [Вернуть боту] [Не могу]     │
└─────────────────────────────────────┘

Менеджер пишет ответ в топик:
→ Ответ пересылается в WhatsApp клиенту
→ Кнопки меняются на [Решено]
```

*Кнопки `[Вернуть боту]` и `[Не могу]` доступны всем. `[В базу]/[На модерацию]` — план, пока не реализовано.*

**Решение по группам:**
- **Одна Telegram-группа на филиал** (`branches.telegram_chat_id`) — wiring pending; сейчас используется `client_settings.telegram_chat_id`.
- **Один топик на клиента** (`users.telegram_topic_id` — канон; `conversations.telegram_topic_id` — копия для активного диалога)

**Реализация:**
- `escalation_service.py` — отправка уведомления
- `telegram_webhook.py` — обработка кнопок и сообщений
- `manager_message_service.py` — пересылка в WhatsApp

### Вариант B: Веб-интерфейс [ПЛАН]
```
Менеджер заходит на dashboard.truffles.kz:
- Видит список эскалаций
- Видит полную историю диалога
- Отвечает в форме
- Ответ уходит клиенту
```

**Статус:** Не реализовано.

### Вариант C: Прямой WhatsApp [НЕ ПЛАНИРУЕТСЯ]

---

## Поведение бота когда менеджер в диалоге [РЕАЛИЗОВАНО]

### Менеджер нажал [Беру]:
1. `handover.status = 'active'`
2. `conversation.state = 'manager_active'`
3. Бот полностью молчит
4. Кнопки меняются на [Решено]

**Реализация:** `telegram_webhook.py` — `handle_callback_query()`, action="take"

### Менеджер нажал [Решено]:
1. `handover.status = 'resolved'`
2. `conversation.state = 'bot_active'`
3. `conversation.bot_muted_until = None`
4. `conversation.no_count = 0`
5. Бот снова активен

**Реализация:** `telegram_webhook.py` — `handle_callback_query()`, action="resolve"

### Менеджер просто написал (не брал явно):
1. Сообщение принимается только в топике клиента
2. Если есть активная заявка (pending/active) — ответ уходит клиенту и заявка становится active
3. Если активной заявки нет — ответ не уходит, менеджер видит отказ

**Реализация:** `manager_message_service.py` — `process_manager_message()`

---

# ЧАСТЬ 5: МОДЕРАЦИЯ И ОБУЧЕНИЕ [ПЛАН]

> ⚠️ **Этот раздел НЕ реализован.**

## Кто модерирует? (план)

**Заказчик сам**, с помощью Truffles на старте.

### Первый месяц:
- Truffles помогает настроить
- Показывает как модерировать
- Проверяет качество

### После:
- Заказчик модерирует сам
- Owner/Admin имеют доступ к интерфейсу модерации

---

## Интерфейс модерации (план)

```
┌─────────────────────────────────────────────────────────────┐
│ МОДЕРАЦИЯ ОТВЕТОВ                              [Сегодня ▼]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Вопрос клиента:                                         │ │
│ │ "Сколько стоит подключить 3 номера с Instagram?"        │ │
│ │                                                         │ │
│ │ Ответ менеджера (Айгуль):                               │ │
│ │ "Для 3 номеров подойдёт тариф Pro за 150,000 тг.        │ │
│ │  Instagram включен. Хотите оформить?"                   │ │
│ │                                                         │ │
│ │ [✅ Добавить в базу] [✏️ Редактировать] [❌ Отклонить]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Статистика:                                                 │
│ • Ожидают модерации: 5                                      │
│ • Добавлено сегодня: 12                                     │
│ • Отклонено: 2                                              │
└─────────────────────────────────────────────────────────────┘
```

**Статус:** Не реализовано.

---

## Автомодерация (план)

Если ответил человек с ролью `owner`:
```
→ Ответ автоматически добавляется в KB
→ Без ручной модерации
→ Логируется: "Добавлено автоматически (owner)"
```

**Статус:** Не реализовано.

---

## Формат знаний из эскалации (план)

```json
{
  "type": "escalation_learning",
  "question": "Сколько стоит на 3 номера с Instagram?",
  "answer": "Для 3 номеров подойдёт тариф Pro за 150,000 тг. Instagram включен.",
  "context": {
    "client_intent": "pricing_custom",
    "conversation_history": ["...", "..."],
    "escalation_reason": "Нет точного ответа в базе"
  },
  "metadata": {
    "answered_by": "Айгуль",
    "answered_by_role": "manager",
    "moderated_by": "Owner",
    "moderated_at": "2025-12-06T10:30:00Z",
    "source": "escalation"
  }
}
```

**Статус:** Не реализовано.

---

## Дедупликация (план)

Перед добавлением в KB:
1. Semantic search по вопросу
2. Если similarity > 0.9 — показать: "Похожий вопрос уже есть. Обновить?"
3. Варианты: [Добавить как новый] [Обновить существующий] [Пропустить]

**Статус:** Не реализовано.

---

# ЧАСТЬ 6: МЕТРИКИ [ЧАСТИЧНО]

## Dashboard для заказчика (план)

```
┌─────────────────────────────────────────────────────────────┐
│ ЭСКАЛАЦИИ                                    Декабрь 2025   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Escalation Rate     ████████░░░░░░░░  32%                 │
│  (цель: <20%)        ↓ было 45% месяц назад                │
│                                                             │
│  Среднее время ответа менеджера: 4.2 мин                   │
│  (цель: <5 мин)                                            │
│                                                             │
│  Добавлено в базу знаний: 47 ответов                       │
│  Ожидают модерации: 3                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ТОП причин эскалации:                                      │
│  1. Кастомные тарифы (34%)                                  │
│  2. Технические вопросы (28%)                               │
│  3. Жалобы (18%)                                            │
│  4. Возвраты (12%)                                          │
│  5. Прочее (8%)                                             │
└─────────────────────────────────────────────────────────────┘
```

**Статус:** Не реализовано.

---

## Главные метрики (North Star)

> Источник: `STRATEGY/MARKET.md`

| Метрика | Формула | Цель | Статус |
|---------|---------|------|--------|
| **Quality Deflection** | Deflection × CSAT × (1 - Repeat Rate) | >40% | 📋 План |
| **Goal Completion** | Завершённые цели / Все диалоги | >60% | 📋 План |
| **CSAT** | Средняя оценка 1-5 | >4.0 | 📋 План |

**Почему эти метрики:**
- Deflection Rate сам по себе врёт — 80% deflection может скрывать 30% фрустрированных
- Quality Deflection учитывает удовлетворённость И повторные обращения

---

## Операционные метрики

| Метрика | Формула | Цель | Статус |
|---------|---------|------|--------|
| Escalation Rate | Эскалации / Все диалоги | <20% через 2 мес | ❌ Не считается |
| Response Time | Время до ответа менеджера | <5 мин | ✅ Есть в БД |
| Resolution Rate | Решённые / Все эскалации | >95% | ⚠️ Можно посчитать |
| Repeat Contact Rate | Повторные обращения / Все | <15% | ❌ Не считается |
| Learning Rate | Добавлено в KB / Эскалации | >50% | ❌ Нет автообучения |
| False Escalation | Ответ был в KB / Эскалации | <10% | ❌ Не считается |

**Данные которые уже собираются:**
- `handover.first_response_at` — время первого ответа
- `handover.resolved_at` — время решения
- `handover.resolution_time_seconds` — длительность
- `handover.resolved_by_name` — кто решил
- `handover.trigger_type`, `trigger_value` — причина эскалации

---

# ЧАСТЬ 7: БАЗА ДАННЫХ [РЕАЛИЗОВАНО]

## Таблицы

### handovers (существует)
```sql
-- Реализация: truffles-api/app/models/handover.py

id                      UUID PRIMARY KEY
conversation_id         UUID (FK → conversations)
client_id               UUID

-- Триггер
trigger_type            TEXT  -- intent, keyword, manual, timeout
trigger_value           TEXT  -- конкретный intent или keyword
user_message            TEXT  -- сообщение клиента

-- Статус
status                  TEXT  -- pending, active, resolved, bot_handling, timeout

-- Назначение
assigned_to             TEXT  -- telegram user id
assigned_to_name        TEXT  -- имя менеджера
first_response_at       TIMESTAMP

-- Решение
resolved_at             TIMESTAMP
resolved_by_id          TEXT
resolved_by_name        TEXT
resolution_type         TEXT  -- solved, transferred, spam, other
resolution_time_seconds INTEGER

-- Telegram
telegram_message_id     BIGINT
channel_ref             TEXT  -- WhatsApp remote_jid (куда отправлять ответ менеджера клиенту)
-- topic_id для Telegram хранится в users.telegram_topic_id (канон), в conversations.telegram_topic_id — копия

-- Напоминания
reminder_1_sent_at      TIMESTAMP
reminder_2_sent_at      TIMESTAMP

-- Мета
created_at              TIMESTAMP
notified_at             TIMESTAMP
skipped_by              JSONB  -- список кто пропустил
```

### conversations (существует)
```sql
-- Реализация: truffles-api/app/models/conversation.py

id                  UUID PRIMARY KEY
client_id           UUID
branch_id           UUID  -- есть; используется в webhook для выбора филиала (не везде wired)
user_id             UUID (FK → users)
channel             TEXT  -- whatsapp, telegram

-- Состояние
state               TEXT  -- bot_active, pending, manager_active
bot_status          TEXT  -- active, muted
bot_muted_until     TIMESTAMP
no_count            INTEGER  -- счётчик отказов

-- Telegram
telegram_topic_id   BIGINT  -- копия users.telegram_topic_id для активного диалога

-- Мета
started_at          TIMESTAMP
last_message_at     TIMESTAMP
escalated_at        TIMESTAMP
```

### users (существует)
```sql
-- Реализация: truffles-api/app/models/user.py

id                  UUID PRIMARY KEY
client_id           UUID
remote_jid          TEXT
telegram_topic_id   BIGINT  -- канон: один топик на клиента
```

### branches (существует)
```sql
-- Реализация: truffles-api/app/models/branch.py

id                  UUID PRIMARY KEY
client_id           UUID
slug                TEXT
name                TEXT
instance_id         TEXT
phone               TEXT
telegram_chat_id    TEXT  -- Telegram-группа для филиала
knowledge_tag       TEXT
is_active           BOOLEAN
```

### client_settings (существует)
```sql
-- Реализация: truffles-api/app/models/client_settings.py

client_id                   UUID PRIMARY KEY

-- Telegram
telegram_bot_token          TEXT
telegram_chat_id            TEXT  -- LEGACY: переносим на branches.telegram_chat_id
owner_telegram_id           TEXT  -- LEGACY: заменяется roles/agent_identities

-- Таймауты
reminder_timeout_1          INTEGER DEFAULT 30  -- минуты
reminder_timeout_2          INTEGER DEFAULT 60  -- минуты
auto_close_timeout          INTEGER DEFAULT 120 -- НЕ ИСПОЛЬЗУЕТСЯ, не планируется

-- Мьют
mute_duration_first_minutes INTEGER DEFAULT 30
mute_duration_second_hours  INTEGER DEFAULT 24

-- Флаги
enable_reminders            BOOLEAN DEFAULT TRUE
enable_owner_escalation     BOOLEAN DEFAULT TRUE
```

### agents (существует, wiring pending)
```sql
-- Пользователи со стороны бизнеса (owner/admin/manager/support)

id          UUID PRIMARY KEY
client_id   UUID
branch_id   UUID  -- NULL = глобальный доступ, иначе филиал
role        TEXT  -- owner, admin, manager, support
name        TEXT
is_active   BOOLEAN DEFAULT TRUE
created_at  TIMESTAMP
```

### agent_identities (существует, wiring pending)
```sql
-- Идентичности в разных каналах

id           UUID PRIMARY KEY
agent_id     UUID REFERENCES agents(id)
channel      TEXT  -- telegram, email, crm
external_id  TEXT  -- telegram user id / email / etc
username     TEXT
metadata     JSONB
created_at   TIMESTAMP
```

### escalation_chain (план, НЕ создана)
```sql
-- Для реализации цепочки эскалации

client_id   UUID
priority    INTEGER
user_id     TEXT
role        TEXT  -- owner, admin, manager, support
contact     TEXT  -- @telegram_username
timeout_min INTEGER DEFAULT 5
is_active   BOOLEAN DEFAULT TRUE
```

### learned_responses (существует, расширяем)
```sql
-- Для автообучения

id              UUID PRIMARY KEY
client_id       UUID
branch_id       UUID  -- филиал, если применимо
handover_id     UUID  -- FK → handovers
question_text   TEXT
response_text   TEXT
source          TEXT  -- manager, owner
source_role     TEXT  -- owner, admin, manager, support
source_channel  TEXT  -- telegram, email, crm
agent_id        UUID  -- FK → agents
status          TEXT  -- pending, approved, rejected
approved_by     UUID  -- FK → agents
approved_at     TIMESTAMP
rejected_at     TIMESTAMP
is_active       BOOLEAN DEFAULT TRUE
qdrant_point_id TEXT  -- ID в Qdrant
question_normalized TEXT
source_name     TEXT
use_count       INTEGER
last_used_at    TIMESTAMP
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

---

# ЧАСТЬ 8: EDGE CASES

## Что если...

| Ситуация | Что делаем | Статус |
|----------|------------|--------|
| Клиент пишет пока ждём менеджера | Бот помогает (state=pending) | ✅ |
| Клиент пишет когда менеджер в диалоге | Форвард в Telegram | ✅ |
| Менеджер ответил после таймаута | Ответ всё равно отправляется | ✅ |
| Два менеджера ответили одновременно | Первый берёт, второй видит "уже взято" | ✅ |
| Клиент ушёл (не отвечает) | Ждём, напоминания, менеджер закрывает вручную | ✅ |
| Ответ менеджера — хуйня | Модерация отклоняет | ❌ Нет модерации |
| Бот эскалировал зря (ответ был в KB) | Пометить как false_escalation | ❌ Не реализовано |
| Клиент вернулся через день | Бот активен (state сбрасывается при resolve) | ✅ |
| Топик удалён в Telegram | Создаётся новый при эскалации | ⚠️ Частично (только в escalation_service) |
| **state=manager_active но топика нет** | Сбросить state → bot_active | ✅ Реализовано 2025-12-11 |
| Много филиалов/каналов | Роутинг по branch_id + Telegram-группа на филиал | 📋 ПЛАН |
| Много заявок в день | Нужны фильтры/приоритеты + batched-уведомления owner | 📋 ПЛАН |

---

## Fallback сообщения [РЕАЛИЗОВАНО]

```python
# Реализация: truffles-api/app/routers/webhook/_legacy.py (и legacy: truffles-api/app/routers/message.py)

MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
```

---

# ЧАСТЬ 9: ПЛАН РЕАЛИЗАЦИИ

## Что сделано ✅

- [x] Таблица `handovers` в БД
- [x] State machine (bot_active → pending → manager_active)
- [x] Telegram уведомления с кнопками
- [x] Кнопка [Беру] → status='active'
- [x] Кнопка [Решено] → status='resolved', unmute bot
- [x] Ответ менеджера → WhatsApp клиенту
- [x] Напоминания (30 мин, 60 мин + owner tag)
- [x] Мьют бота (30 мин / 24ч)
- [x] Автосоздание топика если удалён

## Что осталось 📋

### P1 (следующее):
- [ ] История переписки в заявке для менеджера
- [ ] Автоприветствие менеджера при взятии
- [ ] "Менеджер уже занимается" при повторном вопросе о той же теме
- [ ] "нет" при pending/active → закрыть заявку, бот активен
- [ ] Reminder 3 (2 часа) → уведомить клиента

### P2 (потом):
- [ ] Owner vs остальные (для автообучения: owner → сразу в базу, остальные → модерация)
- [ ] Quiet hours для напоминаний (ночью не будить, копить до утра)
- [ ] Модерация ответов менеджеров
- [ ] Автообучение (ответ → в Qdrant)
- [ ] Dashboard эскалаций

### P3 (будущее):
- [ ] Полная система ролей (owner, admin, manager, support)
- [ ] Цепочка эскалации (primary → others → leadership) — когда 50+ клиентов
- [ ] Веб-интерфейс для менеджеров
- [ ] Метрики и аналитика

---

# ЧАСТЬ 10: ДЕФОЛТЫ И КОНФИГУРАЦИЯ [ЧАСТИЧНО]

## КОНФИГУРИРУЕМЫЕ ПАРАМЕТРЫ

### Реализовано в client_settings:

| Параметр | Дефолт | Где |
|----------|--------|-----|
| `reminder_timeout_1` | 30 мин | client_settings |
| `reminder_timeout_2` | 60 мин | client_settings |
| `mute_duration_first_minutes` | 30 мин | client_settings |
| `mute_duration_second_hours` | 24 ч | client_settings |
| `enable_reminders` | true | client_settings |
| `enable_owner_escalation` | true | client_settings |
| `owner_telegram_id` | — | client_settings (LEGACY: заменяется agents/agent_identities) |
| `branch_resolution_mode` | `hybrid` | client_settings |
| `remember_branch_preference` | true | client_settings |
| `auto_approve_roles` | `owner,admin` | client_settings |
| `manager_scope` | `branch` | client_settings |
| `require_branch_for_pricing` | true | client_settings |

### План (не реализовано):

| Параметр | Дефолт | Описание |
|----------|--------|----------|
| `primary_timeout` | 5 мин | Таймаут первого менеджера |
| `others_timeout` | 5 мин | Таймаут остальных |
| `leadership_timeout` | 10 мин | Таймаут руководства |
| `quiet_hours_enabled` | true | Ночной режим |
| `quiet_hours_start` | by_salon_hours | Начало тихих часов (из `salon.hours`) |
| `quiet_hours_end` | by_salon_hours | Конец тихих часов (из `salon.hours`) |
| `owner_auto_approve` | true | Автомодерация для owner |
| `max_escalations_per_hour` | 50 | Лимит защиты от спама |

---

### Handoff UX (PLAN)

- Клиент получает статус: "Передал администратору. Он подключится при первой возможности." (без минут).
- В тихие часы — только статус/ack, без обещаний по времени; ответ в рабочие часы.
- При нарушении ожидания: мягкое напоминание + запрос удобного времени для ответа.
- При подключении менеджера: "Администратор уже в чате."

### LeadCard contract (PLAN)

- Поля: услуга, окно времени, филиал, язык, риск‑флаги, `intent_queue`, последние N сообщений, рекомендованный следующий вопрос.

**Как менять:** через `/admin/settings/{client_slug}` (нужно расширить API под новые поля).

## ПРИНЦИП ИЗМЕНЕНИЙ

```
Заказчик сказал "30 минут мало, клиенты уходят"
     ↓
UPDATE client_settings SET reminder_timeout_1 = 15 WHERE client_id = '...'
     ↓
Применяется на следующую эскалацию
```

**Сейчас:** Изменения через SQL.
**План:** Интерфейс настроек для заказчика.

---

## ДЕФОЛТЫ ПО НИШАМ (план)

| Ниша | Reminder 1 | Reminder 2 | Особенности |
|------|------------|------------|-------------|
| **Салон красоты** | 30 мин | 60 мин | Стандарт |
| **Доставка еды** | 5 мин | 15 мин | Критично быстро |
| **Медицина** | 10 мин | 30 мин | Критично всегда |
| **Магазин одежды** | 60 мин | 120 мин | Менее срочно |

**При онбординге:** "Вы салон красоты? Вот рекомендуемые настройки."

---

*Создано: 2025-12-06*
*Обновлено: 2025-12-24 — роли/идентичности + очередь обучения + branch routing*
*Это живой документ — дополнять по мере реализации*
