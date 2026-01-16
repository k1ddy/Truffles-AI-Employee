# SYSTEM REFERENCE — Техническая справка Truffles

**Статус:** CANON  
**Owner:** Top Architect  
**Обновлено:** 2026-01-15  
**Scope:** техсправка и операционные детали; поведение бота см. `SPECS/ARCHITECTURE.md` и `SPECS/CONSULTANT.md`.  
**Out of scope:** продуктовые обещания, SLA продаж.  
**Links:** `SPECS/ARCHITECTURE.md`, `SPECS/INFRASTRUCTURE.md`, `TECH.md`, `STATE.md`.

**Читай это перед любыми изменениями.**
---

## 0. Start Here — Process Map (session → audit → evidence)

**Если амнезия/неясно с чего начать:**
1) Открой `AGENTS.md` → `STATE.md` → `STRUCTURE.md`.
2) Определи роль и Task Package (если нет — STOP и вопрос владельцу).
3) Для CA‑аудита открой `STRATEGY/TECH_ROADMAP.md` (CA‑plan) и раздел 4.3 (Live‑check SOP).
4) Отдели аудит от фикса: аудит = evidence, фикс = отдельный Task Package с CA‑ID.

**Правила evidence:**
- Единственный источник фактов — `STATE.md` (PASS/FAIL с conv_id/trace/SQL/CI).
- Статусы в CA‑plan — только статусы аудита; `verified/gap` всегда с ссылкой на `STATE.md`.
- Если live‑check невозможен → статус **BLOCKED**, без подмены.

**Карта инструментов (что запускать):**
- `ops/diagnose.py livecheck` — реальный inbound через ChatFlow, маркеры для SQL evidence.
- `ops/diagnose.py` — health/metrics/outbox snapshot.
- `ops/diagnose.py deploy-verify` — проверка версии деплоя (`/admin/version`) и совпадения commit.
- `ops/sync_client.py` — validate/sync client packs (truth → Qdrant).
- `/home/zhan/restart_api.sh` — restart API контейнера.
- SQL evidence: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "<SQL>"`.

**Где фиксировать изменения:**
- Статус/evidence → `STATE.md` (Brain последним шагом).
- Статус аудита → `STRATEGY/TECH_ROADMAP.md` (Top Architect, со ссылкой на `STATE.md`).
- Процессы/инварианты → `SPECS/*` или `STRATEGY/*` (owner‑docs).

## 1. Репозиторий и процесс

| Параметр | Значение |
|----------|----------|
| Репозиторий | `github.com/k1ddy/Truffles-AI-Employee` (один) |
| Главная ветка | `main` |
| Политика PR | По умолчанию через PR + CI; прямые коммиты в main — исключение. |
| CI | `.github/workflows/ci.yml` — ruff + pytest |

---

## 2. Стек технологий

| Компонент | Технология |
|-----------|------------|
| Backend API | Python 3.11 + FastAPI |
| База данных | PostgreSQL 15 |
| Векторная БД | Qdrant (self-hosted) |
| Embeddings | BGE-M3 (self-hosted, default `http://bge-m3:80/embed`, override `BGE_M3_URL`) |
| LLM | OpenAI-compatible API (default `FAST_MODEL=gpt-5-mini`; router uses `ROUTER_MODEL` or `gpt-4o-mini` when FAST_MODEL starts with gpt-5) |
| Кэш/очереди | Redis |
| Оркестрация | Docker (API через `restart_api.sh`), compose — для инфры/локально |
| Reverse proxy | Traefik |
| WhatsApp | ChatFlow API (`app.chatflow.kz`) |
| Telegram | Bot API (webhook) |
| Сервер | VPS 5.188.241.234, порт SSH 222 |

**Docker версии:** Docker 28.3.2, Compose v2.38.2

---

## 3. Секреты и доступы

| Где | Что |
|----|-----|
| `/home/zhan/truffles-main/truffles-api/.env` | Основные секреты (OPENAI_API_KEY, DATABASE_URL, QDRANT_*) |
| БД `client_settings` | telegram_bot_token, owner_telegram_id |
| Код `chatflow_service.py` | `CHATFLOW_TOKEN` берётся из env (в .env), хардкода нет |

---

## 4. Деплой

**docker-compose в проде:** инфра‑стек разделён: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`); был кейс `KeyError: 'ContainerConfig'` на `up/build`. API деплой — через `/home/zhan/restart_api.sh`. `/home/zhan/truffles-main/docker-compose.yml` — заглушка.

**Стандарт (CI/GHCR):**
```bash
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh"
```

**Fallback (локальная сборка):**
```bash
ssh -p 222 zhan@5.188.241.234 "docker build -t truffles-api_truffles-api /home/zhan/truffles-main/truffles-api"
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```

**Логи:**
```bash
ssh -p 222 zhan@5.188.241.234 "docker logs truffles-api --tail 50"
```

`restart_api.sh` поддерживает `IMAGE_NAME` и `PULL_IMAGE=1`.

**restart_api.sh:**
```bash
#!/bin/bash
IMAGE_NAME="${1:-${IMAGE_NAME:-truffles-api_truffles-api}}"
PULL_IMAGE="${PULL_IMAGE:-0}"

if [ "$PULL_IMAGE" = "1" ]; then
  docker pull "$IMAGE_NAME"
fi

docker stop truffles-api 2>/dev/null
docker rm truffles-api 2>/dev/null
cd /home/zhan/truffles-main/truffles-api
docker run -d --name truffles-api \
  --env-file .env \
  --network truffles_internal-net \
  --network proxy-net \
  -p 8000:8000 \
  --restart unless-stopped \
  -l traefik.enable=true \
  -l 'traefik.http.routers.truffles-api.rule=Host(`api.truffles.kz`)' \
  -l traefik.http.routers.truffles-api.entrypoints=websecure \
  -l traefik.http.routers.truffles-api.tls.certresolver=myresolver \
  -l traefik.http.services.truffles-api.loadbalancer.server.port=8000 \
  -l traefik.docker.network=proxy-net \
  "$IMAGE_NAME"
```

**Проверка нового кода:**
```bash
ssh -p 222 zhan@5.188.241.234 "curl -s http://localhost:8000/admin/version"
ssh -p 222 zhan@5.188.241.234 "curl -s http://localhost:8000/admin/health"
```
⚠️ `/admin/version` возвращает `unknown`, если не переданы build-метаданные (APP_VERSION/GIT_COMMIT/BUILD_TIME) в контейнер.

---

## 4.1 Knowledge update SOP (client_pack → runtime)

**Цель:** избежать рассинхрона `SALON_TRUTH.yaml` ↔ Qdrant ↔ runtime контейнера.

1) **Обновить pack**: `truffles-api/app/knowledge/<client_slug>/SALON_TRUTH.yaml` (+ при необходимости `knowledge/<client_slug>/*.md`).
2) **Валидировать pack** (только python3):
   ```bash
   python3 ops/sync_client.py <client_slug> --validate
   ```
3) **Синхронизировать Qdrant**:
   ```bash
   python3 ops/sync_client.py <client_slug>
   ```
4) **Собрать и перезапустить API** (см. раздел 4). Без `docker cp`/`docker run -v`.
5) **Live-check** (реальный inbound): 1–2 запроса на новые услуги/правила + SQL evidence (`messages.metadata.decision_meta`, `conversations.context.decision_trace`).

**Замечания:**
- `ops/sync_client.py` использует `QDRANT_API_KEY`/`QDRANT__SERVICE__API_KEY` из окружения и `BGE_M3_URL`.
- Онбординг клиента подробно: `SPECS/MULTI_TENANT.md`.

---

## 4.2 Release SOP (code changes)

**Цель:** релиз без дрейфа и без “магии”.

1) **Task Package** содержит DoD/Tests/Live-check/Evidence (иначе STOP).
2) **CI зелёный** (core/long по задаче) — ссылка на run обязательна.
3) **Деплой** по разделу 4 (GHCR → `PULL_IMAGE=1`; fallback build допустим).
4) **Проверка версии**: `/admin/version` + `/admin/health` (если version unknown → STOP).
5) **Live-check** (если указан в DoD): реальный inbound → conv_id + decision_trace/meta.
6) **STATE.md** обновляет Brain последним шагом, с evidence.

**Запрещено:** `docker cp`, `docker run -v`, “локальные” фиксы без CI/перезапуска.

---

## 4.2.1 Deploy Guardrails (anti-drift)

**Цель:** исключить ситуацию “CI зелёный, а контейнер на старом коде”.

**Инварианты (обязательны в проде):**
- Контейнер запускается только из GHCR‑образа (`ghcr.io/k1ddy/truffles-ai-employee:*`).
- `/admin/version` не должен быть `unknown`.
- `git_commit` в `/admin/version` обязан совпадать с SHA деплоя.

**Как обеспечиваем:**
```bash
IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main \
PULL_IMAGE=1 REQUIRE_GHCR=1 VERIFY_VERSION=1 \
EXPECTED_GIT_COMMIT=<sha> EXPECTED_VERSION=main \
bash /home/zhan/restart_api.sh
```

**Ручная проверка:**
```bash
python3 ops/diagnose.py deploy-verify --base-url https://api.truffles.kz \
  --expected-commit <sha> --expected-version main
```

**STOP‑line:** версия `unknown` или commit mismatch.

---

## 4.3 Live-check SOP (CA audit)

**Зачем:** доказать соответствие канону на реальном inbound, убрать дрейф и “каждый раз по‑разному”, зафиксировать готовность к онбордингу.

**Кто делает:**
- **Hands/OPS:** запускают live‑check runner.
- **Brain:** снимает evidence из БД и фиксирует в `STATE.md`.
- **Top Architect:** обновляет статус аудита в `STRATEGY/TECH_ROADMAP.md` (CA‑plan) только со ссылкой на `STATE.md`.

**Перед запуском (обязательно):**
- Используем **отдельный тестовый номер** (внешний JID). Self‑send в ChatFlow не гарантирует доставку на телефон.
- Делаем короткий ping на тестовый номер. Если не дошло — **STOP**, чинить доставку.
- Проверяем согласованность instance_id:
  - `clients.config.instance_id` — outbound instance (ChatFlow).
  - `branches.instance_id` — routing token для branch.
  - `instanceId` в webhook query — routing token (должен совпадать с `branches.instance_id`).

**Операторская инструкция (без тех. знаний):**
- Оператор **не** знает время/conv_id/msg_id/SQL. Это снимает Brain/OPS.
- Оператор только отправляет сообщения по шаблонам ниже и пишет “готово”.
- Порядок строго такой: сообщение → дождаться ответа бота → ACK (`ок`/`да`/`жду`) → дождаться ответа → следующий кейс.
- Если ответа нет 2–3 минуты — **STOP**, сообщить Brain/OPS (проверка доставки/outbox).
- Шаблоны ниже — **ориентиры**, не канон. Главное — смысл категории.

**CA‑01 — текстовые шаблоны (выберите по одному из каждой группы):**
- **Refund:** `хочу вернуть деньги` / `верните оплату` / `нужен возврат денег`
- **Payment:** `можно оплатить картой?` / `есть каспи?` / `можно оплатить переводом?`
- **Reschedule:** `перенесите запись на завтра` / `поменять дату записи` / `переписать на другой день`
- **Medical:** `беременна, можно?` / `аллергия на гель‑лак` / `жжет после окрашивания`

**Человеческие вариации (разрешены и полезны):**
- Опечатки, лишние слова, смайлы, разный регистр — можно.
- Смысл должен сохраняться (refund/payment/reschedule/medical).
- Если удобно, добавляйте короткий тег в конце: `[CA01-1]`, `[CA01-2]` — это ускоряет поиск в БД, но не обязательно.

**Почему такой процесс:**
- Live‑check требует **реального inbound**: только он пишет `decision_meta` и `decision_trace`.
- `send-text`/симуляции не доказывают доставку на телефон, поэтому без внешнего номера audit невалиден.
- Policy‑кейсы переводят диалог в `pending`; без ACK следующий кейс не попадёт в `policy_gate`.
- Вариативные тексты нужны, чтобы проверить устойчивость к человеческим ошибкам, а не “под шаблон”.

**Как проверяем (процесс):**
1) Выбрать CA‑suite (например, `ca01-core`) и окно запуска.
2) Запустить runner (реальный inbound через ChatFlow → `/webhook/{client_slug}`).
3) Brain снимает evidence в БД по marker‑логам (decision_meta + decision_trace).
4) Brain фиксирует PASS/FAIL в `STATE.md` с ссылкой на CA‑ID и артефактами.
5) Top Architect обновляет статус CA‑пункта в `STRATEGY/TECH_ROADMAP.md` с ссылкой на `STATE.md`.
6) Если runner/БД недоступны → статус **BLOCKED**, без фиктивных проверок.

**Принципы:**
- Реальный inbound обязателен (WhatsApp → ChatFlow → `/webhook/{client_slug}`).
- Любой `verified/gap` в CA‑plan обязан ссылаться на evidence в `STATE.md`.
- Токены/секреты **не** попадают в git/логи.
- Если runner недоступен — статус **BLOCKED**, без ручных “подмен”.

**Типы проверок:**
- **CI (gate):** автоматические тесты до релиза, без live‑evidence.
- **Live‑check (CA audit):** реальный inbound + trace/meta + evidence в `STATE.md`.
- **SQL‑snapshot:** подтверждение метрик/состояния (outbox/SLA/trace coverage).

**Запуск (runner):**
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

```sql
SELECT trace
FROM conversations c
JOIN LATERAL jsonb_array_elements(c.context->'decision_trace') AS trace ON true
WHERE c.id = '<CONVERSATION_ID>'
  AND trace->>'stage' = '<EXPECTED_STAGE>'
ORDER BY (trace->>'recorded_at')::timestamptz DESC
LIMIT 3;
```

**Что фиксируем в STATE.md:**
- conv_id + msg_id + decision_meta ключи + trace JSON + PASS/FAIL.
- Ссылка на CA‑ID (например: `CA-01`).

**Где искать процесс:**
- Этот раздел (`SPECS/SYSTEM_REFERENCE.md` → Live‑check SOP).
- CA‑plan в `STRATEGY/TECH_ROADMAP.md` (статусы аудита).
- Стартовый ритуал: `docs/SESSION_START_PROMPT.txt`.

---

## 5. Архитектура — потоки данных

### WhatsApp → Бот (факт)
```
WhatsApp клиент
    ↓
ChatFlow (app.chatflow.kz)
    ↓
POST /webhook/{client_slug} (legacy wrapper: /webhook)
    ↓
ACK-first: outbox enqueue
    ↓
outbox worker/cron → _handle_webhook_payload
    ↓
decision graph (state/LAW/policy/booking/info/consult)
    ↓
chatflow_service → WhatsApp
```

### Эскалация
```
Low confidence (RAG score < MID_CONFIDENCE_THRESHOLD, сейчас 0.5) ИЛИ intent=HUMAN_REQUEST/FRUSTRATION
    ↓
state_service.escalate_to_pending() + escalation_service.send_telegram_notification()
    ↓
Создать handover
    ↓
Topic в Telegram: если у клиента нет topic_id — создать, иначе использовать существующий
    ↓
Кнопки [Беру] [Решено]
```

### Менеджер → Клиент
```
Менеджер пишет в Telegram топик
    ↓
POST /telegram-webhook
    ↓
manager_message_service.process_manager_message()
    ↓
resolve user/topic → active handover (pending/active)
    ↓
chatflow_service → WhatsApp клиент
    ↓
(если owner) learning_service.add_to_knowledge()
```

---

## 6. База данных — ключевые таблицы

### conversations
```sql
id                  UUID PRIMARY KEY
client_id           UUID
user_id             UUID REFERENCES users
channel             TEXT  -- whatsapp, telegram, instagram
state               TEXT  -- bot_active, pending, manager_active
telegram_topic_id   BIGINT  -- копия users.telegram_topic_id для активного диалога
bot_status          TEXT  -- active, muted
bot_muted_until     TIMESTAMP
last_message_at     TIMESTAMP
```

### users
```sql
id                  UUID PRIMARY KEY
client_id           UUID
remote_jid          TEXT
telegram_topic_id   BIGINT  -- канон: один топик на клиента
```

### handovers
```sql
id                  UUID PRIMARY KEY
conversation_id     UUID REFERENCES conversations
client_id           UUID
status              TEXT  -- pending, active, resolved
trigger_type        TEXT  -- intent, low_confidence
user_message        TEXT
manager_response    TEXT
assigned_to         TEXT  -- telegram_id менеджера
telegram_message_id BIGINT
```

### client_settings
```sql
client_id           UUID PRIMARY KEY
telegram_chat_id    TEXT  -- ID группы Telegram
telegram_bot_token  TEXT
owner_telegram_id   TEXT  -- для определения owner
```

---

## 7. Ключевые функции

### find_conversation_by_telegram
```python
def find_conversation_by_telegram(db, chat_id, message_thread_id=None):
    # 1. Найти client по chat_id
    settings = db.query(ClientSettings).filter(
        ClientSettings.telegram_chat_id == str(chat_id)
    ).first()

    # 2. Требуем message_thread_id (топик клиента)
    if not message_thread_id or not settings:
        return None

    # 3. Найти user по topic_id
    user = db.query(User).filter(
        User.client_id == settings.client_id,
        User.telegram_topic_id == message_thread_id,
    ).first()
    if not user:
        return None

    # 4. Найти активный handover по этому user
    handover = (
        db.query(Handover)
        .join(Conversation, Conversation.id == Handover.conversation_id)
        .filter(
            Conversation.user_id == user.id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == handover.conversation_id)
        .first()
        if handover
        else None
    )

    return (conversation, handover)
```

### is_owner_response
```python
def is_owner_response(db, client_id, manager_telegram_id):
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == client_id
    ).first()
    return str(manager_telegram_id) == settings.owner_telegram_id
```

---

## 8. Telegram

| Параметр | Значение |
|----------|----------|
| Тип группы | Супергруппа с темами (forum) |
| Webhook URL | `https://api.truffles.kz/telegram-webhook` |
| Кнопки | Inline buttons: `take_{handover_id}`, `return_{handover_id}`, `skip_{handover_id}`; после take заменяются на `resolve_{handover_id}` |
| Owner detection | `client_settings.owner_telegram_id` == `from_user.id` |
| Manager | Любой кто пишет в топике при активной заявке |

**Проверить webhook:**
```bash
curl "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
```

---

## 9. WhatsApp / ChatFlow

**Входящий webhook payload:**
```json
{
  "client_slug": "demo_salon",
  "body": {
    "messageType": "text",
    "message": "текст сообщения",
    "metadata": {
      "remoteJid": "77001234567@s.whatsapp.net",
      "messageId": "...",
      "sender": "...",
      "timestamp": 123456789
    }
  }
}
```

**Исходящий (ChatFlow):**
```
GET https://app.chatflow.kz/api/v1/send-text
  ?token={CHATFLOW_TOKEN}
  &instance_id={instance_id}
  &jid={remoteJid}
  &msg={message}
```

**Ретраи:** НЕТ. Один запрос, при ошибке — лог + return False.

---

## 10. Эскалация и Confidence

### Thresholds
| Параметр | Значение | Файл |
|----------|----------|------|
| Qdrant score_threshold | 0.5 | knowledge_service.py |
| MID_CONFIDENCE_THRESHOLD | 0.5 | ai_service.py |
| HIGH_CONFIDENCE_THRESHOLD | 0.85 | ai_service.py |

### Intents
| Всегда эскалируются | `HUMAN_REQUEST`, `FRUSTRATION` |
| Не эскалируются по интенту | Остальные (но могут по low confidence) |

### Цели качества (из документов)
| Метрика | Цель |
|---------|------|
| Quality Deflection | >40% |
| Goal Completion | >60% |
| CSAT | >4.0 |

---

## 11. Learning (Active Learning)

**Триггер:** В `manager_message_service.py` после ответа owner.

**Что сохраняется в Qdrant:**
```python
content = f"Вопрос: {handover.user_message}\nОтвет: {handover.manager_response}"
metadata = {
    "client_slug": client_slug,
    "source": "owner",
    "handover_id": str(handover.id),
    "question": handover.user_message,
    "answer": handover.manager_response
}
```

**Qdrant коллекция:** из env `QDRANT_COLLECTION`, размерность 1024

---

## 12. Логирование

| Параметр | Значение |
|----------|----------|
| Формат | JSON |
| Уровень | INFO (DEBUG не показывается) |
| Где смотреть | `docker logs truffles-api` |
| Correlation ID | НЕТ |

---

## 13. Тестирование

| Параметр | Значение |
|----------|----------|
| Фреймворк | pytest |
| Путь | `truffles-api/tests/` |
| conftest.py | Есть |
| Тестовая БД | SQLite in-memory |
| Моки | `unittest.mock.patch` |
| Сервисы в CI | Нет (только mocks) |

**Запуск:**
```bash
cd truffles-api
pytest tests/ -v
```

---

## 14. Ключевые файлы

| Файл | Назначение |
|------|------------|
| `app/routers/webhook/_legacy.py` | Входящие от WhatsApp |
| `app/routers/telegram_webhook.py` | Входящие от Telegram |
| `app/routers/message.py` | Альтернативный endpoint сообщений |
| `app/services/ai_service.py` | Генерация ответов, confidence |
| `app/services/knowledge_service.py` | RAG поиск в Qdrant |
| `app/services/escalation_service.py` | Создание эскалаций |
| `app/services/manager_message_service.py` | Обработка ответов менеджера |
| `app/services/learning_service.py` | Автообучение |
| `app/services/chatflow_service.py` | Отправка в WhatsApp |
| `app/services/state_service.py` | Переходы состояний |

---

## 15. Известные проблемы (legacy)

Актуальные GAP/риски ведём в `docs/IMPERIUM_GAPS.yaml` и `STATE.md`. Этот список — исторический, требует проверки.

### Критичные
1. **Manager reply не работает** — `find_conversation_by_telegram` возвращает None
2. **Active Learning не вызывается** — нет логов "Owner response detected"
3. **Эскалация на всё** — threshold 0.7 слишком высокий

### Инфраструктурные
1. **docker-compose сломан** — `KeyError: 'ContainerConfig'`
2. **Нет /version endpoint** — сложно проверить версию кода
3. **Нет correlation ID** — сложно трейсить запросы

### Данные
1. **State не синхронизирован** — conversation.state=pending при handover.status=resolved

---

## 16. Droids

| Droid | Файл | Назначение |
|-------|------|------------|
| truffles-architect | `.factory/droids/truffles-architect.md` | Архитектура, планирование |
| truffles-coder | `.factory/droids/truffles-coder.md` | Реализация кода |
| truffles-ops | `.factory/droids/truffles-ops.md` | DevOps, деплой |

---

## 17. Без ответа (требует уточнения)

| # | Вопрос |
|---|--------|
| 9 | Что можно ротировать из секретов |
| 10 | Firewall правила |
| 37 | 10 кейсов спама эскалации |
| 46 | Максимальный размер context для droids |

---

## 18. Рекомендации Droid (требуют согласования)

### Смоук на проде
```
1. GET /health → 200
2. POST /webhook с тестовым payload → не 500
3. Telegram webhook доступен
```

### Staging
Нужен тестовый клиент или второй контейнер на порту 8001.

### Разрешения агентов
**Без апрува:** чтение, тесты, PR
**С апрувом:** мерж, деплой, миграции
**Запрещено:** DROP, force push, temporary hacks

---

*Последнее обновление: 2025-12-13*
