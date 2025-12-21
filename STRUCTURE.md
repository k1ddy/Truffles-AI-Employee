# СТРУКТУРА ПРОЕКТА

**Карта: что где лежит, зачем нужно, кому читать.**

---

## КОРЕНЬ

| Файл | Назначение | Кому |
|------|------------|------|
| `STATE.md` | Состояние, план, backlog, история | Архитектор (каждую сессию) |
| `AGENTS.md` | Принципы работы, роли, ошибки | Архитектор (каждую сессию) |
| `STRUCTURE.md` | Этот файл — карта проекта | Оба (каждую сессию) |
| `HOW_TO_WORK.md` | Инструкция для Жанбола | Жанбол |
| `TECH.md` | Доступы, команды, данные сервера | Кодер |
| `SUMMARY.md` | Сводка текущей инвентаризации и GAP | Архитектор |
| `ops/reset.sql` | **Emergency:** закрыть все open handovers + вернуть `bot_active` | Кодер/OPS |

---

## SPECS/ — Спецификации (как должно работать)

| Файл | Содержание | Когда читать |
|------|------------|--------------|
| `ESCALATION.md` | Эскалация, напоминания, мьют, метрики | Работа с handovers, Telegram |
| `ACTIVE_LEARNING.md` | Автообучение на ответах менеджеров | Модерация, Qdrant |
| `CONSULTANT.md` | Поведение бота, 9 правил, границы | Промпт, LLM, ответы |
| `ARCHITECTURE.md` | Техническая архитектура, стек, потоки | Новые компоненты |
| `INFRASTRUCTURE.md` | Инфраструктура, безопасность, CI/CD, тесты | DevOps, качество |
| `MULTI_TENANT.md` | Мультитенантность, онбординг | Новый заказчик |
| `WEEK2_CODER_TASKS.md` | Задачи Недели 2 для кодера | Архив |
| `WEEK3_CODER_TASKS.md` | Задачи Недели 3 для кодера | Кодер: текущая неделя |

**Архитектор:** Читать перед проектированием.
**Кодер:** Читать раздел по задаче.

---

## STRATEGY/ — Стратегия (бизнес, продукт)

| Файл | Содержание | Когда читать |
|------|------------|--------------|
| `REQUIREMENTS.md` | Требования Жанбола (закон) | Архитектор: каждую сессию |
| `TECH_ROADMAP.md` | Технический план | Архитектор: планирование |
| `PRODUCT.md` | Тарифы, roadmap продукта | При вопросах о ценах |
| `MARKET.md` | Исследования, метрики, ниши | При вопросах о рынке |
| `VISION.md` | Видение продукта | Редко |

---

## docs/ — Контекст проекта

| Файл | Содержание |
|------|------------|
| `IMPERIUM_CONTEXT.yaml` | Единый контекст проекта (факты + evidence) |
| `IMPERIUM_DECISIONS.yaml` | CEO-level решения (policy) |
| `IMPERIUM_GAPS.yaml` | Критические пробелы и MVP фиксы |
| `SESSION_START_PROMPT.txt` | Стартовый промпт для новых сессий |

---

## truffles-api/ — Код (Python API)

```
truffles-api/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── routers/
│   │   ├── webhook.py           # POST /webhook/{client_slug} (direct), POST /webhook (n8n legacy) — входящие WhatsApp
│   │   ├── telegram_webhook.py  # POST /telegram-webhook — сообщения/кнопки менеджеров
│   │   ├── admin.py             # /admin/* (health/heal/prompt/settings/version)
│   │   ├── reminders.py         # /reminders/* — cron напоминаний
│   │   ├── callback.py          # /callback — (legacy/n8n)
│   │   └── message.py           # /message — legacy/manual, не основной путь
│   ├── services/
│   │   ├── ai_service.py            # LLM + RAG thresholds + guardrails
│   │   ├── alert_service.py         # Telegram alerts (errors/warnings)
│   │   ├── message_service.py        # save_message + generate_bot_response
│   │   ├── intent_service.py         # Классификация интентов
│   │   ├── knowledge_service.py      # Qdrant RAG поиск + embeddings
│   │   ├── state_machine.py          # ConversationState enum
│   │   ├── state_service.py          # Атомарные переходы + handover create/resolve
│   │   ├── escalation_service.py     # Telegram уведомления + кнопки
│   │   ├── manager_message_service.py# Ответ менеджера → клиент + auto-learning (owner)
│   │   ├── reminder_service.py       # Напоминания по open handovers
│   │   ├── health_service.py         # self-heal инвариантов
│   │   ├── telegram_service.py       # Telegram API wrapper
│   │   ├── chatflow_service.py       # Отправка сообщений в WhatsApp (ChatFlow)
│   │   └── learning_service.py       # Qdrant upsert по ответам owner
│   ├── models/              # SQLAlchemy модели
│   ├── schemas/             # Pydantic схемы
│   └── database.py          # Database connection
├── tests/                   # Pytest тесты
├── docker-compose.yml       # Локальный запуск (на проде НЕ используется)
└── requirements.txt         # Зависимости
```

**Кодер:** Основное место работы.

---

## knowledge/ — База знаний бота

| Файл | Содержание |
|------|------------|
| `faq.md` | Частые вопросы и ответы |
| `objections.md` | Возражения и ответы |
| `cases.md` | Кейсы успеха |
| `examples.md` | Примеры диалогов (как отвечать) |
| `slang.md` | Сленг СНГ (Kaspi, "ноготочки") |
| `README.md` | Описание формата |

**Используется:** RAG поиск, промпт.

---

## context/intents/ — Примеры интентов

16 файлов с примерами фраз для каждого интента:
- `pricing.txt` — "сколько стоит?"
- `human_request.txt` — "позовите менеджера"
- `complaint.txt` — "не работает"
- и т.д.

**Используется:** Intent classification.

---

## prompts/ — Промпты

| Файл | Назначение |
|------|------------|
| `system_prompt_v1.md` | Текущий системный промпт бота |
| `intent_classifier.md` | Промпт для классификации |
| `summarizer.md` | Промпт для суммаризации |

---

## ops/ — Операционные скрипты

**90% МУСОР** — одноразовые скрипты для n8n (старая архитектура).

**Полезное:**
| Файл | Назначение |
|------|------------|
| `monitor.sh` | Мониторинг сервера |
| `health_check.py` | Проверка здоровья системы |
| `onboard_client.py` | Онбординг нового заказчика |
| `update_prompt.py` | Обновление промпта через API |
| `migrations/` | SQL миграции |
| `templates/` | Шаблоны (промпты, FAQ) |
| `LESSONS_LEARNED.md` | Уроки из отладки |

Миграции:
- `ops/migrations/009_add_conversation_context.sql` — JSONB `conversations.context` для диалогового контекста/слотов.
- `ops/migrations/011_add_webhook_secret.sql` — `client_settings.webhook_secret` для защиты /webhook.

**Старые скрипты:** `.archive/ops_old/` — не в git.

---

## Business/ — Бизнес документы

| Папка | Содержание |
|-------|------------|
| `Legal/` | Договоры, NDA |
| `Sales/` | Бриф клиента, скрипты |

**Не для кода.**

---

## .archive/ — Архив

Старые документы, исследования. Не трогать, но можно смотреть для контекста.

---

## .factory/droids/ — Droid'ы

| Файл | Роль |
|------|------|
| `truffles-architect.md` | Архитектор — проектирует |
| `truffles-coder.md` | Кодер — реализует |
| `truffles-ops.md` | DevOps — инфраструктура |

---

## tests/ — Тесты

| Файл | Что тестирует |
|------|---------------|
| `test_cases.json` | Тестовые сценарии диалогов |

---

# НАЧАЛО СЕССИИ

## Архитектор (терминал 1)

```bash
droid --droid truffles-architect
```

**Читать:**
1. `STATE.md` — состояние, план, что дальше
2. `AGENTS.md` — принципы
3. `STRUCTURE.md` — где что лежит
4. `SPECS/*` — по необходимости

**Вопрос себе:** Что в плане? Что конкретно нужно сделать?

---

## Кодер (терминал 2)

```bash
droid --droid truffles-coder
```

**Читать:**
1. `STRUCTURE.md` — где код
2. `TECH.md` — команды, доступы
3. Задачу от архитектора

**Вопрос себе:** Понял ли я задачу? Какие файлы трогать?

---

## Жанбол

**Читать при необходимости:**
- `HOW_TO_WORK.md` — как работать с droid'ами
- `STATE.md` — что сейчас, какой план

---

# ГДЕ ИСКАТЬ ОТВЕТЫ

| Вопрос | Где искать |
|--------|------------|
| Как должна работать эскалация? | `SPECS/ESCALATION.md` |
| Какие тарифы? | `STRATEGY/PRODUCT.md` |
| Как подключить заказчика? | `SPECS/MULTI_TENANT.md` |
| Какие команды на сервере? | `TECH.md` |
| Как бот должен отвечать? | `SPECS/CONSULTANT.md`, `knowledge/examples.md` |
| Какие интенты есть? | `context/intents/` |
| Какой код за что отвечает? | `SPECS/ARCHITECTURE.md` |
| Что было сделано? | `CHANGELOG.md` |
| Требования Жанбола? | `STRATEGY/REQUIREMENTS.md` |
| Метрики, исследования? | `STRATEGY/MARKET.md` |

---

# МУСОР (можно удалить)

```
ops/check_*.py        # ~100 файлов — одноразовая отладка n8n
ops/fix_*.py          # ~50 файлов — одноразовые фиксы n8n
ops/add_*.py          # ~20 файлов — добавление нод в n8n
ops/get_*.py          # ~10 файлов — отладка n8n
ops/*.sql             # Большинство — одноразовые запросы
ops/*.sh              # Кроме monitor.sh — одноразовое
```

**Сохранить из ops/:**
- `monitor.sh`
- `health_check.py`
- `onboard_client.py`
- `migrations/`
- `templates/`
- `LESSONS_LEARNED.md`
- `README.md`

---

*Создано: 2025-12-10*
