# ТЕХНИЧЕСКИЙ ROADMAP — Architecture First

**Цель:** построить управляемый бизнес‑консультант с детерминированным ядром, живым тоном и гарантируемой эскалацией.
**Фокус:** архитектура и контракты как основа для масштабирования и безопасности.
**Обновлено:** 2026-01-09

---

## 0) Итоговый продукт (NorthStar)

- Консультант отвечает 24/7, доводит до записи или корректной эскалации.
- Риск‑зоны не обсуждаются ботом, всегда уходят в эскалацию.
- Один движок на все ниши; различия — только в data packs.
- Память живёт вне LLM: summary + TTL + re‑entry.
- Каждое решение объяснимо по trace/meta.

---

## 1) Канон (инварианты)

1) **Safety/Policy выше смысла.** Любой риск → эскалация.
2) **LLM = смысл.** Факты и решения — детерминированные.
3) **Truth‑first.** Факты только из data packs; иначе уточнение → эскалация.
4) **Один Decision Graph.** Решения идут по фиксированной цепочке, без “долгих размышлений”.
5) **Память явная.** Старые факты требуют подтверждения.
6) **Trace/meta на всё.** Иначе решение считается “не существующим”.

---

## 2) Базовая реализация (что уже есть)

### 2.1 Вход + оркестрация
- Единый вход: `truffles-api/app/routers/webhook/_legacy.py`.
- Решения пишут trace/meta: `truffles-api/app/routers/webhook/trace.py`.

### 2.2 Состояния диалога
- Состояния: `Conversation.state` (`bot_active/pending/manager_active`) в `truffles-api/app/models/conversation.py`.
- Переходы: `truffles-api/app/services/state_service.py`.

### 2.3 Эскалация + Telegram
- Handover + уведомления: `truffles-api/app/services/escalation_service.py`.
- Карточка + кнопки: `truffles-api/app/services/telegram_service.py`.
- TAKE/RESOLVE/RETURN: `truffles-api/app/routers/telegram_webhook.py`.
- Ответ менеджера → клиент: `truffles-api/app/services/manager_message_service.py`.

### 2.4 Session memory (v1.1)
- Память + TTL: `truffles-api/app/routers/webhook/session_memory.py`.
- Summary: `truffles-api/app/routers/webhook/context_manager.py`.

### 2.5 Семантика и данные
- Intent‑классификация: `truffles-api/app/services/intent_service.py`.
- RAG/knowledge: `truffles-api/app/services/knowledge_service.py`.

### 2.6 Pending‑SLA
- Ping + auto‑close: `truffles-api/app/services/reminder_service.py`.
- Pending‑ветка: `truffles-api/app/routers/webhook/_legacy.py`.

### 2.7 Готовые разрывы (GAP)
- Контракты между слоями не зафиксированы в коде (нет schema‑валидации).
- Decision Graph размазан в `_legacy.py`.
- Карточка менеджера не содержит summary/next step.
- Budget/Rate Control отсутствует как системный слой.
- Learning backlog не выделен как процесс (есть частичное добавление в knowledge).

---

## 3) Мост A0 → A1…A7 (совместимость и исправления)

**Зачем:** старые ошибки и зависимости (LLM‑ключи/внешние индексы) ломают базовые сценарии и CI.  
**Принцип:** исправления должны быть совместимы с новой архитектурой и потом “переезжать” в A1–A7 без переделок.

### A0.1 Deterministic Expected Reply (service)
**Почему:** expected_reply=service не должен зависеть от LLM‑ключа или внешнего индекса.  
**Как делаем:**
1) В `truffles-api/app/services/intent_service.py` — если LLM‑ключ отсутствует или LLM падает, трактовать интерпретатор как disabled.
2) В `_legacy.py` при `expected_reply_type=service` — сразу использовать локальный service catalog (data pack) как fallback.
3) Дополнить data pack алиасами “общих” запросов услуги (например, “ногти”), чтобы матчилось без LLM.
**DoD:** при отсутствии ключа LLM expected_reply=service детерминированно ведёт к вопросу даты/времени.

### A0.2 Offline‑safe Service Match
**Почему:** semantic_service_match (внешний индекс) не всегда доступен.  
**Как делаем:** при недоступности внешнего индекса fallback идёт только в локальные aliases из data pack.  
**DoD:** сервисы матчатся по данным клиента даже без Qdrant.

### A0.3 Trace‑evidence для A0‑путей
**Почему:** A0 должен быть измерим и проверяем.  
**Как делаем:** добавить decision_meta: `answer_interpreter_error`, `service_hint_source=local_pack`.  
**DoD:** trace показывает, что LLM не использовался и почему.

**Связь с A1…A7:**
- A0.1/A0.2 → A4 (Data Resolver) + A2 (контракты)
- A0.3 → A7 (observability)

---

## 4) Архитектурный план (полный, по шагам)

### A1. Decision Orchestrator (скелет, без смены поведения)
**Почему:** нужна одна точка истины для логики, чтобы исключить дрейф.
**Зависимости:** нет.
**Как делаем:**
1) В `truffles-api/app/routers/webhook/decision.py` описываем полный Decision Graph как последовательность стадий.
2) Возвращаем `DecisionPlan` (action + причины + контекст). Без побочных эффектов.
3) В `_legacy.py` оставляем только исполнение плана (send/save/trace).
4) Добавляем trace по каждой стадии (State/Risk/Expected/Semantic/Data/Action/Response/Update).
**Артефакты:** новый оркестратор + чистый исполнитель.
**DoD:** порядок решений один, поведение не изменилось, trace отражает стадии.

### A2. Контракты между мышлением и фактами (schema‑first)
**Почему:** чтобы смысл не мог подменить факты.
**Зависимости:** A1.
**Как делаем:**
1) Добавляем Pydantic‑контракты: Intent/Context/Fact/Action/Response/Memory/Trace.
2) Валидируем LLM‑выход в `intent_service.py`.
3) Валидируем факты/политики перед ответом в `_legacy.py`/Data Resolver.
4) Любой контрактный сбой → безопасный fallback + trace.
**Артефакты:** новые схемы в `truffles-api/app/schemas/`.
**DoD:** факты не проходят без контракта; все отказы фиксируются в trace.

### A3. State Machine как единственный источник истины
**Почему:** скрытые переходы ломают SLA и безопасность.
**Зависимости:** A1.
**Как делаем:**
1) Любое изменение `conversation.state` только через `state_service`.
2) Добавить инварианты (pending требует active handover + topic).
3) В оркестраторе фиксировать нарушения как stop‑line.
**Артефакты:** централизованные переходы.
**DoD:** прямых присваиваний `conversation.state` вне `state_service` нет.

### A4. Data Resolver + Fact Gate
**Почему:** факты должны быть из данных, иначе риск доверия.
**Зависимости:** A2.
**Как делаем:**
1) Вводим единый Data Resolver, который возвращает Fact Contract.
2) Response‑слой получает только Fact Contract, а не raw‑данные.
3) Если факта нет → 1 уточнение → эскалация.
**Артефакты:** единый Fact Contract.
**DoD:** текст ответа всегда имеет источник факта.

### A5. Memory + Lifecycle (долгий горизонт)
**Почему:** LLM не запоминает стабильно; нужен внешний контекст.
**Зависимости:** A1.
**Как делаем:**
1) Унифицируем summary + TTL + re‑entry правила.
2) Старые слоты требуют подтверждения.
3) Pending‑resume восстанавливает только допустимый snapshot.
**Артефакты:** единая политика памяти.
**DoD:** re‑entry всегда начинается как NEW с summary.

### A6. Safety/Policy rules‑as‑data
**Почему:** риск‑зоны нельзя держать в эвристиках.
**Зависимости:** A2 + A4.
**Как делаем:**
1) Все policy‑решения только по policy‑pack.
2) Если правил нет — эскалация, без попытки “объяснить”.
3) Удаляем обходы LLM вокруг policy.
**Артефакты:** чистый Policy Gate.
**DoD:** любой риск уходит в эскалацию.

### A7. Observability + Budget Control
**Почему:** без метрик и лимитов масштаб неуправляем.
**Зависимости:** A1.
**Как делаем:**
1) Trace/meta обязательны на каждом решении.
2) Вводим лимиты LLM на тенанта и деградации (fallback → эскалация).
3) Записываем причины деградации в trace.
**Артефакты:** бюджетный слой + метрики.
**DoD:** каждая деградация фиксируется, стоимость контролируема.

---

## 5) Очередность выполнения (жёсткая)

1) **A0** (совместимость/CI‑устойчивость) — минимальные фиксы без изменения логики.
2) **A1 → A2** (скелет + контракты) — без этого всё остальное расползается.
3) **A3 → A5** (state + memory) — стабильная жизнь диалогов и пауз.
4) **A4 → A6** (факты + policy) — безопасность и truth‑first.
5) **A7** (наблюдаемость и бюджет) — контроль качества и стоимости.

---

## 6) Проверка и доказательства (для каждой фазы)

- Trace/meta на каждом шаге Decision Graph.
- State‑инварианты не нарушаются (pending только с handover и topic).
- Ответы содержат только Fact Contract.
- Любой риск → эскалация.
- Re‑entry после TTL требует подтверждения старых фактов.

**Важно:** локальные pytest не являются gate; подтверждение — через CI и trace/meta.

---

## 7) Старт новой сессии (чеклист)

1) Прочитать: `docs/NORTHSTAR.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ESCALATION.md`.
2) Открыть текущий этап в этом roadmap и убедиться в зависимостях.
3) Работать по шагам A1 → A2 → A3 → A5 → A4 → A6 → A7.
4) Любая правка — с фиксацией “почему/что/как” и trace‑evidence.
