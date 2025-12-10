# CHANGELOG — История изменений

---

## 2025-12-10

### Напоминания
- Добавлены настройки в client_settings: enable_reminders, enable_owner_escalation, mute_duration_first_minutes, mute_duration_second_hours
- Cron job: каждую минуту POST /reminders/process
- owner_telegram_id = @ent3rprise для клиента truffles

### Документация
- Создан TECH.md с проверенными данными (контейнеры, БД, команды)
- Старые docs перемещены в .archive/docs_old/
- Создан ROADMAP.md с планами
- Реструктуризация: AGENTS + TECH + ROADMAP + CHANGELOG

### Git
- Репозиторий: github.com/k1ddy/Truffles-AI-Employee (private)
- Код truffles-api закоммичен

---

## 2025-12-09

### Python API (truffles-api)
- Полная реализация /webhook (входящие сообщения)
- Полная реализация /telegram-webhook (callbacks + сообщения менеджеров)
- Intent classification (7 интентов)
- Эскалация: создание топика, кнопки, pin
- take/resolve/skip обработка
- Forward to topic (сообщения клиента → менеджеру)
- Менеджер → клиент (Telegram → WhatsApp)
- Мьют логика (1й нет=30мин, 2й=24ч)
- State machine: bot_active/pending/manager_active
- 62 теста (pytest)

### Инфраструктура
- Telegram webhook переключен на Python (api.truffles.kz/telegram-webhook)
- n8n = только роутинг
