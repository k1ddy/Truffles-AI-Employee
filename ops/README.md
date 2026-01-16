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
| `metrics_daily_snapshot.sql` | Дневной снимок метрик (SLA/LLM/эскалации) | `psql -v client_slug=demo_salon -f metrics_daily_snapshot.sql` |

**Как выполнить SQL:**
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/ФАЙЛ.sql"
```

---

## ЧАСТЫЕ ОПЕРАЦИИ

### 0. Деплой с проверкой версии (обязателен в проде)
```bash
IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main \
PULL_IMAGE=1 REQUIRE_GHCR=1 VERIFY_VERSION=1 \
EXPECTED_GIT_COMMIT=<sha> EXPECTED_VERSION=main \
bash /home/zhan/restart_api.sh
```

Проверка вручную:
```bash
python3 ops/diagnose.py deploy-verify --base-url https://api.truffles.kz \
  --expected-commit <sha> --expected-version main
```

**DoD:** `/admin/version` возвращает `version != unknown` и `git_commit == <sha>`.  
**STOP:** если версия `unknown` или commit не совпадает.

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

### 5. Чек-лист instanceId (канонизация)
Канонический instanceId (demo_salon, подтверждён real inbound):
`eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6ImRlbW9zYWxvbiJ9`

Важно:
- Реальный inbound = WA‑сообщение от клиента → ChatFlow → `/webhook/{client_slug}`.
- ChatFlow `send-text` — outbound; inbound появляется только если получатель — ChatFlow‑инстанс (ChatFlow → ChatFlow).
- POST на `/webhook` — симуляция (использовать только если DoD разрешает).
- В БД поле называется `messages.metadata` (JSONB), не `message_metadata`.
- instanceId в webhook — это routing‑token (наш), provider instanceId ChatFlow не используется.

Шаги:
1) Проверить в ChatFlow URL (UI), что `instanceId=<CANONICAL>`:
   `https://api.truffles.kz/webhook/demo_salon?webhook_secret=...&instanceId=<CANONICAL>`
2) DB: `branches.instance_id` = canonical.
3) DB: inbound message metadata (после реального inbound от test JID).
4) DB: outbox payload по `message_id` из шага 3.

DoD: instanceId во всех источниках совпадает с canonical.

```sql
-- 2) branch_id -> instance_id
SELECT b.id AS branch_id, b.instance_id
FROM branches b
WHERE b.id = 'b7f75692-951e-421a-aae6-f5db97394799';

-- 3) Последнее входящее сообщение по test JID (real inbound)
SELECT m.id, m.created_at,
       m.metadata->>'messageId' AS message_id,
       m.metadata->>'instanceId' AS instance_id,
       m.metadata->>'remoteJid' AS remote_jid,
       c.id AS conversation_id,
       c.branch_id
FROM messages m
JOIN conversations c ON c.id = m.conversation_id
WHERE m.metadata->>'remoteJid' = '77015705555@s.whatsapp.net'
ORDER BY m.created_at DESC
LIMIT 1;

-- 4) outbox payload for this message_id
SELECT o.id, o.created_at,
       o.payload_json->'body'->'metadata'->>'instanceId' AS instance_id,
       o.payload_json->'body'->'metadata'->>'messageId' AS message_id
FROM outbox_messages o
WHERE o.payload_json->'body'->'metadata'->>'messageId' = '<message_id_from_step_3>'
LIMIT 1;
```

---

## Live-check runner (автоматизация)

**Цель:** автоматизированные live‑checks по CA‑плану с паузами/вариациями/опечатками.

**Запуск:**
```bash
CHATFLOW_TOKEN=... \
CHATFLOW_INSTANCE_ID=... \
CHATFLOW_JID=... \
python3 ops/diagnose.py livecheck --suite ca01-core --seed 42 --min-wait 5 --max-wait 15
```

Runner печатает JSON‑лог (marker, case_id, sent_at, expected_policy_section).  
Marker формат: `LC:<suite>:<case_id>:<timestamp>:<seq>`.

**Evidence (SQL):**
```sql
SELECT m.id, m.created_at, m.content,
       m.metadata->>'messageId' AS message_id,
       m.metadata->'decision_meta' AS decision_meta,
       c.id AS conversation_id
FROM messages m
JOIN conversations c ON c.id = m.conversation_id
WHERE m.role = 'user'
  AND m.content ILIKE '%LC:%'
ORDER BY m.created_at DESC
LIMIT 20;
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
| `column message_metadata does not exist` | В схеме используется `messages.metadata` | Использовать `m.metadata->>'...'` |
| `Bad request` в Telegram | Неправильный chat_id или token | Проверить БД client_settings |
| Webhook execution пустой | Webhook не активен | Проверить входящий webhook в ChatFlow |
| Windows escaping errors | PowerShell не понимает кавычки | Использовать файлы вместо inline |

---

## КОПИРОВАНИЕ ФАЙЛОВ

Код деплоится через CI/GHCR; SCP — только для разовых артефактов (логи/дампы).

```bash
# Локально → Сервер
scp -P 222 -i ~/.ssh/id_rsa /path/to/FILE zhan@5.188.241.234:/home/zhan/truffles-main/ops/

# Сервер → Локально  
scp -P 222 -i ~/.ssh/id_rsa zhan@5.188.241.234:/home/zhan/truffles-main/ops/FILE /path/to/target/
```
