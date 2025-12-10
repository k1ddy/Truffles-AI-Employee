# CONVERSATION INTELLIGENCE ARCHITECTURE

**Дата:** 2025-12-05
**Авторы:** Жанбол + Droid
**Статус:** В разработке

---

## ПРОБЛЕМЫ КОТОРЫЕ РЕШАЕМ

| Проблема | Описание |
|----------|----------|
| Race Condition | Клиент шлёт 3 сообщения → бот отвечает 3 раза отдельно |
| Контекст | "да свяжи" без истории → бот не понимает |
| Странные сообщения | ".", "?" → бот паникует |
| Аудио/Фото | Разные форматы → нужна унификация |
| Каналы | WhatsApp сейчас, Instagram потом |

---

## ИССЛЕДОВАНИЕ (что нашли у гигантов)

### End-of-Turn Detection
- VAD (Voice Activity Detection) — тупой, смотрит только паузы
- Semantic Turn Detection — LLM понимает смысл паузы
- LiveKit, Speechmatics — открытые модели

### Message Buffering
- Intercom, Drift, Zendesk — все используют debounce
- n8n — готовые workflows с Redis buffering
- Стандарт: 5 секунд тишины → собрать всё → один ответ

### Multi-Turn Context
- Dialogflow: Slot elicitation, Context lifespan
- Rasa: DialogueStateTracker
- Intercom Fin: Query Refinement перед RAG

---

## АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHANNEL ADAPTER LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Webhook → Channel Detector → WhatsApp/Instagram/Telegram Adapter          │
│                                       ↓                                      │
│                              NORMALIZED MESSAGE                              │
│   {                                                                          │
│     channel: "whatsapp",                                                     │
│     user_id: "77015705555",                                                  │
│     session_id: "77015705555@s.whatsapp.net",                                │
│     message_id: "...",                                                       │
│     timestamp: 1764908574,                                                   │
│     sender_name: "Zh.",                                                      │
│     message_type: "text|audio|image",                                        │
│     text: "...",                                                             │
│     media: { url, base64, mimetype, filename } | null                        │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NORMALIZE LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Text  → text как есть                                                      │
│   Audio → ElevenLabs Scribe v2 → text                                        │
│   Image → (future) GPT Vision → description                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MESSAGE BUFFER LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. RPUSH chat:{session_id} { text, type, ts }                              │
│   2. Первое сообщение? → SET timer:{session_id}, WAIT 5 сек                  │
│   3. Не первое? → просто добавили, выход (200 OK)                            │
│   4. После wait: LRANGE → собрать всё → DEL                                  │
│                                                                              │
│   Redis:                                                                     │
│   - chat:{session_id}   LIST   TTL 30 сек                                    │
│   - timer:{session_id}  STRING TTL 30 сек                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TURN COMPLETENESS LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Input: buffered_messages + last_bot_message + conversation_state           │
│                                                                              │
│   GPT-4o-mini анализирует:                                                   │
│   - Это законченная мысль?                                                   │
│   - Это ответ на вопрос бота?                                                │
│   - Объединить в одно связное сообщение                                      │
│                                                                              │
│   Output:                                                                    │
│   {                                                                          │
│     is_complete: true/false,                                                 │
│     intent_type: "question|answer|continuation|reaction",                    │
│     merged_message: "объединённый текст",                                    │
│     context_hint: "подсказка для следующего шага"                            │
│   }                                                                          │
│                                                                              │
│   Эвристики (до LLM):                                                        │
│   - audio → +0.3 к is_complete (голосовые = законченная мысль)               │
│   - ".", "?" → проверить last_bot_message                                    │
│   - "да", "ок", "свяжи" → intent_type = answer                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT ENRICHMENT LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Добавить к merged_message:                                                 │
│   - last_bot_message                                                         │
│   - conversation_state (status, last_intent, msg_count)                      │
│   - user profile (last_decision)                                             │
│   - history (последние 10 сообщений)                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAIN WORKFLOW                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Classify Intent → RAG Search → Generate Response → Send                    │
│                                                                              │
│   При needs_escalation:                                                      │
│   → Notify Manager (Telegram)                                                │
│   → Всё равно ответить клиенту                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## REDIS СТРУКТУРА

```
# Message Buffer (TTL 30 сек)
chat:{session_id}     LIST    ["msg1", "msg2", "msg3"]
timer:{session_id}    STRING  "1733400000000"

# Deduplication (TTL 24 часа)
dedup:{messageId}     STRING  "1"

# Conversation State (TTL 24 часа)
state:{session_id}    HASH    {
                                status: "active",
                                last_bot_message: "...",
                                last_intent: "...",
                                msg_count: 5
                              }
```

---

## WORKFLOW СТРУКТУРА (n8n)

```
1_Webhook              - Входной webhook + signature + dedup (существует)
2_ChannelAdapter       - WhatsApp adapter (новый)
3_Normalize            - Text/Audio/Image → text (расширить существующий)
4_MessageBuffer        - Redis buffering + wait (новый)
5_TurnDetector         - Completeness detection (новый)
6_ContextEnrichment    - Добавить контекст (новый)
7_Truffles_v2          - Main workflow (существует, модифицировать вход)
```

---

## ПЛАН РЕАЛИЗАЦИИ

### Фаза 1: Channel Adapter + Normalize
- [ ] WhatsApp Adapter (нормализация формата)
- [ ] Расширить Normalize для audio/image

### Фаза 2: Message Buffer
- [ ] Redis buffering logic
- [ ] Wait/collect механизм
- [ ] Тестирование race condition

### Фаза 3: Turn Completeness
- [ ] Эвристики (до LLM)
- [ ] LLM-based detector
- [ ] Интеграция с буфером

### Фаза 4: Context Enrichment
- [ ] Загрузка last_bot_message
- [ ] Conversation state tracking
- [ ] Интеграция с main workflow

### Фаза 5: Интеграция
- [ ] Подключить к Truffles v2
- [ ] Тестирование end-to-end
- [ ] Документация

---

## СООТВЕТСТВИЕ ФИЛОСОФИИ TRUFFLES

| Принцип | Как реализовано |
|---------|-----------------|
| Анти-амнезия | Context Enrichment добавляет историю |
| Терпение к странностям | Turn Detector понимает ".", "?", эмодзи |
| Краткость | Merged message = одна мысль |
| Нет значит нет | conversation_state отслеживает статус |
| Голосовые | Audio → STT → общий поток |

---

*Создано: 2025-12-05*
*Обновлять при изменениях*
