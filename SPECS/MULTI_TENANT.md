# MULTI-TENANT АРХИТЕКТУРА

**Источник правды по архитектуре работы с несколькими заказчиками.**
**Создано:** 2025-12-07
**Обновлено:** 2025-12-24

---

## СТАТУС РЕАЛИЗАЦИИ

| Компонент | Статус |
|-----------|--------|
| Таблица companies | ✅ СУЩЕСТВУЕТ (не используется) |
| Таблица clients | ✅ РАБОТАЕТ |
| Таблица branches | ⚠️ ПОДКЛЮЧЕНА: routing/Telegram по branch есть; RAG branch‑filter с fallback до backfill |
| Таблица client_settings | ✅ РАБОТАЕТ |
| Промпты из БД | ✅ РАБОТАЕТ |
| RAG фильтрация по client_slug | ✅ РАБОТАЕТ (branch‑filter есть, fallback при `branch_filter_empty`) |
| Telegram группы на заказчика | ✅ РАБОТАЕТ (branch‑aware при `manager_scope=branch`) |
| Роутинг через branch_id | ✅ routing/Telegram по branch; RAG branch‑filter с fallback до backfill |
| Онбординг скрипт | ⚠️ РУЧНОЙ (onboard_client.py отсутствует; sync_client.py только для KB) |
| Счётчик сообщений | 📋 ПЛАН |
| Dashboard для заказчика | 📋 ПЛАН |

---

# ЧАСТЬ 1: ТЕРМИНОЛОГИЯ И ИЕРАРХИЯ

## Ключевые термины

| Термин | Значение | Пример |
|--------|----------|--------|
| **Company** | Юр. лицо, биллинг | ТОО "Truffles", ИП "Салон Мира" |
| **Client** | Бренд/продукт компании | Truffles (бот), Demo Salon |
| **Branch** | Филиал (точка, номер WhatsApp) | Алматы, Астана |
| **User** | Конечный клиент (человек в WhatsApp) | Анна, +7 701 570 5555 |
| **Conversation** | Диалог user ↔ bot/manager | conversations.id = UUID |

## Полная иерархия (КОНЕЧНОЕ ВИДЕНИЕ)

```
Company (ТОО "Truffles") — биллинг, владелец
│
├── Client (Truffles — продажа ботов)
│     │
│     ├── Branch (Основной)
│     │     ├── whatsapp: +7 7XX XXX XXXX (instance_id)
│     │     ├── telegram_chat_id: -100XXXXXXXXXX
│     │     ├── knowledge_tag: truffles
│     │     │
│     │     └── Conversations → Messages, Handovers
│     │
│     └── Branch (Астана) — будущее
│           ├── whatsapp: другой номер
│           └── ...
│
└── Client (Demo Salon — демо)
      └── Branch (Основной)
            └── ...
```

## Иерархия ролей (ПЛАН)

```
Company
  └── Владелец (owner) — видит всё, биллинг
        └── Client
              └── Админ — управляет клиентом (может быть branch-scoped)
                    └── Branch
                          └── Руководитель филиала
                                └── Менеджеры
```

## Текущее vs Конечное

| Что | Сейчас | Конечное |
|-----|--------|----------|
| Роутинг | branch_id в webhook + Telegram per branch; RAG branch‑filter с fallback | branch_id везде |
| Telegram credentials | Branch (manager_scope=branch), fallback: client_settings | Branch |
| Knowledge | Branch.knowledge_tag (если есть), fallback: client_slug | Branch.knowledge_tag |
| Conversation привязан к | branch_id (сохраняется, не используется повсеместно) | branch_id |
| Каналы (WhatsApp/Instagram) | 1 на client | через Channel (backlog) |

---

## Структура в БД (ТЕКУЩАЯ)

```
Company (companies) — существует, не используется
    │
    └── Client (clients)
          │
          ├── ClientSettings (client_settings) — telegram, mute, reminders
          ├── Prompt (prompts)
          ├── Branch (branches) — СУЩЕСТВУЕТ, ПОДКЛЮЧЕН ЧАСТИЧНО (выбор филиала в webhook)
          │
          └── User (users)
                │
                └── Conversation (conversations)
                        │
                        ├── Message (messages)
                        └── Handover (handovers)
```

---

# ЧАСТЬ 2: ПРИНЦИП РАБОТЫ

## Один API — много заказчиков

```
Входящее сообщение (WhatsApp)
        ↓
ChatFlow отправляет в API по client_slug (из webhook URL)
        ↓
POST /webhook/{client_slug} { body.message, body.metadata.remoteJid, ... }
        ↓
Python API:
  1. Загружает prompt WHERE client_id
  2. Ищет в Qdrant WHERE client_slug + branch‑filter (если есть)
  3. Отправляет в Telegram WHERE branch.telegram_chat_id (fallback: client_settings.telegram_chat_id)
        ↓
Ответ клиенту через WhatsApp
```

## Что разделено по заказчикам

| Данные | Где хранится | Как разделяется |
|--------|--------------|-----------------|
| Промпт | prompts | WHERE client_id |
| База знаний | Qdrant | filter: metadata.client_slug + branch_id/knowledge_tag (fallback при `branch_filter_empty`) |
| Настройки эскалации | client_settings | WHERE client_id |
| Telegram группа | branches.telegram_chat_id (manager_scope=branch) | fallback: client_settings.telegram_chat_id |
| Пользователи | users | WHERE client_id |
| Диалоги | conversations | WHERE client_id |
| Сообщения | messages | через conversation → client_id |
| Заявки | handovers | WHERE client_id |

## Что общее для всех

| Компонент | Почему общий |
|-----------|--------------|
| Python API | Логика одинаковая |
| Webhook вход | Роутинг одинаковый |
| PostgreSQL | Одна БД, разные записи |
| Qdrant | Одна коллекция, разные фильтры |
| LLM (OpenAI) | Один API key |

## Domain Pack / Client Pack (Knowledge)

- **Domain Pack** — общие категории услуг, RU/KZ синонимы, типовые вопросы, OOD‑якоря. **Без фактов.**
- **Client Pack** — факты конкретного салона: услуги, цены, адрес, часы, правила, акции и т.д.
- **demo_salon** — dummy Client Pack с вымышленными данными, используется только для демо/тестов.

**Где лежит:** `truffles-api/app/knowledge/<client_slug>/SALON_TRUTH.yaml`  
**Формат:** `domain_pack` + `client_pack`, при этом старые ключи остаются для обратной совместимости.

### Классы интентов (канон)
- `domain_pack` хранит **якоря и синонимы** как boost для классификатора, но **не** как единственный сигнал.
- OOD определяется только при out‑signals без in‑signals; info‑класс не должен ломаться от перестановки слов.
- `client_pack` управляет фактами info‑bundle: если поле отсутствует — его нет в ответе (без выдумок).

### Policy‑gates и booking‑mode (client_pack)

**Скидки** — конфигурируются в client_pack и работают только при явных правилах.

```yaml
client_pack:
  discounts:
    enabled: true
    rules:
      - id: birthday
        label: "День рождения"
        when: "+/- 3 дня"
        value_text: "Скидка 10% на услуги"
        confirmation_required: true
```

**Запись (CRM/календарь):**
```yaml
client_pack:
  booking:
    booking_mode: collect_preferences   # collect_preferences | confirm_slots
    availability_provider: none         # none | google_calendar | bitrix | amocrm | manual
```

Если `availability_provider` = `none/manual` (включая Excel/TXT), бот **не обещает слоты**, только собирает предпочтения.

**Оплата (только info):**
```yaml
client_pack:
  payment:
    allow_payment_info: true
    methods:
      - "Kaspi QR"
      - "Карта"
      - "Наличные"
    notes: "Оплату принимает администратор"
```

---

## Онбординг на масштабе (конвейер)

**Цель:** каждый новый клиент получает детерминизм сразу, без ручных правок в коде.
**Статус:** целевой конвейер (P2). Сейчас онбординг — ручной по шагам ниже + `ops/sync_client.py`.

### 1) Входы
- CRM/Calendar/Excel/Google Sheets/сайт → единый формат.
- Минимум: список услуг, адрес/часы, правила (гости/дети/алкоголь), скидки, оплата, филиалы.

### 2) Нормализация
- Удаление дублей, приведение названий услуг, нормализация категорий.
- Фиксация “что есть” = факты client_pack.

### 3) Taxonomy → Alias Expansion
- Domain‑taxonomy (ServiceSample) используется **только для распознавания**.
- Алиасы добавляются **только** к услугам, которые реально есть у клиента.
- Медицинские/рисковые классы помечаются как LAW‑gate.

### 4) Org → Tenant → Branch
- Политики уровня org/client наследуются в branch.
- Branch‑override: адрес, часы, парковка, канал WhatsApp.
- Если филиалов несколько — бот сначала уточняет филиал.

### 5) Валидация и GAP‑лист
- Обязательные факты: адрес, часы, услуги, правила скидок/оплаты/LAW.
- Если чего‑то нет → GAP‑лист и поведение “уточнить/эскалировать”.

### 6) Версионирование паков
- `client_pack.version`, `domain_pack.version`, `compiled_at`, `hash`.
- Версия фиксируется в decision_trace/meta.

### 7) EVAL генерация
- Base‑80 CORE: 3–5 перефраз на услугу/факт.
- Long‑tier: длинный хвост перефразов и хаотичные диалоги.

### 8) Синхронизация
- Client Pack → Qdrant (tenant filter) + cache (`ops/sync_client.py --validate`).
- Изменения паков → обязательный CI core/long перед деплоем.

**Прайс‑медиа (опционально):**
```yaml
client_pack:
  pricing_media:
    mode: text_only        # text_only | image_only | text_plus_image
    image_url: "https://example.com/price.jpg"
    caption: "Актуальный прайс"
```

**Важно:** без `pricing_media.image_url` всегда fallback на текст.

### Data usage и NDA (per client)

**По умолчанию:** данные используются только внутри салона (tenant-only).
**Опционально (opt-in):** разрешены только обезличенные агрегаты для улучшения domain_pack.

```yaml
clients.config:
  data_sharing: off        # off | aggregate
```

**Запрещено при любом режиме:**
- исходные тексты сообщений
- персональные данные и контакты
- медиа/файлы

**Разрешено при `aggregate`:**
- обезличенные паттерны (синонимы, частые формулировки без PII)
- статистика intents/clarify/OOD без текста

---

# ЧАСТЬ 3: СТРУКТУРА ДАННЫХ

## Таблица clients [СУЩЕСТВУЕТ]

```sql
CREATE TABLE clients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,              -- "Салон Мира"
    slug        TEXT UNIQUE NOT NULL,       -- "demo_salon"
    status      TEXT DEFAULT 'active',      -- active, suspended, deleted
    config      JSONB,                      -- дополнительные настройки
    created_at  TIMESTAMP DEFAULT NOW()
);
```

**Статусы:**
- `active` — бот работает
- `suspended` — бот молчит (не оплатил)
- `deleted` — заказчик ушёл

## Таблица client_settings [СУЩЕСТВУЕТ]

```sql
CREATE TABLE client_settings (
    client_id                   UUID PRIMARY KEY REFERENCES clients(id),
    
    -- Telegram
    telegram_chat_id            TEXT,       -- "-1003362579990"
    telegram_bot_token          TEXT,       -- "8045341599:AAGY..."
    owner_telegram_id           TEXT,       -- "@ent3rprise"
    
    -- Напоминания
    reminder_timeout_1          INT DEFAULT 30,   -- минут
    reminder_timeout_2          INT DEFAULT 60,   -- минут
    enable_reminders            BOOLEAN DEFAULT TRUE,
    enable_owner_escalation     BOOLEAN DEFAULT TRUE,
    
    -- Мьют
    mute_duration_first_minutes INT DEFAULT 30,
    mute_duration_second_hours  INT DEFAULT 24
);
```

## Таблица prompts [СУЩЕСТВУЕТ]

```sql
CREATE TABLE prompts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID REFERENCES clients(id),
    name        TEXT NOT NULL,              -- "system"
    text        TEXT NOT NULL,              -- текст промпта
    model       TEXT,                       -- "gpt-4o-mini"
    temperature NUMERIC,                    -- 1.0
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

**Как используется:**
```python
# ai_service.py
def get_system_prompt(db, client_id):
    prompt = db.query(Prompt).filter(
        Prompt.client_id == client_id,
        Prompt.name == "system",
        Prompt.is_active == True
    ).first()
    return prompt.text if prompt else DEFAULT_PROMPT
```

## Qdrant — структура документа

```json
{
  "id": "uuid",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "content": "Текст чанка",
    "metadata": {
      "client_slug": "demo_salon",    // ← фильтр
      "doc_name": "services.md",
      "source": "document"
    }
  }
}
```

**Как ищется:**
```python
# knowledge_service.py
def search_knowledge(query, client_slug, limit=5):
    return qdrant.search(
        filter={"must": [
            {"key": "metadata.client_slug", "match": {"value": client_slug}}
        ]},
        ...
    )
```

---

# ЧАСТЬ 4: ТЕКУЩИЕ ЗАКАЗЧИКИ

## Активные

| name | slug | client_id | telegram_chat_id | Статус |
|------|------|-----------|------------------|--------|
| Truffles | truffles | 499e4744-5e7f-4a97-8466-56ff2cdcf587 | -1003362579990 | Тест (мы) |
| Demo Salon | demo_salon | <CLIENT_ID> | -1003412216010 | Демо |

## Telegram боты

| Заказчик | Bot username | Для чего |
|----------|--------------|----------|
| truffles | @truffles_kz_bot | Эскалации Truffles |
| demo_salon | @salon_mira_bot | Эскалации салона |

---

# ЧАСТЬ 5: ОНБОРДИНГ ЗАКАЗЧИКА

## Что нужно для нового заказчика

| Шаг | Что делаем | Где |
|-----|------------|-----|
| 1 | Создать запись в clients | PostgreSQL |
| 2 | Создать client_settings | PostgreSQL |
| 3 | Создать Telegram группу | Telegram |
| 4 | Добавить бота в группу | Telegram |
| 5 | Создать промпт | PostgreSQL |
| 6 | Подготовить базу знаний | Markdown файлы |
| 7 | Загрузить в Qdrant | Knowledge Sync |
| 8 | Настроить ChatFlow | ChatFlow UI |
| 9 | Тестирование | WhatsApp |

## Шаг 1-2: Создать записи в БД

```sql
-- 1. Создать клиента
INSERT INTO clients (name, slug, status)
VALUES ('Салон Красоты "Элита"', 'salon_elita', 'active')
RETURNING id;

-- Получаем: client_id = 'новый-uuid'

-- 2. Создать настройки
INSERT INTO client_settings (
    client_id,
    telegram_chat_id,
    telegram_bot_token,
    owner_telegram_id
) VALUES (
    'новый-uuid',
    '-100XXXXXXXXXX',      -- ID группы в Telegram
    'BOT_TOKEN',           -- токен бота
    '@owner_username'      -- username владельца
);
```

## Шаг 3-4: Telegram группа

1. Создать группу в Telegram
2. Включить Topics (Темы)
3. Добавить бота (@truffles_kz_bot или новый)
4. Сделать бота админом с правами:
   - Manage Topics
   - Pin Messages
   - Send Messages
5. Получить chat_id: добавить @getidsbot, он покажет ID

## Шаг 5: Создать промпт

```sql
INSERT INTO prompts (client_id, name, text, is_active)
VALUES (
    'новый-uuid',
    'system',
    'Ты — консультант салона красоты "Элита".

ПРАВИЛА:
1. Отвечай кратко: 2-3 предложения
2. Отвечай ТОЛЬКО из базы знаний
3. Если не знаешь — скажи "Уточню у администратора"
4. Не выдумывай цены и услуги
5. Не давай скидки

КОНТАКТ: +7 777 123 4567',
    TRUE
);
```

## Шаг 6-7: База знаний

### Подготовить файлы

```
knowledge/
├── salon_elita/
│   ├── services.md      -- услуги и цены
│   ├── faq.md           -- частые вопросы
│   ├── rules.md         -- правила записи
│   └── objections.md    -- работа с возражениями
```

### Формат services.md

```markdown
# Услуги салона "Элита"

## Маникюр

### Классический маникюр
- Цена: 3,500 тг
- Время: 45 минут
- Описание: Обработка кутикулы, придание формы ногтям

### Маникюр с покрытием гель-лак
- Цена: 6,000 тг
- Время: 1.5 часа
- Описание: Классический маникюр + покрытие гель-лаком

## Педикюр
...
```

### Загрузить в Qdrant

```bash
# На сервере
cd ~/truffles/ops
python3 sync_client.py salon_elita ./knowledge/salon_elita/
```

Или через ручной sync workflow (ручной запуск).

## Шаг 8: Настроить ChatFlow

1. Зайти в ChatFlow
2. Добавить номер WhatsApp заказчика
3. Сгенерировать webhook secret (32+ символов) и записать в `client_settings.webhook_secret`
   - Пример (SQL): `UPDATE client_settings SET webhook_secret = '<SECRET>' WHERE client_id = '<CLIENT_ID>';`
4. Настроить webhook:
   ```
   URL: https://api.truffles.kz/webhook/salon_elita?webhook_secret=<SECRET>
   ```
5. (Опционально) вместо query можно использовать header `X-Webhook-Secret: <SECRET>`
6. Сохранить

## Шаг 9: Тестирование

1. Написать с тестового номера в WhatsApp заказчика
2. Проверить:
   - [ ] Бот отвечает
   - [ ] Ответ из правильной базы знаний
   - [ ] Эскалация идёт в правильную Telegram группу
   - [ ] Кнопки работают
   - [ ] Ответ менеджера доходит до клиента

---

# ЧАСТЬ 6: ВОПРОСЫ И РЕШЕНИЯ

## Решённые вопросы

### 1. Как определять client_id по входящему сообщению?

**Решение:** webhook URL содержит client_slug (прямой вход в API).

```
https://api.truffles.kz/webhook/salon_elita?webhook_secret=...
                                 ↑
                           client_slug
```

API извлекает slug → ищет клиента по `Client.name` (slug должен совпадать с name) → получает client_id.

**Реализация (preferred):** ChatFlow → Python API (`/webhook/{client_slug}`).
**Legacy:** webhook wrapper → Python API (`/webhook`).

---

### 2. База знаний — как разделять?

**Решение:** Одна коллекция Qdrant, фильтр по `metadata.client_slug` + branch_id/knowledge_tag; fallback по client_slug фиксируется в trace как `branch_filter_empty`.

```python
filter={"must": [
    {"key": "metadata.client_slug", "match": {"value": "salon_elita"}}
]}
```

**Реализация:** `knowledge_service.py`.

---

### 3. Эскалация — куда слать?

**Решение:** Отдельная Telegram группа на заказчика.

- `client_settings.telegram_chat_id` — ID группы
- `client_settings.telegram_bot_token` — токен бота
- Топики создаются автоматически для каждого клиента

**Реализация:** `escalation_service.py`.

---

### 4. Что если заказчик не оплатил?

**Решение:** Изменить `clients.status = 'suspended'`.

```python
# message.py — в начале
if client.status != 'active':
    return {"success": False, "message": "Client suspended"}
```

Бот просто не отвечает. Клиент видит что сообщение доставлено, но ответа нет.

**TODO:** Отправлять уведомление заказчику что бот отключен.

---

### 5. Промпт — кто пишет?

**Решение:** Жанбол пишет базовый промпт на основе шаблона.

Шаблон:
```
Ты — консультант [НАЗВАНИЕ].

ПРАВИЛА:
1. Отвечай кратко: 2-3 предложения
2. Отвечай ТОЛЬКО из базы знаний
3. Если не знаешь — скажи "Уточню у [РОЛЬ]"
4. Не выдумывай цены и услуги
5. Не давай скидки

КОНТАКТ: [ТЕЛЕФОН]
```

Заказчик может попросить изменить тон, добавить правила.

---

### 6. Бот работает 24/7?

**Решение:** Да, бот отвечает 24/7. Это selling point.

Quiet hours — только для напоминаний менеджерам (план P2).

---

### 7. Ошибки — что отвечать клиенту?

**Решение:** Fallback сообщение + эскалация.

```python
except Exception as e:
    bot_response = "Извините, произошла ошибка. Менеджер свяжется с вами."
    escalate_with_reason("error", str(e))
```

---

### 8. Active Learning — кто модерирует?

**Решение:** Каждый owner модерирует своих менеджеров.

- Owner ответил → сразу в базу (автомодерация)
- Админ ответил → pending (или auto-approve, если включено для branch)
- Менеджер ответил → owner получает кнопки [В базу] [Отклонить]

**Реализация:** План P2 (ACTIVE_LEARNING.md).

---

### 9. Несколько номеров у одного заказчика?

**Решение:** Через Branch (филиалы), режим определяется конфигом.

**Что есть:**
- Таблица `branches` существует
- Поля: instance_id, telegram_chat_id, knowledge_tag

**Режимы (config):**
- `by_instance`: если у филиалов разные номера → branch по instance_id
- `ask_user`: если номер один → бот спрашивает филиал
- `hybrid`: если instance_id известен → branch, иначе спрашиваем
 - `manager_scope`: `branch` (по умолчанию) или `global`

**Что нужно сделать (в плане):**
- [x] Conversation.branch_id сохраняется (webhook)
- [x] Роутинг по instance_id → branch (by_instance/ask_user/hybrid) реализован в webhook
- [ ] Эскалация из Branch.telegram_chat_id
- [x] RAG фильтр по Branch.knowledge_tag (fallback при `branch_filter_empty`; backfill Qdrant обязателен для strict)
- [ ] Сохранение выбранного филиала у пользователя (optional)

**Статус:** В ТЕКУЩЕМ ПЛАНЕ (STATE.md).

---

## Открытые вопросы

### 10. Счётчик сообщений и лимиты

**Статус:** Не реализовано.

**План:**
```sql
CREATE TABLE usage (
    client_id    UUID REFERENCES clients(id),
    month        DATE,
    messages_in  INT DEFAULT 0,
    PRIMARY KEY (client_id, month)
);

-- После каждого входящего
UPDATE usage 
SET messages_in = messages_in + 1 
WHERE client_id = ? AND month = date_trunc('month', NOW());
```

**Логика:**
- 80% лимита → алерт заказчику
- 100% → уведомление, доплата или пауза

---

### 11. Заказчик ушёл — что с данными?

**Статус:** Не решено.

**Варианты:**
1. Удалять всё (GDPR compliant)
2. Архивировать на N месяцев
3. Оставлять для аналитики (анонимизировать)

**Рекомендация:** Архивировать 6 месяцев, потом удалять.

---

### 12. Dashboard для заказчика

**Статус:** План P2-P3.

**Что показывать:**
- Количество сообщений (использование)
- Количество эскалаций
- Время ответа менеджеров
- Топ вопросов

---

### 13. Язык (казахский/русский)

**Статус:** Автоопределение.

LLM сам определяет язык и отвечает на нём. Дополнительная настройка не нужна.

---

### 14. Версии промптов

**Статус:** Не приоритет.

В prompts есть is_active. Можно создать новый промпт и деактивировать старый.

История изменений — через git (промпты в документах) или audit log (потом).

---

# ЧАСТЬ 7: ЦЕНООБРАЗОВАНИЕ

## Текущие тарифы

| Тариф | Цена | Лимит | Статус |
|-------|------|-------|--------|
| Starter | 50,000 ₸/мес | 1000 сообщений | ✅ Продаём |
| Medium | 100,000 ₸/мес | 3000 сообщений | 📋 План |
| Pro | 150,000 ₸/мес | Безлимит | 📋 План |

## Что входит в Starter

- Бот отвечает 24/7
- База знаний до 50 документов
- Эскалация в Telegram
- 1 номер WhatsApp

## Что НЕ входит

- Dashboard (будет в Medium)
- Аналитика (будет в Medium)
- Kaspi Pay интеграция (не обещаем)
- CRM интеграция (не обещаем)

## Себестоимость на 1000 сообщений

| Компонент | Стоимость |
|-----------|-----------|
| LLM (OpenAI) | ~$2.00 (~900 ₸) |
| Сервер (доля) | ~$5.00 (~2,200 ₸) |
| WhatsApp (ChatFlow) | ~$10.00 (~4,500 ₸) |
| **Итого** | **~7,600 ₸** |

**Маржа Starter:** ~85%

---

# ЧАСТЬ 8: ЧЕКЛИСТ ОНБОРДИНГА

## Чеклист вопросов при онбординге (35 минут)

> Источник: `STRATEGY/MARKET.md`, `.archive/research/NORTH_STAR.md`

### Блок 1: О компании (5 мин)
```
□ Название компании
□ Чем занимаетесь? (1-2 предложения)
□ Кто типичный клиент?
□ Средний чек
□ Сколько клиентов в день/неделю?
```

### Блок 2: Продажи (10 мин)
```
□ Как сейчас продаёте? (WhatsApp/звонки/офлайн)
□ Кто отвечает клиентам?
□ ТОП-5 частых вопросов
□ ТОП-3 возражения ("дорого", "подумаю"...)
□ Как отвечаете на возражения?
□ Есть готовые скрипты?
```

### Блок 3: Процессы (5 мин)
```
□ Как записываете клиентов? (CRM/тетрадка)
□ Как принимаете оплату? (Kaspi/наличка)
□ Кто решает по скидкам?
□ Куда слать эскалации? (WhatsApp/Telegram группа)
```

### Блок 4: Контент (10 мин)
```
□ Есть прайс-лист?
□ Есть описание услуг?
□ Есть отзывы/кейсы?
□ Есть фото/видео?
□ Что бот НЕ должен говорить?
```

### Блок 5: Ожидания (5 мин)
```
□ Что для вас успех через месяц?
□ Что бот точно должен уметь?
□ Что бот точно НЕ должен делать?
□ Готовы отвечать на эскалации за 10 минут?
```

---

## Перед встречей с заказчиком

- [ ] Бриф заполнен (услуги, цены, контакты)
- [ ] Договор готов
- [ ] Понятно кто owner, кто менеджеры

## Техническая настройка

- [ ] Запись в clients
- [ ] Запись в client_settings
- [ ] Telegram группа создана
- [ ] Бот добавлен в группу
- [ ] Промпт написан
- [ ] База знаний подготовлена
- [ ] База знаний загружена в Qdrant
- [ ] ChatFlow настроен
- [ ] Webhook работает

## Тестирование

- [ ] Бот отвечает на простой вопрос
- [ ] Бот отвечает "не знаю" на сложный
- [ ] Эскалация работает
- [ ] Кнопки [Беру] [Решено] работают
- [ ] Ответ менеджера доходит до клиента
- [ ] Напоминания приходят

## Передача заказчику

- [ ] Показать как пользоваться Telegram группой
- [ ] Объяснить кнопки
- [ ] Договориться о контакте для проблем
- [ ] Первая оплата получена

---

# ЧАСТЬ 9: ИЗВЕСТНЫЕ ПРОБЛЕМЫ

| Проблема | Влияние | Решение |
|----------|---------|---------|
| Нет автоматического онбординга | Каждый клиент вручную | Скрипт или UI (P2) |
| Нет счётчика сообщений | Не знаем использование | Реализовать (P2) |
| Нет dashboard | Заказчик не видит статистику | Реализовать (P3) |
| Один бот на всех | Все эскалации от одного бота | Отдельный бот на крупных (опционально) |

---

## СВЯЗЬ С ДРУГИМИ ДОКУМЕНТАМИ

| Документ | Что там |
|----------|---------|
| `SPECS/ARCHITECTURE.md` | Техническая архитектура |
| `SPECS/ESCALATION.md` | Логика эскалации |
| `TECH.md` | Доступы, команды |
| `STRATEGY/PRODUCT.md` | Тарифы, roadmap |

---

*Создано: 2025-12-07*
*Обновлено: 2025-12-10 — синхронизация с текущей реализацией*
