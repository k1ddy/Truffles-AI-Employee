# БЫСТРЫЙ СПРАВОЧНИК

**Цель:** Быстро найти что нужно, не читая всё

---

## ЕСЛИ ЧТО-ТО СЛОМАЛОСЬ

### 1. Эскалация не создаётся
```bash
# Проверить Multi-Agent
python3 get_multiagent_exec.py

# Что смотреть:
# - Is Deadlock выполнился?
# - Prepare Escalation Data выполнился?
# - Call Escalation Handler выполнился?
```

### 2. Кнопка [Беру] не работает
```bash
# Проверить Callback
python3 find_take_exec.py

# Что смотреть:
# - action = "take"?
# - Take Handover выполнился?
# - status = success?
```

### 3. Кнопка [Решено] не работает
```bash
# Проверить Callback
python3 check_resolve_error_new.py

# Типичные ошибки:
# - "Take Response not executed" → разделить ветки
# - "undefined" → проверить источник данных
```

### 4. Бот не отвечает после [Решено]
```bash
# Проверить состояние conversation
docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c \
  "SELECT bot_status, no_count, bot_muted_until FROM conversations WHERE id = 'UUID';"

# Если bot_status='muted' или no_count > 0 → Unmute Bot не сработал
```

### 5. Сообщения не доходят до менеджера
```bash
# Проверить Telegram Adapter
python3 check_adapter_exec.py

# Что смотреть:
# - Send Escalation выполнился?
# - HTTP response 200?
```

### 6. Ответ менеджера не доходит до клиента
```bash
# Проверить что callback получен
python3 get_latest_exec.py

# Проверить Send Manager Reply to WhatsApp
# HTTP response?
```

---

## КОМАНДЫ

### SSH
```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234
cd ~/truffles/ops
```

### Диагностика
```bash
python3 diagnose.py                    # Общий статус
python3 get_latest_exec.py             # Последний execution
python3 get_exec_detail.py EXEC_ID     # Детали execution
python3 get_multiagent_exec.py         # Multi-Agent execution
python3 check_callback_flow.py         # Структура Callback
python3 debug_client.py 77015705555    # История по телефону
```

### База данных
```bash
# Подключиться
docker exec -it truffles_postgres_1 psql -U n8n -d chatbot

# Или одной командой
docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT ..."
```

### SQL запросы

```sql
-- Все conversations
SELECT id, bot_status, no_count, telegram_topic_id FROM conversations;

-- Все handovers
SELECT id, status, assigned_to_name, conversation_id FROM handovers;

-- Состояние клиента
SELECT c.id, c.bot_status, c.no_count, c.bot_muted_until, u.phone
FROM conversations c
JOIN users u ON c.user_id = u.id
WHERE u.phone = '77015705555';

-- Сбросить для теста
UPDATE conversations SET bot_status='active', no_count=0, bot_muted_until=NULL;
DELETE FROM handovers;
```

### Сброс для чистого теста
```bash
docker exec -i truffles_postgres_1 psql -U n8n -d chatbot < ~/truffles/ops/clean_reset.sql
```

---

## WORKFLOW IDs

| Название | ID | Файл |
|----------|-----|------|
| 1_Webhook | 656fmXR6GPZrJbxm | workflow/1_Webhook_656fmXR6GPZrJbxm.json |
| 2_ChannelAdapter | C38zCf2jfc2Zqfzf | workflow/2_ChannelAdapter_C38zCf2jfc2Zqfzf.json |
| 3_Normalize | DCs6AoJDIOPB4ZtF | workflow/3_Normalize_DCs6AoJDIOPB4ZtF.json |
| 4_MessageBuffer | 3QqFRxapNa29jODD | workflow/4_MessageBuffer_3QqFRxapNa29jODD.json |
| 5_TurnDetector | kEXEMbThwUsCJ2Cz | workflow/5_TurnDetector_kEXEMbThwUsCJ2Cz.json |
| **6_Multi-Agent** | **4vaEvzlaMrgovhNz** | workflow/6_Multi-Agent_4vaEvzlaMrgovhNz.json |
| **7_Escalation_Handler** | **7jGZrdbaAAvtTnQX** | workflow/7_Escalation_Handler.json |
| **8_Telegram_Adapter** | **fFPEbTNlkBSjo66A** | workflow/8_Telegram_Adapter.json |
| **9_Telegram_Callback** | **HQOWuMDIBPphC86v** | workflow/9_Telegram_Callback.json |

---

## ТАБЛИЦЫ БД

| Таблица | Ключевые поля | Назначение |
|---------|---------------|------------|
| clients | id, name, config | Клиенты (компании) |
| client_settings | client_id, telegram_chat_id, telegram_bot_token | Настройки |
| users | id, client_id, phone | Пользователи (клиенты компаний) |
| conversations | id, user_id, bot_status, no_count, telegram_topic_id | Диалоги |
| handovers | id, conversation_id, status, assigned_to | Эскалации |
| messages | id, conversation_id, content | Сообщения |

---

## СТАТУСЫ

### conversation.bot_status
| Значение | Что значит |
|----------|------------|
| active | Бот отвечает |
| muted | Бот молчит (до bot_muted_until) |

### handover.status
| Значение | Что значит |
|----------|------------|
| pending | Ждёт менеджера (кнопка [Беру]) |
| active | Менеджер взял (кнопка [Решено ✅]) |
| resolved | Закрыто |

---

## TELEGRAM

### Группы
| Клиент | Chat ID | Forum mode |
|--------|---------|------------|
| demo_salon | -1003412216010 | Да |

### Боты
| Клиент | Token |
|--------|-------|
| demo_salon | 8249719610:AAGdyGmYTM9xnD5NojlsrIA36tbDcZFnpNk |

### Callback data формат
```
take_UUID     → action="take", handover_id="UUID"
resolve_UUID  → action="resolve", handover_id="UUID"
done          → игнорируется (кнопка уже нажата)
```

---

## ТИПИЧНЫЕ ОШИБКИ И ФИКСЫ

| Симптом | Причина | Фикс |
|---------|---------|------|
| undefined в поле | $json берёт данные не из той ноды | Использовать $('NodeName').first().json |
| Нода не выполняется | Не подключена к flow | Проверить connections в n8n UI |
| SQL с undefined | Предыдущая нода не вернула данные | Проверить output предыдущей ноды |
| "Node X not executed" | Нода в другой ветке IF | Разделить ветки полностью |
| Кнопка не исчезает | inline_keyboard не пустой | Использовать {inline_keyboard: []} |
| Повторная эскалация не работает | no_count не сброшен | Добавить no_count=0 в Unmute Bot |

---

## ДОСТУПЫ

### SSH
```
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234
```

### n8n API
```
URL: https://n8n.truffles.kz
API Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4
```

### PostgreSQL
```
Host: postgres (внутри Docker)
DB: chatbot
User: n8n
Password: Iddqd777!
```

### Chatflow
```
Token: a29b2ad2-9485-476c-897d-34799c3f940b
API: https://api.chatflow.me/v1/messages/text/{instance_id}
```

---

## ФАЙЛЫ В РЕПОЗИТОРИИ

```
docs/
├── HANDOVER_2025_12_08.md      ← Полная эстафета
├── POST_MORTEM_2025_12_08.md   ← Анализ ошибок
├── WORKFLOWS_DETAILED.md       ← Детали каждой ноды
├── QUICK_REFERENCE.md          ← Этот файл

ops/
├── diagnose.py                 ← Быстрая диагностика
├── get_latest_exec.py          ← Последний execution
├── get_exec_detail.py          ← Детали execution
├── clean_reset.sql             ← Сброс для теста
├── migrations/                 ← SQL миграции

workflow/
├── 6_Multi-Agent_*.json        ← Главный workflow
├── 7_Escalation_Handler.json   ← Эскалация
├── 8_Telegram_Adapter.json     ← Telegram отправка
├── 9_Telegram_Callback.json    ← Telegram callback
```

---

*Обновлено: 2025-12-08*
