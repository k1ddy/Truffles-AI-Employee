# ACTIVE LEARNING — План реализации

**Дата:** 2025-12-08
**Статус:** Готов к реализации
**Зависимости:** Multi-tenant ✅ готов

---

## КОНТЕКСТ: ЧТО УЖЕ ЕСТЬ

### Multi-tenant (готово):
- `clients` — таблица с config (instance_id, folder_id, phone)
- `prompts` — промпты по клиентам
- RAG фильтрация по `client_slug`
- Динамический instance_id в Send нодах
- Онбординг скрипты (`onboard_client.py`, `sync_client.py`)

### Эскалация (базовая):
- `needs_escalation = true` → отправка в Telegram/WhatsApp менеджеру
- Нет трекинга решения
- Нет сохранения ответа менеджера
- Бот НЕ учится

### Классификатор:
- Сейчас: LLM (GPT) определяет intent
- Дорого, медленно
- Нет своей модели

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

### Таблица `escalations`:

```sql
CREATE TABLE escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  conversation_id UUID REFERENCES conversations(id),
  
  -- Контекст
  user_message TEXT NOT NULL,
  bot_response TEXT,  -- что бот ответил перед эскалацией
  context JSONB,      -- история, intent, knowledge
  
  -- Триггер
  trigger_reason TEXT,  -- 'no_answer', 'human_request', 'negative_sentiment', 'complex_question'
  
  -- Статус
  status TEXT DEFAULT 'pending',  -- pending → assigned → resolved → moderated → learned
  assigned_to TEXT,               -- телефон/id менеджера
  assigned_at TIMESTAMPTZ,
  
  -- Ответ менеджера
  manager_response TEXT,
  resolved_at TIMESTAMPTZ,
  resolution_time_seconds INTEGER,
  
  -- Модерация
  moderated_by TEXT,             -- учредитель или система
  moderation_status TEXT,        -- approved, rejected, edited
  moderation_notes TEXT,
  moderated_at TIMESTAMPTZ,
  
  -- Обучение
  added_to_knowledge BOOLEAN DEFAULT FALSE,
  knowledge_doc_id TEXT,         -- ID документа в Qdrant
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escalations_client ON escalations(client_id);
CREATE INDEX idx_escalations_status ON escalations(status);
```

### Таблица `learned_responses`:

```sql
CREATE TABLE learned_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  escalation_id UUID REFERENCES escalations(id),
  
  -- Паттерн вопроса
  question_pattern TEXT NOT NULL,    -- нормализованный вопрос
  question_embedding VECTOR(1024),   -- для semantic search
  
  -- Ответ
  response TEXT NOT NULL,
  
  -- Метаданные
  source TEXT DEFAULT 'manager',     -- manager, owner, system
  confidence FLOAT DEFAULT 1.0,
  use_count INTEGER DEFAULT 0,
  
  -- Статус
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## FLOW: ОТ ЭСКАЛАЦИИ ДО ОБУЧЕНИЯ

### Шаг 1: Эскалация создаётся

```
Generate Response: needs_escalation = true
    ↓
Создать запись в escalations:
  - user_message
  - bot_response (что бот сказал клиенту)
  - context (история, RAG результаты)
  - trigger_reason
  - status = 'pending'
    ↓
Уведомить менеджера (Telegram/WhatsApp)
```

### Шаг 2: Менеджер отвечает

```
Менеджер пишет ответ
    ↓
Система ловит ответ (webhook от WhatsApp Business)
    ↓
UPDATE escalations:
  - manager_response = ответ
  - resolved_at = NOW()
  - status = 'resolved'
    ↓
Ответ пересылается клиенту (если нужно)
```

### Шаг 3: Модерация

**Вариант A — Автоматическая (для учредителя):**
```
IF manager.role = 'owner':
  moderation_status = 'approved'
  → сразу в обучение
```

**Вариант B — Ручная (для менеджеров):**
```
Учредитель видит список ответов менеджеров
    ↓
[Одобрить] → moderation_status = 'approved' → в обучение
[Отклонить] → moderation_status = 'rejected' → не учить
[Редактировать] → изменить ответ → approved → в обучение
```

### Шаг 4: Обучение

```
moderation_status = 'approved'
    ↓
1. Нормализовать вопрос (убрать мусор, lowercase)
2. Создать embedding вопроса
3. Сохранить в learned_responses
4. Добавить в Qdrant с metadata:
   - client_slug
   - source: 'learned'
   - escalation_id
    ↓
UPDATE escalations:
  - added_to_knowledge = true
  - knowledge_doc_id = id в Qdrant
```

### Шаг 5: Использование

```
Новый вопрос
    ↓
RAG Search ищет в:
  1. Документы (faq.md, services.md)
  2. learned_responses (ответы менеджеров)
    ↓
Если найден learned_response с высоким score:
  - Использовать как ответ
  - UPDATE learned_responses SET use_count = use_count + 1
```

---

## КЛАССИФИКАТОР: LLM → СВОЙ

### Сейчас (дорого):
```
Каждое сообщение → GPT → intent
Стоимость: ~$0.01 за классификацию
```

### Цель (дёшево):
```
Каждое сообщение → Свой классификатор → intent
Стоимость: ~$0 (self-hosted)
```

### План:

**Фаза 1 — Сбор данных:**
```sql
CREATE TABLE classification_examples (
  id UUID PRIMARY KEY,
  client_id UUID,
  message TEXT,
  intent TEXT,           -- on_topic, off_topic, attack, human_request, greeting
  confidence FLOAT,
  source TEXT,           -- 'llm', 'manual', 'corrected'
  created_at TIMESTAMPTZ
);
```

Каждая классификация от LLM сохраняется. Цель: 10,000+ примеров.

**Фаза 2 — Fine-tune:**
- Модель: DistilBERT или similar (маленькая, быстрая)
- Данные: classification_examples
- Результат: своя модель классификации

**Фаза 3 — Замена:**
```
Сообщение → Свой классификатор (self-hosted)
    ↓
IF confidence < 0.8:
    → Fallback на LLM
ELSE:
    → Использовать результат
```

---

## РЕАЛИЗАЦИЯ: ПОРЯДОК ШАГОВ

### Этап 1: БД и базовый трекинг (2-4 часа)

1. Создать таблицу `escalations`
2. Изменить Multi-Agent: при `needs_escalation = true` создавать запись
3. Добавить `escalation_id` в уведомление менеджеру

### Этап 2: Захват ответа менеджера (4-6 часов)

1. Webhook для входящих от менеджера
2. Логика определения: это ответ на эскалацию или новое сообщение?
3. UPDATE escalations с ответом

### Этап 3: Интерфейс модерации (опционально)

**Минимум:** Telegram бот для учредителя
```
Новый ответ от менеджера:
Q: "Сколько стоит балаяж?"
A: "Балаяж от 18,000 тг, зависит от длины волос"

[✅ Одобрить] [❌ Отклонить] [✏️ Редактировать]
```

**Максимум:** Веб-дашборд

### Этап 4: Обучение (2-4 часа)

1. При одобрении → создать embedding
2. Добавить в Qdrant с source='learned'
3. RAG Search учитывает learned_responses

### Этап 5: Классификатор (позже)

1. Сбор данных (автоматически, 2-4 недели)
2. Fine-tune модели
3. Деплой и замена

---

## СВЯЗЬ С СУЩЕСТВУЮЩИМ КОДОМ

### Multi-Agent workflow (6_Multi-Agent):

**Добавить ноду "Create Escalation"** после Check Escalation:
```javascript
// Если needs_escalation = true
const escalation = {
  client_id: $json.client_id,
  conversation_id: $json.conversation_id,
  user_message: $json.message,
  bot_response: $json.response,
  trigger_reason: determineTrigger($json),
  context: {
    history: $json.history,
    intent: $json.currentIntent,
    knowledge: $json.knowledge
  }
};

// INSERT в escalations
```

**Изменить RAG Search:**
```javascript
// Добавить в фильтр OR:
// metadata.client_slug = X AND (metadata.source = 'document' OR metadata.source = 'learned')
```

### Webhook для ответов менеджера:

Новый workflow или расширение 1_Webhook:
```
Входящее от номера менеджера
    ↓
Проверить: есть ли pending escalation для этого клиента?
    ↓
IF да:
  - UPDATE escalations
  - Переслать клиенту
  - Запустить модерацию/обучение
ELSE:
  - Обычная обработка
```

---

## МЕТРИКИ

| Метрика | Как считать | Цель |
|---------|-------------|------|
| Escalation Rate | эскалаций / всего сообщений | Падает со временем |
| Resolution Time | среднее время ответа менеджера | < 10 минут |
| Learn Rate | одобренных / всего эскалаций | > 50% |
| Reuse Rate | использований learned_responses | Растёт |

---

## ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| Файл | Что менять |
|------|------------|
| `ops/create_escalations_table.sql` | Создать (новый) |
| `workflow/6_Multi-Agent` | Добавить Create Escalation |
| `workflow/7_EscalationHandler` | Создать (новый) |
| `ops/sync_client.py` | Учитывать learned_responses |

---

## ПРИОРИТЕТЫ

**P0 (критично):**
- Таблица escalations
- Сохранение эскалаций в БД
- Захват ответа менеджера

**P1 (важно):**
- Модерация через Telegram
- Добавление в Qdrant

**P2 (потом):**
- Веб-дашборд
- Свой классификатор
- Аналитика

---

## ВОПРОСЫ ДЛЯ УТОЧНЕНИЯ

1. **Модерация:** Жанбол модерирует всех клиентов или каждый учредитель своих?
2. **Ответ менеджера:** Через какой канал? WhatsApp Business API даёт webhook на исходящие?
3. **Формат обучения:** Добавлять как отдельный документ в Qdrant или в существующие?

---

*Связанные документы:*
- `SPECS/ESCALATION.md` — детали эскалации
- `SPECS/MULTI_TENANT.md` — архитектура multi-tenant
- `docs/MULTITENANT_IMPLEMENTATION.md` — что уже сделано
