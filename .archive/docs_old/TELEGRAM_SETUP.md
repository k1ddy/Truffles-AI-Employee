# TELEGRAM — ТЕКУЩАЯ НАСТРОЙКА

---

## РЕАЛЬНОЕ СОСТОЯНИЕ

### Группы

| Клиент | Группа | Chat ID | Forum mode | Бот |
|--------|--------|---------|------------|-----|
| truffles | Truffles Group | -1003362579990 | Да | @truffles_kz_bot |
| demo_salon | Salon Mira Demo | -1003412216010 | Да | @salon_mira_bot |

### Ссылки на группы
- truffles: https://t.me/+vOHPaH4hZyI3ZTIy
- demo_salon: https://t.me/+uhPSRE0lfm1mZmMy

**Каждый клиент = отдельная группа + отдельный бот.**

### Боты

| Клиент | Бот | Token | Webhook |
|--------|-----|-------|---------|
| truffles | @truffles_kz_bot | 8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4 | https://n8n.truffles.kz/webhook/telegram-callback |
| demo_salon | @salon_mira_bot | 8249719610:AAGdyGmYTM9xnD5NojlsrIA36tbDcZFnpNk | https://n8n.truffles.kz/webhook/telegram-callback |

**Webhook один на всех** — 9_Telegram_Callback определяет клиента по topic_id.

### Как работает

```
1. Эскалация создаётся
   ↓
2. 8_Telegram_Adapter получает telegram_bot_token из client_settings
   ↓
3. Создаёт топик в группе клиента (или использует существующий)
   ↓
4. Отправляет сообщение с кнопкой [Беру]
   ↓
5. Менеджер нажимает кнопку
   ↓
6. Telegram шлёт callback на webhook
   ↓
7. 9_Telegram_Callback определяет клиента по topic_id
   ↓
8. Загружает bot_token из БД
   ↓
9. Отвечает через правильного бота
```

---

## КАК ДОБАВИТЬ НОВОГО КЛИЕНТА В TELEGRAM

### 1. Создать бота
```
1. Открыть @BotFather в Telegram
2. /newbot
3. Имя: "ClientName Truffles Bot"
4. Username: clientname_truffles_bot
5. Получить token
```

### 2. Создать группу
```
1. Создать группу в Telegram
2. Включить Topics (Forum mode):
   - Настройки группы → Topics → Включить
3. Добавить бота как админа
4. Добавить Жанбола (куратор)
5. Добавить менеджеров клиента
```

### 3. Получить Chat ID
```bash
# После добавления бота, отправить сообщение в группу
# Затем:
curl "https://api.telegram.org/bot{TOKEN}/getUpdates"
# Найти chat.id (будет отрицательный, типа -1001234567890)
```

### 4. Настроить webhook
```bash
curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://n8n.truffles.kz/webhook/telegram-callback"
```

### 5. Добавить в БД
```sql
INSERT INTO client_settings (client_id, telegram_chat_id, telegram_bot_token)
SELECT id, '-100XXXXXXXXXX', 'BOT_TOKEN_HERE'
FROM clients WHERE name = 'new_client';
```

---

## ПЛАНЫ ПО TELEGRAM

### Из SPECS/ESCALATION.md:

1. **Кнопка [Вернуть боту]** — менеджер может вернуть диалог боту без полного закрытия
   - Статус: НЕ реализовано

2. **Цепочка эскалации** — primary manager → all managers → leadership
   - Статус: НЕ реализовано
   - Сейчас: сообщение идёт в общую группу, кто первый нажал [Беру]

3. **Таймауты с уведомлениями** — если менеджер не ответил за X минут, уведомить следующего
   - Статус: НЕ реализовано
   - Сейчас: только автоматический размьют бота через 30 мин

4. **Telegram-бот для Жанбола** — управление без SQL
   - Статус: НЕ реализовано
   - Команды: /status, /unmute, /close_handover

### Что НЕ планируется:

- Отдельные боты для каждого филиала (пока один бот на клиента)
- Интеграция с другими мессенджерами через Telegram

---

## WEBHOOK

### URL
```
https://n8n.truffles.kz/webhook/telegram-callback
```

### Что приходит (callback_query)
```json
{
  "update_id": 123456789,
  "callback_query": {
    "id": "1234567890",
    "from": {
      "id": 1969855532,
      "first_name": "Zh",
      "is_bot": false
    },
    "message": {
      "message_id": 65,
      "chat": {
        "id": -1003412216010,
        "type": "supergroup"
      },
      "message_thread_id": 15
    },
    "data": "take_uuid-uuid-uuid"
  }
}
```

### Что приходит (message от менеджера)
```json
{
  "update_id": 123456790,
  "message": {
    "message_id": 66,
    "from": {
      "id": 1969855532,
      "first_name": "Zh",
      "is_bot": false
    },
    "chat": {
      "id": -1003412216010,
      "type": "supergroup"
    },
    "message_thread_id": 15,
    "text": "Ответ менеджера клиенту"
  }
}
```

---

## ПРОВЕРКА

### Проверить webhook
```bash
curl "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
```

### Проверить что бот админ
```bash
curl "https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHAT_ID}&user_id={BOT_ID}"
```

### Отправить тестовое сообщение
```bash
curl -X POST "https://api.telegram.org/bot{TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "-1003412216010", "text": "Test"}'
```

---

*Создано: 2025-12-08*
