# Truffles Chatbot - Work Log

## Сессия 2025-11-29

### Выполнено:

#### 1. Инфраструктура
- [x] Подключение к серверу (zhan@5.188.241.234:222)
- [x] Добавлен pgAdmin в docker-compose
- [x] Изучена структура Docker (client_zero стек)

#### 2. Workflows - Fixes
- [x] **1_Webhook**: Добавлена дедупликация через Redis (GET/SET messageId, TTL 24h)
- [x] **2_Parse/ChannelRouter**: 
  - Интегрирован CheckUser
  - Добавлен SaveInboundMessage (PostgreSQL Insert)
  - Исправлен Channel Switch (выражение `$('NormalizeEvent').item.json.event.channel`)
  - Исправлен тип поля `event` в Combine User + Event (string → object)
- [x] **3_WhatsApp Adapter**: Добавлен SaveOutboundMessage перед Send WhatsApp

#### 3. База данных
- [x] Проверена структура таблиц в `truffles-chat-bot`:
  - users (UUID id, phone, remote_jid, name, etc.)
  - messages (user_id FK, role, content, intent, channel)
  - prompts, handovers, faq_items, scoring_rules, lead_scores

#### 4. Документация
- [x] Создан CHATBOT_ARCHITECTURE.md
- [x] Создан WORK_LOG.md (этот файл)

### В процессе:

#### Audio обработка (4_NormalizeWhatsapp)
- Проблема: Code нода неправильно проверяет audio
- Решение: Исправить `ev.attachments.mimetype` → `ev.attachments[0]?.mimetype`
- Статус: Код готов, ждёт применения

### Предстоит:

#### Высокий приоритет
1. **Intent Classifier** - создать отдельный workflow 5_ClassifyIntent
2. **Упростить Sales Orchestrator** - разбить на модули
3. **RAG routing по intent** - вопросы → RAG, жалобы → handover

#### Средний приоритет
4. Prompts из БД (не хардкод в workflows)
5. Проверить Redis Chat Memory
6. Конфигурируемые настройки (API keys, модели)

#### Низкий приоритет
7. Telegram Adapter
8. Instagram Adapter
9. Обработка документов/фото
10. Kaspi Pay интеграция

---

## Технические заметки

### Credentials (n8n)
- `Local` (postgres) → подключен к `truffles-chat-bot`
- `Trading DB` → НЕ использовать для chatbot
- `QdrantLocal` → Qdrant с API key
- `OpenAi account` → GPT-4.1-mini, Whisper
- `ElevenLabs account` → STT (Eleven v3)
- `CohereApi account` → Reranker

### Qdrant
- Collection: `truffles_knowledge`
- API Key: в .env (QDRANT__SERVICE__API_KEY)
- Доступ через docker network: `172.22.0.2:6333`

### Redis
- Используется для:
  - Дедупликации сообщений (messageId, TTL 24h)
  - Chat Memory (session_id → history)
  - (Future) Message queue buffer

### Важные ID workflows
- 1_Webhook: `VhlJJVJ2VOcySALy`
- 2_Parse/ChannelRouter: `EbIsyt4wKVyij9Hl`
- 2_1_CheckUser: `e94jQCRIneXDLZfe`
- 3_WhatsApp Adapter: `YvEadsCd8Rg5yxu8`
- 4_NormalizeWhatsapp: `58WFmPNitSNIwbes`
- cronUpdateDocs: `WYTuwxwHUxwdzsSQ`
- Global Error Handler: `fx8FvRvPuWjrtw6E`

---

## Проблемы и решения

### Проблема 1: Event как строка
**Симптом:** `$json.event.channel` возвращает undefined
**Причина:** В Edit Fields тип поля `event` был `string` вместо `object`
**Решение:** Изменить тип на `object`

### Проблема 2: Channel Switch не работает после CheckUser
**Симптом:** Switch не находит channel
**Причина:** CheckUser возвращает только user data, теряя event
**Решение:** Использовать `$('NormalizeEvent').item.json.event.channel`

### Проблема 3: Audio не обрабатывается
**Симптом:** Аудио сообщения игнорируются
**Причина:** Неправильная проверка `ev.attachments.mimetype` (массив, не объект)
**Решение:** `ev.attachments[0]?.mimetype`

