# ACTIVE LEARNING — План реализации

**Дата:** 2025-12-08
**Обновлено:** 2025-12-10
**Статус:** План (P2)
**Зависимости:** Эскалация ✅ готова

---

## СТАТУС РЕАЛИЗАЦИИ

| Компонент | Статус |
|-----------|--------|
| Сохранение ответа менеджера | ✅ РЕАЛИЗОВАНО (заполняется в `manager_message_service.py`) |
| Модерация | 📋 ПЛАН |
| Добавление в Qdrant | ⚠️ ЧАСТИЧНО (owner ответ → авто-upsert в Qdrant; модерация/approval flow — план) |
| Свой классификатор | 📋 ПЛАН (P3) |

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

### Использовать существующую таблицу `handovers`

Поля которые УЖЕ ЕСТЬ:
```sql
-- truffles-api/app/models/handover.py

user_message        TEXT      -- вопрос клиента ✅
manager_response    TEXT      -- ответ менеджера (нужно заполнять!)
trigger_type        TEXT      -- причина эскалации ✅
trigger_value       TEXT      -- детали (intent) ✅
resolved_by_name    TEXT      -- кто ответил ✅
resolved_at         TIMESTAMP -- когда ✅
```

Поля которые НУЖНО ДОБАВИТЬ:
```sql
-- Модерация
moderation_status   TEXT      -- pending, approved, rejected, edited
moderated_by        TEXT      -- telegram_id модератора
moderated_at        TIMESTAMP

-- Обучение
added_to_knowledge  BOOLEAN DEFAULT FALSE
knowledge_point_id  TEXT      -- ID точки в Qdrant
```

### Таблица `learned_responses` [ПЛАН]

```sql
CREATE TABLE learned_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  handover_id UUID REFERENCES handovers(id),
  
  -- Вопрос-ответ
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  
  -- Метаданные
  source TEXT DEFAULT 'manager',     -- manager, owner
  is_owner_response BOOLEAN,         -- для автомодерации
  
  -- Qdrant
  qdrant_point_id TEXT,              -- ID в Qdrant
  
  -- Использование
  use_count INTEGER DEFAULT 0,
  last_used_at TIMESTAMP,
  
  -- Статус
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_learned_responses_client ON learned_responses(client_id);
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
  - Найти handover по topic_id
  - Отправить ответ в WhatsApp
  - ✅ Сохранить manager_response в handover
  - ✅ Если это owner → авто-добавить в KB (Qdrant) (требует корректного owner_telegram_id)
    ↓
Ответ доставлен клиенту
```

**Примечание:** Модерация ответов (approved/rejected/edited) пока по плану.

### Шаг 3: Определение owner vs остальные [ПЛАН]

```python
def is_owner_response(db, client_id, manager_telegram_id):
    """Проверить является ли менеджер owner."""
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == client_id
    ).first()
    
    if not settings or not settings.owner_telegram_id:
        return False
    
    # owner_telegram_id может быть "@username" или "123456789"
    owner_id = settings.owner_telegram_id.lstrip('@')
    return str(manager_telegram_id) == owner_id or f"@{manager_telegram_id}" == settings.owner_telegram_id
```

### Шаг 4: Модерация [ПЛАН]

**Вариант A — Автоматическая (owner):**
```
IF is_owner_response:
  handover.moderation_status = 'approved'
  → сразу в обучение (Шаг 5)
```

**Вариант B — Через Telegram (остальные):**
```
IF NOT is_owner_response:
  handover.moderation_status = 'pending'
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
# В telegram_webhook.py добавить action="approve_learning"

if action == "approve_learning":
    handover.moderation_status = 'approved'
    handover.moderated_by = manager_id
    handover.moderated_at = now
    # Запустить обучение
    add_to_knowledge(db, handover)

if action == "reject_learning":
    handover.moderation_status = 'rejected'
    handover.moderated_by = manager_id
    handover.moderated_at = now
```

### Шаг 5: Обучение (добавление в Qdrant) [ПЛАН]

```python
def add_to_knowledge(db: Session, handover: Handover):
    """Добавить ответ менеджера в базу знаний."""
    
    # 1. Получить client_slug
    client = db.query(Client).filter(Client.id == handover.client_id).first()
    client_slug = client.slug
    
    # 2. Создать текст для индексации
    content = f"Вопрос: {handover.user_message}\nОтвет: {handover.manager_response}"
    
    # 3. Получить embedding
    embedding = get_embedding(content)
    
    # 4. Добавить в Qdrant
    point_id = str(uuid.uuid4())
    
    qdrant_client.upsert(
        collection_name="truffles_knowledge",
        points=[{
            "id": point_id,
            "vector": embedding,
            "payload": {
                "content": content,
                "metadata": {
                    "client_slug": client_slug,
                    "source": "learned",
                    "handover_id": str(handover.id),
                    "question": handover.user_message,
                    "answer": handover.manager_response,
                    "learned_at": datetime.now().isoformat(),
                }
            }
        }]
    )
    
    # 5. Обновить handover
    handover.added_to_knowledge = True
    handover.knowledge_point_id = point_id
    
    # 6. Создать запись в learned_responses
    learned = LearnedResponse(
        client_id=handover.client_id,
        handover_id=handover.id,
        question=handover.user_message,
        answer=handover.manager_response,
        source="owner" if handover.moderation_status == "auto_approved" else "manager",
        qdrant_point_id=point_id,
    )
    db.add(learned)
    
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
        LearnedResponse.qdrant_point_id == result["metadata"]["handover_id"]
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

### Этап 1: Сохранение ответа менеджера (1-2 часа)

**Файл:** `manager_message_service.py`

```python
# После строки send_whatsapp_message(...)
handover.manager_response = message_text

# Определить owner или нет
is_owner = is_owner_response(db, handover.client_id, manager_telegram_id)
if is_owner:
    handover.moderation_status = 'auto_approved'
else:
    handover.moderation_status = 'pending'
```

**Миграция:** Добавить поля в handovers:
```sql
ALTER TABLE handovers ADD COLUMN moderation_status TEXT;
ALTER TABLE handovers ADD COLUMN moderated_by TEXT;
ALTER TABLE handovers ADD COLUMN moderated_at TIMESTAMP;
ALTER TABLE handovers ADD COLUMN added_to_knowledge BOOLEAN DEFAULT FALSE;
ALTER TABLE handovers ADD COLUMN knowledge_point_id TEXT;
```

### Этап 2: Автомодерация для owner (2-3 часа)

1. Функция `is_owner_response()` в `manager_message_service.py`
2. Если owner → `moderation_status = 'auto_approved'`
3. Вызвать `add_to_knowledge()` сразу

### Этап 3: Модерация через Telegram (3-4 часа)

1. После ответа не-owner → отправить owner сообщение с кнопками
2. Callback `approve_learning` / `reject_learning` в `telegram_webhook.py`
3. При approve → `add_to_knowledge()`

### Этап 4: Добавление в Qdrant (2-3 часа)

1. Функция `add_to_knowledge()` в новом файле `learning_service.py`
2. Создать таблицу `learned_responses`
3. Интеграция с Qdrant

### Этап 5: Метрики (опционально)

1. Счётчик use_count в learned_responses
2. Dashboard: сколько выучено, сколько используется

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
| `models/handover.py` | Добавить поля модерации | 1 |
| `migrations/` | ALTER TABLE handovers | 1 |
| `services/manager_message_service.py` | Сохранять manager_response | 1 |
| `services/manager_message_service.py` | is_owner_response() | 2 |
| `services/learning_service.py` | Создать (новый) | 4 |
| `models/learned_response.py` | Создать (новый) | 4 |
| `routers/telegram_webhook.py` | Кнопки модерации | 3 |

---

## ВОПРОСЫ РЕШЕНЫ

| Вопрос | Решение |
|--------|---------|
| Кто модерирует? | Owner каждого клиента модерирует своих менеджеров |
| Owner автоматически? | Да, ответы owner сразу в базу |
| Формат в Qdrant? | Как обычный документ с `source: 'learned'` |

---

## ПРИОРИТЕТЫ

**P2 (после стабилизации):**
- [x] Поля для модерации в handovers — нужна миграция
- [ ] Сохранение manager_response
- [ ] Автомодерация для owner
- [ ] Модерация через Telegram
- [ ] Добавление в Qdrant

**P3 (оптимизация):**
- [ ] Свой классификатор
- [ ] Метрики и аналитика
- [ ] Dashboard обучения

---

*Связанные документы:*
- `SPECS/ESCALATION.md` — основа эскалации
- `STRATEGY/REQUIREMENTS.md` — приоритеты

### ?????????? 2025-12-19 ? ?????????? ?????????

- `owner_telegram_id` ????? ???? ??????? ????? ???????/?????? (numeric id ??? @username), ????????? ????????? id, ?????????? mismatch.
- ?????????? ? KB ?????????? ??????? ???????? Q/A (<5 ????????) ? ???????? skip/?????/??????.
- ????? ????? ?????? ???????? 2000 ????????, ??????/????? ?????????? ? ?????????? ? ????.
- ????????? ???? ???, default ? ?????? owner ?????????????; ????????? ???? ??????? ??????? ?????? (????).
