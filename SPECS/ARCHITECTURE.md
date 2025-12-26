# ARCHITECTURE — Техническая архитектура Truffles

**Читай это перед любыми изменениями.**
**Обновлено:** 2025-12-25

---

## 1. Репозиторий и процесс

| Параметр | Значение |
|----------|----------|
| Репозиторий | `github.com/k1ddy/Truffles-AI-Employee` (один) |
| Главная ветка | `main` |
| Политика PR | Не формализована. Коммиты напрямую в main. |
| CI | GitHub Actions (`.github/workflows/ci.yml`): ruff+pytest, build+push to GHCR, optional deploy |

---

## 2. Стек технологий

| Компонент | Технология |
|-----------|------------|
| Backend API | Python 3.11 + FastAPI |
| База данных | PostgreSQL 15 |
| Векторная БД | Qdrant (self-hosted) |
| Embeddings | BGE-M3 (self-hosted, HTTP `http://bge-m3:8080/embed`) |
| LLM | OpenAI API (по умолчанию `gpt-5-mini`) |
| Кэш/очереди | Redis |
| Оркестрация | Docker (prod), Docker Compose (local) |
| Reverse proxy | Traefik |
| WhatsApp | ChatFlow API (`app.chatflow.kz`) |
| Telegram | Bot API (webhook) |
| Сервер | VPS 5.188.241.234, порт SSH 222 |

**Docker версии:** Docker 28.3.2, Compose v2.38.2

---

## 3. Секреты и доступы

| Где | Что |
|----|-----|
| `/home/zhan/truffles-main/truffles-api/.env` | Основные секреты (OPENAI_API_KEY, DATABASE_URL, QDRANT_*, ALERT_*, CHATFLOW_*) |
| `/home/zhan/infrastructure/.env` | Инфра‑секреты (postgres, qdrant, pgadmin, redis, traefik) |
| БД `client_settings` | telegram_bot_token (global per client) |
| БД `branches` | telegram_chat_id (группа Telegram на филиал) |
| БД `agents/agent_identities` | роли и идентичности менеджеров |
| Код `chatflow_service.py` | CHATFLOW_TOKEN читается из env |

---

## 4. Деплой

**docker-compose в проде:** инфра‑стек разделён: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`); был кейс `KeyError: 'ContainerConfig'` на `up/build`. API деплой — через `restart_api.sh`. `/home/zhan/truffles-main/docker-compose.yml` — заглушка.

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

`restart_api.sh` поддерживает `IMAGE_NAME` и `PULL_IMAGE=1` для работы с образом из registry.

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

## 5. Архитектура — потоки данных

### WhatsApp → Бот (ACK‑first + outbox)
```
WhatsApp клиент
    ↓
ChatFlow (app.chatflow.kz)
    ↓
POST /webhook (webhook_secret)
    ↓
enqueue outbox_messages (PENDING)
    ↓
outbox worker (тик 2s) или POST /admin/outbox/process (cron)
    ↓
_handle_webhook_payload(skip_persist=True)
    ↓
policy/truth gate → intent → RAG/LLM
    ↓
chatflow_service → WhatsApp (retries/backoff + msg_id idempotency)
```

### Медиа‑контур (фото/аудио/документы)
**Цель:** безопасность ресурсов + сохранение контекста + управляемая стоимость.

**Поток:**
1) Входящий payload содержит `mediaData` (`url`, `mimetype`, `size`, `fileName`, `base64`).
2) Guardrails до обработки: allowlist типов, max‑size, rate‑limit (per user).
3) Короткие голосовые (PTT) транскрибируются в текст; транскрипт сохраняется в `messages.metadata.media`.
4) Медиа сохраняется локально (storage dir; TTL очистка — план). Метаданные пишутся в `messages.metadata.media`.
5) Медиа форвардится в Telegram‑топик (sendPhoto/sendAudio/sendDocument); для голосовых — отправляется транскрипт.
6) Документы: только пересылка (обработка позже). Видео: запрещено.

**Конфигурация (per client):**
`clients.config.media` (JSONB) — overrides по лимитам и флагам:
- `enabled`, `allow_photo`, `allow_audio`, `allow_document`
- `max_size_mb.photo/audio/document`
- `rate_limit.count/window_seconds/daily_count/bytes_mb/block_seconds`
- `store_media`, `forward_to_telegram`, `storage_dir`
- `allowed_hosts` (whitelist для скачивания, дефолт `app.chatflow.kz`)

**Дефолты:**
- фото 8MB, аудио 8MB, документы 10MB
- лимит 5 медиа / 10 мин, 20 медиа / сутки, 30MB / 10 мин
- блокировка 15 мин при превышении
- storage dir: `/home/zhan/truffles-media`

**Важно:**
- Менеджер → клиент по медиа требует ChatFlow media API (отдельная интеграция, не в этой сессии).
- URL у ChatFlow может истечь — хранение локально гарантирует доставку в Telegram.
- В `bot_active` медиа не создаёт handover автоматически: если есть текст/транскрипт, обрабатываем как обычное сообщение; если нет текста — просим описание. Референсы/«как на фото» → эскалация.

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
resolve agent_identity → agent.role
    ↓
learning: create learned_responses(status=pending)
    ↓
if role=owner → auto-approve → add_to_knowledge()
```

### Определение филиала (branch routing)

**Варианты:**
- **by_instance:** если у каждого филиала свой номер/instance_id → сразу `branch_id`
- **ask_user:** если один номер на все филиалы → спросить филиал у клиента
- **hybrid:** если instance_id известен → branch_id, иначе спросить

**Хранение:**
- `conversation.branch_id`
- `conversation.context.branch_id` (быстрый доступ)
- `user.metadata.branch_id` (если включено `remember_branch_preference`)

**Гейт:** если `require_branch_for_pricing=true`, без `branch_id` бот не озвучивает цены/скидки/расписание.

---

## 6. База данных — ключевые таблицы

### conversations
```sql
id                  UUID PRIMARY KEY
client_id           UUID
branch_id           UUID  -- TODO: добавить для маршрутизации на филиал
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

### branches
```sql
id                  UUID PRIMARY KEY
client_id           UUID
instance_id         TEXT
telegram_chat_id    TEXT  -- Telegram-группа филиала
knowledge_tag       TEXT
```

### agents
```sql
id          UUID PRIMARY KEY
client_id   UUID
branch_id   UUID  -- NULL = глобальный доступ, иначе филиал
role        TEXT  -- owner, admin, manager, support
name        TEXT
```

### agent_identities
```sql
id           UUID PRIMARY KEY
agent_id     UUID REFERENCES agents(id)
channel      TEXT  -- telegram, email, crm
external_id  TEXT
username     TEXT
```

### learned_responses
```sql
id              UUID PRIMARY KEY
client_id       UUID
branch_id       UUID
handover_id     UUID REFERENCES handovers
question_text   TEXT
response_text   TEXT
status          TEXT  -- pending, approved, rejected
qdrant_point_id TEXT
```

### branches
```sql
id                  UUID PRIMARY KEY
client_id           UUID
telegram_chat_id    TEXT  -- Telegram-группа филиала
```

### client_settings (legacy)
```sql
client_id           UUID PRIMARY KEY
telegram_bot_token  TEXT
telegram_chat_id    TEXT  -- LEGACY: переносим на branches.telegram_chat_id
owner_telegram_id   TEXT  -- LEGACY: заменяется agents/agent_identities
```

### agents
```sql
id          UUID PRIMARY KEY
client_id   UUID
role        TEXT  -- owner, admin, manager, support
name        TEXT
```

### agent_identities
```sql
id           UUID PRIMARY KEY
agent_id     UUID REFERENCES agents(id)
channel      TEXT  -- telegram, email, crm
external_id  TEXT  -- telegram user id / email / etc
username     TEXT
```

---

## 7. Ключевые функции

### find_conversation_by_telegram
```python
def find_conversation_by_telegram(db, chat_id, message_thread_id=None):
    # 1. Найти branch по chat_id (основной путь)
    branch = db.query(Branch).filter(
        Branch.telegram_chat_id == str(chat_id)
    ).first()
    if branch:
        client_id = branch.client_id
        branch_id = branch.id
    else:
        # legacy fallback: client_settings.telegram_chat_id
        settings = db.query(ClientSettings).filter(
            ClientSettings.telegram_chat_id == str(chat_id)
        ).first()
        client_id = settings.client_id if settings else None
        branch_id = None

    # 2. Требуем message_thread_id (топик клиента)
    if not message_thread_id:
        return None

    # 3. Найти user по topic_id (users.telegram_topic_id)
    user = db.query(User).filter(
        User.client_id == client_id,
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
def is_owner_response(db, client_id, manager_telegram_id, manager_username=None):
    identity = db.query(AgentIdentity).filter(
        AgentIdentity.channel == "telegram",
        AgentIdentity.external_id == str(manager_telegram_id)
    ).first()
    if not identity and manager_username:
        identity = db.query(AgentIdentity).filter(
            AgentIdentity.channel == "telegram",
            AgentIdentity.username == manager_username
        ).first()
    if identity:
        agent = db.query(Agent).filter(Agent.id == identity.agent_id).first()
        return agent.role == "owner" if agent else False

    # legacy fallback
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == client_id
    ).first()
    return str(manager_telegram_id) == settings.owner_telegram_id if settings else False
```

---

## 8. Telegram

| Параметр | Значение |
|----------|----------|
| Тип группы | Супергруппа с темами (forum) |
| Группа | Одна Telegram-группа на филиал (`branches.telegram_chat_id`) |
| Webhook URL | `https://api.truffles.kz/telegram-webhook` |
| Кнопки | `take_{handover_id}`, `resolve_{handover_id}`, `approve_{learned_id}`, `reject_{learned_id}` |
| Owner detection | `agent.role == owner` по `agent_identities` |
| Manager | Любой агент в группе; неизвестные — без auto-approve |

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
| KNOWLEDGE_CONFIDENCE_THRESHOLD | 0.7 | ai_service.py |

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
| Сервисы в CI | Нет (unit tests + mocks), CI: ruff + pytest |

**Запуск:**
```bash
cd truffles-api
pytest tests/ -v
```

---

## 14. Ключевые файлы

| Файл | Назначение |
|------|------------|
| `app/routers/webhook.py` | Входящие от WhatsApp |
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

## 15. Известные проблемы

### Критичные
1. **Manager reply не работает** — `find_conversation_by_telegram` возвращает None
2. **Active Learning не вызывается** — нет логов "Owner response detected"
3. **Эскалация на всё** — threshold 0.7 слишком высокий

### Инфраструктурные
1. **docker-compose up/build** — был кейс `KeyError: 'ContainerConfig'` (инфра разделена на `/home/zhan/infrastructure/docker-compose.yml` и `/home/zhan/infrastructure/docker-compose.truffles.yml`)
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
