# TECH_STATUS — ЧТО МОЖНО ЧЕСТНО ПРОДАВАТЬ

**Формат:** Status (OK / PARTIAL / BROKEN), Evidence, Fix plan, Go‑to‑market impact.

**План работ и приоритеты:** см. `STRATEGY/TECH_ROADMAP.md` (разделы P0/P1 и ближайшие задачи). Здесь только статус и фиксация фактов.

---

## A) WhatsApp канал и доставка

### Провайдер WhatsApp
- Status: PARTIAL
- Evidence: `TECH.md`, `truffles-api/app/services/chatflow_service.py`, `SPECS/SYSTEM_REFERENCE.md`
- Факт: используется ChatFlow API (`https://app.chatflow.kz/api/v1/*`).
- Boundary: не подтверждено, что это официальный WhatsApp Business API; риск блокировок/лимитов зависит от ChatFlow.
- Fix plan: верифицировать тип подключения у ChatFlow + задокументировать лимиты/политику.
- Go‑to‑market impact: на сайте говорим “WhatsApp через ChatFlow”, без обещаний “официальный WA API”.

### Надёжность доставки (outbox/retry/dedup)
- Status: OK
- Evidence: `truffles-api/app/services/outbox_service.py`, `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/app/services/chatflow_service.py`, `ops/migrations/012_add_outbox_messages.sql`, `ops/migrations/010_add_message_dedup.sql`
- Факт: ACK‑first → outbox; retries + backoff; inbound dedup (Redis + DB); outbound idempotency `msg_id`.
- Boundary: гарантия “at‑least‑once”, не “exactly once”.
- Fix plan: добавить outbox status history/processing_started_at (для SLA decomposition).
- Go‑to‑market impact: можно обещать “сообщения не теряются, есть повторные попытки”.

### Outbound guard (TEST_MODE + allowlist)
- Status: RISK
- Evidence: `truffles-api/app/services/chatflow_service.py`
- Факт: при `TEST_MODE=1` отправка SKIP (возвращает `True`), если JID не в `OUTBOUND_ALLOWLIST_JIDS`.
- Boundary: выглядит как “бот молчит” при реальном тесте без allowlist.
- Fix plan: `TEST_MODE=0` на проде или явное ведение allowlist; вывести флаг в /admin/health.
- Go‑to‑market impact: без этого нельзя гарантировать ответы пользователю.

### SLA ответов
- Status: PARTIAL
- Evidence: `STATE.md` (SLA замеры), `/admin/metrics` (outbox_latency_p50/p90)
- Факт: последние зафиксированные значения в `STATE.md`; в проде есть метрики `/admin/metrics`.
- Boundary: зависит от LLM/ChatFlow/Qdrant; LLM timeouts возможны.
- Fix plan: регулярно фиксировать p50/p90 из `/admin/metrics` как “официальные цифры”.
- Go‑to‑market impact: обещаем диапазон, а не “мгновенно”.

### Rate limiting
- Status: PARTIAL
- Evidence: `truffles-api/app/routers/webhook/_legacy.py` (media rate limit)
- Факт: rate‑limit есть только для медиа; текстовые сообщения без лимитов.
- Fix plan: добавить per‑tenant rate‑limits для текста.
- Go‑to‑market impact: не обещать “безлимитный поток сообщений”.

---

## B) Запись через Telegram

### Что такое “запись” в Telegram
- Status: PARTIAL
- Evidence: `truffles-api/app/models/handover.py`, `truffles-api/app/services/escalation_service.py`, `truffles-api/app/routers/telegram_webhook.py`
- Факт: создаётся `handover` (pending/active/resolved) + Telegram topic; это **лид/заявка**, не CRM‑запись.
- Boundary: статусы/даты/мастера не подтверждаются автоматически.
- Fix plan: явный “booking” объект + статусы, если хотим обещать полноценную запись.
- Go‑to‑market impact: продаём как “заявка менеджеру/подключение менеджера”, а не “автоматическая запись”.

### Telegram ↔ WhatsApp связка
- Status: PARTIAL
- Evidence: `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/routers/telegram_webhook.py`
- Факт: маршрутизация идёт по `telegram_chat_id` + `message_thread_id` (topic).
- Boundary: нет e2e теста на связку; возможны edge‑cases без topic_id.
- Fix plan: добавить смоук‑тест на связку + health‑check.
- Go‑to‑market impact: обещаем “менеджер получает заявки в Telegram”, без гарантии на edge‑cases.

### Запрет перенос/отмена
- Status: PARTIAL
- Evidence: `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml`
- Факт: policy‑gate для reschedule/cancel реализован.
- Boundary: правило закреплено на уровне demo‑pack.
- Fix plan: закрепить в policy клиента + автотесты на каждом клиенте.

---

## C) “Не выдумывает”

### Truth‑first / policy‑gate
- Status: OK (demo_salon)
- Evidence: `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml`
- Факт: факты из Client Pack; риск‑темы эскалируются; low_confidence → clarify.
- Boundary: truth‑first гарантируется только при заполненном Client Pack.

### OOD / smalltalk
- Status: PARTIAL
- Evidence: `truffles-api/app/services/intent_service.py`, `truffles-api/app/knowledge/demo_salon/INTENTS_PHRASES_DEMO_SALON.yaml`
- Факт: OOD якоря есть, smalltalk ограничен.
- Boundary: пороги требуют калибровки, возможны false‑positives.
- Fix plan: калибровка anchors_out по backlog + тест‑батарее.

### Истина и обновления знаний
- Status: PARTIAL
- Evidence: `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`, `ops/sync_client.py`, `truffles-api/app/services/knowledge_service.py`
- Факт: факты живут в Client Pack + Qdrant; sync через `ops/sync_client.py`.
- Boundary: версионирования паков нет; “какие факты использованы” хранится только через rag_scores/decision_trace.
- Fix plan: добавить версию client_pack и лог использованных фактов.

---

## D) Мульти‑тенантность и безопасность

### Изоляция tenant
- Status: PARTIAL
- Evidence: `truffles-api/app/services/knowledge_service.py`, `truffles-api/app/routers/webhook/_legacy.py`, `SPECS/MULTI_TENANT.md`
- Факт: фильтрация по client_slug/client_id в RAG и routing.
- Boundary: нет формального теста на cross‑tenant leakage.
- Fix plan: добавить тест‑контракт “tenant isolation”.

### Секреты и токены
- Status: PARTIAL
- Evidence: `TECH.md`, `.github/workflows/ci.yml` (gitleaks), `SPECS/INFRASTRUCTURE.md`
- Факт: секреты ожидаются в `.env`/GitHub Secrets; gitleaks включён в CI.
- Boundary: нужна регулярная проверка истории/логов.
- Fix plan: добавить “secret audit” в операционный чеклист.

### Debug endpoint exposure
- Status: OK
- Evidence: `truffles-api/app/routers/webhook/_legacy.py` (`/webhook/debug`)
- Факт: доступ только при `DEBUG_WEBHOOK_ENABLED=true` и валидном `X-Admin-Token`; иначе 404/401.
- Boundary: флаг/токен должны быть под контролем (prod default — disabled).
- Fix plan: держать `DEBUG_WEBHOOK_ENABLED=false` по умолчанию.

---

## E) Прод‑готовность

### Деплой и воспроизводимость
- Status: PARTIAL
- Evidence: `TECH.md`, `/home/zhan/restart_api.sh`, `.github/workflows/ci.yml`
- Факт: GHCR build/push + restart через `IMAGE_NAME`/`PULL_IMAGE=1`.
- Boundary: локальная сборка всё ещё возможна (risk drift).
- Fix plan: запретить локальный build на проде (policy).

### Мониторинг и алерты
- Status: PARTIAL
- Evidence: `truffles-api/app/services/alert_service.py`, `/admin/health`, `/admin/metrics`
- Факт: Telegram alerts и админ‑эндпойнты есть.
- Boundary: нет единой панели/алерт‑политики по SLA/LLM/ChatFlow.
- Fix plan: выделить один “pilot dashboard”.

### Бэкапы и аудит
- Status: PARTIAL
- Evidence: `TECH.md`, `SPECS/INFRASTRUCTURE.md`, `ops/backup_postgres.sh`, `ops/backup_qdrant.sh`
- Факт: скрипты и план описаны; фактический cron требует проверки.
- Fix plan: проверить cron на сервере, добавить “restore drill”.

---

## F) Диалог и живость

### Answer‑Interpreter порог
- Status: OK
- Evidence: `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/app/services/ai_service.py`
- Факт: интерпретатор принимается при `confidence >= 0.65` или валидном slot/value (expected_reply).
- Boundary: нет отдельного eval‑контракта на expected_reply.
- Fix plan: добавить eval‑кейсы для expected_reply.

### Router fallback_reason (SLA)
- Status: OK
- Evidence: `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/app/routers/webhook/trace.py`
- Факт: fallback_reason enum = timeout/invalid_json/budget_exceeded/no_api_key/prompt_missing/empty_message/empty_response/invalid_class/unsupported_temperature/error.
- Факт: низкая уверенность фиксируется отдельно (`controller_low_confidence`), не как fallback_reason.
- Факт: при отсутствии `OPENAI_API_KEY` controller_attempted=false (router не пытается).
- Metric: fallback_rate = count(controller_attempted=true AND controller_fallback_reason IS NOT NULL) / count(controller_attempted=true).
- Fix plan: держать fallback_rate <10% в core/long (SQL + CI).

### Datetime fallback
- Status: PARTIAL
- Evidence: `truffles-api/app/routers/webhook/_legacy.py`
- Факт: распознаёт `HH:MM`/`HH.MM`, “в 6/к 3”, `01.02`, “10 января” + базовые ключевые слова.
- Boundary: “после 7”, “в конце недели” остаются слабо покрыты.
- Fix plan: заменить эвристики на resolver‑слой (data‑lexicon RU/KZ + `dateparser`/`rapidfuzz`), минимальные EVAL‑варианты как доказательство.

### Carryover follow‑up (pricing)
- Status: OK
- Evidence: `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/tests/test_message_endpoint.py`
- Факт: короткие pricing‑вопросы (“Сколько стоит?”, “Цена?”) считаются follow‑up.
- Boundary: нет отдельного CI‑кейса на carryover follow‑up.
- Fix plan: добавить eval‑кейс в core/long.

---

## G) Онбординг и обучение

### Быстрый онбординг
- Status: PARTIAL
- Evidence: `SPECS/MULTI_TENANT.md`, `ops/sync_client.py`, `STRUCTURE.md`
- Факт: онбординг сейчас ручной (SQL + pack + sync); `onboard_client.py` отсутствует в репозитории.
- Boundary: нет self‑serve/авто‑конвейера.
- Fix plan: автоматизация после A4–A7 (см. `STRATEGY/TECH_ROADMAP.md`), иначе риск масштабирования хаоса.
- Go‑to‑market impact: не обещать “быстрый self‑serve”, только ассистированный онбординг.

### Auto‑learning
- Status: PARTIAL
- Evidence: `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/services/learning_service.py`,
  `truffles-api/app/models/learned_response.py`, `truffles-api/app/routers/webhook/_legacy.py`
- Факт: owner‑ответы могут автоматически попадать в Qdrant; очередь learned_responses и модерация не wired.
- Boundary: автообучение не полное, нет гарантии “становится умнее” без участия владельца.
- Fix plan: очередь learned_responses + модерация (P2), см. `SPECS/ACTIVE_LEARNING.md`.
- Go‑to‑market impact: обещаем только owner‑approved learning.

## Phase‑0 Definition of Done (перед первым платным клиентом)
- LAW‑темы всегда эскалируются (тесты + live‑check).
- Truth‑first по топ‑вопросам (часы, адрес, услуги, цены, запись).
- Outbox + retries работают; inbound dedup включён.
- /admin/version соответствует последнему коммиту.
- Core‑50 EVAL проходит в CI (extended — nightly).
- 5‑минутный smoke‑run успешен (см. ниже).

---

## Pilot Readiness Checklist (5–10 min)
- 1) Версия и билд актуальны (C1) — OK/Fail
- 2) Health без критичных ошибок (C2) — OK/Fail
- 3) Метрики доступны (C3) — OK/Fail
- 4) Outbox processing отвечает (C4) — OK/Fail
- 5) Outbox backlog в норме (S1) — OK/Fail
- 6) Decision meta/trace пишутся (S2) — OK/Fail
 
Быстрый прогон: `python3 ops/diagnose.py` (version/health/metrics/outbox/decision_meta).

### Run Log (fill after checklist)
- Date/Time: 2025-12-31T11:07:15+05:00
- Version (/admin/version): main / 247547586335b78e65d159a908b5b2893242c09b (build_time 2025-12-31T05:50:28Z)
- Summary: PASS
- Fails (if any): none

### Smoke commands (copy/paste)
```bash
# 1) Версия/живость
curl -s http://localhost:8000/admin/version
curl -s http://localhost:8000/admin/health

# 2) Метрики за сегодня
curl -s -H "X-Admin-Token: $ALERTS_ADMIN_TOKEN" \
  "http://localhost:8000/admin/metrics?client_slug=demo_salon&metric_date=$(date +%F)"

# 3) Outbox (последние 10)
docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c \
"SELECT status, created_at, updated_at FROM outbox_messages ORDER BY created_at DESC LIMIT 10;"

# 4) Decision meta присутствует
docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c \
"SELECT metadata->'decision_meta' FROM messages ORDER BY created_at DESC LIMIT 5;"
```

### Live smoke (ручной)
- “Сколько стоит маникюр, сколько длится, где находитесь и можно записаться?”
- “по адресу”
- “по записи”
