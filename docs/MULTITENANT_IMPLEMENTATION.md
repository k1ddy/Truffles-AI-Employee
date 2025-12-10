# Полный анализ: Multi-Tenant архитектура Truffles

**Дата:** 2025-12-07
**Автор:** Droid + Жанбол

---

## ЧАСТЬ 1: ИСХОДНОЕ СОСТОЯНИЕ

### Что было до начала работы:

**Архитектура:**
- 6 workflow в цепочке: Webhook → ChannelAdapter → Normalize → MessageBuffer → TurnDetector → Multi-Agent
- Отдельный workflow Knowledge Sync для индексации документов
- PostgreSQL для хранения данных (clients, users, messages, prompts, conversations)
- Qdrant для векторного поиска (RAG)
- BGE-M3 для создания embeddings

**Проблема #1 — Две таблицы клиентов:**
```
clients (для Multi-Agent):
  - id: UUID
  - name: text
  - status: text
  - config: jsonb

knowledge_clients (для Knowledge Sync):
  - id: integer (auto-increment)
  - name: text
  - folder_id: text
  - notify_telegram: text
```

Это дублирование. Разные ID (UUID vs integer), разная структура. Knowledge Sync не знал о clients, Multi-Agent не знал о knowledge_clients.

**Проблема #2 — Захардкоженные значения в workflow:**

В Multi-Agent workflow:
```javascript
// Generate Response - systemMessage
"Ты — консультант компании Truffles..."  // захардкожен

// Send to WhatsApp - instance_id
"eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InRydWZmbGVzLWNoYXRib3QifQ=="  // захардкожен
```

Чтобы добавить нового клиента — нужно копировать весь workflow и менять все эти значения вручную.

**Проблема #3 — RAG без фильтрации:**

В Qdrant документы хранились с:
```json
{"metadata": {"client_id": 1}}
```

Но RAG Search не фильтровал по client_id. Все документы смешивались.

**Проблема #4 — Webhook не различал клиентов:**

Один webhook URL для всех. Система не знала от какого клиента пришло сообщение.

---

## ЧАСТЬ 2: ПЛАН РЕШЕНИЯ

### Цель:
Один workflow для всех клиентов. Добавление нового клиента = записи в БД + настройка webhook в ChatFlow.

### Архитектурное решение:

```
┌─────────────────────────────────────────────────────────────┐
│                      ВХОДЯЩЕЕ СООБЩЕНИЕ                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. WEBHOOK получает сообщение                              │
│     URL: /webhook/.../truffles или /webhook/.../demo_salon  │
│     → Извлекает client_slug из path                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. CHAIN (2-5) передаёт client_slug через все ноды         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. MULTI-AGENT:                                            │
│     a) Load Prompt — загружает prompt + instance_id из БД   │
│     b) RAG Search — фильтрует по client_slug                │
│     c) Generate Response — использует динамический prompt   │
│     d) Send — использует динамический instance_id           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ОТВЕТ уходит через правильный WhatsApp instance         │
└─────────────────────────────────────────────────────────────┘
```

---

## ЧАСТЬ 3: РЕАЛИЗАЦИЯ — БАЗА ДАННЫХ

### Шаг 3.1: Консолидация таблицы clients

**Действие:**
Добавили все необходимые параметры в `clients.config`:

```sql
UPDATE clients 
SET config = config || '{
  "folder_id": "1jV5E6J9E6b4gZVR...",
  "instance_id": "eyJ1aWQi...dHJ1ZmZsZXMtY2hhdGJvdCJ9",
  "phone": "+77759841926"
}'::jsonb
WHERE name = 'truffles';
```

**Причина:**
- `folder_id` — нужен для Knowledge Sync (откуда брать документы)
- `instance_id` — нужен для отправки ответов через правильный WhatsApp
- `phone` — номер бота для справки

**Следствие:**
Теперь ВСЕ данные клиента в одном месте. Не нужно ходить по разным таблицам.

---

### Шаг 3.2: Создание второго клиента (demo_salon)

**Действие:**
```sql
INSERT INTO clients (name, status, config) VALUES (
  'demo_salon', 
  'active',
  '{
    "folder_id": "1SxeLyiBczLJ9D28eoXA79c6kB51Unhb7",
    "instance_id": "eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InNhbG9uZGVtbyJ9",
    "phone": "+77055740455"
  }'
);
```

**Причина:**
Нужен реальный второй клиент для тестирования multi-tenant. Demo_salon — салон красоты, полностью другой бизнес чем Truffles.

**Следствие:**
Теперь есть два клиента с разными:
- WhatsApp номерами
- Google Drive папками
- Бизнес-контекстами

---

### Шаг 3.3: Промпты в базе данных

**Действие:**
Добавили промпт для Truffles:
```sql
INSERT INTO prompts (client_id, name, text)
SELECT c.id, 'system_prompt', 
'Ты — консультант компании Truffles.

## О КОМПАНИИ
Truffles — AI-бот для бизнеса в WhatsApp...
(полный текст промпта)'
FROM clients c WHERE c.name = 'truffles';
```

Добавили промпт для demo_salon:
```sql
INSERT INTO prompts (client_id, name, text)
SELECT c.id, 'system', 
'# Салон красоты "Мира" — AI-помощник

Ты — помощник салона красоты "Мира" в Алматы...
(полный текст промпта)'
FROM clients c WHERE c.name = 'demo_salon';
```

**Причина:**
Каждый бизнес требует свой промпт:
- Truffles — IT-компания, продаёт AI-ботов, технический язык
- Demo_salon — салон красоты, записывает клиентов, дружелюбный тон

Захардкоженный промпт в workflow = нужно менять код для каждого клиента.
Промпт в БД = меняешь запись, бот сразу работает по-новому.

**Следствие:**
Промпт загружается динамически по `client_slug`. Изменение поведения бота = UPDATE в БД.

---

### Шаг 3.4: Удаление knowledge_clients

**Действие:**
```sql
DROP TABLE IF EXISTS knowledge_clients CASCADE;
```

**Причина:**
Таблица больше не нужна. Все данные теперь в `clients.config`:
- `folder_id` — папка с документами
- Другие параметры — тоже там

Две таблицы клиентов = источник багов и путаницы.

**Следствие:**
Единый источник правды — таблица `clients`.

---

## ЧАСТЬ 4: РЕАЛИЗАЦИЯ — QDRANT И RAG

### Шаг 4.1: Изменение структуры metadata

**Было:**
```json
{
  "content": "текст документа",
  "metadata": {
    "client_id": 1,
    "doc_name": "faq.md"
  }
}
```

**Стало:**
```json
{
  "content": "текст документа",
  "metadata": {
    "client_slug": "truffles",
    "doc_name": "faq.md"
  }
}
```

**Причина:**
- Integer `client_id: 1` — непонятно какой это клиент, зависит от порядка создания
- String `client_slug: "truffles"` — очевидно и уникально

**Следствие:**
Фильтрация в Qdrant стала понятной и надёжной.

---

### Шаг 4.2: Пересоздание коллекции Qdrant

**Действие:**
Скрипт `recreate_collection.py`:

```python
# 1. Удалить старую коллекцию
requests.delete(f"{QDRANT_URL}/collections/{COLLECTION}")

# 2. Создать новую с правильными параметрами
requests.put(f"{QDRANT_URL}/collections/{COLLECTION}", json={
    "vectors": {
        "size": 1024,  # BGE-M3 dimension
        "distance": "Cosine"
    }
})

# 3. Переиндексировать документы с client_slug
for doc in documents:
    vector = get_embedding(doc.content)
    points.append({
        "id": point_id,
        "vector": vector,
        "payload": {
            "content": doc.content,
            "metadata": {
                "client_slug": doc.client_slug,  # новое поле
                "doc_name": doc.name
            }
        }
    })
```

**Причина:**
Старые документы имели `client_id: 1`. Нужно было переиндексировать с `client_slug`.

**Следствие:**
После переиндексации:
- truffles: 43 chunks
- demo_salon: 20 chunks
- Всего: 63 chunks с правильными metadata

---

### Шаг 4.3: Фильтрация в RAG Search

**Действие:**
Изменили ноду RAG Search в Multi-Agent:

```javascript
const clientSlug = $json.client_slug;

const filter = {
  must: [{
    key: 'metadata.client_slug',
    match: { value: clientSlug }
  }]
};

// Запрос к Qdrant с фильтром
const response = await qdrant.search({
  vector: queryVector,
  filter: filter,
  limit: 5
});
```

**Причина:**
Без фильтра RAG возвращал документы всех клиентов. Клиент demo_salon мог получить ответ на основе базы знаний Truffles.

**Следствие:**
RAG возвращает только релевантные документы текущего клиента.

---

## ЧАСТЬ 5: РЕАЛИЗАЦИЯ — WEBHOOK CHAIN

### Шаг 5.1: Параметризованный webhook path

**Действие:**
Изменили webhook path в 1_Webhook:

**Было:**
```
/a29b2ad2-9485-476c-897d-34799c3f940b
```

**Стало:**
```
/a29b2ad2-9485-476c-897d-34799c3f940b/:client
```

**Причина:**
Нужен способ идентифицировать клиента на входе. Webhook path — самый надёжный:
- ChatFlow настраивается один раз на конкретный URL
- URL содержит slug клиента
- Нет зависимости от данных в теле запроса

**Следствие:**
- Truffles шлёт на: `.../a29b2ad2.../truffles`
- Demo_salon шлёт на: `.../a29b2ad2.../demo_salon`

---

### Шаг 5.2: Извлечение client_slug

**Действие:**
В ноде "Restore Webhook Data":

```javascript
return {
  body: $('Webhook').item.json.body,
  headers: $('Webhook').item.json.headers,
  query: $('Webhook').item.json.query,
  client_slug: $('Webhook').item.json.params?.client || 'truffles'
};
```

**Причина:**
n8n парсит path параметры в `params`. `:client` в path = `params.client` в данных.

**Следствие:**
`client_slug` доступен для передачи дальше по цепочке.

---

### Шаг 5.3: Передача через ChannelAdapter

**Действие:**
В 2_ChannelAdapter, нода "WhatsApp Adapter":

```javascript
return {
  platform: 'whatsapp',
  remoteJid: body.data.key.remoteJid,
  phone: phone,
  message: messageText,
  // ... другие поля
  client_slug: $json.client_slug  // передаём дальше
};
```

**Причина:**
Каждый workflow в цепочке получает данные от предыдущего. Если не передать `client_slug`, он потеряется.

**Следствие:**
`client_slug` доступен в MessageBuffer.

---

### Шаг 5.4: Передача через MessageBuffer

**Действие:**
В 4_MessageBuffer, нода "Merge Messages":

```javascript
return {
  phone: messages[0].phone,
  remoteJid: messages[0].remoteJid,
  combined_text: combinedText,
  message_count: messages.length,
  client_slug: messages[0].client_slug  // передаём дальше
};
```

**Причина:**
MessageBuffer объединяет несколько сообщений в одно. Нужно сохранить `client_slug` от первого сообщения.

**Следствие:**
`client_slug` доступен в Multi-Agent.

---

## ЧАСТЬ 6: РЕАЛИЗАЦИЯ — MULTI-AGENT WORKFLOW

### Шаг 6.1: Parse Input

**Действие:**
```javascript
const raw = $json;
return {
  phone: raw.phone,
  remoteJid: raw.remoteJid,
  message: raw.combined_text || raw.text,
  client_slug: raw.client_slug || 'truffles'  // извлекаем
};
```

**Причина:**
Точка входа в Multi-Agent. Нужно извлечь и сохранить `client_slug` для использования в последующих нодах.

**Следствие:**
`client_slug` доступен через `$('Parse Input').first().json.client_slug` в любой ноде workflow.

---

### Шаг 6.2: Load Prompt — загрузка промпта и instance_id

**Действие:**
Добавили Postgres ноду "Load Prompt":

```sql
SELECT 
  p.text as system_prompt,
  c.config->>'instance_id' as instance_id
FROM clients c
LEFT JOIN prompts p ON p.client_id = c.id 
  AND p.name IN ('system', 'system_prompt') 
  AND p.is_active = true
WHERE c.name = '{{ $('Parse Input').first().json.client_slug }}'
LIMIT 1;
```

**Причина:**
Одним запросом получаем:
- `system_prompt` — текст промпта для LLM
- `instance_id` — для отправки ответа через правильный WhatsApp

**Следствие:**
Данные загружены из БД, доступны для использования.

---

### Шаг 6.3: Prepare Prompt — сборка финального промпта

**Действие:**
Добавили Code ноду "Prepare Prompt":

```javascript
const ctx = $json; // данные от Add Knowledge (history, knowledge, intent)
const loadedPrompt = $('Load Prompt').first().json;

const basePrompt = loadedPrompt.system_prompt || 'Ты — AI-помощник.';
const instanceId = loadedPrompt.instance_id || '';

const fullPrompt = basePrompt + `

## ДАННЫЕ
История: ${ctx.history}
База знаний: ${ctx.knowledge}
Intent: ${ctx.currentIntent}
isInCooldown: ${ctx.isInCooldown}

## ЭСКАЛАЦИЯ
...

## ПРАВИЛА
...
`;

return [{
  json: {
    ...ctx,
    full_prompt: fullPrompt,
    instance_id: instanceId
  }
}];
```

**Причина:**
n8n Agent node не поддерживает сложный JavaScript в systemMessage. Пришлось вынести логику в отдельную Code ноду.

Было (не работало):
```
systemMessage: "={{ /* сложный JS */ }}"
// Ошибка: invalid syntax
```

Стало (работает):
```
Prepare Prompt (Code) → собирает промпт
Generate Response: systemMessage = "={{ $json.full_prompt }}"
```

**Следствие:**
Generate Response получает готовый промпт, включающий:
- Base prompt из БД (специфичный для клиента)
- Контекст (история, knowledge, intent)
- Общие правила (эскалация, формат ответа)

---

### Шаг 6.4: Generate Response — использование динамического промпта

**Действие:**
Изменили systemMessage:

**Было:**
```
"Ты — консультант компании Truffles... (захардкоженный текст на 50 строк)"
```

**Стало:**
```
"={{ $json.full_prompt }}"
```

**Причина:**
Промпт теперь собирается в Prepare Prompt и передаётся через `$json.full_prompt`.

**Следствие:**
LLM получает промпт, специфичный для текущего клиента.

---

### Шаг 6.5: Prepare Response — передача instance_id

**Действие:**
Изменили ноду Prepare Response:

```javascript
const prev = $('Build Context').first().json;
const generation = $('Generate Response').first().json.output;
const instanceId = $('Prepare Prompt').first().json.instance_id;  // берём из Prepare Prompt

return [{
  json: {
    conversation_id: prev.conversation_id,
    remoteJid: prev.remoteJid,
    response: generation.response,
    instance_id: instanceId  // передаём в Send
  }
}];
```

**Причина:**
Send ноды должны получить `instance_id` чтобы отправить через правильный WhatsApp.

**Следствие:**
`instance_id` доступен в Send нодах.

---

### Шаг 6.6: Send ноды — динамический instance_id

**Действие:**
Изменили ВСЕ Send ноды (Send to WhatsApp, Me, Send Fallback2, Send Off-Topic):

**Было:**
```javascript
instance_id: "eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InRydWZmbGVzLWNoYXRib3QifQ=="
// Захардкожен Truffles instance
```

**Стало:**
```javascript
instance_id: "={{ $('Prepare Response').first().json.instance_id }}"
// Динамический, из БД
```

**Причина:**
Это была КЛЮЧЕВАЯ проблема. Все ответы отправлялись через Truffles instance, даже для demo_salon.

Когда demo_salon получал сообщение:
1. Сообщение обрабатывалось правильно (RAG фильтровал по demo_salon)
2. Ответ генерировался правильно (промпт demo_salon)
3. НО отправлялся через Truffles instance
4. Truffles instance отправлял на номер клиента
5. Сообщение приходило в "Сохранённые" (потому что Truffles отправлял сам себе)

**Следствие:**
- Сообщение от Truffles → ответ через Truffles instance → в чат с Truffles
- Сообщение от demo_salon → ответ через demo_salon instance → в чат с demo_salon

---

## ЧАСТЬ 7: ДОКУМЕНТЫ ДЛЯ DEMO_SALON

### Шаг 7.1: Создание документов

**Действие:**
Создали 4 документа для базы знаний demo_salon:

1. **services.md** — прайс услуг:
```markdown
# Услуги и цены

## Стрижки
- Женская стрижка — от 5,000 тг
- Мужская стрижка — 3,000 тг
...

## Маникюр
- Классический маникюр — 3,000 тг
...
```

2. **faq.md** — частые вопросы:
```markdown
# Частые вопросы

### Как записаться?
Напишите желаемую услугу, дату и время...

### Какие способы оплаты?
Наличные, Kaspi перевод, Kaspi QR.
...
```

3. **objections.md** — работа с возражениями:
```markdown
# Работа с возражениями

### "У вас дорого"
Понимаю. Наши цены отражают качество...

### "Я подумаю"
Хорошо, без давления...
```

4. **rules.md** — правила работы бота:
```markdown
# Правила работы бота

## Что делать
- При вопросе о ценах — дать цену из прайса
- При желании записаться — собрать данные

## Чего не делать
- Не выдумывать
- Не давать скидки без согласования
```

**Причина:**
Для demo салона красоты нужна своя база знаний. Документы Truffles (про AI-ботов) не подходят.

**Следствие:**
RAG для demo_salon возвращает информацию о салоне, а не о Truffles.

---

### Шаг 7.2: Индексация документов

**Действие:**
Запустили скрипт `manual_sync_demo.py`:

```python
for doc in docs:
    content = read_file(doc)
    chunks = split_into_chunks(content)
    
    for chunk in chunks:
        vector = get_embedding(chunk.content)
        points.append({
            "id": point_id,
            "vector": vector,
            "payload": {
                "content": chunk.content,
                "metadata": {
                    "client_slug": "demo_salon",
                    "doc_name": doc.name
                }
            }
        })

upsert_to_qdrant(points)
```

**Причина:**
Knowledge Sync workflow имел баг с вложенными loops — второй клиент не обрабатывался. Пришлось сделать ручной sync.

**Следствие:**
Demo_salon: 20 chunks в Qdrant с правильными metadata.

---

## ЧАСТЬ 8: ИНСТРУМЕНТЫ ОНБОРДИНГА

### Шаг 8.1: Скрипт onboard_client.py

**Действие:**
Создали интерактивный скрипт:

```python
def main():
    # Спрашиваем параметры
    slug = input("Slug: ")
    business_name = input("Название: ")
    instance_id = input("Instance ID: ")
    phone = input("Телефон: ")
    folder_id = input("Folder ID: ")
    
    # Создаём запись в clients
    sql = f"""
    INSERT INTO clients (name, status, config)
    VALUES ('{slug}', 'active', '{config_json}')
    """
    run_sql(sql)
    
    # Создаём промпт
    sql = f"""
    INSERT INTO prompts (client_id, name, text)
    SELECT c.id, 'system', '{prompt}'
    FROM clients c WHERE c.name = '{slug}'
    """
    run_sql(sql)
    
    # Выводим инструкции
    print(f"Webhook URL: .../webhook/.../{ slug}")
    print(f"Загрузи документы в: drive.google.com/.../{ folder_id}")
```

**Причина:**
Онбординг нового клиента должен быть простым и повторяемым. Скрипт:
- Задаёт правильные вопросы
- Создаёт записи в БД
- Генерирует промпт по шаблону
- Выдаёт инструкции что делать дальше

**Следствие:**
Добавление нового клиента = запуск скрипта + 5 минут на ввод данных.

---

### Шаг 8.2: Скрипт sync_client.py

**Действие:**
```python
def sync_client(client_slug, docs_dir):
    # Удаляем старые документы
    delete_client_docs(client_slug)
    
    # Читаем .md файлы
    for filename in os.listdir(docs_dir):
        content = read_file(filename)
        chunks = split_into_chunks(content)
        
        for chunk in chunks:
            vector = get_embedding(chunk)
            points.append({...})
    
    # Загружаем в Qdrant
    upsert_to_qdrant(points)
```

**Причина:**
Knowledge Sync workflow имеет баг. Нужен надёжный способ синхронизации документов.

**Следствие:**
`python3 sync_client.py demo_salon ./docs` — синхронизирует документы за минуту.

---

### Шаг 8.3: Шаблоны документов

**Действие:**
Создали шаблоны в `ops/templates/`:
- `salon_services.md` — прайс
- `salon_faq.md` — FAQ
- `salon_objections.md` — возражения
- `salon_rules.md` — правила

**Причина:**
Большинство клиентов — салоны красоты. Шаблоны ускоряют онбординг:
1. Копируешь шаблоны
2. Заполняешь данные клиента (цены, адрес, телефон)
3. Синхронизируешь

**Следствие:**
Создание базы знаний для салона = 30 минут вместо нескольких часов.

---

## ЧАСТЬ 9: ИТОГОВАЯ АРХИТЕКТУРА

### Что получилось:

```
┌─────────────────────────────────────────────────────────────┐
│                         БАЗА ДАННЫХ                         │
├─────────────────────────────────────────────────────────────┤
│  clients:                                                   │
│    - name: "truffles" | "demo_salon" | ...                 │
│    - config: {folder_id, instance_id, phone, ...}          │
│                                                             │
│  prompts:                                                   │
│    - client_id → clients.id                                │
│    - text: "Ты — помощник салона..."                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          QDRANT                             │
├─────────────────────────────────────────────────────────────┤
│  Документы с metadata.client_slug:                         │
│    - truffles: 43 chunks                                   │
│    - demo_salon: 20 chunks                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     ЕДИНЫЙ WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│  1. Webhook: извлекает client_slug из path                 │
│  2. Chain: передаёт client_slug                            │
│  3. Multi-Agent:                                           │
│     - Load Prompt: загружает prompt + instance_id          │
│     - RAG: фильтрует по client_slug                        │
│     - Generate: использует динамический prompt             │
│     - Send: использует динамический instance_id            │
└─────────────────────────────────────────────────────────────┘
```

### Добавление нового клиента:

1. **ChatFlow:** создать instance, получить instance_id
2. **Google Drive:** создать папку, получить folder_id
3. **Скрипт:** `python3 onboard_client.py` — создаёт записи в БД
4. **ChatFlow:** указать webhook URL `.../webhook/.../new_client`
5. **Документы:** загрузить в Google Drive или локально
6. **Скрипт:** `python3 sync_client.py new_client ./docs`
7. **Тест:** написать на номер бота

**Время: 30-60 минут вместо нескольких дней.**

---

## ЧАСТЬ 10: ИЗВЕСТНЫЕ ПРОБЛЕМЫ

### Проблема 1: Knowledge Sync workflow

**Симптом:** Вложенные loops (Loop Clients → Loop Docs) не работают. Второй клиент не обрабатывается.

**Причина:** Баг n8n — Split In Batches не сбрасывается между итерациями внешнего loop.

**Workaround:** Использовать `sync_client.py` для ручной синхронизации.

**Решение (будущее):** Переписать Knowledge Sync без вложенных loops или использовать внешний скрипт.

---

### Проблема 2: Webhook URL в ChatFlow

**Симптом:** "URL вебхука не найден" на скриншоте demo_salon.

**Причина:** В ChatFlow нужно указать правильный webhook URL с slug клиента.

**Решение:** Указать `https://n8n.truffles.kz/webhook/.../demo_salon` в настройках ChatFlow instance.

---

## РЕЗЮМЕ

### Что было сделано:

| # | Компонент | Изменение |
|---|-----------|-----------|
| 1 | БД: clients | Добавлен config с folder_id, instance_id, phone |
| 2 | БД: prompts | Промпты для каждого клиента |
| 3 | БД: knowledge_clients | Удалена (дублирование) |
| 4 | Qdrant | Переиндексация с client_slug |
| 5 | 1_Webhook | Параметризованный path /:client |
| 6 | 2-5_Chain | Передача client_slug |
| 7 | 6_Multi-Agent: Load Prompt | Загрузка prompt + instance_id из БД |
| 8 | 6_Multi-Agent: Prepare Prompt | Сборка финального промпта |
| 9 | 6_Multi-Agent: RAG Search | Фильтрация по client_slug |
| 10 | 6_Multi-Agent: Send nodes | Динамический instance_id |
| 11 | Скрипты | onboard_client.py, sync_client.py |
| 12 | Шаблоны | Документы для салонов красоты |

### Результат:

**Один workflow для всех клиентов.** Добавление нового клиента = записи в БД + webhook + документы.

---

## ФАЙЛЫ НА СЕРВЕРЕ

### База данных (PostgreSQL):
- `clients` — таблица клиентов с config
- `prompts` — промпты привязанные к клиентам

### Скрипты (`~/truffles/ops/`):
- `onboard_client.py` — интерактивный онбординг
- `sync_client.py` — синхронизация одного клиента
- `sync_all_clients.py` — синхронизация всех клиентов
- `run_sql.py` — выполнение SQL файлов

### Шаблоны (`~/truffles/ops/templates/`):
- `salon_services.md`
- `salon_faq.md`
- `salon_objections.md`
- `salon_rules.md`

### Workflows (n8n):
- 1_Webhook — параметризованный path
- 2_ChannelAdapter — передача client_slug
- 4_MessageBuffer — передача client_slug
- 6_Multi-Agent — Load Prompt, Prepare Prompt, динамические Send
- Knowledge Sync — (баг с loops, использовать скрипты)
