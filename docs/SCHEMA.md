# SCHEMA.md

Структура базы данных Truffles.

**Дата обновления:** 2024-12-09

---

## Ключевые таблицы

### users
Клиенты (конечные пользователи WhatsApp).

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| client_id | uuid | FK → clients |
| phone | text | Номер телефона |
| remote_jid | text | WhatsApp JID (77015705555@s.whatsapp.net) |
| name | text | Имя (если известно) |
| metadata | jsonb | Дополнительные данные |
| created_at | timestamptz | Дата создания |
| last_active_at | timestamptz | Последняя активность |
| telegram_topic_id | bigint | ID топика в Telegram |

### conversations
Диалоги между user и ботом.

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| client_id | uuid | FK → clients |
| user_id | uuid | FK → users |
| channel | text | Канал (whatsapp) |
| status | text | Статус диалога |
| started_at | timestamptz | Начало диалога (НЕ created_at!) |
| last_message_at | timestamptz | Последнее сообщение |
| bot_status | text | 'active' / 'muted' |
| bot_muted_until | timestamptz | До когда бот молчит |
| telegram_topic_id | bigint | ID топика |
| no_count | integer | Счётчик "нет" от клиента |

### messages
История сообщений.

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| conversation_id | uuid | FK → conversations |
| client_id | uuid | FK → clients |
| role | text | 'user', 'assistant', 'manager', 'system' |
| content | text | Текст сообщения |
| intent | text | Определённый intent |
| confidence | numeric | Уверенность классификатора |
| metadata | jsonb | message_id, event и т.д. |
| created_at | timestamptz | Время создания |

### handovers
Заявки на эскалацию к менеджеру.

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| conversation_id | uuid | FK → conversations |
| client_id | uuid | FK → clients |
| status | text | 'pending', 'active', 'resolved', 'bot_handling', 'timeout' |
| trigger_type | text | 'intent', 'keyword', 'manual', 'timeout' |
| assigned_to_name | text | Имя менеджера |
| created_at | timestamptz | Время создания |
| first_response_at | timestamptz | Первый ответ менеджера |
| resolved_at | timestamptz | Время закрытия |
| telegram_message_id | bigint | ID сообщения в Telegram |
| reminder_1_sent_at | timestamptz | Время первого напоминания |
| reminder_2_sent_at | timestamptz | Время второго напоминания |

**Статусы handover:**
- `pending` — создана, ждёт [Беру]
- `active` — взята менеджером
- `resolved` — решена (кнопка [Решено])
- `bot_handling` — возвращена боту (кнопка [Вернуть боту])
- `timeout` — автозакрыта по таймауту

### client_settings
Настройки для каждого заказчика.

| Колонка | Тип | Default | Описание |
|---------|-----|---------|----------|
| client_id | uuid | - | FK → clients |
| telegram_chat_id | text | - | ID группы Telegram |
| telegram_bot_token | text | - | Токен бота |
| reminder_timeout_1 | integer | 30 | Минут до первого напоминания |
| reminder_timeout_2 | integer | 60 | Минут до второго (срочного) |
| auto_close_timeout | integer | 120 | Минут до автозакрытия |
| owner_telegram_id | text | - | Username руководителя для тега |
| escalation_cooldown_minutes | integer | 30 | Cooldown между эскалациями |

### clients
Заказчики (B2B клиенты Truffles).

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| name | text | Название компании |
| status | text | Статус подписки |
| config | jsonb | instance_id и др. |

### prompts
Промпты для LLM.

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | uuid | PK |
| client_id | uuid | FK (null = глобальный) |
| name | text | Название ('system_prompt', 'classifier') |
| text | text | Текст промпта |
| is_active | boolean | Активен ли |

---

## Связи

```
clients (1) ──< users (N)
clients (1) ──< conversations (N)
clients (1) ──< client_settings (1)
users (1) ──< conversations (N)
conversations (1) ──< messages (N)
conversations (1) ──< handovers (N)
```

---

## CHECK constraints

**handovers.status:**
```sql
CHECK (status IN ('pending', 'active', 'resolved', 'bot_handling', 'timeout'))
```

**handovers.trigger_type:**
```sql
CHECK (trigger_type IN ('intent', 'keyword', 'manual', 'timeout'))
```
