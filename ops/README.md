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

```powershell
# Локально
.\ops\smoke_local.ps1

# На прод
.\ops\smoke_local.ps1 -BaseUrl "https://api.truffles.kz"
```
     
---

## ДОСТУПЫ

**Секреты не храним в git.** Используй env переменные (`QDRANT_API_KEY`, `DB_PASSWORD`, Telegram bot tokens).

### SSH
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234
```

### PostgreSQL
```
Container: truffles_postgres_1
DB: chatbot
User: ${DB_USER}
Password: ${DB_PASSWORD}
```

### Qdrant
```
Container: truffles_qdrant_1
IP: 172.24.0.3 (внутренний)
Port: 6333
API Key: ${QDRANT_API_KEY}
Collection: truffles_knowledge
```

### Telegram Bots
```
TrufflesChatBot: токен в секретах (не в git)
DemoSalonBot: токен в секретах (не в git)
```

---

## СКРИПТЫ

### База данных

| Файл | Назначение | Использование |
|------|------------|---------------|
| `reset.sql` | **Emergency:** закрыть все open handovers + вернуть `bot_active` | `psql < reset.sql` |
| `update_instance_demo.sql` | Обновить instance_id для demo_salon | `psql < update_instance_demo.sql` |
| `update_truffles_prompt.sql` | Обновить промпт truffles (SQL) | `psql < update_truffles_prompt.sql` |

**Как выполнить SQL:**
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/ФАЙЛ.sql"
```

---

## ЧАСТЫЕ ОПЕРАЦИИ

### 1. Сбросить muted status
```bash
 # Файл лежит на сервере: ~/truffles-main/ops/reset_muted.sql
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/reset_muted.sql"
```

### 2. Посмотреть Qdrant коллекции
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: ${QDRANT_API_KEY}' 'http://172.24.0.3:6333/collections'"
```

### 3. Настроить Telegram webhook
API принимает путь `/telegram-webhook` (прямо в FastAPI).
```bash
# FastAPI напрямую
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s \"https://api.telegram.org/botTOKEN/setWebhook?url=https://api.truffles.kz/telegram-webhook\""
```

### 4. Проверить Telegram webhook
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s \"https://api.telegram.org/botTOKEN/getWebhookInfo\""
```

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
| Webhook execution пустой | Webhook не активен | Проверить входящий webhook в ChatFlow |
| Windows escaping errors | PowerShell не понимает кавычки | Использовать файлы вместо inline |

---

## КОПИРОВАНИЕ ФАЙЛОВ

```bash
# Локально → Сервер
scp -i C:\Users\user\.ssh\id_rsa -P 222 "C:\Users\user\Documents\Truffles-AI-Employee\ops\FILE" zhan@5.188.241.234:~/truffles-main/ops/

# Сервер → Локально  
scp -i C:\Users\user\.ssh\id_rsa -P 222 zhan@5.188.241.234:~/truffles-main/ops/FILE "C:\Users\user\Documents\Truffles-AI-Employee\ops\"
```
