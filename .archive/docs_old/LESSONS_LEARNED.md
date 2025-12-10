# УРОКИ: Telegram Callback Workflow

**Дата:** 2025-12-08
**Время потрачено:** ~4 часа
**Должно было занять:** ~30 минут

---

## ПОЧЕМУ ТАК ДОЛГО

### 1. Не проверил данные ПЕРЕД написанием кода
**Ошибка:** Писал код не зная что реально приходит от Telegram.
**Решение:** ВСЕГДА сначала логировать входные данные.

```bash
# Перед любой работой с Telegram — проверить что приходит:
ssh ... "python3 ~/truffles/ops/get_latest_exec.py"
```

### 2. Неправильные ссылки на данные в n8n
**Ошибка:** Использовал `$json` вместо `$('Node Name').first().json`
**Проблема:** `$json` зависит от того что пришло на вход ТЕКУЩЕЙ ноды, не от предыдущих.

**Правило для n8n:**
```javascript
// НЕПРАВИЛЬНО (данные могут быть не те):
$json.field

// ПРАВИЛЬНО (явная ссылка на ноду):
$('Parse Callback').first().json.field
```

### 3. Не понимал flow данных в n8n
**Ошибка:** Думал что данные автоматически передаются через весь workflow.
**Реальность:** Каждая нода получает только output предыдущей подключённой ноды.

**Flow в нашем callback:**
```
Telegram Webhook → Parse Callback → Get Bot Token → Merge Token → Is Callback? → Action Switch
                                                                                      ↓
                                                            Take Handover → Take Response → Answer Callback → Update Buttons → Notify in Chat
```

**Данные в каждой ноде:**
- `Notify in Chat` получает output от `Update Buttons`, НЕ от `Take Response`
- Чтобы получить данные из `Take Response`, нужно явно: `$('Take Response').first().json`

### 4. Не проверял SQL перед выполнением
**Ошибка:** `clean_reset.sql` сбрасывал `telegram_topic_id` — создавались дубликаты топиков.
**Решение:** Читать SQL файлы перед запуском.

### 5. Windows PowerShell escaping
**Ошибка:** Тратил время на escaping кавычек в командах.
**Решение:** ВСЕГДА использовать файлы, не inline команды.

```bash
# НЕПРАВИЛЬНО:
ssh ... "psql -c \"SELECT * FROM table;\""

# ПРАВИЛЬНО:
ssh ... "psql < ~/file.sql"
```

---

## КАК УСКОРИТЬ В БУДУЩЕМ

### 1. Диагностика ПЕРЕД кодом (5 минут)
```bash
# 1. Последняя execution
ssh ... "python3 ~/truffles/ops/get_latest_exec.py"

# 2. Детали конкретной execution
ssh ... "python3 ~/truffles/ops/get_exec_detail.py EXEC_ID"

# 3. Проверить что в БД
ssh ... "psql < ~/truffles/ops/check_conversations_topic.sql"
```

### 2. Чеклист для n8n HTTP Request к Telegram
```
□ URL содержит правильный токен: $('Merge Token').first().json.bot_token
□ chat_id из правильной ноды
□ message_thread_id (topic_id) передаётся для Forum групп
□ text не пустой — проверить откуда берётся
□ reply_markup — JSON.stringify() для объектов
```

### 3. Чеклист для Telegram callback
```
□ Parse Callback извлекает: action, handover_id, chat_id, topic_id, message_id
□ topic_id = callback.message.message_thread_id
□ Для каждой ветки (take/resolve/skip) свой Response node
□ Update Buttons использует данные из Response node, не из $json
□ Notify in Chat ссылается на правильный Response node
```

### 4. Тестовый запрос перед workflow
```bash
# Проверить что Telegram API работает:
curl -X POST "https://api.telegram.org/bot{TOKEN}/sendMessage" \
  -d "chat_id={CHAT_ID}" \
  -d "message_thread_id={TOPIC_ID}" \
  -d "text=Test"
```

---

## АВТОМАТИЗАЦИЯ

### Скрипт для быстрой диагностики
Создан: `ops/diagnose.py`
```bash
# Одна команда — вся информация:
python3 ~/truffles/ops/diagnose.py
```

### Скрипт для проверки workflow перед деплоем
Создан: `ops/validate_workflow.py`
```bash
# Проверяет ссылки на ноды, наличие нужных полей:
python3 ~/truffles/ops/validate_workflow.py callback.json
```

---

## ЧАСТЫЕ ОШИБКИ TELEGRAM

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `message text is empty` | `$json.field` вместо `$('Node').first().json.field` | Исправить ссылку |
| `message thread not found` | Неправильный topic_id или топик удалён | Проверить topic_id в БД |
| `Bad request` | Неправильный формат параметров | Использовать bodyParameters вместо jsonBody |
| Кнопка не меняется | Update Buttons не в правильной ветке flow | Проверить connections |

---

## ПРАВИЛЬНЫЙ ПОРЯДОК РАБОТЫ

1. **Понять задачу** (2 мин)
2. **Проверить текущее состояние** (3 мин)
   - Последние executions
   - Данные в БД
3. **Написать код** (10 мин)
4. **Проверить перед деплоем** (2 мин)
   - Ссылки на ноды правильные?
   - SQL не ломает данные?
5. **Тест** (3 мин)
6. **Если ошибка — проверить execution детали** (2 мин)

**Итого: 20-25 минут вместо 4 часов**

---

## СОЗДАННЫЕ ИНСТРУМЕНТЫ

| Файл | Назначение |
|------|------------|
| `get_latest_exec.py` | Последняя execution callback workflow |
| `get_exec_detail.py` | Детали любой execution |
| `check_adapter_exec.py` | Executions Telegram Adapter |
| `dump_exec.py` | Полный dump execution данных |
| `check_notify_input.py` | Что приходит на вход Notify in Chat |
| `list_callback_execs.py` | Список callback executions с action |

---

## ВЫВОД

**Главная проблема:** Писал код не понимая как данные текут в n8n.

**Решение:** 
1. ВСЕГДА проверять execution детали ПЕРЕД написанием кода
2. Использовать явные ссылки `$('Node').first().json`
3. Не использовать `$json` — он непредсказуем
