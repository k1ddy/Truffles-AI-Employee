# N8N FULL ARCHITECTURE

Детальное описание ВСЕЙ системы в n8n — от входящего сообщения до ответа.
**Читай это перед реализацией в Python.**

---

## ЧАСТЬ 0: ВХОДЯЩИЕ СООБЩЕНИЯ

### Полный путь сообщения

```
WhatsApp (ChatFlow.kz) → 1_Webhook → 2_ChannelAdapter → 3_Normalize → 4_MessageBuffer → 5_TurnDetector → 6_Multi-Agent
```

---

## 0.1. WEBHOOK (1_Webhook)

**URL:** `https://n8n.truffles.kz/webhook/:client`

**Что делает:**
1. Принимает POST от ChatFlow.kz
2. Дедупликация через Redis (чтобы не обрабатывать дважды)
3. Передаёт в 2_ChannelAdapter

**Формат входящего:**
```json
{
  "body": {
    "messageType": "text",
    "message": "Привет",
    "metadata": {
      "sender": "Zh.",
      "timestamp": 1764911619,
      "messageId": "3F1D0B6CB1B912F5CFC7",
      "remoteJid": "77015705555@s.whatsapp.net"
    },
    "mediaData": null
  }
}
```

**client_slug** берётся из URL параметра `:client` (например `/webhook/truffles`).

---

## 0.2. CHANNEL ADAPTER (2_ChannelAdapter)

**Что делает:** Парсит WhatsApp формат в нормализованный.

**JavaScript:**
```javascript
const body = $json.body || $json;
const metadata = body.metadata || {};
const mediaData = body.mediaData || null;
const clientSlug = $json.client_slug || 'truffles';

const remoteJid = metadata.remoteJid || '';
const phone = remoteJid.replace('@s.whatsapp.net', '');

return [{
  json: {
    channel: 'whatsapp',
    user_id: phone,                    // "77015705555"
    session_id: remoteJid,             // "77015705555@s.whatsapp.net"
    message_id: metadata.messageId,
    timestamp: metadata.timestamp,
    sender_name: metadata.sender,
    message_type: body.messageType,    // "text" | "audio" | "image"
    text: body.message,
    media: mediaData ? {
      type: mediaData.type,
      url: mediaData.url,
      base64: mediaData.base64,
      mimetype: mediaData.mimetype,
      filename: mediaData.fileName,
      caption: mediaData.caption
    } : null,
    client_slug: clientSlug
  }
}];
```

---

## 0.3. NORMALIZE (3_Normalize) — STT

**Что делает:**
1. Если `message_type == "text"` → просто передаёт дальше
2. Если `message_type == "audio"` → транскрибирует через ElevenLabs STT
3. Если `message_type == "image"` → placeholder `[image received]`

### STT Flow (для аудио):

**Prepare Audio:**
```javascript
const media = input.media || {};
if (!media.base64) {
  return [{ json: { ...input, normalized_text: '[audio without data]' } }];
}
const buffer = Buffer.from(media.base64, 'base64');
return [{
  json: input,
  binary: {
    audio: {
      data: buffer,
      mimeType: media.mimetype || 'audio/ogg',
      fileName: media.filename || 'voice.ogg'
    }
  }
}];
```

**ElevenLabs STT:**
```
POST https://api.elevenlabs.io/v1/speech-to-text
Headers: xi-api-key: {ELEVENLABS_API_KEY}
Body: multipart/form-data
  - file: {binary audio}
  - model_id: "scribe_v2"
```

**Ответ:**
```json
{"text": "Расшифрованный текст"}
```

**Audio Result:**
```javascript
return [{
  json: {
    ...input,
    normalized_text: sttResult.text || '[audio not transcribed]',
    processing: 'audio_stt'
  }
}];
```

---

## 0.4. MESSAGE BUFFER (4_MessageBuffer)

**Зачем:** Клиент шлёт несколько сообщений подряд → объединить в одно.

**Как работает:**

1. **Prepare Keys:**
```javascript
const bufferKey = `chat:${input.client_slug}:${input.session_id}`;
const timerKey = `timer:${input.client_slug}:${input.session_id}`;
```

2. **Push to Buffer:** `RPUSH {bufferKey} {messageData}`

3. **Get Timer:** `GET {timerKey}`

4. **Is First Message?**
   - Если таймера нет → это первое сообщение
   - SET таймер с TTL 30 сек
   - Wait 5 сек
   - Get all messages: `LRANGE {bufferKey} 0 -1`
   - Merge messages
   - Clear buffer: `DEL {bufferKey}`

5. **Если таймер есть** → Stop (не обрабатывать, ждать)

**Merge Messages:**
```javascript
const messages = messagesRaw.map(m => JSON.parse(m));
const mergedText = messages.map(m => m.text).filter(t => t).join('\n');
const hasAudio = messages.some(m => m.type === 'audio');

return [{
  json: {
    buffered_messages: messages,
    buffered_count: messages.length,
    merged_text: mergedText,
    has_audio: hasAudio,
    last_message_type: messages[messages.length - 1]?.type || 'text'
  }
}];
```

---

## 0.5. TURN DETECTOR (5_TurnDetector)

**Зачем:** Определить — это законченная мысль или клиент ещё печатает? + исправить опечатки.

### Эвристики (до LLM):
```javascript
let confidence = 0.5;
let skipLLM = false;
let intentType = 'unknown';

// Аудио = законченная мысль (+0.3)
if (input.has_audio) confidence += 0.3;

// Несколько сообщений = скорее законченная мысль (+0.2)
if (messages.length >= 2) confidence += 0.2;

// Короткие ответы
const shortAnswers = ['да', 'нет', 'ок', 'окей', 'хорошо', 'ладно', 'давай', 'понял', 'ага', 'угу'];
if (shortAnswers.includes(lowerText)) {
  confidence = 0.95;
  intentType = 'answer';
  skipLLM = true;
}

// Вопрос в конце = законченная мысль
if (mergedText.trim().endsWith('?')) {
  confidence += 0.2;
  intentType = 'question';
}

// Если confidence >= 0.85 — пропускаем LLM
```

### LLM (если нужен):
- Модель: `gpt-4.1-mini`
- Задача: объединить сообщения, исправить опечатки, определить intent

**Output:**
```json
{
  "is_complete": true,
  "intent_type": "question",
  "merged_message": "Привет, расскажи о бизнесе",
  "context_hint": "компания, деятельность"
}
```

---

## ЧАСТЬ 1: ОСНОВНАЯ ОБРАБОТКА (6_Multi-Agent)

## ОБЩАЯ СХЕМА

```
Клиент пишет в WhatsApp
        ↓
   6_Multi-Agent
        ↓
   [Check Active Handover] ──→ Есть активный handover? ──→ [Forward to Topic] → EXIT
        ↓ нет
   [Classify Intent] → [Generate Response]
        ↓
   needs_escalation = true?
        ↓ да
   7_Escalation_Handler
        ↓
   8_Telegram_Adapter
        ↓
   Создаёт топик (если нет) → Отправляет сообщение с кнопками → Pin
        ↓
   Менеджер видит в Telegram
        ↓
   [Беру] / [Не могу] / текст ответа
        ↓
   9_Telegram_Callback
        ↓
   [Беру] → status='active', Update Buttons
   [Текст] → Отправить в WhatsApp, "✅ Доставлено"
   [Решено] → status='resolved', Unmute Bot, Unpin
```

---

## 1. ПРОВЕРКА HANDOVER В 6_Multi-Agent

**Нода:** `Check Active Handover`

**Когда вызывается:** После `Build Context`, ДО генерации ответа

**SQL запрос:**
```sql
SELECT 
  h.id as handover_id,
  h.conversation_id as handover_conversation_id,
  c.telegram_topic_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  COALESCE(u.name, u.phone, 'Клиент') as client_name
FROM conversations c
LEFT JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
LEFT JOIN client_settings cs ON cs.client_id = c.client_id
LEFT JOIN users u ON u.id = c.user_id
WHERE c.id = '{conversation_id}'
LIMIT 1;
```

**Логика (нода `Handover Active?`):**
```javascript
if ($json.handover_id) {
  // Есть активный handover → Forward to Topic → EXIT
} else {
  // Нет → продолжить обычную обработку
}
```

**Нода `Forward to Topic`:**
```
POST https://api.telegram.org/bot{bot_token}/sendMessage
{
  "chat_id": "{telegram_chat_id}",
  "message_thread_id": "{telegram_topic_id}",
  "text": "💬 {client_name}: {originalMessage}"
}
```

**ВАЖНО:** Когда handover активен, бот НЕ отвечает. Сообщение клиента идёт напрямую менеджеру.

---

## 2. ESCALATION_HANDLER (7_Escalation_Handler)

**Вход:**
```json
{
  "conversation_id": "uuid",
  "client_id": "uuid",
  "phone": "77015705555",
  "remoteJid": "77015705555@s.whatsapp.net",
  "message": "текст клиента",
  "reason": "human_request" | "frustration" | "escalation"
}
```

**Flow:**

### 2.1. Load Status
```sql
SELECT 
  c.bot_status,
  c.no_count,
  c.bot_muted_until,
  c.user_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  cs.silence_after_first_no_minutes,
  cl.name as client_name,
  cl.config->>'instance_id' as instance_id
FROM conversations c
JOIN clients cl ON c.client_id = cl.id
LEFT JOIN client_settings cs ON cs.client_id = cl.id
WHERE c.id = '{conversation_id}';
```

### 2.2. Decide Action (JavaScript)
```javascript
const botStatus = status.bot_status || 'active';
const noCount = status.no_count || 0;
const mutedUntil = status.bot_muted_until ? new Date(status.bot_muted_until) : null;
const now = new Date();
const silenceMinutes = status.silence_after_first_no_minutes || 30;
const isMuted = botStatus === 'muted' && mutedUntil && now < mutedUntil;

let action = 'process';
let responseText = null;
let shouldMute = false;
let newNoCount = noCount;

if (isMuted) {
  action = 'silent_exit';  // Бот молчит
} else if (input.reason === 'human_request') {
  newNoCount = noCount + 1;
  if (newNoCount === 1) {
    responseText = 'Передаю ваш вопрос менеджеру — свяжется в ближайшее время.';
    shouldMute = true;
  } else {
    action = 'silent_exit';  // Повторный запрос — молчим
  }
} else if (input.reason === 'frustration') {
  responseText = 'Понимаю, передаю менеджеру — свяжется с вами лично.';
  shouldMute = true;
  newNoCount = noCount + 1;
} else {
  responseText = 'Уточню у коллег и вернусь с ответом.';
}
```

### 2.3. Update Conversation
```sql
UPDATE conversations SET
  bot_status = CASE WHEN {should_mute} THEN 'muted' ELSE bot_status END,
  bot_muted_until = CASE WHEN {should_mute} THEN NOW() + INTERVAL '{silence_minutes} minutes' ELSE bot_muted_until END,
  no_count = {new_no_count}
WHERE id = '{conversation_id}';
```

### 2.4. Create Handover
```sql
INSERT INTO handovers (
  conversation_id,
  client_id,
  user_message,
  status,
  trigger_type,
  trigger_value,
  escalation_reason
) VALUES (
  '{conversation_id}',
  '{client_id}',
  '{message}',
  'pending',
  'intent',
  '{reason}',
  '{reason}'
) RETURNING id;
```

### 2.5. Call Telegram Adapter
Передаёт:
```json
{
  "telegram_chat_id": "-100xxx",
  "telegram_bot_token": "xxx:xxx",
  "phone": "77015705555",
  "client_name": "Имя",
  "client_slug": "truffles",
  "business_name": "Название бизнеса",
  "message": "текст клиента",
  "handover_id": "uuid",
  "conversation_id": "uuid"
}
```

---

## 3. TELEGRAM_ADAPTER (8_Telegram_Adapter)

**Создаёт топик если нет, отправляет сообщение с кнопками, pin.**

### 3.1. Prepare Data
```javascript
const topicName = `${phone} ${clientName} [${businessName}]`;
// Пример: "77015705555 Жанбол [Truffles]"
```

### 3.2. Get Existing Topic
```sql
SELECT telegram_topic_id 
FROM conversations 
WHERE id = '{conversation_id}';
```

### 3.3. Create Topic (если нет)
```
POST https://api.telegram.org/bot{bot_token}/createForumTopic
{
  "chat_id": "{telegram_chat_id}",
  "name": "{topic_name}"
}
```

**Ответ:**
```json
{
  "result": {
    "message_thread_id": 123
  }
}
```

### 3.4. Save Topic ID
```sql
UPDATE conversations 
SET telegram_topic_id = {message_thread_id} 
WHERE id = '{conversation_id}';
```

### 3.5. Send Escalation
```
POST https://api.telegram.org/bot{bot_token}/sendMessage
{
  "chat_id": "{telegram_chat_id}",
  "message_thread_id": "{topic_id}",
  "text": "🚨 НОВАЯ ЗАЯВКА\n\n📱 Телефон: {phone}\n👤 Клиент: {client_name}\n🏢 Бизнес: {business_name}\n\n💬 Сообщение:\n{message}",
  "reply_markup": {
    "inline_keyboard": [[
      {"text": "Беру ✋", "callback_data": "take_{handover_id}"},
      {"text": "Не могу ❌", "callback_data": "skip_{handover_id}"}
    ]]
  }
}
```

**Ответ:**
```json
{
  "result": {
    "message_id": 456
  }
}
```

### 3.6. Pin Escalation
```
POST https://api.telegram.org/bot{bot_token}/pinChatMessage
{
  "chat_id": "{telegram_chat_id}",
  "message_id": 456,
  "disable_notification": true
}
```

### 3.7. Save Channel Refs
```sql
UPDATE handovers 
SET channel = 'telegram', 
    channel_ref = '{topic_id}', 
    telegram_message_id = {message_id}
WHERE id = '{handover_id}';
```

---

## 4. TELEGRAM_CALLBACK (9_Telegram_Callback)

**Обрабатывает кнопки и сообщения менеджеров.**

**Webhook URL:** `https://n8n.truffles.kz/webhook/telegram-callback`

**Настройка webhook на бота:**
```
POST https://api.telegram.org/bot{bot_token}/setWebhook
{
  "url": "https://n8n.truffles.kz/webhook/telegram-callback"
}
```

### 4.1. Parse Callback (JavaScript)
```javascript
const body = $json.body || $json;

// CALLBACK (кнопка нажата)
const callback = body.callback_query;
if (callback) {
  const data = callback.data;  // "take_uuid" или "resolve_uuid"
  const firstUnderscore = data.indexOf('_');
  const action = data.substring(0, firstUnderscore);  // "take"
  const handoverId = data.substring(firstUnderscore + 1);  // "uuid"
  
  return [{
    json: {
      type: 'callback',
      action,
      handover_id: handoverId,
      manager_id: String(callback.from.id),
      manager_name: callback.from.first_name,
      callback_query_id: callback.id,
      message_id: callback.message?.message_id,
      chat_id: callback.message?.chat?.id,
      topic_id: callback.message?.message_thread_id
    }
  }];
}

// MESSAGE (текст от менеджера)
const msg = body.message;
if (msg) {
  return [{
    json: {
      type: 'message',
      chat_id: msg.chat?.id,
      topic_id: msg.message_thread_id,
      text: msg.text || '',
      from_id: msg.from.id,
      from_name: msg.from.first_name,
      is_bot: msg.from.is_bot || false
    }
  }];
}
```

### 4.2. Get Bot Token
```sql
SELECT telegram_bot_token 
FROM client_settings 
WHERE telegram_chat_id = '{chat_id}';
```

### 4.3. Action Switch

**[Беру] (take):**
```sql
UPDATE handovers 
SET status = 'active', 
    assigned_to = '{manager_id}', 
    assigned_to_name = '{manager_name}' 
WHERE id = '{handover_id}' AND status = 'pending'
RETURNING id;
```

**Answer Callback:**
```
POST https://api.telegram.org/bot{bot_token}/answerCallbackQuery
{
  "callback_query_id": "{callback_query_id}",
  "text": "✅ Вы взяли заявку"
}
```

**Update Buttons:**
```
POST https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup
{
  "chat_id": "{chat_id}",
  "message_id": "{message_id}",
  "reply_markup": {
    "inline_keyboard": [[
      {"text": "Решено ✅", "callback_data": "resolve_{handover_id}"}
    ]]
  }
}
```

---

**[Решено] (resolve):**
```sql
UPDATE handovers 
SET status = 'resolved', resolved_at = NOW() 
WHERE id = '{handover_id}';
```

**Unmute Bot:**
```sql
UPDATE conversations 
SET bot_status = 'active', bot_muted_until = NULL, no_count = 0
WHERE id = (
  SELECT conversation_id FROM handovers 
  WHERE id = '{handover_id}'
);
```

**Remove Buttons:**
```
POST editMessageReplyMarkup
{
  "reply_markup": {"inline_keyboard": []}
}
```

**Unpin:**
```
POST unpinChatMessage
{
  "chat_id": "{chat_id}",
  "message_id": "{message_id}"
}
```

---

**Сообщение менеджера (type = 'message'):**

**Find Handover Data:**
```sql
SELECT 
  h.id as handover_id,
  h.conversation_id,
  c.client_id,
  u.phone,
  u.phone || '@s.whatsapp.net' as remote_jid,
  cl.config->>'instance_id' as instance_id,
  cs.telegram_bot_token as bot_token
FROM conversations c
JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
JOIN users u ON u.id = c.user_id
JOIN clients cl ON cl.id = c.client_id
JOIN client_settings cs ON cs.client_id = c.client_id
WHERE c.telegram_topic_id = {topic_id};
```

**Send to WhatsApp:**
```
GET https://app.chatflow.kz/api/v1/send-text
  ?token={chatflow_token}
  &instance_id={instance_id}
  &jid={remote_jid}
  &msg={text}
```

**Save Manager Message:**
```sql
UPDATE handovers 
SET messages = COALESCE(messages, '[]'::jsonb) || 
  jsonb_build_array(jsonb_build_object(
    'from', 'manager',
    'name', '{manager_name}',
    'text', '{text}',
    'at', NOW()::text
  ))
WHERE id = '{handover_id}';
```

**Confirm Sent:**
```
POST sendMessage → "✅ Доставлено"
```
(через 3 сек удаляется)

---

## 5. ТАБЛИЦЫ В БД

### conversations
```sql
telegram_topic_id INTEGER     -- ID топика в Telegram
bot_status VARCHAR            -- 'active' | 'muted'
bot_muted_until TIMESTAMP     -- Когда размьютить
no_count INTEGER              -- Счётчик отказов
escalated_at TIMESTAMP        -- Когда последний раз эскалировали
```

### handovers
```sql
id UUID PRIMARY KEY
conversation_id UUID
client_id UUID
user_message TEXT             -- Сообщение клиента
status VARCHAR                -- 'pending' | 'active' | 'resolved'
trigger_type VARCHAR          -- 'intent'
trigger_value VARCHAR         -- 'human_request' | 'frustration'
escalation_reason VARCHAR
assigned_to VARCHAR           -- Telegram ID менеджера
assigned_to_name VARCHAR      -- Имя менеджера
telegram_message_id INTEGER   -- ID сообщения в Telegram
channel VARCHAR               -- 'telegram'
channel_ref VARCHAR           -- topic_id
messages JSONB                -- История сообщений
reminder_1_sent_at TIMESTAMP
reminder_2_sent_at TIMESTAMP
resolved_at TIMESTAMP
created_at TIMESTAMP
```

### client_settings
```sql
telegram_chat_id VARCHAR      -- ID группы менеджеров
telegram_bot_token VARCHAR    -- Токен бота
silence_after_first_no_minutes INTEGER  -- 30
owner_telegram_id VARCHAR     -- Кого тегать при СРОЧНО
```

---

## 6. CREDENTIALS

| Что | Значение |
|-----|----------|
| Telegram Bot Token | `8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4` |
| ChatFlow Token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzYyMTExNDU2fQ.myOt6xgCLfqbD9IF9EdJxkAyjij3fMty1B7sOhP2iKA` |
| ChatFlow URL | `https://app.chatflow.kz/api/v1/send-text` |
| Telegram API | `https://api.telegram.org/bot{token}/{method}` |

---

## 7. ПОРЯДОК РЕАЛИЗАЦИИ В PYTHON

1. **Check Handover Early** — в `/message` endpoint:
   - Проверить есть ли активный handover
   - Если да — Forward to Topic, не отвечать ботом

2. **Создание топиков** — в escalation_service:
   - Если нет telegram_topic_id → createForumTopic
   - Сохранить в conversations

3. **Кнопки** — callback_data формат:
   - `take_{handover_id}`
   - `skip_{handover_id}`
   - `resolve_{handover_id}`

4. **Telegram Webhook** — `/telegram-webhook`:
   - Парсить callback_query и message
   - Роутить по action
   - Для message — найти conversation по topic_id

5. **Update Buttons** — после [Беру]:
   - editMessageReplyMarkup → оставить только [Решено]

6. **Unpin** — после [Решено]:
   - unpinChatMessage

7. **Unmute Bot** — после [Решено]:
   - UPDATE conversations SET bot_status='active', bot_muted_until=NULL, no_count=0
