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
3) **Гибрид обязателен.** Семантика — LLM, слоты/факты — resolver‑слой (offline‑first).
4) **Truth‑first.** Факты только из data packs; иначе уточнение → эскалация.
5) **Один Decision Graph.** Решения идут по фиксированной цепочке, без “долгих размышлений”.
6) **Память явная.** Старые факты требуют подтверждения.
7) **Trace/meta на всё.** Иначе решение считается “не существующим”.

---

## 2) Прозрачный протокол сессии (обязательный)

**Цель:** любая сессия должна быть воспроизводима и понятна без устных объяснений.

**Источники истины (читать перед началом):**
- `AGENTS.md` — правила ролей/stop‑line.
- `STATE.md` — текущее подтвержденное состояние.
- `docs/NORTHSTAR.md` — продуктовая цель.
- `SPECS/ARCHITECTURE.md` — архитектурные инварианты.
- `SPECS/ESCALATION.md` — процесс эскалации.
- `STRATEGY/TECH_ROADMAP.md` — этап, зависимости, DoD.

**Принцип прозрачности:**
- “Что сделано” фиксируется только в `STATE.md` с evidence (CI/trace/лог). В roadmap не дублируем факты.
- “Что делаем” фиксируется через Session Card и ссылку на этап A0–A7.

**Session Card (обязательный формат):**
- Goal
- Stage (A0–A7) + Why now
- Blocker/Evidence (CI run URL / trace / log)
- Scope (files allowed)
- DoD (acceptance)
- Tests/Checks (CI / live / trace)
- Risks / Stop-line triggers
- Owner (role)

**Порядок сессии (сквозной):**
1) Подтвердить роль и права (Architect/Brain/Hands).
2) Прочитать источники истины (список выше).
3) Определить активный этап и блокер (доказательство).
4) Сформировать Session Card и согласовать с Brain.
5) Выполнить один issue (1 проблема → 1 правка → 1 проверка).
6) Зафиксировать evidence (trace/meta + CI).
7) Передать результат в формате GOAL/FILES/TESTS/LIVE/EVIDENCE/COMMIT/RISKS.
8) Brain коммитит/пушит, обновляет STATE.md (последним).

---

## 3) Протокол реализации (скелет для всех этапов)

**Цель:** единый порядок действий, чтобы этапы были совместимы и не ломали систему.

**Цепочка выполнения (обязательная):**
1) Диагностика: где в Decision Graph ломается поведение, какие инварианты нарушены.
2) Решение: минимальная правка, совместимая с A1–A7; без изменения поведения.
3) Реализация: точечные изменения в существующих файлах, без “велосипедов”.
4) Проверка: CI + trace/meta; локальные тесты не gate.
5) Фиксация: evidence и передача Brain (коммит/STATE).

**Stage Card (обязательный формат для A0–A7):**
- Вход (док/код)
- Действия (по шагам)
- Выход (артефакты)
- Проверка (CI/trace)
- Риски/Stop-line

---

## 4) Базовая реализация (что уже есть)

**Важно:** статус “сделано/не сделано” фиксируется в `STATE.md` с evidence. Здесь только карта опорных модулей.

### 4.1 Вход + оркестрация
- Единый вход: `truffles-api/app/routers/webhook/_legacy.py`.
- Решения пишут trace/meta: `truffles-api/app/routers/webhook/trace.py`.

### 4.2 Состояния диалога
- Состояния: `Conversation.state` (`bot_active/pending/manager_active`) в `truffles-api/app/models/conversation.py`.
- Переходы: `truffles-api/app/services/state_service.py`.

### 4.3 Эскалация + Telegram
- Handover + уведомления: `truffles-api/app/services/escalation_service.py`.
- Карточка + кнопки: `truffles-api/app/services/telegram_service.py`.
- TAKE/RESOLVE/RETURN: `truffles-api/app/routers/telegram_webhook.py`.
- Ответ менеджера → клиент: `truffles-api/app/services/manager_message_service.py`.

### 4.4 Session memory (v1.1)
- Память + TTL: `truffles-api/app/routers/webhook/session_memory.py`.
- Summary: `truffles-api/app/routers/webhook/context_manager.py`.

### 4.5 Семантика и данные
- Intent‑классификация: `truffles-api/app/services/intent_service.py`.
- RAG/knowledge: `truffles-api/app/services/knowledge_service.py`.

### 4.6 Pending‑SLA
- Ping + auto‑close: `truffles-api/app/services/reminder_service.py`.
- Pending‑ветка: `truffles-api/app/routers/webhook/_legacy.py`.

### 4.7 Готовые разрывы (GAP)
- Контракты между слоями не зафиксированы в коде (нет schema‑валидации).
- Decision Graph размазан в `_legacy.py`.
- Карточка менеджера не содержит summary/next step.
- Budget/Rate Control отсутствует как системный слой.
- Learning backlog не выделен как процесс (есть частичное добавление в knowledge).

### 4.8 Сравнение текущего и целевого (по слоям)

- Decision Graph: сейчас логика размазана по `_legacy.py` → цель: единый оркестратор `decision.py` → этап A1.
- Контракты: сейчас implicit dict‑ы → цель: Pydantic‑контракты Intent/Fact/Action/Response → этап A2.
- Resolver‑слой (slots): сейчас эвристики/regex → цель: единый offline‑resolver RU/KZ → этап A4.
- Policy Gate: сейчас смешан с логикой → цель: rules‑as‑data (policy pack) → этап A6.
- State Machine: сейчас ручные переходы → цель: явная FSM и инварианты → этап A3.
- Memory/Lifecycle: сейчас TTL разрознен → цель: единый контракт памяти + re‑entry → этап A5.
- Observability/Budget: сейчас trace есть, лимитов нет → цель: метрики/бюджеты/деградации → этап A7.

### 4.9 Готовые инструменты (обязательный список, без велосипедов)

- FSM/State Machine: `python-statemachine` (A3).
- Контракты/валидация: `pydantic` (A2), опционально `jsonschema` для data packs.
- Policy rules‑as‑data: `jsonlogic` (A6).
- Time/Date resolver: `dateparser` (Python) для RU/KZ (A4).
- Service/name matching: `rapidfuzz` для alias‑matching поверх data pack (A4).
- Observability: `prometheus_client` + `sentry-sdk` (A7).

---

## 5) Мост A0 → A1…A7 (совместимость и исправления)

**Зачем:** старые ошибки и зависимости (LLM‑ключи/внешние индексы) ломают базовые сценарии и CI.  
**Принцип:** исправления должны быть совместимы с новой архитектурой и потом “переезжать” в A1–A7 без переделок.

### A0.1 Deterministic Expected Reply (service)
**Почему:** expected_reply=service не должен зависеть от LLM‑ключа или внешнего индекса.  
**Stage Card:**
- Вход: `truffles-api/app/services/intent_service.py`, `truffles-api/app/routers/webhook/_legacy.py`, `SALON_TRUTH.yaml`.
- Действия (шаги):
  1) Если LLM‑ключ отсутствует/ошибка — считать интерпретатор disabled.
  2) При `expected_reply_type=service` использовать только локальный service catalog (data pack).
  3) Добавить алиасы “общих” запросов услуги в data pack (например, “ногти”).
- Выход: deterministic service‑match без LLM/индекса.
- Проверка: CI core/long (кейсы service_choice), trace/meta показывают локальный источник.
- Риски/Stop-line: если сервисный матч зависит от LLM или внешнего индекса — stop.

### A0.2 Offline‑safe Service Match
**Почему:** semantic_service_match (внешний индекс) не всегда доступен.  
**Stage Card:**
- Вход: `truffles-api/app/services/demo_salon_knowledge.py`, `knowledge_service.py`, data pack.
- Действия (шаги):
  1) При недоступности внешнего индекса использовать только локальные aliases.
  2) Не “додумывать” сервисы по подстроке; допускается только явный alias‑match.
- Выход: офлайн‑совместимый service‑match.
- Проверка: CI core/long, отсутствие warning “embedding failed” как причины маршрутизации.
- Риски/Stop-line: подмена логики на эвристику вместо данных.

### A0.3 Trace‑evidence для A0‑путей
**Почему:** A0 должен быть измерим и проверяем.  
**Stage Card:**
- Вход: `truffles-api/app/routers/webhook/trace.py`, `_legacy.py`.
- Действия (шаги):
  1) Добавить `answer_interpreter_error` и `service_hint_source` в decision_meta.
  2) Фиксировать источник (LLM/local_pack) и причину fallback.
- Выход: trace/meta однозначно показывают A0‑путь.
- Проверка: CI long; trace содержит source/error без LLM‑ключа.
- Риски/Stop-line: trace пустой или двусмысленный.

**Связь с A1…A7:**
- A0.1/A0.2 → A4 (Data Resolver) + A2 (контракты)
- A0.3 → A7 (observability)

---

## 6) Архитектурный план (полный, по шагам)

### A1. Decision Orchestrator (скелет, без смены поведения)
**Почему:** нужна одна точка истины для логики, чтобы исключить дрейф.
**Зависимости:** нет.
**Stage Card:**
- Вход: `truffles-api/app/routers/webhook/decision.py`, `_legacy.py`, `SPECS/ARCHITECTURE.md`.
- Действия (шаги):
  1) Описать Decision Graph как последовательность стадий в `decision.py`.
  2) Вернуть `DecisionPlan` (action + причины + контекст) без побочных эффектов.
  3) В `_legacy.py` оставить исполнение плана (send/save/trace).
  4) Добавить trace по каждой стадии: State/Risk/Expected/Semantic/Data/Action/Response/Update.
- Выход: единый оркестратор + чистый исполнитель.
- Проверка: CI core/long без изменения поведения; trace отражает все стадии.
- Риски/Stop-line: изменение поведения или пропущенные стадии.

### A2. Контракты между мышлением и фактами (schema‑first)
**Почему:** чтобы смысл не мог подменить факты.
**Зависимости:** A1.
**Stage Card:**
- Вход: `truffles-api/app/schemas/*.py`, `intent_service.py`, `knowledge_service.py`, `_legacy.py`.
- Действия (шаги):
  1) Ввести Pydantic‑контракты: Intent/Context/Fact/Action/Response/Memory/Trace (расширяем существующие schemas).
  2) Валидировать LLM‑выход в `intent_service.py`.
  3) Валидировать факты/политики перед ответом в Data Resolver.
  4) Любой контрактный сбой → безопасный fallback + trace.
- Выход: проверяемый контракт на каждый слой.
- Проверка: CI core/long; trace фиксирует contract_error.
- Риски/Stop-line: “молчаливые” дефолты без trace.

### A3. State Machine как единственный источник истины
**Почему:** скрытые переходы ломают SLA и безопасность.
**Зависимости:** A1.
**Stage Card:**
- Вход: `state_service.py`, `conversation.py`, `pending.py`, `escalation_service.py`.
- Действия (шаги):
  1) Любое изменение `conversation.state` только через `state_service`.
  2) Ввести карту допустимых переходов + инварианты (pending требует active handover + topic).
  3) Нарушения фиксировать как stop‑line в trace.
- Выход: единый источник состояния.
- Проверка: CI core/long; trace отражает переходы.
- Риски/Stop-line: прямые присваивания вне `state_service`.

### A4. Data Resolver + Fact Gate
**Почему:** факты должны быть из данных, иначе риск доверия.
**Зависимости:** A2.
**Stage Card:**
- Вход: `knowledge_service.py`, `demo_salon_knowledge.py`, `SALON_TRUTH.yaml`, `policy` pack.
- Действия (шаги):
  1) Ввести единый Data Resolver, возвращающий Fact Contract.
  2) Response‑слой использует только Fact Contract, не raw‑данные.
  3) Если факта нет → 1 уточнение → эскалация (без “догадок”).
- Выход: ответы всегда с источником факта.
- Проверка: CI core/long; trace содержит fact_source.
- Риски/Stop-line: факты без источника или из LLM.

### A5. Memory + Lifecycle (долгий горизонт)
**Почему:** LLM не запоминает стабильно; нужен внешний контекст.
**Зависимости:** A1.
**Stage Card:**
- Вход: `context_manager.py`, `session_memory.py`, `state_service.py`.
- Действия (шаги):
  1) Унифицировать summary + TTL + re‑entry правила.
  2) Старые слоты требуют подтверждения.
  3) Pending‑resume восстанавливает только допустимый snapshot.
- Выход: единая политика памяти и re‑entry.
- Проверка: CI long; trace показывает re_entry + summary.
- Риски/Stop-line: использование устаревших слотов без подтверждения.

### A6. Safety/Policy rules‑as‑data
**Почему:** риск‑зоны нельзя держать в эвристиках.
**Зависимости:** A2 + A4.
**Stage Card:**
- Вход: `policy.py`, `SPECS/ESCALATION.md`, policy‑pack в data pack.
- Действия (шаги):
  1) Policy‑решения только по policy‑pack (без LLM‑обходов).
  2) Если правил нет — эскалация.
  3) Hard‑LAW всегда выше любых semantic сигналов.
- Выход: детерминированный Policy Gate.
- Проверка: CI core/long; trace содержит policy_gate/risk_level.
- Риски/Stop-line: обходы policy через LLM или эвристику.

### A7. Observability + Budget Control
**Почему:** без метрик и лимитов масштаб неуправляем.
**Зависимости:** A1.
**Stage Card:**
- Вход: `trace.py`, `admin/metrics`, `intent_service.py`, `knowledge_service.py`.
- Действия (шаги):
  1) Trace/meta обязательны на каждом решении и стадии.
  2) Ввести лимиты LLM на тенанта и деградации (fallback → эскалация).
  3) Записывать причины деградации и стоимость в trace/metrics.
- Выход: наблюдаемость + бюджетные ограничения.
- Проверка: CI core/long; метрики и trace фиксируют деградации.
- Риски/Stop-line: деградации без объяснения.

---

## 7) Очередность выполнения (жёсткая)

1) **A0** (совместимость/CI‑устойчивость) — минимальные фиксы без изменения логики.
2) **A1 → A2** (скелет + контракты) — без этого всё остальное расползается.
3) **A3 → A5** (state + memory) — стабильная жизнь диалогов и пауз.
4) **A4 → A6** (факты + policy) — безопасность и truth‑first.
5) **A7** (наблюдаемость и бюджет) — контроль качества и стоимости.

**Условия перехода между этапами:**
- A0 → A1: CI core/long зелёный без LLM‑ключа; trace фиксирует A0‑пути.
- A1 → A2: Decision Graph покрывает все стадии, trace содержит стадии без пропусков.
- A2 → A3: контракты валидируются, есть trace по contract_error.
- A3 → A5: state‑переходы идут только через `state_service`, pending/resume корректны.
- A4 → A6: факты всегда из data pack; policy‑gate не обходит LLM.
- A6 → A7: risk‑gate стабильный, далее подключаем бюджеты/метрики.

---

## 8) Проверка и доказательства (для каждой фазы)

- Trace/meta на каждом шаге Decision Graph.
- State‑инварианты не нарушаются (pending только с handover и topic).
- Ответы содержат только Fact Contract.
- Любой риск → эскалация.
- Re‑entry после TTL требует подтверждения старых фактов.

**Важно:** локальные pytest не являются gate; подтверждение — через CI и trace/meta.

---

## 9) Старт новой сессии (чеклист)

1) Прочитать: `AGENTS.md` → `STATE.md` → `docs/NORTHSTAR.md` → `SPECS/ARCHITECTURE.md` → `SPECS/ESCALATION.md`.
2) Открыть текущий этап A0–A7 в этом roadmap и проверить зависимости.
3) Сформировать Session Card (Goal/Stage/Blocker/Evidence/Scope/DoD/Tests/Risks/Owner).
4) Работать строго по Stage Card выбранного этапа (один issue).
5) Любая правка — с фиксацией “почему/что/как” и trace‑evidence; передать Brain в формате handoff.

---

## 10) Уроки (подтвержденные фактами)

- Offline‑путь должен быть first‑class: CI без LLM выявляет пробелы resolver‑слоя (E553/E556).
- Контракт expected_reply обязателен для любого уточнения: отсутствие ломает trace и ветвление (E554).
- Trace‑retention должен покрывать long‑диалоги: иначе теряются критичные записи (E554).
- TTL consult‑контекста должен соответствовать длине long‑eval (E564).
- YAML‑turns с `:` требуют кавычек, иначе тест валится на parsing (E564).
- Явная фраза “меня зовут …” должна побеждать шум сервис/время (E563).
