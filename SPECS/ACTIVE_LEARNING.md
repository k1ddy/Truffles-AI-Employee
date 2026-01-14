# ACTIVE LEARNING — План реализации
SOURCE OF TRUTH: canonical active learning spec and status.

**Дата:** 2025-12-08
**Обновлено:** 2025-12-24
**Статус:** Решение (P2) + частичная реализация
**Зависимости:** Эскалация ✅; роли/идентичности — план; A4–A7 до полного обучения

---

## СТАТУС РЕАЛИЗАЦИИ

| Компонент | Статус |
|-----------|--------|
| Сохранение ответа менеджера | ✅ РЕАЛИЗОВАНО (заполняется в `manager_message_service.py`) |
| Роли/идентичности (agents) | 📋 ПЛАН |
| Очередь обучения (learned_responses) | ⚠️ PARTIAL (таблица есть, wiring pending) |
| Модерация | 📋 ПЛАН |
| Добавление в Qdrant | ⚠️ ЧАСТИЧНО (owner ответ → авто-upsert в Qdrant; очередь/approval flow — план) |
| Свой классификатор | 📋 ПЛАН (P3) |

---

## ПРИОРИТЕТ И ЭТАП

- Этап: P2 после завершения A4–A7 (`STRATEGY/TECH_ROADMAP.md`).
- Причина: сначала стабильность фактов/policy/observability, затем обучение.

---

## ПОЛИТИКА ДАННЫХ (NDA + data_sharing)

- **По умолчанию:** обучение и RAG работают только внутри салона (tenant-only).
- **Opt-in:** допускается только агрегированная, обезличенная статистика для улучшения domain_pack.
- **Запрещено всегда:** PII, контакты, исходные тексты сообщений, медиа.

Источник флага: `clients.config.data_sharing` (см. `SPECS/MULTI_TENANT.md`).

---

## КАЛИБРОВКА ПО КАЖДОМУ САЛОНУ (процесс)

1) Найти pain points: `decision_trace/meta`, `knowledge_backlog`, `/admin/metrics`.
2) Классифицировать: data gap / policy gap / intent gap / logic bug.
3) Обновить pack (client_pack/domain_pack) без изменения кода.
4) Добавить/обновить EVAL кейсы (включая long-form) и прогнать.
5) Зафиксировать эффект до/после по метрикам.

**Принцип:** улучшения делаются через данные/правила, не через fine-tune модели.

---

## КОНТЕКСТ: ЧТО УЖЕ ЕСТЬ [РЕАЛИЗОВАНО]

### Эскалация (работает):
- Таблица `handovers` с полями для обучения
- `handover.user_message` — вопрос клиента
- `handover.manager_response` — ответ менеджера ✅ (сохраняется)
- `handover.trigger_type`, `trigger_value` — причина эскалации
- Ответ менеджера пересылается в WhatsApp

**Реализация:** 
- `truffles-api/app/models/handover.py`
- `truffles-api/app/services/manager_message_service.py`

### RAG (работает):
- Qdrant коллекция `truffles_knowledge`
- Фильтрация по `metadata.client_slug`
- BGE-M3 для embeddings

**Реализация:** `truffles-api/app/services/knowledge_service.py`

### Классификатор (работает):
- LLM (GPT) определяет intent
- Intents: human_request, frustration, rejection, question, greeting, thanks, other

**Реализация:** `truffles-api/app/services/intent_service.py`

---

## ЦЕЛЬ: СИСТЕМА КОТОРАЯ УМНЕЕТ

```
СЕЙЧАС:
Вопрос → Бот не знает → Эскалация → Менеджер ответил → КОНЕЦ

ДОЛЖНО БЫТЬ:
Вопрос → Бот не знает → Эскалация → Менеджер ответил 
    → Ответ сохранён → Модерация → В базу знаний
    → Следующий раз бот знает сам
```

**Метрика успеха:** Escalation Rate падает со временем.

---

## АРХИТЕКТУРА ACTIVE LEARNING

### Источник данных: `handovers` (как есть)

Поля которые УЖЕ ЕСТЬ:
```sql
-- truffles-api/app/models/handover.py

user_message        TEXT      -- вопрос клиента ✅
manager_response    TEXT      -- ответ менеджера ✅
trigger_type        TEXT      -- причина эскалации ✅
trigger_value       TEXT      -- детали (intent) ✅
resolved_by_name    TEXT      -- кто ответил ✅
resolved_at         TIMESTAMP -- когда ✅
```

**Принцип:** не усложнять `handovers`. Модерация и обучение живут в отдельной очереди.

**GAP:** auto_approve_roles конфиг есть (client_settings), но логика approval ещё не подключена к learned_responses.

### Очередь обучения: `learned_responses` (pending/approved/rejected)

```sql
-- Очередь кандидатов на обучение

id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
client_id       UUID REFERENCES clients(id),
branch_id       UUID REFERENCES branches(id),
handover_id     UUID REFERENCES handovers(id),

question_text   TEXT NOT NULL,
response_text   TEXT NOT NULL,

source          TEXT DEFAULT 'manager',
source_role     TEXT,
source_channel  TEXT,
agent_id        UUID, -- FK → agents

status          TEXT DEFAULT 'pending', -- pending, approved, rejected
approved_by     UUID,
approved_at     TIMESTAMP,
rejected_at     TIMESTAMP,

qdrant_point_id TEXT,

use_count       INTEGER DEFAULT 0,
last_used_at    TIMESTAMP,
is_active       BOOLEAN DEFAULT TRUE,

created_at      TIMESTAMP DEFAULT NOW(),
updated_at      TIMESTAMP DEFAULT NOW()
```

---

## FLOW: ОТ ЭСКАЛАЦИИ ДО ОБУЧЕНИЯ

### Шаг 1: Эскалация создаётся [РЕАЛИЗОВАНО]

```
POST /message: should_escalate(intent) = true
    ↓
escalation_service.escalate_conversation():
  - Создать handover
  - user_message = сообщение клиента
  - trigger_type = 'intent'
  - trigger_value = intent.value
    ↓
Уведомление в Telegram с кнопками
```

**Реализация:** `escalation_service.py`

### Шаг 2: Менеджер отвечает [ЧАСТИЧНО]

```
Менеджер пишет в Telegram топик
    ↓
POST /telegram-webhook
    ↓
manager_message_service.process_manager_message():
  - Найти user по topic_id (users.telegram_topic_id)
  - Найти активный handover (pending/active) для этого user
  - Отправить ответ в WhatsApp
  - ✅ Сохранить manager_response в handover
  - [ПЛАН] Создать learned_responses(status=pending)
  - ✅ Если роль owner → auto-approve → add_to_knowledge()
    ↓
Ответ доставлен клиенту
```

**Примечание:** Модерация идёт через очередь `learned_responses`.

### Шаг 3: Определение роли (agents) [ПЛАН]

```python
def resolve_agent_role(db, manager_telegram_id, manager_username=None):
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
        return agent.role if agent else None
    return None
```

### Шаг 4: Модерация [ПЛАН]

**Вариант A — Автоматическая (owner):**
```
IF role == "owner" (или role ∈ auto_approve_roles):
  learned.status = "approved"
  → сразу в обучение (Шаг 5)
```

**Ограничение:** если auto-approve разрешён для `admin`, он действует только в рамках `branch_id` агента.

**Конфиг:** `client_settings.auto_approve_roles` (строка/список).

**Вариант B — Через Telegram (остальные):**
```
IF role not in auto_approve_roles:
  learned.status = "pending"
  → Отправить owner сообщение с кнопками:

┌─────────────────────────────────────┐
│ 📝 Новый ответ для модерации        │
│                                     │
│ Вопрос: "Сколько стоит балаяж?"     │
│                                     │
│ Ответ (Айгуль):                     │
│ "Балаяж от 18,000 тг, зависит от    │
│ длины волос"                        │
│                                     │
│ [✅ В базу] [❌ Отклонить]           │
└─────────────────────────────────────┘
```

**Callback обработка:**
```python
# В telegram_webhook.py: approve_{learned_id} / reject_{learned_id}
if action == "approve":
    learned.status = "approved"
    learned.approved_by = agent_id
    learned.approved_at = now
    add_to_knowledge(db, learned)

if action == "reject":
    learned.status = "rejected"
    learned.rejected_at = now
```

### Шаг 5: Обучение (добавление в Qdrant) [ПЛАН]

```python
def add_to_knowledge(db: Session, learned: LearnedResponse):
    """Добавить approved ответ в базу знаний."""
    client = db.query(Client).filter(Client.id == learned.client_id).first()
    client_slug = client.slug
    content = f"Вопрос: {learned.question_text}\nОтвет: {learned.response_text}"
    embedding = get_embedding(content)
    point_id = str(uuid.uuid4())

    qdrant_client.upsert(...metadata: {"source": "learned", "learned_id": learned.id})

    learned.qdrant_point_id = point_id
    learned.status = "approved"
    return point_id
```

### Шаг 6: Использование [ЧАСТИЧНО РЕАЛИЗОВАНО]

RAG уже ищет по client_slug. Нужно только добавлять learned responses в Qdrant с правильными metadata.

```python
# knowledge_service.py — уже работает
# Поиск найдёт и документы, и learned_responses
results = search_knowledge(query, client_slug, limit=5)
```

**Опционально:** Увеличивать use_count при использовании:
```python
# После успешного использования learned_response
if result.get("metadata", {}).get("source") == "learned":
    learned = db.query(LearnedResponse).filter(
        LearnedResponse.qdrant_point_id == result["metadata"]["learned_id"]
    ).first()
    if learned:
        learned.use_count += 1
        learned.last_used_at = datetime.now()
```

---

## СВОЙ КЛАССИФИКАТОР [ПЛАН P3]

> Это оптимизация стоимости. Приоритет P3 — делать когда будет экономически выгодно.

### Сейчас (работает, но дорого):
```
Каждое сообщение → GPT-4o-mini → intent
Стоимость: ~$0.01 за классификацию
```

**Реализация:** `intent_service.py`

### Цель (когда будет много сообщений):
```
Каждое сообщение → Свой классификатор → intent
Стоимость: ~$0 (self-hosted)
```

### План реализации:

**Фаза 1 — Сбор данных:**

Добавить логирование классификаций:
```python
# intent_service.py

def classify_intent(message: str) -> Intent:
    intent = ... # текущая логика
    
    # Логировать для будущего обучения
    log_classification(message, intent.value, confidence=1.0, source="llm")
    
    return intent
```

Таблица для сбора:
```sql
CREATE TABLE classification_logs (
  id UUID PRIMARY KEY,
  client_id UUID,
  message TEXT,
  intent TEXT,
  confidence FLOAT,
  source TEXT,  -- 'llm', 'manual', 'model'
  created_at TIMESTAMP
);
```

Цель: 10,000+ примеров.

**Фаза 2 — Fine-tune (когда данных достаточно):**
- Модель: DistilBERT multilingual или ruBERT
- Данные: classification_logs
- Результат: своя модель классификации

**Фаза 3 — Замена:**
```python
def classify_intent(message: str) -> Intent:
    # Сначала свой классификатор
    intent, confidence = local_classifier.predict(message)
    
    if confidence < 0.8:
        # Fallback на LLM
        intent = llm_classify(message)
        log_classification(message, intent, source="llm_fallback")
    else:
        log_classification(message, intent, confidence, source="model")
    
    return intent
```

---

## ПЛАН РЕАЛИЗАЦИИ

### Этап 1: Схема данных (P0)

- Таблицы `agents`, `agent_identities`
- Расширение `learned_responses` (status, agent_id, qdrant_point_id)
- `conversations.branch_id` для маршрутизации

### Этап 2: Роли и идентичности (P0)

- Разрешение роли по `agent_identities` (telegram user id/username)
- Fallback на `client_settings.owner_telegram_id` (legacy)

### Этап 3: Очередь обучения (P0)

- При ответе менеджера → создать `learned_responses(status=pending)`
- Если role=owner → auto-approve → `add_to_knowledge()`

### Этап 4: Модерация через Telegram (P1)

- Owner получает кнопки approve/reject
- Callback обновляет `learned_responses.status`
- При approve → `add_to_knowledge()`

### Этап 5: Метрики и контроль (P1)

- use_count/last_used_at
- Отчёт: сколько добавлено/сколько отклонено

---

## МЕТРИКИ

| Метрика | Как считать | Цель | Статус |
|---------|-------------|------|--------|
| Escalation Rate | handovers / messages | Падает | ❌ Не считается |
| Learn Rate | approved / resolved handovers | >50% | 📋 После реализации |
| Reuse Rate | использований learned | Растёт | 📋 После реализации |
| Auto-approve Rate | auto_approved / approved | Зависит от owner | 📋 После реализации |

---

## ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| Файл | Что менять | Этап |
|------|------------|------|
| `models/agent.py` | Роли агентов | 1 |
| `models/agent_identity.py` | Идентичности (telegram/email) | 1 |
| `models/learned_response.py` | Очередь обучения | 1 |
| `migrations/` | agents + agent_identities + learned_responses columns | 1 |
| `services/manager_message_service.py` | Создавать learned_responses | 3 |
| `services/learning_service.py` | add_to_knowledge(learned) | 3 |
| `routers/telegram_webhook.py` | approve/reject для learned_responses | 4 |

---

## ВОПРОСЫ РЕШЕНЫ

| Вопрос | Решение |
|--------|---------|
| Кто модерирует? | Owner каждого клиента модерирует своих менеджеров |
| Owner автоматически? | Да, ответы owner сразу в базу |
| Формат в Qdrant? | Как обычный документ с `source: 'learned'` |

---

## IMPLEMENTATION BRAIN — ускорение внедрений и качества

**Идея:** отдельный “мозг внедрений”, который учится на каждом клиенте и превращает опыт в стандарты.  
**Цель:** запускать следующих клиентов быстрее и стабильнее, без повторения одних и тех же ошибок.

### Что это НЕ делает
- Не “тренирует LLM на чужих данных”.
- Не меняет прод напрямую без проверки.

### Что это делает
- Собирает факты/ошибки/инциденты/вопросы.
- Находит повторяющиеся паттерны.
- Превращает это в обновления: truth‑шаблоны, интенты, тесты, чек‑листы, политики.

### Источники данных
- Онбординг: анкеты, прайсы, правила, договорные условия.
- Техподдержка: тикеты, жалобы, “не работает”.
- Логи: эскалации, low‑confidence, outbox ошибки, отказанные сообщения.
- Ответы менеджеров (с модерацией).

### Нормализация (таксономия проблем)
Каждую находку фиксировать как:
- `fact_gap` — нет факта (график/услуга/цена).
- `intent_gap` — нет фразы/синонима.
- `policy_risk` — опасные вопросы (оплата/мед/возврат).
- `integration_gap` — тех. сбои/нестабильность.
- `process_gap` — нет стандарта/чек‑листа.
- `legal_gap` — риск договоров/обязательств.

### Выходы (артефакты)
- `SALON_TRUTH.yaml` / шаблоны truth для вертикали.
- `INTENTS_*` + новые примеры фраз.
- `EVAL.yaml` — тесты “навсегда”.
- Чек‑листы внедрения и поддержки.
- Политики и ограничения (эскалация/ответы).

### Режим работы (цикл)
```
Каждую неделю:
  1) Топ‑20 эскалаций и инцидентов
  2) Классификация по таксономии
  3) Правка фактов/интентов/политик
  4) Добавление тестов (EVAL)
```

### Безопасность и конфиденциальность
- Клиентские данные остаются клиентскими.
- В общий слой попадают только анонимизированные паттерны.
- Любое изменение проходит проверку и тесты.

### Как “таскать” агента
- Запуск локально: “папка данных” + скрипт отчёта (manual).
- Потом перенос на сервер: те же входы, регулярный отчёт.

### Этапы внедрения
1) **Manual**: еженедельный отчёт + правки руками.
2) **Semi‑auto**: автоматический сбор топ‑паттернов.
3) **Auto‑assist**: авто‑предложения изменений (с ручным аппрувом).

---

## ПРИОРИТЕТЫ

**P0 (сейчас):**
- [ ] Роли/идентичности (agents)
- [ ] Очередь обучения (learned_responses)
- [ ] Auto-approve owner → Qdrant

**P1 (после стабилизации):**
- [ ] Модерация через Telegram
- [ ] Метрики обучения

**P3 (оптимизация):**
- [ ] Свой классификатор
- [ ] Dashboard обучения

---

*Связанные документы:*
- `SPECS/ESCALATION.md` — основа эскалации
- `STRATEGY/REQUIREMENTS.md` — приоритеты

### Замечания (2025-12-24)

- `owner_telegram_id` в legacy часто ломается (ID vs @username) → нужен `agent_identities`.
- Короткие Q/A (<5 символов) пропускать, чтобы не засорять KB.
- Ограничение 2000 символов: длинные ответы триммить.
- Auto-approve owner должен иметь откат (удаление из KB).
