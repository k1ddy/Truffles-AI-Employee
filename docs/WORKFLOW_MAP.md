# WORKFLOW_MAP.md

Карта workflows в n8n.

**Дата обновления:** 2024-12-09

---

## Активные workflows

| ID | Название | Назначение |
|----|----------|------------|
| 656fmXR6... | 1_Webhook | Входная точка WhatsApp |
| HQOWuMDI... | 9_Telegram_Callback | Кнопки и сообщения менеджеров |
| ZRcuYYCv... | 10_Handover_Monitor | Напоминания и автозакрытие (cron 5 мин) |
| zTbaCLWL... | Knowledge Sync | Синхронизация базы знаний |

**Inactive но используемые через Execute Workflow:**
- 6_Multi-Agent — основная логика бота
- 7_Escalation_Handler — создание эскалаций
- 8_Telegram_Adapter — отправка в Telegram

---

## Основной flow сообщения

```
WhatsApp → 1_Webhook → 2_ChannelAdapter → 3_Normalize → 4_MessageBuffer → 5_TurnDetector → 6_Multi-Agent
```

### 6_Multi-Agent — главный workflow

**Входные данные:**
```json
{
  "channel": "whatsapp",
  "user_id": "77015705555",
  "session_id": "77015705555@s.whatsapp.net",
  "buffered_messages": [{"text": "..."}]
}
```

**Flow:**
```
Start → Parse Input → Intent Router → Check Handover Early → Handover Active Early?
                                                              ├→ [yes] Forward to Topic Early → Exit
                                                              └→ [no] Pass Input → Skip Classifier?
                                                                                    ├→ [0] Upsert User → ... → Generate Response
                                                                                    └→ [1] Classify Intent → Is On Topic?
                                                                                                              ├→ [yes] Upsert User
                                                                                                              └→ [no] Build Off-Topic → Send Off-Topic
```

**Ключевые ноды:**
- `Check Handover Early` — проверяет есть ли активный handover ДО классификации
- `Build Context` — собирает историю, summary, intent
- `Check Active Handover` — вторая проверка после Build Context
- `Generate Response` — LLM генерация ответа
- `Check Escalation` — решает нужна ли эскалация
- `Forward to Topic` — пересылка сообщения менеджеру

---

## 9_Telegram_Callback — обработка кнопок

**Триггер:** Webhook от Telegram

**Action Switch (по $json.action):**

| Index | Action | Следующая нода | Что делает |
|-------|--------|----------------|------------|
| 0 | take | Take Handover | [Беру] — взять заявку |
| 1 | resolve | Resolve Handover | [Решено] — закрыть заявку |
| 2 | skip | Skip Response | [Не могу] — пропустить |
| 3 | return | Return Handover | [Вернуть боту] |
| 4 | answered | Answered Response | [Ответил ✓] — отметить |
| 5 | snooze | Snooze Handover | [+30 мин] — отложить |

**Flow [Беру]:**
```
Take Handover (UPDATE status='active') → Take Response → Answer Callback → Update Buttons
```

**Flow [Решено]:**
```
Resolve Handover (UPDATE status='resolved') → Unmute Bot → Save Resolved to History → Resolve Response → Remove Buttons → Unpin Escalation → Answer Callback
```

**Flow [Вернуть боту]:**
```
Return Handover (UPDATE status='bot_handling') → Unmute Bot Return → Return Response → Answer Callback → Update Buttons Return
```

**Flow сообщения менеджера:**
```
Parse Message → Find Handover Data → Has Active Handover? → Send Manager Reply to WhatsApp → Save Manager Message → Save Manager to History → Confirm Sent to Topic
```

---

## 10_Handover_Monitor — автонапоминания

**Триггер:** Schedule каждые 5 минут

**Flow:**
```
Load Active Handovers (status IN pending, active) → Decide Action → Action Switch
                                                                     ├→ [reminder_1] Send Reminder 1 → Mark Sent
                                                                     ├→ [reminder_2] Send Reminder 2 → Mark Sent
                                                                     └→ [auto_close] Close Handover → Unmute Bot → Notify Client → Notify Topic
```

**Таймауты (из client_settings):**
- `reminder_timeout_1` (30 мин) — первое напоминание с кнопками
- `reminder_timeout_2` (60 мин) — "🔴 СРОЧНО" + тег руководителя
- `auto_close_timeout` (120 мин) — автозакрытие

**Кнопки в напоминании:**
- [Ответил ✓] — callback `answered_{handover_id}`
- [Закрыть] — callback `resolve_{handover_id}`
- [+30 мин] — callback `snooze_{handover_id}`

---

## 7_Escalation_Handler — создание эскалации

**Вызывается из:** 6_Multi-Agent (Execute Workflow)

**Flow:**
```
Start → Load Status → Decide Action → Should Process? → Update Conversation → Create Handover → Save Escalation to History → Has Telegram? → Call Telegram Adapter
```

**Создаёт:**
- handover со статусом 'pending'
- Сообщение в Telegram с кнопкой [Беру]
- Закрепление (pin) сообщения

---

## Credential IDs

| Название | ID | Использование |
|----------|-----|---------------|
| ChatbotDB | SUHrbh39Ig0fBusT | PostgreSQL |
