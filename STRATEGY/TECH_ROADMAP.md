# ТЕХНИЧЕСКИЙ ROADMAP

**Статус:** CANON  
**Owner:** Жанбол  
**Обновлено:** 2026-01-15  
**Scope:** приоритеты и фазы развития технической части.  
**Out of scope:** реализация задач, evidence.  
**Links:** `STATE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/INFRASTRUCTURE.md`.

**Цель:** управляемый LLM‑консультант для салонов с детерминированным ядром и “живым” ответом.

---

## КАНОН (не меняется)

1. **Safety/Policy выше смысла; LAW‑гейты и truth‑first всегда.**
2. **Deterministic Core** для фактов и решений (часы, адрес, услуги, цены, правила).
3. **LLM — для смысла, подачи и консультации**, не для бизнес‑решений.
4. **Гибрид обязателен.** Семантика — LLM, слоты/факты — resolver‑слой (offline‑first).
5. **Факты только из data packs.** Иначе уточнение → эскалация.
6. **Один Decision Graph.** Решения идут по фиксированной цепочке, без “долгих размышлений”.
7. **Память явная.** Старые факты требуют подтверждения.
8. **Trace/meta на всё.** Иначе решение считается “не существующим”.
9. **CORE‑eval в CI блокирует релиз**, long‑eval — отдельный tier.

---

## ПРАВИЛА РАЗРАБОТКИ (без велосипедов)

1. **Сначала ищем готовое решение.** Новая логика = сначала стандартные библиотеки/инструменты/контейнеры, потом код.
2. **Запрещены костыли и “под кейсы”.** Исправляем причину, не симптомы.
3. **Любая реализация привязана к ценности.** Для каждого компонента фиксируем: цель → реализация → доказательство.
4. **Никаких “старых методологий”.** Используем актуальные и поддерживаемые инструменты, документируем выбор.
5. **One‑issue flow.** Одна проблема → одна правка → одна проверка → evidence.

---

## CANON AUDIT PLAN (P0)

**Goal:** runtime соответствует канону для старта бизнеса (стабильно + быстрый онбординг), только evidence-first.

**Scope:** P0 инварианты (LAW/policy, truth-first, booking/consult, trace/meta, pending/outbox, observability, onboarding).  
**Out of scope:** внедрение новых фич; любые фиксы идут отдельными задачами после аудита.

**Canon sources:** `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`.

**Status legend:** pending / in_progress / verified / gap (gap = подтвержденное несоответствие с evidence).

**Audit guardrails:**
- Статусы в этом плане — статусы аудита, не статусы системы. Фактический статус и evidence фиксируются только в `STATE.md`.
- Любой `verified`/`gap` обязан ссылаться на evidence в `STATE.md` (conv_id/trace/SQL/CI).
- Любые фиксы — только через отдельный Task Package с CA‑ID.
- Live-check процесс: см. `SPECS/SYSTEM_REFERENCE.md` (Live-check SOP); запуск через `ops/diagnose.py livecheck`.
- CI обязан покрывать все CA‑инварианты: для пунктов с live‑evidence используется CI live‑check job (safety‑контур обязателен).
- Live‑check в CI на проде допускается **только** в dev‑фазе при включённом safety‑контуре; после готовности — выборочный ручной live‑check владельцем.

### Checklist (evidence-first)

| ID | Requirement | Canon source | Evidence required | Status |
| --- | --- | --- | --- | --- |
| CA-01 | Hard-LAW pre-LLM gate на всех входах (`/webhook`, `/message`) | REQUIREMENTS + CONSULTANT | code refs + decision_trace `policy_gate=hard_law` + decision_meta `action=escalate` + live-check (conv_id, msg_id) | in_progress |
| CA-02 | Policy gates (discounts/payment) по policy_pack, fail-closed | REQUIREMENTS + CONSULTANT | code refs + trace `policy_gate` (`policy_type`, `risk_level`) + CI core case + live-check | pending |
| CA-03 | Truth-first факты + info_bundle инвариант | CONSULTANT + ARCHITECTURE | trace `truth_gate/info_class` + `info_sections` + llm_used=false + CI core info cases | pending |
| CA-04 | Service matcher + service presence ответы | CONSULTANT | trace `service_matcher/service_presence` + CI core service cases + live-check | pending |
| CA-05 | Booking-first + expected_reply интерпретатор + booking_interrupt | CONSULTANT | trace `booking/booking_interrupt` + `expected_reply_type` + CI booking tests + live-check | pending |
| CA-06 | Consult pack-only + short-circuit при явной услуге | CONSULTANT | trace `consult_flow/consult` + `consult_playbook_id` + `source=pack` + CI consult cases | pending |
| CA-07 | OOD + low-signal guard + smalltalk redirect | CONSULTANT + ARCHITECTURE | trace `out_of_domain/fast_intent/smalltalk` + CI core cases | pending |
| CA-08 | State machine + pending/manager_active поведение | ESCALATION | trace `pending_sla/pending_resume` + SQL state vs handover + live-check | pending |
| CA-09 | Escalation pipeline + manager reply + learning trigger | ESCALATION | Telegram flow logs + DB handovers update + manager reply delivered + learned_responses/Qdrant evidence (owner) | pending |
| CA-10 | Outbox ack-first + dedup + idempotency | ARCHITECTURE | trace `outbox/dedupe` + SQL outbox status + `/admin/outbox/process` evidence | pending |
| CA-11 | Trace/meta coverage + critical stages retention | ARCHITECTURE | SQL decision_trace stages + trace validation + missing-stage audit | pending |
| CA-12 | Router SLA + LLM budget/degradation | ARCHITECTURE + REQUIREMENTS | decision_meta router_* + trace `budget_gate/llm_degradation` + `/admin/metrics` | pending |
| CA-13 | Branch routing isolation before pricing | ARCHITECTURE + REQUIREMENTS | decision_meta `branch_id/knowledge_tag` + RAG filter evidence + live-check | pending |
| CA-14 | Onboarding readiness (pack validate + sync) | TECH_ROADMAP + MULTI_TENANT | `ops/sync_client.py --validate` output + Qdrant sync log + `/admin/version` | pending |
| CA-15 | Observability baseline (health/metrics/alerts) | REQUIREMENTS + ARCHITECTURE | `/admin/health` + `/admin/metrics` + `/alerts/test` + no_response alerts evidence | verified (STATE.md:783) |

---

## ПРОФЕССИОНАЛЬНЫЙ ПЛАН РАЗВИТИЯ (что/почему/как)

### Фаза 1 — A4→A6→A7 (ядро фактов, политики, наблюдаемость)
**Почему:** это базовая надежность и безопасность; без неё любой “быстрый” масштаб превращается в костыли.
**Что делаем:**
1. **A4 Data Resolver + Fact Gate** — факты только из data packs; все ответы имеют FactContract.
2. **A6 Policy rules‑as‑data** — LAW/риски и скидки живут в policy‑pack, без LLM‑обходов.
3. **A7 Observability + Budget** — метрики/trace/лимиты, причины деградации фиксируются.
**Как проверяем:** CI core/long + trace/meta + `/admin/metrics`.

### Фаза 2 — Быстрый онбординг (операционный стандарт)
**Почему:** масштабируемость без ручного хаоса.
**Что делаем:**
1. **Официальный “ручной” чек‑лист** остаётся единственным источником истины до автоматизации
   (`SPECS/MULTI_TENANT.md`).
2. **Автоматизация**: либо реально появляется `onboard_client.py`, либо удаляем упоминания из структуры.
3. **Валидация packs** через `ops/sync_client.py --validate` (без генерации новых файлов).
**Как проверяем:** синк в Qdrant, smoke‑check в WhatsApp, `/admin/version`.

### Фаза 3 — UX для админов (Telegram‑first, затем Web)
**Почему:** операционная эффективность и контроль SLA.
**Что делаем:**
1. **Telegram как официальный UI**: статусы pending/active/resolved, карточка заявки, SLA‑сообщения.
2. **Минимальный web‑админ** через `/admin/*` API (monitoring/knowledge‑backlog).
3. **Dashboard** (P2/P3) после стабилизации ядра.
**Как проверяем:** trace pending‑SLA, `/admin/health`, ручной smoke.

### Фаза 4 — Auto‑Learning (после реальных данных)
**Почему:** снижение эскалаций и затрат.
**Что делаем:**
1. **Очередь learned_responses** + модерация (owner auto‑approve, остальные pending).
2. **Upsert в Qdrant** только после approval.
3. **Метрика эффекта**: снижение escalation rate.
**Как проверяем:** записи в learned_responses + Qdrant payload + `/admin/metrics`.

---

## ПРИОРИТЕТЫ

### P0 — Детерминизм и релизная стабильность
- Base‑80 CORE: часы/адрес/услуги/цены/скидки/парковка/guest_policy без OpenAI.
- Taxonomy → Alias Expansion: ServiceSample расширяет aliases **только** для услуг салона.
- CI deploy без конфликтов; `/admin/version` всегда = HEAD.
- Core/long в CI раздельно; локальные тесты не являются gate.

### P1 — “Разумный хост”
- Goal‑stack и consult‑return при перебивках.
- Answer‑Interpreter: устойчивое понимание ответов клиента на вопрос бота.
- RU/KZ resolver слотов (datetime/name/service): data‑lexicon + `dateparser`/`rapidfuzz`, без расширения regex/словников.
- Router SLA <10% fallback с прозрачным `fallback_reason`.
- Long‑хаос 12–15 ходов в `EVAL_TIER=long`.

### P2 — Active Learning
- Очередь `learned_responses` + модерация.
- Калибровка по живым диалогам, tenant‑only, opt‑in.
- Метрики “где ломается” и регрессии.

### P3 — Enterprise слой
- Единый мониторинг качества (SLA/ошибки/регрессии).
- CRM/Calendar интеграции (Bitrix/Amo/Google Calendar).
- Версионирование client_pack и аудит фактов.

---

## ТЕКУЩИЙ СТАТУС (DERIVED, НЕ ИСТОЧНИК ИСТИНЫ)

_Сводка для ориентира; актуальный статус и evidence — в `STATE.md`._

| Блок | Статус |
|------|--------|
| Base‑80 CORE | In Progress (E4xx фикс‑луп) |
| CI split core/long | ✅ Done |
| LLM Router + Answer‑Interpreter | ⚠️ Partial (SLA tuning) |
| Goal‑stack/consult‑return | ✅ Done |
| Active learning queue | 📋 Plan |
| Monitoring | ⚠️ Partial |

---

## БЛИЖАЙШИЕ ЗАДАЧИ (P0)

1. Закрыть Base‑80 CORE без OpenAI.
2. Авто‑обогащение aliases из ServiceSample для услуг салона.
3. Проверить стабильность CI‑deploy (без конфликтов контейнера).

## БЛИЖАЙШИЕ ЗАДАЧИ (P1)

1. **Закрыть evidence для Task A/B**:
   - pending_wait trace + pending_action meta, retention не теряет запись.
   - consult pack meta/trace (consult_playbook_id/consult_variant_id/tips_used/source=pack).
   - policy_gate trace на “Есть скидки?”.
2. **Router SLA evidence**: controller_attempted/low_confidence/fallback_reason + SQL‑breakdown, зафиксировать в `STATE.md`
   (допускается waiver для simulated `/webhook`).
3. **Подтвердить consult pack‑runtime (post‑merge)**: live‑check evidence + запись в `STATE.md`.
4. **Запустить блок GAP‑014/015/016** (после evidence):
   - Hard‑LAW pre‑LLM gate для всех входов,
   - `/message` выключить или прогнать через общий pipeline,
   - policy_pack для всех клиентов (fail‑closed при отсутствии правил).
5. **Outbox latency** — отложено до закрытия пунктов 1–4 (фиксируем в конце).
6. **GAP‑017 (branch isolation)** — backfill Qdrant с `branch_id/knowledge_tag` и включить strict branch‑filter (без fallback).

---

*Обновлено: 2026-01-14*

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
- Контракты между слоями частично зафиксированы (Pydantic schemas + trace validation есть), но enforcement в legacy не полный.
- Decision Graph размазан в `_legacy.py`.
- Карточка менеджера не содержит summary/next step.
- Budget/Rate Control частично: LLM budget gate есть, per‑tenant rate limits отсутствуют.
- Learning backlog не выделен как процесс (есть частичное добавление в knowledge).

### 4.8 Сравнение текущего и целевого (по слоям)

- Decision Graph: сейчас логика размазана по `_legacy.py` → цель: единый оркестратор `decision.py` → этап A1.
- Контракты: Pydantic контракты Intent/Fact/Action/Response/Trace есть (`decision.py`/`trace.py`), цель — полное покрытие legacy → этап A2.
- Resolver‑слой (slots): сейчас эвристики/regex → цель: единый offline‑resolver RU/KZ → этап A4.
- Policy Gate: сейчас смешан с логикой → цель: rules‑as‑data (policy pack) → этап A6.
- State Machine: сейчас ручные переходы → цель: явная FSM и инварианты → этап A3.
- Memory/Lifecycle: сейчас TTL разрознен → цель: единый контракт памяти + re‑entry → этап A5.
- Observability/Budget: trace + бюджет есть, метрики/алерты частично → цель: полный A7.

### 4.9 Готовые инструменты (обязательный список, без велосипедов)

- FSM/State Machine: `python-statemachine` (A3).
- Контракты/валидация: `pydantic` (A2), опционально `jsonschema` для data packs.
- Policy rules‑as‑data: `jsonlogic` (A6).
- Time/Date resolver: `dateparser` (Python) для RU/KZ (A4).
- Service/name matching: `rapidfuzz` для alias‑matching поверх data pack (A4).
- Observability: `prometheus_client` + `sentry-sdk` (A7).

---

## 4.10 КАРТА КОМПОНЕНТОВ (ценность → реализация → доказательство)

| Компонент | Ценность | Реализация (код) | Данные | Доказательство |
|---|---|---|---|---|
| Ingress + Outbox | Ответ 24/7 без потерь | `app/routers/webhook/_legacy.py`, `app/services/outbox_service.py` | outbox DB | `/admin/health`, `/admin/metrics` |
| Decision Graph + Trace | Объяснимые решения | `app/routers/webhook/decision.py`, `app/routers/webhook/trace.py` | decision_trace/meta | CI core/long |
| State Machine | SLA и корректная эскалация | `app/services/state_service.py` | conversations.state | CI core/long |
| Memory + Re‑entry | Длинные диалоги без дрейфа | `app/routers/webhook/session_memory.py`, `context_manager.py` | context/session_memory | trace `session_memory` |
| Fact Resolver | “Не выдумывает” | `app/services/demo_salon_knowledge.py` + truth‑gate | client_pack/YAML | FactContract trace |
| Policy Gate | LAW‑безопасность | policy‑pack + `demo_salon_knowledge.py` | policy data | trace policy_gate |
| Booking | Конверсия в запись | `app/routers/webhook/booking.py` | booking context | EVAL booking |
| Escalation UX | Ответ человека вовремя | `app/services/escalation_service.py`, `telegram_webhook.py` | handovers | pending‑SLA trace |
| Onboarding | Быстрый запуск клиента | `ops/sync_client.py`, `SPECS/MULTI_TENANT.md` | client_pack | smoke‑check |
| Active Learning | Снижение эскалаций | `app/services/learning_service.py` (partial) | learned_responses | `/admin/metrics` |

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

1) Прочитать: `AGENTS.md` → `STATE.md` → `STRATEGY/VISION.md` → `SPECS/ARCHITECTURE.md` → `SPECS/ESCALATION.md`.
2) Открыть текущий этап A0–A7 в этом roadmap и проверить зависимости.
3) Сформировать Session Card (Goal/Stage/Blocker/Evidence/Scope/DoD/Tests/Risks/Owner).
4) Для передачи Hands обязателен Task Package по шаблону в `AGENTS.md` (Scope/Out of scope/Files/Steps/DoD/Tests/Evidence/Dependencies/Risks).
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
