# STATE — Состояние проекта

**Центральный хаб. Обновляется каждую сессию.**

---

## ТЕКУЩЕЕ СОСТОЯНИЕ

⚠️ Требует проверки: факты ниже нужно подтверждать через API/DB/логи, не полагаться на записи.

### БАЗОВЫЕ ФАКТЫ (читать первым делом)
- Входящие WhatsApp идут напрямую в API: `POST /webhook/{client_slug}` (direct ChatFlow). `POST /webhook` — legacy wrapper.
- `demo_salon` в ChatFlow направлен на `https://api.truffles.kz/webhook/demo_salon` + `webhook_secret` (секрет хранится в ChatFlow, не в git).
- `webhook_secret` всегда генерируем сами (не заказчик); хранится в ChatFlow/DB, не в git.
- `metadata.instanceId` отсутствует, если ChatFlow не передаёт. API принимает instanceId из query (`instanceId`/`instance_id`/`instance`), metadata или `nodeData`. Проверено: demo_salon после добавления query‑param — instanceId приходит, `conversation.branch_id` ставится.
- Outbox cron: `/etc/cron.d/truffles-outbox` → `/admin/outbox/process` раз в минуту.
- Outbox worker в API: фоновой цикл обрабатывает outbox каждые `OUTBOX_WORKER_INTERVAL_SECONDS` (дефолт 2s) при `OUTBOX_WORKER_ENABLED=1`; в pytest отключён.
- Outbox auto-heal: зависшие `PROCESSING` старше `OUTBOX_STALE_PROCESSING_SECONDS` возвращаются в `PENDING` или `FAILED` при исчерпании попыток.
- Деплой API: CI build/push → на проде `IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash /home/zhan/restart_api.sh` (локальная сборка — fallback; см. `TECH.md`).
- Инфра compose: `/home/zhan/infrastructure/docker-compose.yml` + `/home/zhan/infrastructure/docker-compose.truffles.yml`; `/home/zhan/truffles-main/docker-compose.yml` — заглушка.

### КЛЮЧЕВЫЕ МОЗГИ / РИСКИ / ПРОВЕРКИ (быстрый чек)
- Мозги: `outbox → _handle_webhook_payload → policy/truth → booking → intent → RAG/LLM`.
- Риски: payment/reschedule/medical/complaint — только эскалация; не озвучивать способы оплаты; branch‑gate для цен.
- Проверки качества: `EVAL.yaml` + `pytest truffles-api/tests/test_<client>_eval.py` + sync KB (`ops/sync_client.py`).
- Инструменты фактов: `docker logs truffles-api --tail 200`, SQL по `outbox_messages`/`handovers`.
- Фиксация: шаблон рассуждений + обновление `STATE.md` каждый раз.
- Детальный бриф салона заполнен эталоном (фейковые данные): `Business/Sales/Бриф_клиента.md`.
- Demo salon knowledge pack обновлён под эталон (truth/intents/eval + обзор услуг).

### ПОСЛЕДНЯЯ ПРОВЕРКА (prod, 2025-12-26)
- Preflight: truffles-api running, image `ghcr.io/k1ddy/truffles-ai-employee:main`.
- Env: `PUBLIC_BASE_URL=https://api.truffles.kz`, `MEDIA_SIGNING_SECRET=SET`, `MEDIA_URL_TTL_SECONDS=3600`, `MEDIA_CLEANUP_TTL_DAYS=7`, `CHATFLOW_MEDIA_TIMEOUT_SECONDS=90`.
- `/admin/version`: version `main`, git_commit `10ae71a58882efe4c2d4db6ff851fb1b2f5a7d82`, build_time `2025-12-25T12:24:15Z`.
- `/admin/health`: conversations bot_active 15, pending 0, manager_active 0; handovers pending 0, active 0 (checked_at `2025-12-26T02:05:32.178465+00:00`).
- DB (ops/diagnose): DB_USER `n8n`; conversations 15 total, 0 muted, 8 with topic; handovers 92 total, 0 pending, 0 active.

### MEDIA RUNBOOK (амнезия, 3–5 минут)
- Точка входа: `truffles-api/app/routers/webhook.py` → `_handle_webhook_payload()` + outbox coalesce.
- Guardrails: тип/размер/rate‑limit → `clients.config.media` (см. `SPECS/ARCHITECTURE.md`).
- Хранение: `/home/zhan/truffles-media/<client>/<conversation>/` + мета в `messages.metadata.media`.
- Forward: Telegram `sendPhoto/sendAudio/sendVoice/sendDocument` (см. `truffles-api/app/services/telegram_service.py`).
- Outbox: если в батче медиа — обработка по одному (иначе теряются вложения).
- Быстрые факты (SQL):
  `SELECT payload_json->'body'->>'messageType', payload_json->'body'->'mediaData' FROM outbox_messages ORDER BY created_at DESC LIMIT 1;`
  `SELECT metadata->'media' FROM messages ORDER BY created_at DESC LIMIT 1;`

### Что мешало быстрому входу (зафиксировано)
- Было несколько корней кода и часть ссылок указывала на несуществующие пути (`/home/zhan/truffles`, `/home/zhan/Truffles-AI-Employee`) → команды/доки расходились.
- Inbound payload для медиа: в коде добавлено сохранение + ответ, но на проде без деплоя всё ещё отбрасывается.
- В репо лежали workflow JSON и упоминания n8n → удалены, чтобы не вводить в заблуждение.
- Git worktree был сломан: `.git` указывал на несуществующий gitdir → восстановлено, commit/push работают.
- В спеках и ops были старые инструкции со scp по деплою → выровнено с CI/GHCR и `/home/zhan/restart_api.sh`.

### Что работает
- [x] Бот отвечает на сообщения WhatsApp
- [x] RAG поиск по базе знаний (Qdrant)
- [x] Классификация интентов
- [x] Эскалация в Telegram (кнопки Беру/Решено)
- [x] Ответ менеджера → клиенту
- [x] Напоминания (15 мин, 1 час) — cron
- [x] Мультитенант (truffles, demo_salon)

### Что не работает / в процессе
- [ ] **⚠️ Новая архитектура эскалации/обучения** — роли/идентичности + очередь обучения + Telegram per branch описаны в спеках, **код не внедрён**
- [ ] **⚠️ Эскалация всё ещё частая на реальные вопросы** — KB неполная, score часто < 0.5 → создаётся заявка; мелкие сообщения ("спасибо", "ок?") больше не должны создавать заявки (whitelist + guardrails)
- [ ] **⚠️ Active Learning частично** — owner-ответ → auto-upsert в Qdrant работает (логи 2025-12-25: "Owner response detected" / "Added to knowledge"), но нет модерации/метрик
- [ ] **⚠️ Ответы медленные (outbox)** — замер: SENT за последний час avg 17s, p90 25s, max 26s (created_at → updated_at); цель < 10s не достигнута
- [ ] **⚠️ Склейка сообщений ломает multi‑intent** — demo_salon: price‑ответ перехватывает до booking; в pending truth‑gate съедает booking; фикс в коде (booking flow в pending + price sidecar), нужен деплой/проверка
- [ ] **⚠️ Закрепы заявок в Telegram** — фикс в коде: `unpin` теперь использует `handover.telegram_message_id` (fallback на callback message_id); нужен деплой/проверка
- [ ] **⚠️ Дубли заявок на одного клиента** — владельцу неудобно; нужен guard: при open handover не создавать новый, а писать в текущий топик
- [ ] **Branch подключен частично** — webhook ставит `conversation.branch_id`, но Telegram per branch + RAG фильтры ещё не wired → `SPECS/MULTI_TENANT.md`
- [ ] **⚠️ by_instance зависит от instanceId** — demo_salon исправлен (query‑param даёт instanceId), остальным клиентам нужно прокинуть
- [ ] **⚠️ demo_salon truth-gate даёт цену на "как у/в стиле"** — нет правила style_reference, фото не поддерживаются; нужен отдельный ответ/эскалация
- [ ] **⚠️ Медиа (аудио/фото/документы)** — guardrails + Telegram forward + локальное хранение + транскрипция коротких PTT добавлены в код (нужен деплой); длинные аудио/видео и OCR/vision отсутствуют
- [ ] Метрики (Quality Deflection, CSAT) — план: `SPECS/ESCALATION.md`, часть 6
- [ ] Dashboard для заказчика — backlog
- [ ] Quiet hours для напоминаний — P2

### Блокеры
- **docker-compose** — инфра‑стек жив и разделён: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`); был кейс `KeyError: 'ContainerConfig'` на `up/build`; API деплой через `/home/zhan/restart_api.sh` (CI image через `IMAGE_NAME` + `PULL_IMAGE=1`, локальный `docker build` — fallback); `/home/zhan/truffles-main/docker-compose.yml` — заглушка

---

## РЕГЛАМЕНТ: МОЗГИ БОТА (каждая сессия)

- Старт: минимальный пакет памяти — `docs/SESSION_START_PROMPT.txt` (Brain Pack), `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, пакет клиента `truffles-api/app/knowledge/<client_slug>/`.
- Паттерн работы: проблема → диагностика (1–2 шага) → решение → тест → запись в `STATE.md`.
- Источник истины (без дублей): факты только в `SALON_TRUTH.yaml`, политика только в `POLICY.md`, фразы только в `INTENTS_*.yaml`, тесты только в `EVAL.yaml`.
- Обязательный остаток до "идеального консультанта": см. `SPECS/CONSULTANT.md` → раздел "Идеальный консультант — обязательный остаток".
- Проверка: `pytest truffles-api/tests/test_<client>_eval.py` + sync KB в Qdrant (`ops/manual_sync_demo.py` или `ops/sync_client.py`).

---

## PHASE 0 — RELEASE CRITERIA (DoD)

См. `STRATEGY/REQUIREMENTS.md` → раздел "DEFINITION OF DONE — PHASE 0".

Кратко:
- Safety/Law: оплата/предоплата/проверка/возврат, перенос, скидки, medical/complaint → только эскалация/шаблон.
- Core value: truth‑first по базовым вопросам + сбор лида на запись.
- Reliability: ACK‑first + outbox; coalescing 8s; без дублей/потерь.
- Evidence: pytest+eval+ruff зелёные + smoke‑check на проде.

---

## ТЕКУЩИЙ ПЛАН

> Источники: `STRATEGY/TECH_ROADMAP.md`, `STRATEGY/REQUIREMENTS.md`

### Сейчас (эта сессия / неделя)
1. [x] Аудит документов и структуры
2. [x] **Gap в спеке: state=manager_active без топика** (P0) ✅
3. [x] **Промпт: бот представляется** (Закон РК об ИИ) ✅
   - Бот говорит "Я виртуальный помощник" при приветствии
4. [x] **Confidence threshold** — score < 0.5 → не выдумывать ✅
   - Реализовано в ai_service.py
5. [x] **Low confidence: уточнить → потом заявка** — теперь 1–2 уточнения + подтверждение перед эскалацией
6. [x] Контракт поведения: приоритеты интентов + матрица state × intent → action (SPECS/CONSULTANT.md, SPECS/ESCALATION.md)
7. [x] Policy engine: normalize → detect signals → resolve → action; demo_salon вынесен в policy handler (без client-specific if в flow)
8. [x] Модель слотов записи: валидаторы service/datetime/name + запрет opt-out/фрустрации в слотах
9. [x] Golden-scenarios: автопрогон ключевых кейсов из tests/test_cases.json (decision/signals)

### Следующее (по порядку)

**НЕДЕЛЯ 1: Критичная инфраструктура [P0]** → `SPECS/INFRASTRUCTURE.md` ✅ DONE
1. [x] Секреты → .env (убрать из кода)
2. [x] Бэкап PostgreSQL (cron ежедневно 3:00)
3. [x] Бэкап Qdrant (cron воскресенье 4:00)
4. [x] Алерты в Telegram (сервис готов, нужно интегрировать)

**НЕДЕЛЯ 2: Качество кода [P1]** ✅ DONE
5. [x] Базовые тесты (91 тест, pytest проходит)
6. [x] Логирование (JSON, 46 print→0)
7. [x] CI/CD (GitHub Actions)
8. [x] Линтер (ruff)
9. [x] Интеграция alert_service в код

**НЕДЕЛЯ 3: Защита кода [P0]** → `SPECS/ARCHITECTURE.md` ЧАСТЬ 10 ✅ DONE
10. [x] Result pattern — `services/result.py` (11 тестов)
11. [x] State service — атомарные переходы с транзакциями (13 тестов)
12. [x] Health service — self-healing (6 тестов)
13. [x] SQL Constraint — `migrations/003_add_state_constraint.sql`
14. [x] Рефакторинг webhook.py — использует state_service
15. [x] Health endpoints — GET/POST /admin/health, /admin/heal

**НЕДЕЛЯ 4: Функционал** ⚠️ ЧАСТИЧНО (есть проблема)
16. [x] Эскалация при низком confidence — РЕАЛИЗОВАНО (MID=0.5, HIGH=0.85 + whitelist/guardrails)
17. [x] Active Learning — owner ответы автоматически в Qdrant
18. [ ] Multi-level confidence (в продукте: 0.85/0.5/low_confidence + уточнения)
19. [ ] Telegram кнопки модерации [В базу] [Отклонить] для не-owner

**АРХИТЕКТУРА ЭСКАЛАЦИИ/ОБУЧЕНИЯ [P0] — НОВОЕ РЕШЕНИЕ**
20. [ ] Роли + идентичности (agents/agent_identities) в БД
21. [ ] Очередь обучения (learned_responses: pending/approved/rejected) + auto-approve owner
22. [ ] Telegram per branch (branches.telegram_chat_id) + routing по branch_id

**⚠️ ПРОБЛЕМА:** Эскалация срабатывает слишком часто — даже на "ты еще здесь?"
- **Причина:** KB неполная → RAG score часто < 0.5 на реальные вопросы
- **Решения:**
  1. Threshold уже понижен до 0.5 (MID) + HIGH=0.85
  2. Whitelist/guardrails уже добавлены (greeting/thanks/ok/???)
  3. Добавить базовые ответы в knowledge base
  4. Добавить «уточнение перед заявкой» (см. пункт 5 в плане)

---

## BACKLOG (хотелки)

> Идеи на потом. НЕ ДЕЛАТЬ пока не в плане.

| Идея | Зачем | Приоритет | Откуда |
|------|-------|-----------|--------|
| **Омниканальность (Channel)** | Instagram, Telegram bot, CRM — без переделки | P2 | архитектура |
| **Branch к роутингу** | Несколько номеров WhatsApp у одного клиента | P2 | архитектура |
| **Implementation Brain (внедрения/поддержка)** | Быстрее запускать клиентов, фиксировать паттерны и ошибки | P1 | стратегия |
| Алерт "бот пронёс хуйню" | Критичные ошибки сразу владельцу | P1 | my_notes |
| Dashboard для заказчика | Видеть статистику | P2 | REQUIREMENTS |
| Kaspi Pay проверка | Автопроверка оплат | P2 | REQUIREMENTS |
| Telegram чат для владельца | Модерация, обсуждение, быстрая связь | P2 | my_notes |
| Ежедневный отчёт владельцу | Сколько диалогов, эскалаций, проблем | P2 | my_notes |
| Аргументы для сбора данных | В договор — почему выгодно делиться | P2 | my_notes |
| CRM интеграция | Синхронизация | P3 | Идея |
| Голосовые сообщения | Расшифровка | P3 | Идея |
| Google Drive для баз знаний | Заказчик сам обновляет FAQ | P3 | my_notes |
| Скрипт синхронизации knowledge/ → Qdrant | Автозагрузка базы знаний | P1 | папки |
| Скрипт загрузки prompts/ → БД | Автозагрузка промптов | P2 | папки |
| Использовать context/intents/ в классификаторе | Улучшить intent detection | P2 | папки |
| Автотесты из tests/test_cases.json | Проверка качества бота | P2 | папки |
| Исследование LLM моделей | Найти оптимальные модели для задач | P2 | сессия |
| Сжатие диалогов (summarizer) | Киллер-фича для длинных разговоров | P2 | сессия |
| Скрипт update_parameter | Управление параметрами с защитой от дураков | P2 | сессия |
| Веб-интерфейс (личный кабинет) | Заказчик сам меняет параметры | P3 | сессия |

---

## КАРТА ДОКУМЕНТОВ

| Область | Документ | Когда обновлять |
|---------|----------|-----------------|
| **Принципы** | `AGENTS.md` | Редко, только важное |
| **Состояние** | `STATE.md` | Каждую сессию |
| **Структура** | `STRUCTURE.md` | При добавлении/удалении файлов |
| **Техника** | `TECH.md` | При изменении доступов/команд |
| **Инфра compose** | `/home/zhan/infrastructure/docker-compose.yml`, `/home/zhan/infrastructure/docker-compose.truffles.yml` | При изменении инфраструктуры |
| **Контекст** | `docs/IMPERIUM_CONTEXT.yaml` | При изменении фактов/архитектуры |
| **Решения** | `docs/IMPERIUM_DECISIONS.yaml` | При изменении CEO-level policy |
| **Gaps** | `docs/IMPERIUM_GAPS.yaml` | При закрытии/открытии критических пробелов |
| **Старт сессии** | `docs/SESSION_START_PROMPT.txt` | При изменении правил запуска |
| **Сводка** | `SUMMARY.md` | После инвентаризации/крупных изменений |
| **Анкета** | `CHATGPT_QUESTIONS_ANSWERS.md` | При обновлении ответов |
| | | |
| **Эскалация** | `SPECS/ESCALATION.md` | handovers, напоминания, Telegram |
| **Поведение бота** | `SPECS/CONSULTANT.md` | промпт, правила ответов |
| **Автообучение** | `SPECS/ACTIVE_LEARNING.md` | модерация, Qdrant |
| **Архитектура** | `SPECS/ARCHITECTURE.md` | новые сервисы, потоки данных |
| **Инфраструктура** | `SPECS/INFRASTRUCTURE.md` | безопасность, CI/CD, тесты |
| **CI/CD** | `.github/workflows/ci.yml` | При изменении pipeline |
| **Pre-commit** | `.pre-commit-config.yaml` | При изменении hooks/сканеров |
| **Мультитенант** | `SPECS/MULTI_TENANT.md` | онбординг, новые клиенты |
| | | |
| **Миграции** | `ops/migrations/*.sql` | при изменении схемы БД |
| **Миграции** | `ops/migrations/011_add_webhook_secret.sql` | webhook secret per tenant |
| **Миграции** | `ops/migrations/014_add_branch_routing_settings.sql` | настройки branch routing + auto-approve |
| **Требования** | `STRATEGY/REQUIREMENTS.md` | Требования Жанбола |
| **Roadmap** | `STRATEGY/TECH_ROADMAP.md` | Технический план |
| **Продукт** | `STRATEGY/PRODUCT.md` | Тарифы, фичи |
| **Рынок** | `STRATEGY/MARKET.md` | Исследования, метрики |
| | | |
| **База знаний** | `knowledge/*.md`, `knowledge/demo_salon/*.md` | FAQ, примеры, сленг, демо-салон |
| **Интенты** | `context/intents/*.txt` | Новые интенты |
| **Промпты** | `prompts/*.md` | Системный промпт |

---

## ШАБЛОН ДЛЯ ФИКСАЦИИ РАССУЖДЕНИЙ (1–2 минуты)

- Боль/симптом: что именно ломает качество (факт/лог/пример)
- Почему важно: риск для клиента/бизнеса
- Диагноз: почему это происходит
- Решение: что меняем и где (файлы/правила)
- Проверка: команда/результат
- Осталось: что ещё не закрыто и следующий шаг

---

## ИСТОРИЯ СЕССИЙ

### 2025-12-26 — Outbox: policy trigger_type violation fix

**Что сделали:**
- В demo_salon policy‑gate поменяли `trigger_type` с `policy` на `intent` (валидное значение).

**Разбор (шаблон):**
- Боль/симптом: outbox worker падал, voice‑сообщения зависали в PROCESSING; бот “молчал” на голосовые.
- Почему важно: потеря ответов и зависшие сообщения.
- Диагноз: `handovers_trigger_type_check` не допускает `policy`, вставка handover падала.
- Решение: использовать `trigger_type="intent"` с `trigger_value=decision.intent`.
- Проверка: деплой + голосовые проходят, outbox не падает.
- Осталось: перевыставить старые PROCESSING при необходимости.

### 2025-12-26 — Prod: audio transcription enabled

**Что сделали:**
- Включили ASR для коротких PTT: `AUDIO_TRANSCRIPTION_ENABLED=1`, `AUDIO_TRANSCRIPTION_MAX_MB=2`, `AUDIO_TRANSCRIPTION_MODEL=whisper-1`, `AUDIO_TRANSCRIPTION_LANGUAGE=ru`.
- Перезапустили API.

**Разбор (шаблон):**
- Боль/симптом: бот отвечал “файл получил…” на голосовые без понимания.
- Почему важно: теряем смысл сообщения и точность ответа.
- Диагноз: транскрибация была выключена (env не задан).
- Решение: включили ASR и рестарт.
- Проверка: отправить PTT → в `messages.metadata.media.transcript` появляется текст; бот отвечает по смыслу.
- Осталось: проверить поведение в `pending/manager_active`.

### 2025-12-26 — Media: без авто‑handover + голосовые транскрипты + safe auto‑learning

**Что сделали:**
- Входящее медиа в `bot_active` больше не создаёт handover автоматически; референсы/«как на фото» эскалируются, остальное — по смыслу текста/транскрипта.
- Добавили транскрибацию коротких PTT‑голосовых (env‑гейты) и проброс транскрипта в Telegram.
- Для pending добавили системный hint: бот собирает детали, не обещает результат.
- Автообучение фильтрует “мусор” (placeholder/короткие/ack).
- Обновили спеки и TECH по новым правилам и env.

**Разбор (шаблон):**
- Боль/симптом: любое медиа сразу открывало заявку и плодило эскалации; голосовые не понимались ботом; автообучение рисковало брать мусор.
- Почему важно: лишняя нагрузка на менеджера + бот не закрывает 80% вопросов, риск плохих ответов.
- Диагноз: правило “media → handover” и отсутствие ASR для PTT; слабые фильтры в learning.
- Решение: перевести медиа на текст‑first (caption/ASR), эскалировать только style‑reference; добавить ASR‑гейты и фильтры learning.
- Проверка: юнит‑тесты не гонял; требуется деплой + проверка медиа/голосовых на проде.
- Осталось: задать env для транскрипции и проверить сценарии (бот_active/pending/manager_active).

### 2025-12-26 — Prod: media env values set

**Что сделали:**
- Добавили `MEDIA_URL_TTL_SECONDS`, `MEDIA_CLEANUP_TTL_DAYS`, `CHATFLOW_MEDIA_TIMEOUT_SECONDS` в `/home/zhan/truffles-main/truffles-api/.env`.
- Перезапустили API через `/home/zhan/restart_api.sh` на `ghcr.io/k1ddy/truffles-ai-employee:main`.

**Разбор (шаблон):**
- Боль/симптом: preflight показывал MISSING для media TTL/cleanup/timeout при активном медиа.
- Почему важно: ссылки могут жить бесконечно, нет регулярной очистки, риск таймаутов при отправке медиа.
- Диагноз: переменные не заданы в `truffles-api/.env`.
- Решение: задать значения и перезапустить контейнер.
- Проверка: `python3 ops/diagnose.py` → значения есть в preflight.
- Осталось: при необходимости выполнить `/admin/media/cleanup` (dry_run) и проверить отправку медиа.

### 2025-12-26 — Prod: stale pending handover закрыт

**Что сделали:**
- Закрыли pending handover `27403967-0389-42ee-9d09-a5d4eaf08f26` по conversation `4b355349-15bc-41df-b26d-4c76a6e7be41` через `manager_resolve` (system), добавили `resolution_type=other` и `resolution_notes`.
- Pending стало 0.

**Разбор (шаблон):**
- Боль/симптом: один pending handover висел с 2025-12-21.
- Почему важно: мусор в очереди, риск ложных сигналов и пропущенных действий.
- Диагноз: менеджер не ответил, заявка не была закрыта.
- Решение: ручное закрытие handover и возврат conversation в `bot_active`.
- Проверка: `python3 ops/diagnose.py` → pending=0.
- Осталось: при необходимости проверить топик 551 в Telegram.

### 2025-12-25 — Topic binding: one topic per client (P0 safety)

**Что сделали:**
- Канон: `users.telegram_topic_id`; `conversations.telegram_topic_id` — копия для активного диалога.
- Убрали fallback “последний handover без топика” в менеджерских ответах: сообщения принимаются только из топика клиента.
- Эскалация/создание топика теперь используют user‑topic; при пропаже темы пересоздание и синк.
- Health‑heal восстанавливает `conversation.telegram_topic_id` из `users.telegram_topic_id` вместо сброса стейта.

**Статус:**
- Нужен деплой и ретест: менеджер пишет только в топике, без темы — “не доставлено”.

### 2025-12-25 — Prod verification: media/manager/TTL checks

**Что проверили:**
- Диагностика: `python3 ops/diagnose.py` (handovers/pending — пусто).
- Логи: `docker logs truffles-api --tail 200 | rg -n "Escalated|topic|telegram|handover|media"` → есть "Manager media received" (photo).
- SQL:
  - `SELECT ... FROM handovers ORDER BY created_at DESC LIMIT 10;`
  - `SELECT ... FROM conversations WHERE state IN ('pending','manager_active');`
  - `SELECT created_at, content, metadata->'media' FROM messages WHERE metadata ? 'media' ORDER BY created_at DESC LIMIT 5;`

**Статус:**
- В контейнере `MEDIA_SIGNING_SECRET` и `PUBLIC_BASE_URL` отсутствуют → signed URL не генерится, `messages.metadata.media.public_url` пустой.
- TTL cleanup (dry_run) отрабатывает: `total_files=1`, `total_bytes=59579`, `deleted_files=0`.

**Разбор (шаблон):**
- Боль/симптом: manager→client медиа не получает `public_url`, signed URL проверить нельзя.
- Почему важно: клиент не получает медиа, ломается менеджерский поток.
- Диагноз: env `MEDIA_SIGNING_SECRET`/`PUBLIC_BASE_URL` не заданы в API.
- Решение: добавить env и перезапустить API.
- Проверка: менеджер шлёт медиа → в `messages.metadata.media` есть `public_url` и `storage_path`, `curl -I <public_url>` отдаёт файл.
- Осталось: ручные WA/Telegram проверки (handover + media), повторить SQL/логи после env-фікса.

### 2025-12-25 — Manager→client media: ChatFlow требует caption

**Что нашли:**
- Логи: `ChatFlow media response: success=false, message="Parameter [token, instance_id, caption, jid, imageurl] are required!"`
- `public_url` генерится и `/media/...` отдаёт файл, но ChatFlow отказывает без caption.

**Решение:**
- В `send_whatsapp_media` всегда прокидывать `caption` для image/doc/video (если нет — отправлять пробел).

**Статус:**
- Код обновлён, нужен деплой и ретест отправки медиа.

### 2025-12-25 — Manager→client media: ChatFlow timeout + ложные "Не доставлено"

**Что нашли:**
- Логи: `Error sending WhatsApp media: The read operation timed out` спустя ~30s после `process_manager_media`.
- Итог: медиа доходит с задержкой, но в топике появляется `❌ Не доставлено`.

**Диагноз:**
- ChatFlow media endpoint отвечает дольше 30s; синхронный webhook ловит timeout и считает отправку проваленной.

**Решение:**
- Отправку медиа от менеджера вынесли в background task (Telegram webhook отвечает сразу).
- Для ChatFlow media увеличен timeout (env `CHATFLOW_MEDIA_TIMEOUT_SECONDS`, дефолт 90s).

**Проверка:**
- Отправить фото/док/аудио в топик → нет `❌ Не доставлено`, WA получает медиа; в логах `ChatFlow media response: success=true`.

### 2025-12-25 — Manager→client media + signed URL + TTL cleanup

**Что сделали:**
- Добавили signed‑URL выдачу медиа (`/media/{path}`) и валидацию подписи.
- Реализовали manager→client медиа: Telegram file_id → download → локальное хранение → ChatFlow send‑image/audio/doc/video.
- Добавили admin endpoint `/admin/media/cleanup` для TTL‑очистки и алерта при превышении объёма.

**Статус:**
- Нужен деплой; требуется `MEDIA_SIGNING_SECRET` + `PUBLIC_BASE_URL` в env.

**Разбор (шаблон):**
- Боль/симптом: менеджер отправляет медиа → клиент его не получает (нет ChatFlow media API в коде).
- Почему важно: менеджер не может передавать фото/документы клиенту → ломается процесс.
- Диагноз: отсутствует Telegram download + public URL, нет ChatFlow send‑media.
- Решение: download в `/home/zhan/truffles-media`, signed‑URL выдача, ChatFlow send‑media, TTL‑cleanup.
- Проверка: менеджер шлёт фото/аудио/док/видео → клиент получает файл; `/media/...` отдаёт файл по подписи; cleanup удаляет старые файлы.
- Осталось: деплой + настройка env; интеграционные проверки.

### 2025-12-25 — Human request escalation (rule-based fallback)

**Что сделали:**
- В `intent_service.py` добавили rule‑based детект запроса менеджера до LLM, чтобы эскалация не зависела от классификатора.
- В `message_service.py` расширили паттерны human_request (склонения/опечатки), чтобы корректно отбирать контекст для handover.
- Добавили unit‑тесты на детект human_request.

**Статус:**
- Нужен деплой; `pytest` недоступен (не установлен).

**Разбор (шаблон):**
- Боль/симптом: пользователь пишет “позвать менеджера”, бот отвечает “передал администратору”, но handover не создаётся, Telegram‑топик не появляется.
- Почему важно: пользователь получает ложный статус, менеджер не видит заявку.
- Диагноз: human_request определялся только LLM, из‑за промахов классификации/опечаток эскалация не запускалась.
- Решение: добавить детерминированный regex‑детект human_request перед LLM и расширить паттерны.
- Проверка: отправить “позвать менеджера” → появляется handover + topic, в ответе MSG_ESCALATED.
- Осталось: деплой и проверка на проде.

### 2025-12-25 — Media: rate-limit double count + fast-forward storage

**Что сделали:**
- В `webhook.py` добавили `count_rate_limit` и выключили счётчик при `skip_persist=True` (outbox), чтобы лимиты не считались повторно.
- В fast-forward (enqueue_only) сохраняем медиа до отправки в Telegram, используем `stored_path` при отправке.
- В metadata сообщения пишем `storage_path/stored/storage_error/sha256`, чтобы storage не повторялся.

**Статус:**
- Нужен деплой и проверка на проде.

**Разбор (шаблон):**
- Боль/симптом: в Telegram приходят `[image]/[audio]/[document]`, в `messages.metadata.media.decision` — `rate_limited`.
- Почему важно: менеджер не видит медиа клиента → теряются заявки/контекст.
- Диагноз: rate‑limit считался повторно при outbox (skip_persist), fast‑forward в `manager_active` форвардил URL без локального хранения.
- Решение: отключить счётчик лимитов при `skip_persist`, сохранять медиа перед fast‑forward и отправлять файл с диска.
- Проверка: отправить 3–4 медиа подряд → decision.allowed=true, Telegram получает файл; `storage_path` заполнен.
- Осталось: ChatFlow media API для manager→client, TTL‑очистка хранилища.

### 2025-12-25 — Media: fix trigger_type constraint + rate limits

**Что сделали:**
- Обновили `handovers_trigger_type_check` (добавили `media`), чтобы эскалации по медиа не падали.
- Смягчили лимиты медиа: 5/10 мин, 20/сутки, 30MB/10 мин.
- PTT аудио с `audio/mpeg` теперь шлём как audio (не voice).

**Статус:**
- Требуется проверка на проде: аудио/документы должны доходить в Telegram как файлы.

**Разбор (шаблон):**
- Боль/симптом: audio/doc приходят как `[audio]/[document]`, outbox падал по constraint.
- Почему важно: медиа не доходит менеджеру, outbox ломается.
- Диагноз: trigger_type не допускает `media`, rate‑limit слишком жёсткий, PTT mime не совпадает с voice.
- Решение: расширили constraint, подняли лимиты, отправка PTT как audio при `audio/mpeg`.
- Проверка: отправить фото+аудио+док → в Telegram приходят файлы, в логах нет CheckViolation.
- Осталось: manager→client media, ASR/обработка.

### 2025-12-25 — Media guardrails + Telegram forwarding

**Что сделали:**
- Guardrails для медиа: allowlist типов, max‑size, rate‑limit (policy через `clients.config.media`).
- Отправка медиа в Telegram (sendPhoto/sendAudio/sendDocument/sendVoice) + caption.
- Локальное хранение медиа + метаданные в `messages.metadata.media`.
- Outbox: при медиа в батче — обработка по одному (без coalesce), чтобы не терять вложения.

**Статус:**
- Нужен деплой.

**Разбор (шаблон):**
- Боль/симптом: фото/аудио/документы не доходили менеджеру и могли убивать ресурсы.
- Почему важно: теряются лиды и растут риски по ресурсам/стоимости.
- Диагноз: только текстовый forward, нет лимитов и storage.
- Решение: guardrails + локальное хранение + Telegram media forward + media‑safe outbox.
- Проверка: отправить фото/аудио → файл в Telegram топике, бот отвечает шаблоном; лимиты режут спам.
- Осталось: деплой; TTL очистка хранилища; ChatFlow media API для manager→client; ASR/обработка файлов.

### 2025-12-25 — CI gitleaks warning fix

**Что сделали:**
- Убрали unsupported `args` из `gitleaks/gitleaks-action@v2` (warning “Unexpected input(s) 'args'”).

**Статус:**
- Готово, ждём прогон CI.

### 2025-12-25 — Fast-forward inbound to Telegram (pending/manager_active)

**Что сделали:**
- В enqueue_only: если `state=pending/manager_active` и есть `telegram_topic_id` — сообщение сразу форвардится в Telegram.
- В outbox: переносим `forwarded_to_telegram` и пропускаем повторный форвард.
- Добавили поле `forwarded_to_telegram` в `WebhookMetadata`.

**Статус:**
- Нужен деплой.

**Разбор (шаблон):**
- Боль/симптом: при active/pending сообщение клиента доходит до менеджера с задержкой outbox.
- Почему важно: менеджер отвечает медленнее → хуже конверсия записи.
- Диагноз: форвард в Telegram делается только при обработке outbox.
- Решение: fast-forward на входе + флаг, чтобы не было дублей.
- Проверка: написать клиентом в WA при `manager_active` и сравнить задержку.
- Осталось: деплой и проверка на проде.

### 2025-12-25 — Multi-intent booking (batch-aware)

**Что сделали:**
- Добавили batch-aware booking: детект записи по нескольким сообщениям (service+datetime) + предзаполнение слотов.
- Demo_salon: эскалация policy по каждому сообщению в батче; price sidecar при booking, если найдена конкретная услуга.
- Outbox: передаёт список сообщений в обработчик (batch_messages).
- Тесты: добавлены unit-тесты на batch booking helpers.

**Статус:**
- Нужен деплой; `pytest` недоступен в окружении.

**Разбор (шаблон):**
- Боль/симптом: multi-intent “цена+запись” теряется при склейке.
- Почему важно: теряются лиды на запись, растут эскалации.
- Диагноз: coalescing + demo_salon truth gate отвечают ценой до booking; booking детект только по ключевым словам.
- Решение: batch-aware сигналы + booking prefill; demo_salon policy → сначала, price sidecar → вместе с booking.
- Проверка: `pytest truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_demo_salon_eval.py` (не запускалось: `pytest` отсутствует).
- Осталось: деплой и проверка на проде.

### 2025-12-26 — Booking: service hint между сообщениями

**Что сделали:**
- При price-query сохраняем service hint в `conversations.context` (demo_salon).
- Booking flow подхватывает свежий hint (окно 120 мин) если в сообщении нет услуги; после использования очищаем.
- Добавили unit-тесты на срок жизни service hint.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: "сколько стоит маникюр" → "запишите на завтра" → бот снова просит услугу.
- Почему важно: теряется контекст и конверсия записи.
- Диагноз: booking flow видит только текущий батч и не помнит услугу из price-query.
- Решение: сохранять service hint из price-query и применять при старте booking.
- Проверка: ruff ok; требуется ручной тест на проде.
- Осталось: деплой и проверка в боевом диалоге.

### 2025-12-26 — Reminders: auto_close_timeout

**Что сделали:**
- Обнаружено: `auto_close_timeout=3` мин → заявки закрывались до напоминаний (30/60 мин).
- Обновили `client_settings.auto_close_timeout` до 120 мин для demo_salon и truffles.

**Статус:**
- Настройки обновлены в БД; нужен ручной тест напоминаний.

**Разбор (шаблон):**
- Боль/симптом: напоминаний не было.
- Почему важно: менеджер не получает пинга, клиент ждёт.
- Диагноз: auto-close закрывал заявки раньше таймаутов напоминаний.
- Решение: поднять auto_close_timeout до 120 мин (после reminder_2).
- Проверка: SQL выборка + ожидание reminder_1/2 на реальной заявке.
- Осталось: открыть заявку и проверить Telegram-напоминания.

### 2025-12-26 — Booking flow: opt-out/фрустрация не превращаются в заявку

**Что сделали:**
- Opt‑out теперь bypass’ит booking/truth-gate, чтобы “не пиши мне” не становилось именем.
- Фрустрация **не** блокирует booking; слоты не заполняются из opt‑out/мата.
- При opt‑out во время booking — сбрасываем booking context + service hint.
- Добавили тесты: составной opt‑out и запрет имени из ругани.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: “не хочу чтобы ты писал…/иди нахуй” в booking → “Передал менеджеру”.
- Почему важно: нарушает правило “нет значит нет”, портит UX.
- Диагноз: booking flow мог принять opt‑out/мат за слот “имя” и эскалировать.
- Решение: bypass booking/truth-gate для opt‑out + защита слотов от мата.
- Проверка: ruff ok; нужен ручной тест после деплоя.
- Осталось: деплой и проверка сценария.

### 2025-12-26 — Решение: hybrid логика mute/booking

**Решение (реализовано):**
- **Hybrid:** booking сильнее mute, но при конфликте opt‑out + booking в одном батче → просим подтверждение “Хотите снова общаться? да/нет”.
- Если booking пришёл **после** mute (без opt‑out в сообщении) → снимаем mute и продолжаем запись.
- Фрустрация + явный booking → **не эскалировать**, вести запись (если нет `human_request`).

**Почему нужно:**
- Сейчас mute ранним return делает поведение “молчание навсегда”, Telegram пустой и клиент теряется.

**Что сделали:**
- Ранний mute return пропускает booking: unmute при booking‑сигнале.
- Добавили `reengage_confirmation` в `conversation.context` с TTL.
- При opt‑out+booking: подтверждение “да/нет”, без заявки.
- Обновили тесты на подтверждение и на защиту слотов.

**Статус:** реализовано, нужен деплой и ручной тест.

### 2025-12-26 — Decision trace для re-engage/mute

**Что сделали:**
- В `conversation.context` пишется `decision_trace` (список до 12 событий) по ключевым веткам: re‑engage, mute, booking, demo truth‑gate, intent/escalation, out‑of‑domain, AI‑ответ.
- Добавлены manual тесты в `tests/test_cases.json` для hybrid‑сценариев.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: сложно понять “почему бот молчит/почему размьют”.
- Почему важно: нужен воспроизводимый дебаг и контроль регресса.
- Диагноз: решения не фиксировались ни в БД, ни в логах.
- Решение: сохранять decision trace в `conversation.context` + сценарные тесты.
- Проверка: проверить `conversations.context->'decision_trace'` на новых сообщениях.

### 2025-12-26 — План полной переработки (черновик)

**Цель:** предсказуемая логика + масштабируемость + дебаг.

1) **Контракт поведения**
   - Формальная матрица `state × intent × signals → action`.
   - Чёткие приоритеты: opt‑out vs booking vs frustration vs human_request.

2) **Policy Engine**
   - Убрать client_slug if’ы из `webhook.py`.
   - Правила/порог/таймауты в конфиге (DB/YAML), код — исполнитель.

3) **Slot Manager**
   - Явная модель слотов записи + валидаторы.
   - Запрещённые токены для слотов (opt‑out/мат).

4) **Decision Trace**
   - Лог + таблица: intent, policy_rule, chosen_action, confidence.
   - Использовать для AI‑дебага и регресса.

5) **Golden Scenarios**
   - Набор “что‑если” диалогов, CI‑проверка.
   - Тесты на батч/коалесинг/повторные сообщения.

6) **Observability**
   - Метрики: escalation rate, mute‑break, no‑response.
   - Алерты на противоречия (например, booking→mute).

### 2025-12-26 — Booking flow в pending (price+booking)

**Что сделали:**
- Разрешили booking flow при `state=pending`, чтобы batch "цена+запись" не перехватывался truth-gate.
- При pending не создаём новый handover: отвечаем пользователю и закрываем booking context.
- Добавили routing matrix/gates для booking/truth-gate и unit-тесты на правила.

**Статус:**
- Нужен деплой и повторный ручной тест; `pytest` отсутствует в окружении.

**Разбор (шаблон):**
- Боль/симптом: "сколько стоит маникюр" + "запишите на завтра" в pending → ответ "подскажите услугу".
- Почему важно: теряется контекст услуги, ухудшается конверсия записи.
- Диагноз: booking flow запускался только в bot_active; в pending срабатывал demo_salon truth gate.
- Решение: включить booking flow в pending, без создания нового handover.
- Проверка: повторить тест в pending — должен спросить имя + дать цену (sidecar); тесты не запускались (нет pytest).
- Осталось: деплой.

### 2025-12-26 — Routing matrix расширена (эскалация/малый чат)

**Что сделали:**
- Привязали smalltalk, out‑of‑domain и intent‑эскалацию к routing policy.
- Добавили guard: при pending human_request/frustration → ответ “уже передал”, без нового handover.
- Добавили unit‑тест на `_should_escalate_to_pending` и пересечения policy.

**Статус:**
- Ruff OK; pytest по‑прежнему отсутствует в окружении.

**Разбор (шаблон):**
- Боль/симптом: ветки реагируют по-разному в зависимости от state, возможны коллизии.
- Почему важно: логические баги на пересечениях “state × intent”.
- Диагноз: state‑гейты размазаны по веткам, нет единого решения.
- Решение: routing policy + единый gate для эскалаций/ответов.
- Проверка: `ruff check app tests` (ok), unit‑тесты добавлены.
- Осталось: pytest‑прогон в окружении с зависимостями.

### 2025-12-26 — Opt-out / агрессия в intent‑детекторе

**Что сделали:**
- Расширили opt‑out (“не пиши”, “отпишись”, “заткнись/заткнитесь”) → `Intent.REJECTION`.
- Эвристики агрессии/мата (“заебал” и т.п.) → `Intent.FRUSTRATION`.
- В pending‑эскалации для фрустрации отвечаем коротко без просьбы уточнить.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: “не хочу чтобы ты писал мне / заткнись” → ответ “уже передал… уточните”.
- Почему важно: нарушается правило “нет значит нет”.
- Диагноз: LLM не ловит opt‑out/фрустрацию, падаем в low‑confidence.
- Решение: локальные эвристики + корректный ответ в pending.
- Проверка: ruff ok; нужен ручной тест после деплоя.

### 2025-12-25 — Media fallback (non-text)

**Что сделали:**
- Перестали отбрасывать non-text payload: сохраняется в outbox, ответ “опишите текстом”.
- В messages добавлен `message_type/has_media` в metadata для входящих.

**Статус:**
- Нужен деплой, чтобы fallback начал работать; ASR/OCR/vision не реализованы.

### 2025-12-25 — Truffles instanceId prep

**Что сделали:**
- Создали branch `main` для `truffles` с `instance_id`.
- Сгенерировали `webhook_secret` для `truffles` (значение выдано Жанболу).

**Статус:**
- Обновили ChatFlow webhook URL и проверили: instanceId приходит, `conversation.branch_id` ставится.

### 2025-12-25 — InstanceId in inbound payload

**Что сделали:**
- Добавили `instanceId` в webhook (query‑param) для demo_salon.
- Проверили: instanceId пришёл в payload, `conversation.branch_id` проставился (main).

**Статус:**
- Работает для demo_salon; нужно повторить для остальных клиентов.

### 2025-12-25 — Outbox latency check

**Что сделали:**
- Измерили задержку outbox по БД (created_at → updated_at для SENT).
- Разложили задержку на wait (coalesce+interval) и processing по логам.

**Статус:**
- Avg 17s, p90 25s, max 26s за последний час; цель <10s не достигнута.
- Breakdown: wait ~8.7s, processing ~6.6s (выборка 4 батча).

### 2025-12-25 — Amnesia-mode checklist

**Что сделали:**
- Добавили короткий режим "амнезии" в `docs/SESSION_START_PROMPT.txt` для быстрого входа и сохранения знаний.

### 2025-12-25 — Human_request uses last meaningful message

**Что сделали:**
- Для handover при `human_request` берём последнее содержательное user-сообщение вместо "позови менеджера".
- Добавлен helper и тесты для выбора meaningful сообщения.
- В БД: выставлен `client_settings.owner_telegram_id` для `demo_salon` = `1969855532`.

**Статус:**
- Требуется деплой и проверка: handover.user_message теперь содержит реальный вопрос клиента.

### 2025-12-25 — Outbox worker + owner learning fallback

**Что сделали:**
- Добавили outbox worker в API (тик 2s) и вынесли обработку outbox в общий хелпер.
- Telegram: sender_chat fallback для идентификации менеджера.
- Auto-learning: не затирает assigned_to при unknown; fallback на assigned_to для owner-check; поддержка отрицательных ID.

**Статус:**
- Проверено по логам: "Owner response detected" + "Added to knowledge" (2025-12-25); latency < 10с ещё не проверена.

### 2025-12-25 — Demo salon: law-safe KB + policy keywords

**Что сделали:**
- Почистили demo_salon FAQ/возражения/правила: оплаты/перенос/medical/жалобы → эскалация, убран телефон администратора.
- Обновили `SALON_TRUTH.yaml`: убрали блок оплат, оставили только medical_note.
- Расширили policy-ключевые слова в `demo_salon_knowledge.py` (оплата/перенос/medical/жалобы/скидки).
- Обновили фразы и `EVAL.yaml` под новые кейсы.
- Добавили ответ на “ты тут?/алло” через `is_bot_status_question` в `ai_service.py`.
- Обновили sync-скрипты: BGE/Qdrant URL берутся из env или docker IP, Qdrant key из env (с trim).

**Статус:**
- KB demo_salon синхронизирована в Qdrant через `ops/manual_sync_demo.py` (34 points).

### 2025-12-24 — Admin settings for branch routing

**Что сделали:**
- Расширили `/admin/settings` под branch routing + auto-approve роли.
- Починили маппинг reminder_* → `reminder_timeout_*` в настройках.
- Добавили миграцию `ops/migrations/014_add_branch_routing_settings.sql`.
- Встроили branch routing (by_instance/ask_user/hybrid) и remember_branch в `webhook.py`.
- Дефолт auto-approve обновлён на `owner,admin` (спека/модель/миграция).
- **Prod fix:** применили миграцию 013/014 (не было `conversations.branch_id` → webhook падал).

### 2025-12-24 — Спеки + скелет архитектуры обучения

**Что сделали:**
- Обновили `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ACTIVE_LEARNING.md` (роли/идентичности, очередь обучения, Telegram per branch).
- Зафиксировали решение в `docs/IMPERIUM_DECISIONS.yaml` (DEC-008).
- Добавили модели `Agent`, `AgentIdentity`, `LearnedResponse` и миграцию `ops/migrations/013_add_agents_and_learning_queue.sql` (branch_id для агентов и обучения).
- Обновили `STRUCTURE.md` и `STATE.md`.

**Статус:**
- Код пока не подключён к потокам Telegram/обучения — это следующий шаг.

### 2025-12-24 — Sync: latency + multi-intent + git hygiene

**Что выяснили:**
- Задержка ответов/пересылки в Telegram: ACK-first + cron `/admin/outbox/process` раз в минуту + `OUTBOX_COALESCE_SECONDS=8` → 8–60 сек.
- Demo_salon multi-intent ломается: coalescing склеивает сообщения, truth-first возвращает цену до booking → запись теряется.

**Что сделали:**
- Создали `CHATGPT_QUESTIONS_ANSWERS.md` (ответы на анкету).
- Обновили `STATE.md` и `STRUCTURE.md` (новые проблемы и приоритеты).
- EVAL: `test_demo_salon_eval.py` — 1 passed (локальный venv).
- Git hygiene: секреты вынесены в env vars в docs/ops; добавлен gitleaks в CI и pre-commit; `/.venv/` добавлен в `.gitignore`.

### 2025-12-24 — Ротация OpenAI ключа (prod)

**Проблема:** 401 `invalid_api_key` после CI (ключ утёк).

**Что сделали:**
- Обновили `OPENAI_API_KEY` в `/home/zhan/truffles-main/truffles-api/.env` (из `/home/zhan/secrets/openaikey.txt`)
- Перезапустили API через `/home/zhan/restart_api.sh`
- Проверка: `docker logs truffles-api --tail 50` — ошибок 401 нет

### 2025-12-23 — Hotfix: outbox delivery + ChatFlow idempotency

**Проблема:** бот молчал при обработке outbox.

**Диагностика:**
- В логах `send_bot_response() got an unexpected keyword argument 'idempotency_key'`
- 401 от OpenAI (ключ в контейнере невалиден)

**Что сделали:**
- `chatflow_service.send_bot_response()` принимает `idempotency_key`/`raise_on_fail`
- `send_whatsapp_message()` прокидывает `msg_id` (idempotency)

**Статус:**
- Код запушен в `main`, CI должен собрать/задеплоить.
- OpenAI ключ всё ещё возвращает 401 — нужен валидный ключ.

### 2025-12-23 — Demo salon truth-first + outbox coalescing (repo)

**Что сделали:**
- Реализован truth-first/policy-gate для demo_salon (до RAG/LLM) + EVAL pytest
- Добавлена склейка сообщений в outbox (coalescing по conversation_id, 6–10 сек тишины)
- Введён канон `knowledge/demo_salon/` для синка (fallback на `ops/demo_salon_docs`)
- Документы обновлены: `docs/SESSION_START_PROMPT.txt`, `TECH.md`, `STRUCTURE.md`

**Важно:** код в репо обновлён; чтобы изменения заработали на проде, нужен `docker build` + `bash ~/restart_api.sh` (restart без build не подтягивает код).

### 2025-12-23 — Outbound retries/idempotency + EVAL fixes (prod)

**Что сделали:**
- Добавлены retry/backoff для ChatFlow + msg_id idempotency в webhook/outbox
- Outbox: повторные попытки с backoff до `OUTBOX_MAX_ATTEMPTS`
- Исправлены EVAL кейсы demo_salon (guest_policy, бренды, рескейджул, прайс токены)
- Документы обновлены: `TECH.md`, `docs/IMPERIUM_GAPS.yaml`, `SUMMARY.md`

**Тесты:**
- `pytest -q` (145 passed; Pydantic warnings)

**Деплой:**
- `docker build -t truffles-api_truffles-api .` + `bash /home/zhan/restart_api.sh`

### 2025-12-22 — PR-004: Outbox + ACK-first (prod)

**Что сделали:**
- Добавили таблицу `outbox_messages` + сервис outbox
- `/webhook` теперь ACK-first: сохраняет входящее, кладёт в outbox, возвращает 200 без LLM
- Добавили `POST /admin/outbox/process` (X-Admin-Token) для обработки очереди
- Задеплоено на прод, проверка: enqueue → process → SENT

### 2025-12-22 — PR-002: Alerts endpoint restored on prod

**Что сделали:**
- Добавили router `/alerts/test` + защита `ALERTS_ADMIN_TOKEN`
- Прописали `ALERTS_ADMIN_TOKEN` в `truffles-api/.env`, пересобрали и перезапустили API
- Проверка: `/alerts/test` → 401 без токена, 200 с токеном

**Статус:** PR-002 DONE on prod

### 2025-12-21 — Sync: перенос реализаций из truffles_origin

**Что сделали:**
- Вернули domain router + guardrails (бот статус/оффтоп) в webhook/message
- Добавили low_confidence retries (до 2) + подтверждение handover (yes/no)
- Включили DB dedup через `message_dedup`
- В learning_service добавлены alert_warning на skip/success
- Обновили тест `tests/test_intent.py` под `Intent.OUT_OF_DOMAIN`

### 2025-12-21 — Runbook: health/webhook/outbound

**Диагностика:**
- `curl http://localhost:8000/health` из текущей оболочки → connection refused; внутри контейнера `/health` и `/db-check` дают 200
- `POST /webhook` (demo_salon + remoteJid) → 200; в логах есть `ChatFlow response` и `Delivered`
- В контейнере `OPENAI_API_KEY` отсутствовал → 401 от OpenAI
- В контейнере `QDRANT_API_KEY` отсутствовал → ошибки knowledge search
- Alert service использует `ALERT_BOT_TOKEN`/`ALERT_CHAT_ID` (эндпоинта `/alerts/test` в контейнере нет)
- `truffleskz_bot` был с webhook на `rocket-api...` → менеджерские ответы/кнопки не доходили
- `alert_service` ломался на сообщениях с `_` из-за Markdown parse errors
- Репозиторий не содержал `app/main.py`, `app/services/knowledge_service.py`, `app/services/learning_service.py` → сборка API падала

**Что сделали:**
- Обновили `truffles-api/.env`: `OPENAI_API_KEY`, `QDRANT_API_KEY`, `ALERT_BOT_TOKEN`, `ALERT_CHAT_ID=1969855532`
- Обновили `client_settings.telegram_bot_token` для `truffles` и `demo_salon`
- Поставили webhook для `truffleskz_bot` и `salon_mira_bot` → `https://api.truffles.kz/telegram-webhook`
- Восстановили `app/` из последнего рабочего образа (`9abdfaf8c85e`) и пересобрали `truffles-api_truffles-api`
- Переписали `app/services/alert_service.py` на HTML-экранирование (устойчиво к `_`)
- Перезапустили API через `/home/zhan/restart_api.sh`
- Проверка: `/health` и `send_alert` → OK

### 2025-12-21 — Диагностика: inbound молчит

**Диагностика:**
- В БД по `77015705555@s.whatsapp.net` нет новых user сообщений после 2025-12-20 12:16 (12-21 были тестовые с `sender=test`)
- Значит ChatFlow не стучится в webhook / не принимает WhatsApp входящие

**Следующий шаг:**
- Проверить в ChatFlow webhook URL `https://api.truffles.kz/webhook/{client_slug}` и статус инстанса

### 2025-12-21 — Direct webhook

**Что сделали:**
- Добавлен endpoint `POST /webhook/{client_slug}` для прямого ChatFlow (без промежуточной обёртки)
- Добавлен fallback-парсер для разных форматов webhook payload + логирование недостающих полей
- Добавлен CORS middleware + `GET /webhook/{client_slug}` для UI-проверок
- Для UI-теста с пустым body добавлен мягкий ответ `success=true` ("Empty payload")
- Убрали 400 от OpenAI на intent (temperature=1.0 для gpt-5-mini)
- Обработан `ClientDisconnect` в webhook (не валит логи)
- Direct webhook теперь отвечает сразу (async processing), чтобы ChatFlow не слал “Ошибка вызова вебхука”
- Domain router: добавлен keyword override для цен/записи/адреса, чтобы не ловить false out-of-domain

**Действие:**
- В ChatFlow указать webhook `https://api.truffles.kz/webhook/{client_slug}`

### 2025-12-21 — Out-of-domain: строгий фильтр + RAG override

**Что сделали:**
- Добавили "strong out-of-domain" с более строгими порогами + min_len (консервативный OOD)
- Добавили `get_rag_confidence()` и проверку RAG перед OOD‑ответом
- В `webhook.py` и `message.py` OOD‑ответ только если strong OOD / intent=out_of_domain и **нет** уверенного RAG
- Добавили логи "Domain out-of-domain gate" при `DOMAIN_ROUTER_LOG_SCORES=1`

### 2025-12-21 — Webhook auth + тесты

**Что сделали:**
- Вернули проверку `webhook_secret` для `/webhook` (401 до валидации payload)
- Добавили `webhook_secret` в `ClientSettings` модель + `alert_warning` при отсутствии секрета
- Прогнали тесты в отдельном образе: `123 passed`

### 2025-12-21 — Direct webhook auth + async fix

**Что сделали:**
- `/webhook/{client_slug}` теперь проверяет `webhook_secret` и отдаёт 401 при отсутствии/невалидном секрете
- Async обработчик теперь вызывает общий обработчик корректно (без сломанной подписи)
- Тест обновлён: direct webhook без секрета → 401
- В БД добавлен `client_settings.webhook_secret` и задан секрет для `demo_salon`
- API пересобран и перезапущен
- ChatFlow для `demo_salon` переключён на `https://api.truffles.kz/webhook/demo_salon?webhook_secret=...`

### 2025-12-20 — Health check: убрали ложные алерты

**Диагностика:**
- `ops/health_check.py` использовал статические IP контейнеров → после рестарта IP меняются, «Connection refused».
- `https://api.truffles.kz/healthz` возвращает 404 → алерты даже при живом API.

**Что сделали:**
- `ops/health_check.py` теперь получает IP контейнера через `docker inspect`.
- Health-check допускает 200/30x/401/403.
- Qdrant API key берётся из env (fallback на старый).

### 2025-12-20 — Traefik не видел docker → API недоступен

**Диагностика:**
- Traefik отдавал 404 по `api.truffles.kz`.
- В логах: `client version 1.24 is too old` → docker provider не поднимался.

**Что сделали:**
- Обновили Traefik до `v2.11` в `/home/zhan/infrastructure/docker-compose.yml`.
- Перезапустили контейнер, docker provider поднялся, маршруты появились.

### 2025-12-20 — Консолидация: один корень `/home/zhan/truffles-main`

**Диагностика:**
- Было 3 корня: `/home/zhan/truffles-main`, `/home/zhan/Truffles-AI-Employee`, `/home/zhan/truffles`.
- Команды/доки ссылались на разные пути → путаница.

**Что сделали:**
- Скопировали актуальные документы и директории в `/home/zhan/truffles-main`.
- Перенесли API‑код в `/home/zhan/truffles-main/truffles-api`.
- Обновили пути в `restart_api.sh` и документах.
- Архивировали старый `/home/zhan/Truffles-AI-Employee` в `/home/zhan/_trash`.

### 2025-12-20 - Guardrails: оффтоп и "бот молчит" без заявок

**Диагностика:**
- Оффтоп ("трусы") и вопрос "почему не отвечает?" уходили в low_confidence/frustration → создавалась заявка.

**Что сделали:**
- Добавили intent `out_of_domain` в классификатор.
- Ответ на `out_of_domain` без эскалации (возврат к теме салона).
- Guardrail на вопросы "бот не отвечает" → шаблонный ответ без заявки.
- Подняли `DEBOUNCE_INACTIVITY_SECONDS` до 3.0 (лучше склейка коротких сообщений).
- Обновили FAQ demo_salon ("Чем вы занимаетесь?") и пересинхронизировали KB.
- Intent классификатор перевели на `temperature=0.0` (меньше случайных эскалаций).
- Для low_confidence добавили до 2 уточнений перед эскалацией.

### 2025-12-20 — Domain router + подтверждение эскалации

**Диагностика:**
- Off-topic и низкая уверенность всё ещё могли создавать заявки менеджерам.

**Что сделали:**
- Добавили embedding-based domain router (якоря in/out) и ранний оффтоп-ответ без эскалации.
- Добавили подтверждение эскалации после low_confidence (да/нет) с окном 15 минут.
- Исправили битые domain anchors (кодировка).
- Протянули логику в `/webhook` и legacy `/message`.
- Задеплоили `webhook.py`, `message.py`, `intent_service.py` и перезапустили API.
- Добавили domain router config per-client (anchors + thresholds) в `clients.config`.
- Включили логирование domain scores через `DOMAIN_ROUTER_LOG_SCORES=1`.
- Перезалили `intent_service.py`, `webhook.py`, `message.py` и перезапустили API.

### 2025-12-19 - AL наблюдаемость + дедуп + KB sync

**Диагностика:**
- Нет видимости успехов/пропусков AL; дедуп messageId опирался на Redis/БД сообщений; KB demo могла быть несинхронна.

**Что сделали:**
- AL: alert_warning на skip (нет текста/слишком коротко/нет client_slug) и на success (point_id, длины).
- Дедуп: таблица message_dedup + INSERT ON CONFLICT, логируем дубли.
- KB: пересобрали demo_salon (faq/objections/rules/services) — 34 chunks в Qdrant.



### 2025-12-18 — Active Learning: owner detection

**Диагностика:**
- Owner response не детектился → автообучение не запускалось.

**Что сделали:**
- Разрешили список `owner_telegram_id` через запятую/пробел (username или numeric id).
- Добавили диагностические логи при mismatch owner vs manager.
- Обновили тесты `is_owner_response`.



### 2025-12-18 — Стабильность: авто‑закрытие и алерты “нет ответа”

**Диагностика:**
- Зависшие handover без закрытия.
- Нет алерта, когда пользователь написал, а бот не ответил.

**Что сделали:**
- Авто‑закрытие pending/active по `client_settings.auto_close_timeout` в `/reminders/process`.
- Алерт “вход есть — ответа нет” при задержке > `NO_RESPONSE_ALERT_MINUTES`.

### 2025-12-18 — Диалоговый контур: слоты записи + контекст

**Диагностика:**
- Короткие ответы и “странные” клиенты ломают контекст, особенно в сценариях записи.

**Что сделали:**
- Добавили `conversations.context` (JSONB) для хранения краткого контекста/слотов.
- Слот‑филлинг для записи: услуга → дата/время → имя, с передачей админу.
- Очистка контекста при reset/resolve/новой сессии.

### 2025-12-18 — Приветствия и whitelist: убрали ложные “уточните”

**Диагностика:**
- Сообщения типа “добрый день + …” считались whitelisted → LLM отвечал “вслепую”.
- “ДД” попадал в low-signal и выдавал уточнение вместо приветствия.

**Что сделали:**
- Добавили распознавание приветствий/благодарности, включая “дд”.
- `is_whitelisted_message` теперь только точное совпадение, без `startswith`.
- Приветствия/спасибо больше не считаются low-signal; отдельный shortcut в webhook.

### 2025-12-18 — Контекст для “да/нет” + FAQ “туалет”

**Диагностика:**
- Короткие ответы “да/нет” после вопроса бота уходили в low-signal и теряли контекст.
- В FAQ не было ответа про туалет.

**Что сделали:**
- Разрешили short-confirmation после yes/no вопроса использовать историю (contextual RAG).
- Добавили FAQ “есть ли туалет” в demo_salon.

### 2025-12-18 — Дебаунс: убрать дублирование контента в prompt

**Диагностика:**
- При буфере сообщений объединенный текст добавлялся поверх уже сохраненной истории → дубли в LLM и лишние токены.

**Что сделали:**
- Добавили флаг `append_user_message` и выключаем его при буфере, чтобы не повторять контент.
- Прокинули флаг через `generate_bot_response` → `generate_ai_response`.

### 2025-12-18 — Автообучение owner + дедуп по messageId

**Диагностика:**
- Owner auto-learning мог не срабатывать при `owner_telegram_id` в формате username или при сообщениях без `from_user` (анонимный админ).

**Что сделали:**
- `is_owner_response` теперь матчится по id или username (case-insensitive) и принимает `manager_username`; добавлен warning, если `from_user` отсутствует.
- Дедуп по `metadata.messageId`: Redis SETNX + fallback на БД (`messages.metadata.message_id`), сохраняем `message_id` в metadata входящих сообщений.
- `get_system_prompt` ищет `system`, а при отсутствии — `system_prompt` (обратная совместимость).
- Пересинхронизировали KB для `demo_salon` из `~/truffles/ops/demo_salon_docs` (22 chunks).
- Добавлен буфер сообщений поверх debounce (склеивание нескольких сообщений в одно перед обработкой).
- Обновлены шаблоны промптов: явное правило для вопросов вне темы бизнеса.
- Промпт `demo_salon` обновлён: оффтоп (маркетинг/продвижение) → вернуть к теме салона.
- Прод: `DEBOUNCE_INACTIVITY_SECONDS=2.0`.
- KB `demo_salon` расширена под полный FAQ/запись/гигиена/услуги/конфликты (34 chunks).
- Тест: `python -m pytest truffles-api/tests/test_learning_service.py -q` (16 passed).

### 2025-12-17 — Фикс “бот молчит” + защита заявок

**Диагностика:**
- “Бот молчит” часто означает не баг, а состояние `manager_active` — по протоколу бот должен молчать и только форвардить в Telegram-топик.
- На проде были зависшие заявки (`handovers.pending/active`) и один опасный случай mismatch `handover.channel_ref` (риск ответить не тому клиенту).

**Что сделали:**
- Emergency reset: `ops/reset.sql` теперь (1) чинит `channel_ref` у открытых заявок, (2) закрывает все open handovers, (3) возвращает диалоги в `bot_active`.
- Защита: self-heal чинит mismatch `channel_ref`, а ответы менеджера отправляются по `user.remote_jid` (source of truth).
- Reminders: напоминания теперь идут по всем open handovers (`pending` + `active`), чтобы заявки не висели бесконечно.
- Debounce: в FastAPI `POST /webhook` добавлен Redis-debounce — при серии быстрых сообщений бот отвечает один раз (последнее сообщение после паузы). Параметры: `DEBOUNCE_ENABLED` (default=on), `DEBOUNCE_INACTIVITY_SECONDS` (default=1.5), `REDIS_URL` (default=`redis://truffles_redis_1:6379/0`). Быстрый откат: поставить `DEBOUNCE_ENABLED=0` в `.env` и `bash ~/restart_api.sh`.

### 2025-12-12 (вечер) — Неделя 4: ПРОВАЛ

---

## ⚠️ КРИТИЧНО ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ

**Состояние бота: ЧАСТИЧНО РАБОТАЕТ, НО ПЛОХО**

Важно:
- Если клиент пишет в WA и “бот молчит” — первым делом проверить `conversation.state`: в `manager_active` это ожидаемое поведение.
- Если заявки зависли и нужно срочно “оживить” бота — использовать `ops/reset.sql`.
- **Outbox требует планировщика:** cron `*/1` → `POST /admin/outbox/process` (см. `/etc/cron.d/truffles-outbox`).
- **Новая архитектура эскалации/обучения принята:** роли/идентичности + очередь обучения + Telegram per branch; см. `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ACTIVE_LEARNING.md`, миграция `ops/migrations/013_add_agents_and_learning_queue.sql`.

Протокол проверки (10 минут, без догадок):
1. Проверить прод-состояние: `curl -s http://localhost:8000/admin/health` (через SSH на сервере).
2. Если `pending/active > 0` и это тесты — закрыть: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/reset.sql`.
3. Прогнать WA тест-диалог с номера `+77015705555`: приветствие → попросить менеджера → менеджер ответил → [Решено].
4. Смотреть `docker logs truffles-api --tail 200` и убедиться что видно `remote_jid`, `state` и что не происходит loop `pending → pending`.
5. Если есть “молчание”, но нет открытых заявок — выполнить `POST /admin/heal` и проверить инварианты (state/topic/handover).

Runbook (если “всё странно” или сессия оборвалась):
1. Подключиться на прод: `ssh -p 222 zhan@5.188.241.234`.
2. Быстро понять “это заявка или баг”: `curl -s http://localhost:8000/admin/health`.
3. Если `handovers.pending/active > 0` и это тестовый мусор — одним выстрелом очистить: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/reset.sql`.
4. Если “бот молчит” у конкретного клиента — проверить состояние диалога (пример для `+77015705555`):
   `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT c.id, c.state, c.telegram_topic_id, c.last_message_at FROM conversations c JOIN users u ON u.id=c.user_id WHERE u.remote_jid='77015705555@s.whatsapp.net' ORDER BY c.started_at DESC LIMIT 3;"`
5. Если `state=manager_active` — это НЕ баг: бот обязан молчать, а сообщения должны улетать в Telegram-топик.
6. Если `state=bot_active`, но бот “молчит” — смотреть логи доставки: `docker logs truffles-api --tail 300`.

Правило тестов (чтобы самому себе не ломать картину):
- Не мешать сценарии в одну кашу: отдельно “прайс/запись”, отдельно “эскалация”, отдельно “жалоба”.
- Быстрые сообщения подряд (“подскажите/…/…”) теперь debounced на уровне API → промежуточные сообщения сохраняются в историю, но бот отвечает один раз (по последнему сообщению после паузы).
- После тестов закрывать заявки кнопкой [Решено] или делать `reset.sql`, чтобы диалоги не оставались в `pending/manager_active`.

Ключевые файлы для отладки: `truffles-api/app/routers/webhook.py`, `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/services/ai_service.py`, `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/services/state_service.py`, `ops/reset.sql`.

Что работает:
- Бот отвечает при RAG score ≥ 0.5 (medium/high), а приветствия/«спасибо»/«ок?»/«???» — без заявок (guardrails)
- В `pending` бот отвечает и не создаёт повторную заявку (но сообщения всё равно форвардятся в Telegram-топик)
- Кнопки [Беру] [Решено] работают (после починки traefik labels)
- Заявки создаются

Что НЕ работает:
- Low confidence всё ещё часто уходит в заявку из-за неполной базы знаний (нужно «уточнение перед заявкой»)
- Active Learning по owner-ответам подтверждён логами (2025-12-25), но нужна модерация/метрики

---

## МОИ ОШИБКИ (архитектор)

1. **Написал код не понимая систему.** Добавил learning_service.py, не проверив как сообщения менеджера вообще доходят до API.

2. **Не читал документацию.** В SPECS/ARCHITECTURE.md описан путь сообщения менеджера. В ops/README.md написано куда настроен Telegram webhook. Я не читал.

3. **Отчитывался "сделано" когда ничего не проверил.** Сказал что Active Learning работает, хотя ни разу не проверил логи.

4. **Спрашивал Жанбола то, что должен найти сам.** "Как твоё сообщение дошло до клиента?" — это я должен был выяснить из кода, не спрашивать.

5. **Извинялся вместо того чтобы делать.** Извинения — мусор. Нужны действия.

---

## ФАКТЫ (что точно известно)

### Из логов:
```
"сколько стоит маникюр?" → score 0.742 → бот ответил сам ✓
"сколько стоит постричь ногти?" → score 0.655 → эскалация
"спасибо" → score 0.535 → эскалация ← ПЛОХО
"ты еще здесь?" → эскалация ← ПЛОХО
```

### Outbox latency (DB факт):
- `outbox_messages` SENT за последний час: avg 17s, p90 25s, max 26s (created_at → updated_at)
- Последние 10 сообщений: 9-21s

### Outbox latency breakdown (логи+DB, выборка 4 батча):
- Wait до старта обработки (start - last_created): avg 8.7s, p90 9.9s → совпадает с coalesce+interval
- Processing (processed - start): avg 6.6s, p90 12.7s
- End-to-end от последнего сообщения: avg 15.4s, p90 21.3s
- В outbox есть старые `PROCESSING` (3) и `FAILED` (2) записи (возраст ~1.5–1.9 дня) — потенциальный мусор/ретраи
- Пример (08:55 местн, сообщение “Добрый день. Это мое сообщение”): wait 9.3s, processing 17.7s, total 27.0s

### Кнопки:
- Сначала не работали — traefik labels были пустые
- После `ops/restart_api.sh` — заработали
- Скрипт `ops/restart_api.sh` — правильный способ деплоя

### Обучение (Active Learning):
- Код написан: `learning_service.py`, вызов в `manager_message_service.py`
- В логах есть `"Owner response detected"` и `"Added to knowledge"` (2025-12-25) → auto-upsert в Qdrant сработал
- Жанбол писал "5000 тысяч" в топик — сообщение дошло до клиента

### Telegram webhook:
- В ops/README.md зафиксирован webhook `https://api.truffles.kz/telegram-webhook` (прямой в API)
- В коде ожидается: `api.truffles.kz/telegram-webhook`
- Я предположил что это причина — но Жанбол сказал что это хуйня

### Прод (2025-12-24):
- API падал на `/webhook` из-за отсутствия `conversations.branch_id` (миграция 013 не была применена) — применено, падение исчезло.
- `/etc/cron.d/truffles-outbox` есть и дергает `/admin/outbox/process` каждую минуту (через `ALERTS_ADMIN_TOKEN`).
- Inbound payload не нёс `metadata.instanceId` (раньше), поэтому by_instance не работал; после добавления query‑param для demo_salon instanceId приходит.
- Demo_salon: запросы вида "как у/в стиле" → отвечают прайсом (truth-gate), нужно отдельное правило.

### Branch routing (DB факт):
- `demo_salon`: `branch_resolution_mode=by_instance`, `remember_branch_preference=true`, `require_branch_for_pricing=true`, `auto_approve_roles=owner,admin`, `webhook_secret` установлен.
- `truffles`: `branch_resolution_mode=hybrid`, `remember_branch_preference=true`, `require_branch_for_pricing=true`, `auto_approve_roles=owner,admin`, `webhook_secret` установлен; branch `main` с `instance_id` подключён (ChatFlow webhook обновлён).

### Branches (DB факт):
- `demo_salon` имеет 1 активный branch (`slug=main`) с `instance_id` и `telegram_chat_id`.
- `truffles` имеет 1 активный branch (`slug=main`) с `instance_id`.

### Inbound payload (DB факт):
- Ранее в `outbox_messages.payload_json.body.metadata` были только `sender`, `messageId`, `remoteJid`, `timestamp` → `instanceId` отсутствовал.
- Теперь при webhook с query‑param `instanceId` присутствует (пример: "второе сообщение", 2025‑12‑25 04:22 UTC) и `conversation.branch_id` = `b7f75692-951e-421a-aae6-f5db97394799` (main).
- Проверка:
```
SELECT payload_json->'body'->'metadata' AS metadata
FROM outbox_messages
ORDER BY created_at DESC
LIMIT 1;
```
- Пример текстового payload (из `outbox_messages.payload_json`):
```
{"body": {"message": "вот мое просто сообщение", "metadata": {"sender": "Zh.", "messageId": "3EB0747A962FBC720E44FF", "remoteJid": "77015705555@s.whatsapp.net", "timestamp": 1766582383}, "messageType": "text"}, "client_slug": "demo_salon"}
```
- Пример нетекстового payload (из логов, `has_message=false`): ключи `messageType`, `message`, `metadata`, `to`, `mediaData`, `nodeData`.
- Сейчас такие payload на проде отбрасываются (“Empty message”); после деплоя будут сохраняться и получать ответ “опишите текстом”.

---

## ЧТО МЕНЯЛОСЬ В КОДЕ

| Файл | Изменение |
|------|-----------|
| `conversation.py` | Добавлен `context` (JSONB) для краткого контекста/слотов |
| `webhook.py` | Слот-филлинг записи + контекст диалога |
| `state_service.py` | Очистка контекста при resolve |
| `ops/reset.sql` | Сброс контекста при emergency reset |
| `reminder_service.py` | Авто‑закрытие handover + алерт “нет ответа” |
| `ai_service.py` | Возвращает `Result[Tuple[str, str]]` с confidence |
| `message.py` | Обработка low_confidence → эскалация |
| `webhook.py` | То же самое (ОБА файла обрабатывают сообщения!) |
| `learning_service.py` | СОЗДАН: `is_owner_response()`, `add_to_knowledge()` |
| `manager_message_service.py` | Добавлен вызов `add_to_knowledge()` для owner |
| `main.py` | Фоновый outbox worker (тик 2s, опционально через env) |
| `admin.py` | Outbox processing вынесен в общий хелпер |
| `webhook.py` | Добавлен `_process_outbox_rows()` для reuse в admin/worker |
| `schemas/telegram.py` | Добавлены `sender_chat`/`author_signature`, username у chat |
| `telegram_webhook.py` | sender_chat fallback для идентификации менеджера |
| `telegram_webhook.py` | unpin использует `handover.telegram_message_id` (fallback на callback message_id) |
| `manager_message_service.py` | Не затирает assigned_to при unknown, fallback на assigned_to для owner-check |
| `learning_service.py` | Owner match принимает отрицательные ID (sender_chat) |
| `message_service.py` | Выбор последнего содержательного user-сообщения для handover |
| `webhook.py` | human_request эскалируется с последним meaningful сообщением |
| `message.py` | То же поведение для `/message` |
| `webhook.py` | Decision engine (normalize → signals → resolve → action) + policy handler для truth gate |
| `webhook.py` | Валидация слотов записи (service/datetime/name) + запрет opt-out/фрустрации |
| `config.py` | Settings: игнорировать лишние env-поля (запуск тестов в окружении с .env) |
| `tests/test_cases.json` | Добавлены автоматизируемые кейсы для golden-прогона |
| `tests/test_message_endpoint.py` | Автотесты golden-cases (decision/signals) |
| `schemas/telegram.py` | Перевёл Pydantic Config на ConfigDict (убрал депрекейшн) |

**owner_telegram_id:** было `@ent3rprise` (НЕ РАБОТАЛО), исправлено на `1969855532`

---

## ВОПРОСЫ БЕЗ ОТВЕТА

1. **Как сообщение менеджера доходит до клиента?** Нужна трассировка от Telegram webhook до ChatFlow отправки.

2. **Правильный ли threshold?** Сейчас в коде: MID=0.5, HIGH=0.85. Дальше тюнить только по фактам (сколько эскалаций/качество ответов).

---

## СЛЕДУЮЩАЯ СЕССИЯ — ЧТО ДЕЛАТЬ

### 1. СНАЧАЛА РАЗОБРАТЬСЯ, ПОТОМ ДЕЛАТЬ

Прежде чем что-то менять:
1. Прочитать SPECS/ARCHITECTURE.md полностью
2. Прочитать SPECS/ESCALATION.md
3. Проследить путь сообщения менеджера в коде

### 2. КОНКРЕТНЫЕ ЗАДАЧИ

| Приоритет | Задача | Как проверить |
|-----------|--------|---------------|
| P0 | Вкатить latest CI image на прод (pull GHCR) | В `/admin/version` новый коммит; поведение соответствует изменениям |
| P0 | Прокинуть `instanceId` в inbound payload (ChatFlow) для всех клиентов | `payload.body.metadata.instanceId` есть; `conversation.branch_id` ставится (demo_salon + truffles ok) |
| P0 | Снизить задержку ответов (outbox): сейчас avg 17s, p90 25s | Avg/p90 < 10s |
| P0 | Починить multi‑intent при склейке (цена → запись) | Сообщения “цена+запись” ведут к сбору записи, не теряют контекст |
| P1 | Убрать дубли заявок на одного клиента | При open handover новые не создаются, идёт ответ в существующий топик |
| P1 | Пины в Telegram снимаются после "Решено" | После resolve закреп исчезает всегда |
| P1 | Проработать UX Telegram для владельца/менеджеров | Спека: как работать с заявками без хаоса |
| P1 | Добавить базовые фразы в knowledge base | "ты еще здесь?" → бот отвечает сам |
| P1 | demo_salon: правило style_reference (как у/в стиле) | Ответ без фото/без выдумок, с объяснением зависимости от базы |

### 3. КАК ДЕПЛОИТЬ

```bash
# CI build/push → pull image
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh"

# Проверить логи
ssh -p 222 zhan@5.188.241.234 "docker logs truffles-api --tail 50"

# Локальная сборка (fallback)
ssh -p 222 zhan@5.188.241.234 "docker build -t truffles-api_truffles-api /home/zhan/truffles-main/truffles-api"
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```

---

## УРОК

Жанбол прав: проблема не в том что я "несу хуйню". Проблема в контекстном окне и амнезии. Много информации, много файлов — и я теряю контекст.

Решение: ЧИТАТЬ ДОКУМЕНТАЦИЮ ПЕРЕД ТЕМ КАК ДЕЛАТЬ. Не спрашивать Жанбола — искать самому. Не извиняться — делать.

---

**Коммиты:** `8e10fa8`, `379ba4c`, `2f74e1b`, `736139e`

---

### 2025-12-12 — Неделя 2 + Неделя 3 + Улучшение workflow

**Что сделали:**

*Неделя 2 (качество кода):*
- ruff, logging (JSON), alerts integration, CI/CD, 91 тест
- Закоммичено и запушено

*Неделя 3 (защита кода):*
- Result pattern — `services/result.py`
- State service — атомарные переходы с транзакциями
- Health service — self-healing
- SQL constraint — `migrations/003_add_state_constraint.sql`
- Рефакторинг webhook.py — использует state_service
- Health endpoints — /admin/health, /admin/heal
- 121 тест всего

*Улучшили workflow архитектора:*
- Добавили секцию "ГДЕ ИСКАТЬ ОТВЕТЫ" — карта документов
- Правило: сначала grep, спрашивать только если не нашёл
- Убрали MVP-менталити из документов

**Ключевой урок:**
Все ответы уже есть в документах. Архитектор ищет, не спрашивает.

**Следующая сессия:**
- Неделя 4: Эскалация при низком confidence, Active Learning

---

### 2025-12-10 (вечер) — Архитектура мультитенанта + Дройды

**Что сделали:**

*Архитектура:*
- Разобрали иерархию Company → Client → Branch
- Обнаружили: Branch существует в БД, но не подключен к роутингу
- Добавили в план: подключить Branch (conversation.branch_id вместо client_id)
- Добавили в backlog: омниканальность (Channel) для Instagram/Telegram

*Дройды:*
- truffles-architect.md — добавили: СТАРТ СЕССИИ, РАБОТА С ЖАНБОЛОМ, ДИАГНОСТИКА, РЕВЬЮ КОДЕРА
- truffles-coder.md — добавили: СТАНДАРТ КАЧЕСТВА
- AGENTS.md — добавили: ошибка #0 "Экономлю на качестве"

*Документы:*
- SPECS/ARCHITECTURE.md — обновили схему БД (companies, branches)
- SPECS/MULTI_TENANT.md — добавили полную иерархию, роли, текущее vs конечное

**Затронутые файлы:**
- [x] STATE.md
- [x] SPECS/ARCHITECTURE.md
- [x] SPECS/MULTI_TENANT.md
- [x] AGENTS.md
- [x] .factory/droids/truffles-architect.md
- [x] .factory/droids/truffles-coder.md

**Почему так решили:**
- Документы не отражали реальную архитектуру БД → синхронизировали
- Дройд не понимал контекст на старте → добавили СТАРТ СЕССИИ
- AI экономил на качестве → добавили СТАНДАРТ КАЧЕСТВА как принцип #0
- Не было диагностики проблем → добавили раздел ДИАГНОСТИКА

**Следующая сессия:**
- [ ] Диагностика: бот не отвечает (блокер)
- [ ] Подключить Branch к роутингу
- [ ] Мозги LLM — промпт

---

### 2025-12-10 — Аудит документов + Мозги LLM

**Что сделали:**

*Часть 1: Документы и структура*
- Обновили все SPECS/ документы (синхронизация с кодом)
- Добавили метрики North Star в ESCALATION.md
- Добавили чеклист онбординга 35 мин в MULTI_TENANT.md
- Создали STRUCTURE.md — карту проекта
- Создали HOW_TO_WORK.md — инструкция для Жанбола
- Создали droid'ы: truffles-architect, truffles-coder
- Удалили мусор из ops/ (~175 файлов → архив)
- Создали STATE.md — центральный хаб
- Добавили .gitignore (исключает .archive/ops_old/)

*Часть 2: Мозги LLM*
- Проанализировали как работает бот: webhook → intent → RAG → LLM
- Нашли проблему: промпт слишком общий, бот обещает то что не умеет
- Создали API для управления промптами: `PUT /admin/prompt/{client_slug}`
- Создали API для управления настройками: `PUT /admin/settings/{client_slug}`
- Создали скрипт: `ops/update_prompt.py` с защитой от дураков
- Создали шаблон промпта: `ops/templates/prompt_template.md`

**Затронутые документы/файлы:**
- [x] STATE.md — создан, обновлён
- [x] STRUCTURE.md — создан
- [x] HOW_TO_WORK.md — создан
- [x] SPECS/ESCALATION.md — добавлены метрики
- [x] SPECS/MULTI_TENANT.md — добавлен чеклист онбординга
- [x] .factory/droids/truffles-architect.md — создан
- [x] .factory/droids/truffles-coder.md — создан
- [x] truffles-api/app/routers/admin.py — создан (API управления)
- [x] truffles-api/app/main.py — добавлен admin router
- [x] ops/update_prompt.py — скрипт управления промптами
- [x] ops/templates/prompt_template.md — шаблон промпта
- [x] .gitignore — создан

**Архитектура LLM (для справки):**
```
Сообщение → Webhook 
    → classify_intent() [LLM #1]
    → Решение (эскалация/мьют/ответ)
    → generate_ai_response() [LLM #2]
        → get_system_prompt() из БД
        → search_knowledge() из Qdrant (RAG)
        → full_prompt = system + RAG_context
        → history (10 сообщений)
        → LLM.generate()
```

**Почему так решили:**
- Документы были разрознены → создали карту и хаб
- Нет удобного управления промптами → создали API
- Промпт не ограничивал бота → создали шаблон с чёткими границами
- Хардкод SQL — плохо → API + скрипт с валидацией

**Следующая сессия:**
- [ ] Обновить промпт truffles через новый API
- [ ] Тестировать что бот не обещает лишнего
- [ ] Confidence threshold (не выдумывать если RAG пустой)
- [ ] Эскалация — добить

---

*Последнее обновление: 2025-12-26*
