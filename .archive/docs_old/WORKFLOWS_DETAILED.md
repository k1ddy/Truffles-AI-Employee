# ДЕТАЛЬНОЕ ОПИСАНИЕ ВСЕХ WORKFLOWS И НОД

**Дата:** 2025-12-08
**Цель:** Понимать каждую ноду, каждый workflow от А до Я

---

## WORKFLOW 1: 1_Webhook (656fmXR6GPZrJbxm)

### Назначение
Точка входа. Принимает webhook от ChatFlow, определяет клиента по URL.

### Ноды

| Нода | Тип | Что делает | Input | Output |
|------|-----|------------|-------|--------|
| Webhook | webhook | Слушает POST на `/:client` | HTTP request | Raw body + params |
| Extract Client | code | Извлекает client_slug из URL | Webhook output | `{client_slug, ...body}` |
| Call Channel Adapter | workflow | Вызывает следующий workflow | Extract Client | — |

### Данные

```
ChatFlow POST /webhook/.../demo_salon
    ↓
{
  "client_slug": "demo_salon",  // из URL
  "data": {...}                  // из body
}
```

---

## WORKFLOW 2: 2_ChannelAdapter (C38zCf2jfc2Zqfzf)

### Назначение
Нормализация данных из ChatFlow формата в наш формат.

### Ноды

| Нода | Тип | Что делает | Input | Output |
|------|-----|------------|-------|--------|
| Start | execute workflow trigger | Точка входа | От Webhook | Raw data |
| Parse ChatFlow | code | Извлекает поля | Start | Normalized data |
| Call Normalize | workflow | Следующий шаг | Parse ChatFlow | — |

### Данные

```
Input (ChatFlow format):
{
  "data": {
    "key": {
      "remoteJid": "77015705555@s.whatsapp.net"
    },
    "message": {
      "conversation": "Привет"
    },
    "pushName": "Клиент"
  }
}

Output (наш формат):
{
  "client_slug": "demo_salon",
  "phone": "77015705555",
  "remoteJid": "77015705555@s.whatsapp.net",
  "senderName": "Клиент",
  "message": "Привет"
}
```

---

## WORKFLOW 3: 3_Normalize (DCs6AoJDIOPB4ZtF)

### Назначение
Очистка и нормализация текста сообщения.

### Что делает
- Убирает лишние пробелы
- Нормализует unicode
- Обрабатывает emoji

---

## WORKFLOW 4: 4_MessageBuffer (3QqFRxapNa29jODD)

### Назначение
Буферизация сообщений в Redis. Клиент может отправить несколько сообщений подряд — собираем в одно.

### Ключ Redis
```
chat:${client_slug}:${session_id}
```

**ВАЖНО:** Раньше был `chat:${session_id}` без client_slug — сообщения разных клиентов смешивались!

---

## WORKFLOW 5: 5_TurnDetector (kEXEMbThwUsCJ2Cz)

### Назначение
Определение конца "хода" клиента. Ждёт паузу перед обработкой.

---

## WORKFLOW 6: 6_Multi-Agent (4vaEvzlaMrgovhNz) — ГЛАВНЫЙ

### Назначение
Основная логика бота: классификация, RAG, генерация ответа, эскалация.

### Полная карта нод

```
START
  │
  ▼
┌─────────────┐
│ Parse Input │ ← Извлекает client_slug, phone, message, remoteJid, senderName
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ Intent Router│ ← Определяет нужна ли классификация
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ Skip Classifier?│ ← IF: пропустить классификацию?
└────┬───────┬────┘
     │       │
   [false] [true]
     │       │
     ▼       │
┌────────────────────────┐    │
│Load History for Classif│    │
└────────────┬───────────┘    │
             │                │
             ▼                │
┌────────────────────────┐    │
│ Format Classifier Input│    │
└────────────┬───────────┘    │
             │                │
             ▼                │
┌────────────────────────┐    │
│   OpenAI Chat Model    │    │
└────────────┬───────────┘    │
             │                │
             ▼                │
┌────────────────────────┐    │
│Structured Output Parser│    │
└────────────┬───────────┘    │
             │                │
             ▼                │
┌─────────────────┐           │
│ Classify Intent │           │
└────────┬────────┘           │
         │                    │
         ▼                    │
┌────────────────┐            │
│   Is On Topic  │ ← IF: on_topic == true?
└────┬──────┬────┘            │
     │      │                 │
  [true] [false]              │
     │      │                 │
     │      ▼                 │
     │  [Off-topic response]  │
     │                        │
     ▼◄───────────────────────┘
┌─────────────┐
│ Upsert User │ ← СОЗДАЁТ/ОБНОВЛЯЕТ user и conversation
└──────┬──────┘   ИСПОЛЬЗУЕТ: $('Parse Input').first().json
       │
       ▼
┌──────────────────┐
│ Save User Message│ ← Сохраняет сообщение в БД
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│ Load History │ ← Загружает историю диалога
└──────┬───────┘
       │
       ▼
┌─────────────┐
│ Load Prompt │ ← Загружает промпт клиента из БД
└──────┬──────┘
       │
       ▼
┌───────────────┐
│ Build Context │ ← Собирает контекст: message, history, reason
└───────┬───────┘
        │
        ▼
┌──────────────────────┐
│ Check Active Handover│ ← Проверяет есть ли активный handover
└──────────┬───────────┘
           │
           ▼
┌──────────────────┐
│ Handover Active? │ ← IF: handover_id != null?
└────┬────────┬────┘
     │        │
  [true]   [false]
     │        │
     ▼        ▼
┌──────────────────┐    ┌─────────────┐
│ Forward to Topic │    │ Is Deadlock │ ← IF: reason == 'human_request'?
│ Save Client Msg  │    └──────┬──────┘
│ Exit             │       [true]  [false]
└──────────────────┘           │        │
                               ▼        ▼
                    ┌──────────────────┐  ┌────────────┐
                    │Prepare Escalation│  │ RAG Search │
                    │      Data        │  └─────┬──────┘
                    └────────┬─────────┘        │
                             │                  ▼
                             │         ┌──────────────┐
                             │         │ Add Knowledge│
                             │         └──────┬───────┘
                             │                │
                             │                ▼
                             │         ┌───────────────┐
                             │         │ Prepare Prompt│
                             │         └───────┬───────┘
                             │                 │
                             │                 ▼
                             │         ┌────────────────────┐
                             │         │ OpenAI Chat Model1 │
                             │         └─────────┬──────────┘
                             │                   │
                             │                   ▼
                             │         ┌─────────────────────────┐
                             │         │ Structured Output Parser1│
                             │         └───────────┬─────────────┘
                             │                     │
                             │                     ▼
                             │         ┌───────────────────┐
                             │         │ Generate Response │
                             │         └─────────┬─────────┘
                             │                   │
                             │                   ▼
                             │         ┌──────────────────┐
                             │         │ Check Escalation │ ← IF: needs_escalation?
                             │         └────┬────────┬────┘
                             │           [true]   [false]
                             │              │        │
                             │              ▼        ▼
                             │   ┌──────────────────┐  [Send Response]
                             │   │Prepare Escalation│
                             │   │      Data        │
                             │   └────────┬─────────┘
                             │            │
                             ▼◄───────────┘
                    ┌────────────────────────┐
                    │ Call Escalation Handler│
                    └────────────────────────┘
```

### Детали ключевых нод

#### Parse Input
**Код:**
```javascript
const data = $input.first().json;
return [{
  json: {
    client_slug: data.client_slug || 'truffles',
    phone: data.phone,
    remoteJid: data.remoteJid,
    senderName: data.senderName || data.pushName || 'Клиент',
    message: data.message
  }
}];
```

#### Upsert User
**SQL:**
```sql
WITH client AS (
  SELECT id FROM clients WHERE name = '{{ $('Parse Input').first().json.client_slug }}'
),
upserted_user AS (
  INSERT INTO users (client_id, phone, remote_jid, name, last_active_at)
  SELECT
    (SELECT id FROM client),
    '{{ $('Parse Input').first().json.phone }}',
    '{{ $('Parse Input').first().json.remoteJid }}',
    '{{ $('Parse Input').first().json.senderName }}',
    NOW()
  ON CONFLICT (client_id, phone) DO UPDATE SET
    last_active_at = NOW(),
    name = COALESCE(NULLIF('{{ $('Parse Input').first().json.senderName }}', ''), users.name)
  RETURNING id
),
existing_conv AS (
  SELECT id FROM conversations
  WHERE user_id = (SELECT id FROM upserted_user)
    AND status = 'active'
  ORDER BY last_message_at DESC
  LIMIT 1
),
new_conv AS (
  INSERT INTO conversations (client_id, user_id, channel, status, last_message_at)
  SELECT
    (SELECT id FROM client),
    (SELECT id FROM upserted_user),
    'whatsapp',
    'active',
    NOW()
  WHERE NOT EXISTS (SELECT 1 FROM existing_conv)
  RETURNING id
)
SELECT
  (SELECT id FROM upserted_user) AS user_id,
  COALESCE(
    (SELECT id FROM existing_conv),
    (SELECT id FROM new_conv)
  ) AS conversation_id,
  (SELECT id FROM client) AS client_id;
```

**КРИТИЧНО:** Все `$('Parse Input').first().json` — явные ссылки!

#### Check Active Handover
**SQL:**
```sql
SELECT 
  h.id as handover_id,
  h.conversation_id as handover_conversation_id,
  c.telegram_topic_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  COALESCE(u.name, u.phone, 'Клиент') as client_name
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
LEFT JOIN client_settings cs ON cs.client_id = c.client_id
WHERE c.id = '{{ $('Upsert User').first().json.conversation_id }}';
```

**ВАЖНО:** LEFT JOIN на handovers — всегда возвращает данные, даже если нет активного handover.

#### Is Deadlock
**Условие:** `{{ $('Build Context').first().json.reason }} == 'human_request'`

Если клиент явно просит менеджера → true → эскалация.

#### Prepare Escalation Data
**Код:**
```javascript
return [{
  json: {
    conversation_id: $('Upsert User').first().json.conversation_id,
    client_id: $('Upsert User').first().json.client_id,
    phone: $('Parse Input').first().json.phone,
    remoteJid: $('Parse Input').first().json.remoteJid,
    message: $('Parse Input').first().json.message,
    reason: $('Build Context').first().json.reason || 'needs_escalation',
    bot_response: $('Generate Response').first()?.json?.response || 
                  'Передаю ваш вопрос менеджеру.'
  }
}];
```

**Собирает данные из РАЗНЫХ нод для передачи в Escalation Handler.**

---

## WORKFLOW 7: 7_Escalation_Handler (7jGZrdbaAAvtTnQX)

### Назначение
Решает что делать с эскалацией: создать handover, мьютить бота, отправить в Telegram.

### Карта нод

```
START (данные от Multi-Agent)
  │
  ▼
┌─────────────┐
│ Load Status │ ← Загружает bot_status, no_count, настройки
└──────┬──────┘
       │
       ▼
┌───────────────┐
│ Decide Action │ ← Логика: process или silent_exit
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│ Should Process? │ ← IF: action == 'process'
└────┬───────┬────┘
  [true]  [false]
     │       │
     │       ▼
     │   ┌─────────────┐
     │   │ Silent Exit │
     │   └─────────────┘
     ▼
┌─────────────────────┐
│ Update Conversation │ ← Обновляет bot_status, no_count
└──────────┬──────────┘
           │
           ▼
┌─────────────────┐
│ Create Handover │ ← Создаёт запись в handovers
└────────┬────────┘
         │
         ▼
┌────────────────────────┐
│ Call Telegram Adapter  │ ← Вызывает Telegram Adapter
└────────────┬───────────┘
             │
             ▼
┌──────────────────┐
│ Should Respond?  │ ← IF: response_text != null
└────┬────────┬────┘
  [true]   [false]
     │        │
     ▼        ▼
┌─────────────────────┐  (end)
│Send WhatsApp Response│
└──────────┬──────────┘
           │
           ▼
┌───────────────┐
│ Save Response │
└───────────────┘
```

### Детали ключевых нод

#### Load Status
**SQL:**
```sql
SELECT 
  c.bot_status,
  c.no_count,
  c.bot_muted_until,
  c.user_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  cs.silence_after_first_no_minutes,
  cs.max_retry_offers,
  cl.name as client_name,
  cl.config->>'instance_id' as instance_id
FROM conversations c
JOIN clients cl ON c.client_id = cl.id
LEFT JOIN client_settings cs ON cs.client_id = cl.id
WHERE c.id = '{{ $json.conversation_id }}';
```

#### Decide Action
**Логика:**
```javascript
const isMuted = botStatus === 'muted' && mutedUntil && now < mutedUntil;

if (isMuted) {
  action = 'silent_exit';  // Бот уже молчит
}
else if (input.reason === 'human_request') {
  newNoCount = noCount + 1;
  if (newNoCount === 1) {
    // Первый раз — эскалируем
    responseText = 'Передаю ваш вопрос менеджеру — свяжется в ближайшее время.';
    shouldMute = true;
  } else {
    // Повторно — молчим
    action = 'silent_exit';
  }
}
else if (input.reason === 'frustration') {
  responseText = 'Понимаю, передаю менеджеру — свяжется с вами лично.';
  shouldMute = true;
  newNoCount = noCount + 1;
}
else {
  // Обычная эскалация
  responseText = input.bot_response || 'Уточню у коллег и вернусь с ответом.';
}
```

#### Update Conversation
**SQL:**
```sql
UPDATE conversations SET
  bot_status = CASE WHEN {{ $json.should_mute }} THEN 'muted' ELSE bot_status END,
  bot_muted_until = CASE WHEN {{ $json.should_mute }} THEN NOW() + INTERVAL '{{ $json.silence_minutes }} minutes' ELSE bot_muted_until END,
  no_count = {{ $json.new_no_count }}
WHERE id = '{{ $json.conversation_id }}';
```

#### Create Handover
**SQL:**
```sql
INSERT INTO handovers (conversation_id, status, trigger_type, escalation_reason, question)
VALUES (
  '{{ $json.conversation_id }}',
  'pending',
  'intent',
  '{{ $json.reason }}',
  '{{ $json.message.replace(/'/g, "''") }}'
)
RETURNING id;
```

---

## WORKFLOW 8: 8_Telegram_Adapter (fFPEbTNlkBSjo66A)

### Назначение
Отправка эскалации в Telegram: создание топика, отправка сообщения с кнопками, закрепление.

### Карта нод

```
START (данные от Escalation Handler)
  │
  ▼
┌──────────────┐
│ Prepare Data │ ← Готовит данные для отправки
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Get Existing Topic │ ← Ищет топик по conversation_id
└─────────┬──────────┘
          │
          ▼
┌─────────────┐
│ Has Topic?  │ ← IF: telegram_topic_id exists
└────┬───┬────┘
  [false][true]
     │     │
     ▼     │
┌──────────────┐    │
│ Create Topic │    │
└──────┬───────┘    │
       │            │
       ▼            │
┌──────────────┐    │
│ Get Topic ID │◄───┘
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ Send Escalation │ ← HTTP POST sendMessage с кнопками
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pin Escalation  │ ← HTTP POST pinChatMessage
└────────┬────────┘
         │
         ▼
┌───────────────────┐
│ Save Channel Refs │ ← Сохраняет topic_id в conversations
└───────────────────┘
```

### Детали ключевых нод

#### Get Existing Topic
**SQL:**
```sql
SELECT telegram_topic_id 
FROM conversations 
WHERE id = '{{ $json.conversation_id }}';
```

#### Create Topic
**HTTP POST:**
```
URL: https://api.telegram.org/bot{token}/createForumTopic
Body: {
  "chat_id": "-1003412216010",
  "name": "77015705555 demo_salon"
}
```

#### Send Escalation
**HTTP POST:**
```
URL: https://api.telegram.org/bot{token}/sendMessage
Body: {
  "chat_id": "-1003412216010",
  "message_thread_id": 15,
  "text": "🆕 НОВАЯ ЗАЯВКА\n📱 Телефон: 77015705555\n...",
  "reply_markup": {
    "inline_keyboard": [[
      {"text": "Беру", "callback_data": "take_UUID"}
    ]]
  }
}
```

#### Save Channel Refs
**SQL:**
```sql
UPDATE conversations 
SET telegram_topic_id = {{ $json.topic_id }}
WHERE id = '{{ $json.conversation_id }}';

UPDATE handovers
SET channel = 'telegram',
    channel_ref = '{{ $json.topic_id }}',
    telegram_message_id = {{ $json.message_id }}
WHERE id = '{{ $json.handover_id }}';
```

---

## WORKFLOW 9: 9_Telegram_Callback (HQOWuMDIBPphC86v)

### Назначение
Обработка callback'ов от кнопок и сообщений менеджера в топиках.

### Карта нод — CALLBACK FLOW

```
Telegram Webhook
  │
  ▼
┌────────────────┐
│ Parse Callback │ ← Определяет тип: callback или message
└───────┬────────┘
        │
        ▼
┌───────────────┐
│ Get Bot Token │ ← Загружает токен по topic_id
└───────┬───────┘
        │
        ▼
┌─────────────┐
│ Merge Token │ ← Объединяет данные
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ Is Callback? │ ← IF: type == 'callback'
└────┬────┬────┘
  [true][false]
     │     │
     ▼     ▼
┌───────────────┐  [Message Flow - см. ниже]
│ Action Switch │
└────┬─────┬────┘
     │     │
  [take] [resolve]
     │     │
     ▼     ▼
┌──────────────┐  ┌──────────────────┐
│Take Handover │  │ Resolve Handover │
└──────┬───────┘  └────────┬─────────┘
       │                   │
       ▼                   ▼
┌──────────────┐  ┌─────────────┐
│Take Response │  │ Unmute Bot  │
└──────┬───────┘  └──────┬──────┘
       │                 │
       ▼                 ▼
┌────────────────┐  ┌──────────────────┐
│Answer Callback │  │ Resolve Response │
└───────┬────────┘  └────────┬─────────┘
        │                    │
        ▼                    ▼
┌────────────────┐  ┌───────────────────────┐
│ Update Buttons │  │ Remove Buttons Resolve│
└────────────────┘  └───────────┬───────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │ Unpin Escalation │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │ Answer Callback Resolve│
                    └────────────────────────┘
```

### Карта нод — MESSAGE FLOW

```
Is Callback? [false]
  │
  ▼
┌───────────────┐
│ Parse Message │ ← Извлекает текст, topic_id
└───────┬───────┘
        │
        ▼
┌───────────────────┐
│ Find Handover Data│ ← Ищет активный handover по topic_id
└─────────┬─────────┘
          │
          ▼
┌─────────────────────┐
│ Has Active Handover?│ ← IF: handover exists
└────┬───────────┬────┘
  [true]      [false]
     │           │
     ▼           ▼
┌───────────────────────────┐  (end)
│Send Manager Reply to WA   │
└───────────────┬───────────┘
                │
                ▼
┌────────────────────┐
│ Save Manager Message│
└──────────┬─────────┘
           │
           ▼
┌─────────────────────┐
│ Confirm Sent to Topic│
└──────────┬──────────┘
           │
           ▼
┌──────────┐
│ Wait 3s  │
└────┬─────┘
     │
     ▼
┌───────────────────────┐
│ Delete Confirm Message│
└───────────────────────┘
```

### Детали ключевых нод

#### Parse Callback
**Код:**
```javascript
const body = $input.first().json.body;

// Callback query (кнопка)
if (body.callback_query) {
  const cq = body.callback_query;
  const callbackData = cq.data;
  
  // Парсим: "take_UUID" или "resolve_UUID"
  const firstUnderscore = callbackData.indexOf('_');
  const action = firstUnderscore > 0 ? callbackData.substring(0, firstUnderscore) : callbackData;
  const handoverId = firstUnderscore > 0 ? callbackData.substring(firstUnderscore + 1) : '';
  
  return [{
    json: {
      type: 'callback',
      action: action,
      handover_id: handoverId,
      manager_id: String(cq.from.id),
      manager_name: cq.from.first_name || 'Менеджер',
      callback_query_id: cq.id,
      message_id: cq.message.message_id,
      chat_id: cq.message.chat.id,
      topic_id: cq.message.message_thread_id
    }
  }];
}

// Message (текст от менеджера)
if (body.message && body.message.text) {
  return [{
    json: {
      type: 'message',
      text: body.message.text,
      topic_id: body.message.message_thread_id,
      manager_id: String(body.message.from.id),
      manager_name: body.message.from.first_name || 'Менеджер',
      message_id: body.message.message_id,
      chat_id: body.message.chat.id,
      is_bot: body.message.from.is_bot
    }
  }];
}

return [];
```

#### Take Handover
**SQL с race condition защитой:**
```sql
UPDATE handovers 
SET status = 'active', 
    assigned_to = '{{ $json.manager_id }}', 
    assigned_to_name = '{{ $json.manager_name.replace(/'/g, "''") }}'
WHERE id = '{{ $json.handover_id }}' 
  AND status = 'pending'  -- ТОЛЬКО если pending!
RETURNING id, conversation_id;
```

#### Unmute Bot
**SQL:**
```sql
UPDATE conversations 
SET bot_status = 'active', 
    bot_muted_until = NULL, 
    no_count = 0  -- СБРОС счётчика!
WHERE id = (
  SELECT conversation_id FROM handovers 
  WHERE id = '{{ $('Merge Token').first().json.handover_id }}'
);
```

#### Update Buttons (после [Беру])
**HTTP POST:**
```
URL: https://api.telegram.org/bot{token}/editMessageReplyMarkup
Body: {
  "chat_id": -1003412216010,
  "message_id": 65,
  "reply_markup": {
    "inline_keyboard": [[
      {"text": "Решено ✅", "callback_data": "resolve_UUID"}
    ]]
  }
}
```

#### Remove Buttons Resolve (после [Решено])
**HTTP POST:**
```
URL: https://api.telegram.org/bot{token}/editMessageReplyMarkup
Body: {
  "chat_id": -1003412216010,
  "message_id": 65,
  "reply_markup": {
    "inline_keyboard": []  // ПУСТОЙ массив убирает кнопки
  }
}
```

#### Send Manager Reply to WhatsApp
**HTTP GET (Chatflow API):**
```
URL: https://api.chatflow.me/v1/messages/text/aLZLzwtwP3RpBXzG6SlmZ5cS96boQyc?token=a29b2ad2-9485-476c-897d-34799c3f940b
Query params:
  - number: 77015705555
  - text: "Ответ менеджера"
```

---

## ПОТОК ДАННЫХ — ПОЛНАЯ КАРТИНА

### Сценарий: Клиент просит менеджера

```
1. WhatsApp → ChatFlow → 1_Webhook
   Данные: {raw webhook data}
   
2. 1_Webhook → 2_ChannelAdapter
   Данные: {client_slug: "demo_salon", data: {...}}
   
3. 2_ChannelAdapter → ... → 6_Multi-Agent
   Данные: {client_slug, phone, remoteJid, senderName, message}
   
4. Parse Input
   Output: {client_slug: "demo_salon", phone: "77015705555", message: "хочу менеджера"}
   
5. Classify Intent
   Output: {on_topic: true, reason: "human_request", ...}
   
6. Upsert User
   Input: $('Parse Input').first().json
   Output: {user_id, conversation_id, client_id}
   
7. Build Context
   Output: {message, history, reason: "human_request"}
   
8. Check Active Handover
   Output: {handover_id: null, telegram_topic_id: 15, ...}
   
9. Is Deadlock = TRUE (reason == 'human_request')
   
10. Prepare Escalation Data
    Output: {conversation_id, phone, message, reason: "human_request"}
    
11. Call Escalation Handler
    Input: данные от Prepare Escalation Data
    
12. 7_Escalation_Handler: Load Status
    Output: {bot_status: "active", no_count: 0, ...}
    
13. Decide Action
    Output: {action: "process", should_mute: true, response_text: "Передаю..."}
    
14. Update Conversation
    SQL: SET bot_status='muted', bot_muted_until=NOW()+30min, no_count=1
    
15. Create Handover
    SQL: INSERT INTO handovers... RETURNING id
    Output: {id: "uuid"}
    
16. Call Telegram Adapter
    Input: {conversation_id, handover_id, phone, message, ...}
    
17. 8_Telegram_Adapter: Get Existing Topic
    SQL: SELECT telegram_topic_id FROM conversations
    Output: {telegram_topic_id: 15}  // уже есть
    
18. Send Escalation
    HTTP: sendMessage с кнопкой [Беру]
    Output: {message_id: 82}
    
19. Pin Escalation
    HTTP: pinChatMessage
    
20. Save Channel Refs
    SQL: UPDATE handovers SET telegram_message_id=82
    
21. Менеджер видит сообщение в Telegram топике
```

### Сценарий: Менеджер нажимает [Беру]

```
1. Telegram → 9_Telegram_Callback webhook
   Body: {callback_query: {data: "take_uuid", from: {id: 1969855532}}}
   
2. Parse Callback
   Output: {type: "callback", action: "take", handover_id: "uuid", manager_name: "Zh"}
   
3. Get Bot Token
   SQL: SELECT telegram_bot_token FROM client_settings...
   Output: {telegram_bot_token: "8249..."}
   
4. Merge Token
   Output: {...все данные + bot_token}
   
5. Is Callback? = TRUE
   
6. Action Switch → take branch
   
7. Take Handover
   SQL: UPDATE handovers SET status='active', assigned_to='1969855532' WHERE status='pending'
   Output: {id, conversation_id}
   
8. Take Response
   Output: {text: "✅ Zh взял(а) заявку", show_alert: false}
   
9. Answer Callback
   HTTP: answerCallbackQuery
   
10. Update Buttons
    HTTP: editMessageReplyMarkup → кнопка [Решено ✅]
```

### Сценарий: Менеджер нажимает [Решено]

```
1. Telegram → callback_query: {data: "resolve_uuid"}
   
2. Parse Callback
   Output: {type: "callback", action: "resolve", handover_id: "uuid"}
   
3. Action Switch → resolve branch
   
4. Resolve Handover
   SQL: UPDATE handovers SET status='resolved', resolved_at=NOW()
   
5. Unmute Bot
   SQL: UPDATE conversations SET bot_status='active', no_count=0
   
6. Resolve Response
   Output: {text: "Заявка закрыта"}
   
7. Remove Buttons Resolve
   HTTP: editMessageReplyMarkup → пустой inline_keyboard
   
8. Unpin Escalation
   HTTP: unpinChatMessage
   
9. Answer Callback Resolve
   HTTP: answerCallbackQuery
   
10. Бот снова отвечает клиенту
```

---

## TELEGRAM API ENDPOINTS

| Метод | URL | Назначение |
|-------|-----|------------|
| sendMessage | /bot{token}/sendMessage | Отправить сообщение |
| editMessageText | /bot{token}/editMessageText | Изменить текст |
| editMessageReplyMarkup | /bot{token}/editMessageReplyMarkup | Изменить кнопки |
| answerCallbackQuery | /bot{token}/answerCallbackQuery | Ответить на callback |
| pinChatMessage | /bot{token}/pinChatMessage | Закрепить |
| unpinChatMessage | /bot{token}/unpinChatMessage | Открепить |
| createForumTopic | /bot{token}/createForumTopic | Создать топик |
| deleteMessage | /bot{token}/deleteMessage | Удалить сообщение |

---

## CHATFLOW API

### Отправка текста
```
GET https://api.chatflow.me/v1/messages/text/{instance_id}
Query params:
  - token: a29b2ad2-9485-476c-897d-34799c3f940b
  - number: 77015705555
  - text: "Текст сообщения"
```

### Instance IDs
- truffles: `eyJ1aWQiOiJ...dHJ1ZmZsZXMtY2hhdGJvdCJ9`
- demo_salon: `eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InNhbG9uZGVtbyJ9`

---

*Документ создан: 2025-12-08*
