# OPS — Инструменты диагностики и управления

## ВАЖНО: Windows PowerShell

**Проблема:** PowerShell не понимает кавычки и спецсимволы как bash.

**Решение:** Всегда использовать SQL/Python файлы, НЕ inline команды.

```bash
# НЕПРАВИЛЬНО (ломается в PowerShell):
ssh ... "psql -c \"SELECT * FROM table;\""

# ПРАВИЛЬНО:
ssh ... "psql < ~/truffles/ops/query.sql"
```

---

## ДОСТУПЫ

### SSH
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234
```

### n8n API
```
URL: https://n8n.truffles.kz
API Key: <REDACTED>_JWT
```

### PostgreSQL
```
Container: truffles_postgres_1
DB: chatbot
User: n8n
Password: REDACTED_PASSWORD
```

### Qdrant
```
Container: truffles_qdrant_1
IP: 172.24.0.3 (внутренний)
Port: 6333
API Key: <REDACTED>_PASSWORD
Collection: truffles_knowledge
```

### Telegram Bots
```
TrufflesChatBot: REDACTED_TELEGRAM_BOT_TOKEN
DemoSalonBot: REDACTED_TELEGRAM_BOT_TOKEN
```

---

## СКРИПТЫ

### База данных

| Файл | Назначение | Использование |
|------|------------|---------------|
| `check_settings.sql` | Посмотреть client_settings | `psql < check_settings.sql` |
| `check_handovers.sql` | Посмотреть handovers | `psql < check_handovers.sql` |
| `reset_muted.sql` | Сбросить bot_status всех | `psql < reset_muted.sql` |
| `reset_handover.sql` | Сбросить конкретный handover | `psql < reset_handover.sql` |

**Как выполнить SQL:**
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec -i truffles_postgres_1 psql -U n8n -d chatbot < ~/truffles/ops/ФАЙЛ.sql"
```

### n8n Workflows

| Файл | Назначение | Использование |
|------|------------|---------------|
| `create_workflow.py` | Создать workflow в n8n | `python3 create_workflow.py FILE.json` |
| `get_latest_exec.py` | Последняя execution workflow | `python3 get_latest_exec.py` |
| `get_exec_detail.py` | Детали execution | `python3 get_exec_detail.py EXEC_ID` |
| `check_callback_exec.py` | Executions callback workflow | `python3 check_callback_exec.py` |

**Как выполнить Python:**
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "python3 ~/truffles/ops/ФАЙЛ.py"
```

### Диагностика workflows

| Файл | Назначение |
|------|------------|
| `check_workflow.py` | Показать nodes и credentials workflow |
| `check_connections.py` | Показать connections между nodes |
| `check_connections2.py` | Детальные connections + webhook node |

### Фиксы

| Файл | Что исправляет |
|------|----------------|
| `fix_buffer_key.py` | MessageBuffer — добавляет client_slug в ключ |
| `fix_is_deadlock_connection.py` | Подключает Is Deadlock в flow |
| `fix_callback_parse.py` | Parse Callback — правильный split UUID |
| `fix_callback_complete.py` | Полный фикс callback (topic_id, buttons) |
| `fix_call_escalation.py` | Prepare Escalation Data node |
| `update_escalation_to_adapter.py` | Escalation Handler → Telegram Adapter |

---

## ЧАСТЫЕ ОПЕРАЦИИ

### 1. Посмотреть последние executions workflow
```bash
# Скопировать скрипт
scp -i C:\Users\user\.ssh\id_rsa -P 222 "C:\Users\user\Documents\Truffles-AI-Employee\ops\get_latest_exec.py" zhan@5.188.241.234:~/truffles/ops/

# Выполнить
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "python3 ~/truffles/ops/get_latest_exec.py"
```

### 2. Сбросить muted status
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec -i truffles_postgres_1 psql -U n8n -d chatbot < ~/truffles/ops/reset_muted.sql"
```

### 3. Скачать workflow из n8n
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s -H 'X-N8N-API-KEY: API_KEY' 'https://n8n.truffles.kz/api/v1/workflows/WORKFLOW_ID' > /tmp/workflow.json"
```

### 4. Посмотреть Qdrant коллекции
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: <REDACTED>_PASSWORD' 'http://172.24.0.3:6333/collections'"
```

### 5. Настроить Telegram webhook
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s 'https://api.telegram.org/botTOKEN/setWebhook?url=https://n8n.truffles.kz/webhook/telegram-callback'"
```

### 6. Проверить Telegram webhook
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s 'https://api.telegram.org/botTOKEN/getWebhookInfo'"
```

---

## WORKFLOW IDs

| Workflow | ID | Назначение |
|----------|-----|------------|
| 6_Multi-Agent | 4vaEvzlaMrgovhNz | Основной обработчик сообщений |
| 7_Escalation_Handler | 7jGZrdbaAAvtTnQX | Логика эскалаций |
| 8_Telegram_Adapter | fFPEbTNlkBSjo66A | Создание топиков, отправка в Telegram |
| 9_Telegram_Callback | HQOWuMDIBPphC86v | Обработка кнопок [Беру] [Решено] |

---

## МИГРАЦИИ

| Файл | Что добавляет |
|------|---------------|
| `001_add_settings_and_escalations.sql` | Начальная структура |
| `003_add_escalation_reason.sql` | escalation_reason в handovers |
| `004_add_telegram_token.sql` | telegram_bot_token в client_settings |
| `005_insert_demo_salon_settings.sql` | Настройки demo_salon |
| `006_handover_messages.sql` | messages JSONB, channel, channel_ref |
| `007_handover_assigned.sql` | assigned_to, assigned_to_name, resolved_at |

---

## АРХИТЕКТУРА ТАБЛИЦ

```
clients
├── id (UUID)
├── name
└── config (JSONB)

client_settings
├── client_id (FK)
├── telegram_bot_token
├── telegram_chat_id
└── ... (настройки)

users
├── id (UUID)
├── phone
├── name
└── telegram_topic_id

conversations
├── id (UUID)
├── client_id
├── user_id
├── bot_status (active/muted)
├── no_count
└── bot_muted_until

handovers
├── id (UUID)
├── conversation_id
├── status (pending/active/resolved)
├── escalation_reason
├── assigned_to
├── assigned_to_name
├── messages (JSONB)
├── channel (telegram/crm)
├── channel_ref (topic_id)
└── telegram_message_id
```

---

## ТИПИЧНЫЕ ОШИБКИ

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `column X does not exist` | Не выполнена миграция | Выполнить нужную миграцию |
| `Bad request` в Telegram | Неправильный chat_id или token | Проверить БД client_settings |
| Workflow execution пустой | Webhook не активен | Активировать workflow в n8n UI |
| Windows escaping errors | PowerShell не понимает кавычки | Использовать файлы вместо inline |

---

## КОПИРОВАНИЕ ФАЙЛОВ

```bash
# Локально → Сервер
scp -i C:\Users\user\.ssh\id_rsa -P 222 "C:\Users\user\Documents\Truffles-AI-Employee\ops\FILE" zhan@5.188.241.234:~/truffles/ops/

# Сервер → Локально  
scp -i C:\Users\user\.ssh\id_rsa -P 222 zhan@5.188.241.234:~/truffles/ops/FILE "C:\Users\user\Documents\Truffles-AI-Employee\ops\"
```
