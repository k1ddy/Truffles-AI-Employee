# ARCHITECTURE — Техническая архитектура Truffles

**Статус:** CANON  
**Owner:** Top Architect  
**Обновлено:** 2026-01-22  
**Scope:** архитектура рантайма, decision graph, компоненты и потоки.  
**Out of scope:** тарифы/продажи, evidence/CI.  
**Links:** `SPECS/CONSULTANT.md`, `SPECS/INFRASTRUCTURE.md`, `STATE.md`.

**Читай это перед любыми изменениями.**
---

## 1. Репозиторий и процесс

| Параметр | Значение |
|----------|----------|
| Репозиторий | `github.com/k1ddy/Truffles-AI-Employee` (один) |
| Главная ветка | `main` |
| Политика PR | По умолчанию через PR + CI; прямые коммиты в main — исключение. |
| CI | GitHub Actions (`.github/workflows/ci.yml`): ruff+pytest, build+push to GHCR, optional deploy |

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
| Оркестрация | Docker (prod через `restart_api.sh`), Docker Compose (local/infra) |
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
POST /webhook/{client_slug} (direct ChatFlow; /webhook — legacy wrapper; webhook_secret проверяется если задан)
    ↓
enqueue outbox_messages (PENDING)
    ↓
outbox worker (тик 2s) или POST /admin/outbox/process (cron)
    ↓
_handle_webhook_payload(skip_persist=True)
    ↓
behavioral shield (spam/toxic) → pending/opt‑out/Hard‑LAW escalation → policy‑gates (скидки/оплата info)
→ answer‑interpreter (expected_reply_type) → LLM‑first понимание (intent/slots JSON) + semantic resolver → early OOD (только при out‑signals без in‑signals)
→ tools/packs fact‑resolver (info/consult/booking/service) → fast intent (smalltalk) → LLM‑формулировка поверх фактов → Response Guard → truth gate fallback → low‑confidence handling
    ↓
chatflow_service → WhatsApp (single request; msg_id idempotency; retries/backoff отсутствуют)
```

#### Outbox payload contract + action gate
- **Контракт payload:** валидируем перед enqueue (см. `contracts/events/outbox.webhook_payload.v1.jsonschema` и `truffles-api/app/schemas/outbox_payload.py`).  
- **Поведение при ошибке:** `decision_trace.stage=outbox_payload_guard`, `decision_meta.action=error`, outbox не ставится в очередь.  
- **Timing в БД:** `decision_meta.timing.outbox` + `outbox_messages.meta.timing` (корреляция по `outbox_id`/`inbound_message_id`/`trace_id`).  
- **Action gate:** если `decision_meta.action` не записан — фиксируем `action_gate` и `action=error` перед commit.  

#### Stage order snapshot
- Каноничный порядок стадий фиксируется в `DECISION_STAGE_ORDER_SNAPSHOT` (`truffles-api/app/routers/webhook/trace.py`) и защищён hash‑тестом.  
- Любая смена порядка стадий → обновить список + test hash (сознательное изменение).  

#### Observability (DEC-012)
- Корреляция: `message_id`/`outbox_id`/`trace_id` в логах + decision_meta + outbox meta.
- Тайминги стадий: `decision_meta.timing.stages` + `decision_meta.timing.outbox` + `outbox_messages.meta.timing`.
- OTel spans в API/outbox/sentinel с атрибутами `message_id`, `outbox_id`, `trace_id`, `client_slug`, `conversation_id`, `branch_id`; Tempo хранит трейсы.

#### Observability roadmap (Phase 2; follow-ups after DEC-012)
1) Trace retention policy (Tempo)  
   - Зафиксировать retention для Tempo (L0/L1/L2), бюджет хранения, безопасность.  
   - Ввести единую схему `trace_event` + экспортер из decision_trace.  
   - Добавить trace‑viewer и правила retention (L0/L1/L2).  
   - CI‑гейт: критические стадии не теряются.  
2) Unified log contract + alerts  
   - Лог‑схема: обязательные ключи `message_id`, `outbox_id`, `trace_id`, `stage`, `elapsed_ms`.  
   - Внедрить wrapper в API + outbox + console, добавить алерты (missing_action, outbox_p90, error_rate).  
   - Обновить `docs/runbooks/INCIDENTS.md` + `docs/runbooks/OUTBOX.md`.  
3) Stage order snapshot + SOP  
   - Snapshot уже в коде (Phase 1), добавить SOP “изменение порядка стадий” в `docs/runbooks/TRACE_BUNDLE.md`.  
   - Любая правка → обновление snapshot hash + запись причины.  

### Decision Graph (legacy map, `_legacy.py`)
Фактическая карта стадий и ранних return в `_handle_webhook_payload` (legacy pipeline). Это **не** целевой оркестратор `decision.py`, а снимок текущего поведения. Целевой канон добавляет стадии `semantic_resolver`, `tool_fact_resolver`, `response_guard`.

#### Stage order (gates/early returns)
1) Preflight rejects и outbox-only путь → early return с `preflight`/`outbox`/`outbox_payload_guard` trace (если conversation резолвится; иначе trace не пишется).
2) Контракт + план Decision Graph → `contract`, `decision_graph`.
3) Session memory + re-entry + carryover cleanup → `session_memory`, `re_entry`, `class_carryover`, `service_carryover`, `consult_context`.
4) Expected reply (answer interpreter) → `question_contract`.
5) Branch selection prompt/confirm → early return с `branch_selection` trace.
6) Behavioral shield → `shield` (drop/escalate).
7) Policy/Hard-LAW gate → `policy_gate`.
8) State/pending/mute gates → `routing`, `rejection`, `pending_*`.
9) Media-only handling → `media`.
10) Debounce/hand‑over confirmation → early return с `debounce`/`handover_confirmation` trace.
11) Router + intent decomposition + carryover guard → `intent_decomposition`, `class_router`, `intent`, `carryover_guard`.
12) Domain flows (booking/info/consult) → `booking_gate`, `complaint_guard`, `out_of_domain`, `consult_flow`, `intent_queue`, `booking`, `consult`, `clarify_guard`, `booking_interrupt`, `service_matcher`, `truth_gate`, `multi_truth`, `service_semantic_matcher`, `time_only_guard`, `info_class`.
13) Fast intent (smalltalk) before LLM → `fast_intent`.
14) LLM response/fallback → `llm_guard`, `ai_response`, `rewrite`, `budget_gate`, `llm_degradation`.
15) Post-response hooks (summary/consult return) → `context_manager`, `consult_return`.
16) Escalation/state updates → `escalation`, `state_transition`.
17) Action gate (missing action) → `action_gate`.

#### Legacy stage map (stage → condition → action → trace)
| Stage | Condition | Action | Trace |
| --- | --- | --- | --- |
| `preflight` | Missing client/remoteJid/empty message | Фиксируем причину reject | decision_trace.stage=`preflight` (`truffles-api/app/routers/webhook/_legacy.py:1777`) |
| `outbox_payload_guard` | Invalid outbox payload contract | Reject enqueue, action=error | decision_trace.stage=`outbox_payload_guard` (`truffles-api/app/routers/webhook/outbox.py`) |
| `skip_persist` | skip_persist: missing conversation/user | Фиксируем причину skip_persist | decision_trace.stage=`skip_persist` (`truffles-api/app/routers/webhook/_legacy.py:2026`) |
| `dedupe` | Duplicate message_id | Фиксируем dedupe skip | decision_trace.stage=`dedupe` (`truffles-api/app/routers/webhook/_legacy.py:2097`) |
| `outbox` | enqueue_only accept | Фиксируем outbox accept | decision_trace.stage=`outbox` (`truffles-api/app/routers/webhook/_legacy.py:2277`) |
| `branch_selection` | Branch prompt/confirm | Фиксируем prompt/choice | decision_trace.stage=`branch_selection` (`truffles-api/app/routers/webhook/_legacy.py:3141`) |
| `debounce` | Debounce skip/manager_active after debounce | Фиксируем debounce решение | decision_trace.stage=`debounce` (`truffles-api/app/routers/webhook/_legacy.py:4358`) |
| `handover_confirmation` | Handover confirmed/declined | Фиксируем подтверждение | decision_trace.stage=`handover_confirmation` (`truffles-api/app/routers/webhook/_legacy.py:4514`) |
| `state_transition` | Попытка перехода состояния при handover (invalid) | Логируем нарушение перехода | decision_trace.stage=`state_transition` (`truffles-api/app/routers/webhook/_legacy.py:1574`) |
| `escalation` | Reuse/создание handover | Фиксируем reuse + telegram_sent | decision_trace.stage=`escalation` (`truffles-api/app/routers/webhook/_legacy.py:1595`) |
| `budget_gate` | LLM budget events | Allow/deny + budget meta | decision_trace.stage=`budget_gate` (`truffles-api/app/routers/webhook/_legacy.py:1739`) |
| `llm_degradation` | LLM деградация (timeout/skip) | Фиксируем reason | decision_trace.stage=`llm_degradation` (`truffles-api/app/routers/webhook/_legacy.py:1777`) |
| `rewrite` | RAG rewrite применён/пропущен | Запись rewrite_used/text | decision_trace.stage=`rewrite` (`truffles-api/app/routers/webhook/_legacy.py:1816`) |
| `contract` | Контракты context/intent/fact/action/response | OK/error по схеме | decision_trace.stage=`contract` (`truffles-api/app/routers/webhook/_legacy.py:2070`) |
| `decision_graph` | План Decision Graph | Запись plan_id + стадий | decision_trace.stage=`decision_graph` (`truffles-api/app/routers/webhook/_legacy.py:2087`) |
| `fact_guard` | fact_source есть, фактов нет | Clarify или escalate | decision_trace.stage=`fact_guard` (`truffles-api/app/routers/webhook/_legacy.py:2251`) |
| `fact_resolver` | Факты/источники собраны | Resolved/missing | decision_trace.stage=`fact_resolver` (`truffles-api/app/routers/webhook/_legacy.py:2331`) |
| `session_memory` | Reset/contract_error/expected_reply_fallback | Обновление/сброс памяти | decision_trace.stage=`session_memory` (`truffles-api/app/routers/webhook/_legacy.py:2409`) |
| `re_entry` | Требуется re-entry после reset/resume | Пометка re-entry | decision_trace.stage=`re_entry` (`truffles-api/app/routers/webhook/_legacy.py:2466`) |
| `class_carryover` | Истёк class carryover | Пометка expired | decision_trace.stage=`class_carryover` (`truffles-api/app/routers/webhook/_legacy.py:2534`) |
| `service_carryover` | Истёк service carryover | Пометка expired | decision_trace.stage=`service_carryover` (`truffles-api/app/routers/webhook/_legacy.py:2543`) |
| `consult_context` | Истёк consult context | Пометка expired | decision_trace.stage=`consult_context` (`truffles-api/app/routers/webhook/_legacy.py:2552`) |
| `context_manager` | Summary/goal/refusal updates | Обновление контекста | decision_trace.stage=`context_manager` (`truffles-api/app/routers/webhook/context_manager.py:753`) |
| `question_contract` | Expected reply match/miss/invalid | Запись expected_reply_type/value | decision_trace.stage=`question_contract` (`truffles-api/app/routers/webhook/_legacy.py:2761`) |
| `shield` | Spam/too_long/toxic/nonsense | Drop или escalate | decision_trace.stage=`shield` (`truffles-api/app/routers/webhook/_legacy.py:2937`) |
| `policy_gate` | Hard‑LAW/discount/payment rules | Reply/escalate | decision_trace.stage=`policy_gate` (`truffles-api/app/routers/webhook/_legacy.py:3078`) |
| `routing` | State gate (manager_active/muted) | Silent/skip reply | decision_trace.stage=`routing` (`truffles-api/app/routers/webhook/_legacy.py:3252`) |
| `rejection` | Opt‑out в pending | Cancel handover + mute | decision_trace.stage=`rejection` (`truffles-api/app/routers/webhook/_legacy.py:3526`) |
| `pending_sla` | pending_close/ack/ping | Обновление pending_action | decision_trace.stage=`pending_sla` (`truffles-api/app/routers/webhook/_legacy.py:3556`) |
| `pending_resume` | pending_ack + resume snapshot | Restore context + re_entry | decision_trace.stage=`pending_resume` (`truffles-api/app/routers/webhook/_legacy.py:3605`) |
| `pending_status` | pending status вопрос | Reply status | decision_trace.stage=`pending_status` (`truffles-api/app/routers/webhook/_legacy.py:3647`) |
| `pending_wait` | pending default wait | Reply wait | decision_trace.stage=`pending_wait` (`truffles-api/app/routers/webhook/_legacy.py:3712`) |
| `media` | Media‑only/ограничения | Media ответ/forward | decision_trace.stage=`media` (`truffles-api/app/routers/webhook/_legacy.py:3752`) |
| `intent_decomposition` | Декомпозиция intents | intents/service_query | decision_trace.stage=`intent_decomposition` (`truffles-api/app/routers/webhook/_legacy.py:4302`) |
| `carryover_guard` | Carryover ignored | Пометка ignored | decision_trace.stage=`carryover_guard` (`truffles-api/app/routers/webhook/_legacy.py:4413`) |
| `booking_gate` | Booking blocked (info/low-signal) | Отключение booking | decision_trace.stage=`booking_gate` (`truffles-api/app/routers/webhook/_legacy.py:4569`) |
| `complaint_guard` | Complaint signal | Suppress/accept | decision_trace.stage=`complaint_guard` (`truffles-api/app/routers/webhook/_legacy.py:4706`) |
| `out_of_domain` | OOD guard (early/anchor/semantic) | OOD reply | decision_trace.stage=`out_of_domain` (`truffles-api/app/routers/webhook/_legacy.py:4897`) |
| `consult_flow` | Consult clarify/escalate/short‑circuit | Выбор ветки consult | decision_trace.stage=`consult_flow` (`truffles-api/app/routers/webhook/_legacy.py:4979`) |
| `intent_queue` | Multi-intent очередь | Enqueue/dequeue | decision_trace.stage=`intent_queue` (`truffles-api/app/routers/webhook/_legacy.py:5303`) |
| `booking` | Booking flow | Prompt/capture/escalate | decision_trace.stage=`booking` (`truffles-api/app/routers/webhook/_legacy.py:5480`) |
| `consult` | Consult reply | Ответ по playbook | decision_trace.stage=`consult` (`truffles-api/app/routers/webhook/_legacy.py:5923`) |
| `consult_return` | Consult follow-up appended | Возврат к consult-вопросу | decision_trace.stage=`consult_return` (`truffles-api/app/routers/webhook/context_manager.py:656`) |
| `clarify_guard` | Clarify limit | Escalate | decision_trace.stage=`clarify_guard` (`truffles-api/app/routers/webhook/_legacy.py:6325`) |
| `booking_interrupt` | Info вопрос во время booking | Info + booking‑prompt | decision_trace.stage=`booking_interrupt` (`truffles-api/app/routers/webhook/_legacy.py:6364`) |
| `service_matcher` | Deterministic service match | Match + facts | decision_trace.stage=`service_matcher` (`truffles-api/app/routers/webhook/_legacy.py:6376`) |
| `truth_gate` | Truth‑first fact reply | Reply from pack | decision_trace.stage=`truth_gate` (`truffles-api/app/routers/webhook/_legacy.py:6384`) |
| `multi_truth` | Multi‑section facts | Combined reply | decision_trace.stage=`multi_truth` (`truffles-api/app/routers/webhook/_legacy.py:6395`) |
| `fast_intent` | Greeting/thanks/ack before LLM | Fast reply | decision_trace.stage=`fast_intent` (`truffles-api/app/routers/webhook/_legacy.py:6778`) |
| `info_class` | Info bundle reply | Location/hours/etc | decision_trace.stage=`info_class` (`truffles-api/app/routers/webhook/_legacy.py:7152`) |
| `llm_guard` | LLM blocked topics | Escalate | decision_trace.stage=`llm_guard` (`truffles-api/app/routers/webhook/_legacy.py:7503`) |
| `ai_response` | LLM response | Send bot reply | decision_trace.stage=`ai_response` (`truffles-api/app/routers/webhook/_legacy.py:7542`) |
| `class_router` | Router classes/signals | Record router output | decision_trace.stage=`class_router` (`truffles-api/app/routers/webhook/_legacy.py:7917`) |
| `intent` | Итоговый intent | Record intent | decision_trace.stage=`intent` (`truffles-api/app/routers/webhook/_legacy.py:7965`) |
| `smalltalk` | Smalltalk decision | Reply greeting/thanks | decision_trace.stage=`smalltalk` (`truffles-api/app/routers/webhook/_legacy.py:8127`) |
| `bot_status` | Bot status запрос | Reply status | decision_trace.stage=`bot_status` (`truffles-api/app/routers/webhook/_legacy.py:8162`) |
| `style_reference` | Style reference без медиа | Prompt media | decision_trace.stage=`style_reference` (`truffles-api/app/routers/webhook/_legacy.py:8179`) |
| `time_only_guard` | Время без услуги | Уточнение услуги | decision_trace.stage=`time_only_guard` (`truffles-api/app/routers/webhook/_legacy.py:8499`) |
| `service_semantic_matcher` | Семантический сервис‑match | Reply/suggestions | decision_trace.stage=`service_semantic_matcher` (`truffles-api/app/routers/webhook/_legacy.py:8608`) |
| `action_gate` | Missing decision_meta.action | Action=error + trace | decision_trace.stage=`action_gate` (`truffles-api/app/routers/webhook/decision.py`) |

#### Critical trace-stages (must-have)
- `preflight`, `outbox_payload_guard`, `skip_persist`, `dedupe`, `outbox`, `branch_selection`, `debounce`, `handover_confirmation` — ранние возвраты (trace при резолве conversation).
- `contract`, `decision_graph` — обязательны для аудита плана и контрактов.
- `session_memory`, `re_entry`, `question_contract` — устойчивость expected_reply и reset.
- `shield`, `policy_gate` — safety-гейты (spam/toxic/Hard‑LAW).
- `routing`, `pending_sla`, `pending_resume` — состояние pending/manager и SLA.
- `class_router`, `intent`, `intent_decomposition` — выбор смысла/класса.
- `booking_gate`, `booking`, `booking_interrupt` — booking-first инварианты.
- `info_class`, `service_matcher`, `truth_gate`, `multi_truth` — truth‑first факты.
- `consult_flow`, `consult`, `clarify_guard`, `consult_return` — consult‑playbooks, follow-up, эскалация.
- `out_of_domain` — строгий OOD guard.
- `llm_guard`, `ai_response`, `budget_gate`, `llm_degradation`, `rewrite` — LLM path + деградации.
- `action_gate` — обязательность `decision_meta.action`.
- `escalation`, `state_transition` — handover + стейт‑машина.

#### Trace coverage exceptions
- Для `preflight`/`skip_persist`/`dedupe` trace пишется только если conversation удаётся резолвить (conversation_id/message_id/remote_jid). Placeholder conversation не создаём, поведение не меняем.
- Требование trace/meta относится к ответам бота; при отсутствии conversation/response trace не обязателен.

### Agentic orchestration = роли пайплайна (без отдельных агентов)
Термин “agentic” — это **логические роли стадий** в одном потоке `_handle_webhook_payload`, а не отдельные рантайм‑агенты.

**Соответствие ролей фактическому порядку:**
- **Router** → вход + outbox + порядок стадий из цепочки выше.
- **Safety Guard** → pending/opt‑out/Hard‑LAW escalation + policy‑gates (скидки/оплата info).
- **OOD Guard** → early OOD (только если нет in‑signals).
- **Booking Guard** → booking guard/flow + expected_reply_type + slot-lock + booking_confirm.
- **Info/RAG Specialist** → tools/packs fact‑resolver → LLM‑формулировка → Response Guard → truth gate fallback.
- **Host Persona** → формулировка ответа (шаблоны/LLM) по `SPECS/CONSULTANT.md`, CTA/quiet hours в response‑слое.
- **Observability** → decision_trace/meta на каждом сообщении.

### LLM‑first Understanding + Deterministic Commit — канон
- Цель: **LLM даёт смысл**, но commit решения проходит через deterministic validators.
- Выход LLM (IntentContract): `intent`, `slots`, `language`, `emotion`, `confidence`, `risk_signals`.
- Booking slot extract: LLM выделяет `service/master/time/name` в JSON; при низкой уверенности → `booking_confirm`.
- `slot_extract` вызывается только при активном booking‑signal (expected_reply_type/current_goal=booking или LLM intent/slots указывают на запись); Hard‑LAW/pending/opt‑out блокируют slot_extract.
- Semantic resolver подтверждает/опровергает; расхождения фиксируются в trace/meta (proposed vs committed).
- Факты извлекаются **только** через tools/packs; LLM не создаёт факты.
- Response Guard обязателен: текст = ack + facts + next_step, иначе fallback.
- Классы (по приоритету): Hard‑LAW → policy → opt‑out → human/frustration → booking → info‑bundle → consult → greeting → OOD.
- Anchors/лексика/эвристики — **fallback/boost**, не основной источник смысла.
- LLM‑контроллер — основной арбитр смысла; словари/якоря не расширяем ради покрытия, только для safety‑gate и минимальных якорей.
- OOD допустим **только** если есть out‑signals и **нет** in‑signals (strict‑in).
- Если confidence ниже порога/LLM недоступен → fallback на semantic resolver/детерминированный router; фиксация в trace.
- Multi‑intent: сильный класс отвечает первым, остальные идут в очередь (intent_queue) с возвратом к цели.
- `info_bundle` — **отдельный класс**, не “схлопывается” в `info`.

### Decision Graph contracts (Pydantic, source of truth)
- ContextContract: `tenant_id`, `branch_id`, `state`, `timezone`, `mode`.
- IntentContract: `intent`, `slots`, `language`, `emotion`, `confidence`, `risk_signals`.
- FactContract: `facts`, `sources`, `policy_flags`.
- ActionContract: `action_type`, `required_next_slots`, `escalation_reason`.
- ResponseContract: `tone`, `must_include`, `must_not_include`, `language`.
- MemoryContract: `mode`, `slots`, `summary`, `last_updated`, `ttl`, `last_updated_at`, `ttl_hours`, `active_goal`, `last_question_type`, `goal_stack`, `pending_slots`, `unanswered_questions`, `slot_lock`, `slot_snapshot`, `slot_confirmation_required`.
- TraceContract: `stage`, `decision`, `reason`, `meta`.

### Slot extraction + confirmation (P0)
- Stages: `slot_extract` (LLM JSON), `slot_validate` (детерминированно), `booking_confirm` (подтверждение слотов).
- Запуск `slot_extract` — только при активном booking‑signal; в остальных случаях слоты не извлекаем.
- Slot-lock: активный `expected_reply_type` сохраняется при перебивках; смена только на заполнение слота/отмену/`pending`.
- decision_trace: `stage=slot_extract|slot_validate|booking_confirm` с `decision` и `slot_summary`.
- decision_meta: `slot_source`, `slot_confidence`, `slot_confirmation_required`, `slot_summary`.

### Tool Fact Contracts (P0)
**Цель:** единственный источник фактов; LLM не создаёт факты.

**Слои:**
1) **Semantic resolver** → выбирает intent/service кандидаты (embeddings + thresholds).
2) **Tool resolver** → собирает факты из packs/инструментов.
3) **Response Guard** → проверяет финальный текст на допустимые секции.

**Tools (deterministic):**
- `fact.info_bundle` → address/hours/parking/guest_policy.
- `fact.pricing` → price_item + price_text.
- `fact.duration` → duration_item + duration_text.
- `fact.service_match` → service_id + service_text (presence/availability).
- `fact.consult_playbook` → playbook_id + lead/questions/options/next_step.
- `fact.policy` → policy_section + rule_text (discounts/payment_info).
- `fact.booking_prompt` → next_slot + prompt_text (expected_reply_type).
- `fact.handoff` → escalation_text (pending/manager_active status).

**Tool output contract (minimum):**
```json
{
  "fact_source": "truth|service_matcher|consult_playbook|policy|booking|handoff",
  "fact_payload": {"info_sections": [], "service_query": "", "price_item": "", "duration_item": ""},
  "fact_text": "string"
}
```

**Trace/meta requirements:**
- decision_trace: `stage=tool_fact_resolver`, `tool_name`, `tool_decision`.
- decision_meta: `fact_source`, `fact_payload` keys, `tool_used`.

### Semantic Resolver (P0)
**Цель:** устойчивость RU/KZ/mixed без раздувания ключевых слов; детерминированный commit.

**Вход:**
- `user_text`, `expected_reply_type`, `client_slug`, `branch_id`
- LLM proposal: `intent/slots/confidence` (если есть)
- Intent/Service cards (packs/Qdrant)

**Cards (rules‑as‑data):**
- `domain_pack.intent_cards`: id, title, description, examples (ru/kk/mixed), risk_flags
- `client_pack.service_cards`: service_id, name, category, description, examples (ru/kk/mixed)
- Индексация: `ops/sync_client.py --sync` → Qdrant, metadata `{client_slug, branch_id, card_type, id}`

**Scoring (deterministic):**
- Embeddings (BGE‑M3), top‑k=5.
- Пороги: `intent_threshold`, `service_threshold` (глобальные + per‑card override).

**Commit rules:**
- Если `semantic_score >= threshold` → commit semantic result (может override LLM).
- Если `semantic_score < threshold` и LLM `confidence` высокий → commit LLM result, но метка `semantic_low_confidence`.
- Иначе → clarify или handoff (по правилам).

**Output (meta):**
- `semantic_used`, `semantic_intent`, `semantic_service_id`
- `semantic_score`, `semantic_threshold`, `semantic_candidates` (top‑3)
- `semantic_version` (для воспроизводимости)

**Trace:**
- `decision_trace.stage=semantic_resolver` с кандидатом, score, threshold, decision.
- `decision_meta` включает все output‑поля.

**Fallback:**
- При недоступных embeddings/ошибках → deterministic anchors (record `semantic_fallback_reason`).

### Response Guard (P0)
**Цель:** ноль галлюцинаций и строгое соответствие фактам.

**Правила:**
- Финальный текст может содержать только `ack` + `fact_text` + `next_step`.
- Если `fact_payload` пустой → clarify или handoff (по правилам).
- Запрещены новые факты/советы/обещания вне `fact_payload`.
- Для booking: разрешён только slot‑echo из валидированных слотов.
- Для handoff: только эскалационные шаблоны.

**Fallback:**
- Нарушение → deterministic шаблон или clarify/escalate, записать guard‑решение.

**Trace/meta:**
- decision_trace: `stage=response_guard`, `decision=pass|fallback`, `reason`.
- decision_meta: `response_guard`, `guard_reason`, `guard_fallback`.

**Живой хост — канон (in-domain):**
- **3 исхода:** факт‑ответ (info/consult), booking intake, эскалация.
- **Fact‑answer (info/consult):** только факты из `client_pack`/`consult_playbooks`; LLM может **только перефразировать** эти факты, новые факты/советы запрещены.
- **Booking intake:** сбор слотов записи (`expected_reply_type`); при перебивке — факт‑ответ и возврат к последнему booking‑вопросу.
- **Hard‑LAW:** оплата (подтверждение/проверка/возвраты), медицинка, жалобы, переносы → только эскалация.
- **Policy‑gates:** скидки и способы оплаты разрешены **только** по явным правилам в `client_pack`; иначе эскалация.
- **Clarify limit:** максимум 2 уточнения (`clarify_limit=2`), далее эскалация.

### Action Layer (PLAN)
- Поток: Sense → Decide → Act → Speak.
- Действия (пример): `leadcard_update`, `handoff_create`, `status_update`, `clarify_request`, `booking_step`.
- Риск‑типы: low/medium/high; high‑risk действия → только handoff.
- LLM может предложить `tool_call`, но исполняет только deterministic executor по policy.
- Allowed‑facts validator: проверяет, что ответ использует только разрешённые факты; при нарушении → clarify/handoff.
- ActionContract: `action_type`, `required_next_slots`, `escalation_reason` (остальное — meta).
- Trace meta: `action_id`, `tool_used`, `policy_override`.

### Answer‑Interpreter (expected_reply_type) — канон
- Включается **только** если ожидается ответ на вопрос (`expected_reply_type` активен).
- Делает **семантический** разбор ответа (slot/value/confidence), а не классификацию запроса.
- Низкая уверенность/ошибка → fallback на детерминированный парсер + короткий уточняющий вопрос.
- Не может менять класс ответа и не влияет на Hard‑LAW/policy‑gates.

### Consult clarify (pack-only, no LLM advice)
- Consult canon: info-first only from pack playbooks; no LLM advice/facts. If explicit info/booking request (pricing/duration/location/hours/booking) and service recognized → short-circuit to normal info/booking; advice-style consult stays in consult even if service recognized. If playbook missing and no service → max 2 clarifications (`clarify_limit=2`), then escalate `consult_no_service`.
- Consult‑интенты → пытаемся матчить `client_pack.consult_playbooks`. Если playbook найден → info-first ответ только из pack (`lead`, `questions`, `options`, `next_step`).
- Если consult‑интент содержит распознанную услугу/категорию → short‑circuit в обычный info/booking (без уточнения).
- Если playbook не найден и услуги нет → максимум 2 уточнения (`clarify_limit=2`); после лимита без услуги → эскалация с reason `consult_no_service`.
- Hard‑LAW/Policy/opt‑out/human гейты срабатывают раньше consult.
- Trace: `stage=consult_flow` с `decision=consult_clarify|consult_escalate|short_circuit`, `consult_playbook_id`, `consult_variant_id`, `tips_used`, `source=pack`.

### Datetime Resolver (offline) — контракт
- Вход: raw user text + `domain_pack.datetime_lexicon` (days/dayparts RU/KZ) + `expected_reply_type=time`.
- Выход: `slot=datetime` → `{value, confidence, evidence}`.
  - `value`: нормализованный RU‑слот или исходный текст (если содержит время/числа).
  - `confidence`: 0.0–1.0.
  - `evidence`: `{normalized_text, lexicon_matches, parser}`.
- Использование: booking expected‑reply и booking‑signal; без LLM.
- Ограничение: лексика только из data‑pack; в коде не добавляем regex/словари.

### Info‑bundle (композиция фактов)
- Любые сочетания “где/когда/парковка/гости/ранний приход/сегодня” → единый факт‑ответ: адрес + часы + нужные секции.
- Если запрошена цена без услуги → уточнение услуги (без цен), но адрес+часы остаются.
- Источник: только client_pack (truth‑first), без фантазий.
- Follow‑up “по времени/по часам”: если carryover содержит `hours` и нет явной услуги — **не** используем service‑matcher/carryover, ответ остаётся в `hours`.

### Pack Compiler и онбординг (offline‑pipeline)
- Источники: CRM/Calendar/Excel/Sheets/сайт → единый формат.
- Нормализация: услуги/категории/правила → client_pack факты.
- Taxonomy → Alias Expansion: ServiceSample расширяет алиасы **только** для услуг клиента (распознавание ≠ правда).
- Branch overrides: адрес/часы/канал/политики на уровне филиала.
- Валидация: обязательные поля (адрес/часы/услуги/правила); если нет — GAP‑лист.
- Версионирование: `client_pack.version`, `domain_pack.version`, `compiled_at`, `hash`.
- Output: compiled client_pack → Qdrant sync + Base‑80 EVAL генерация.

**Runtime использует только compiled client_pack**; domain taxonomy не даёт право на ответ, если факта нет.

### Context carryover (класс‑уровень)
- После info‑bundle хранить класс и ключевые факты в контексте, чтобы перестановка вопросов не сбрасывала ветку.
- Carryover не подменяет Hard‑LAW/policy‑gates и не меняет факты.
- Храним `class=info_bundle` + `info_sections`; service‑carryover не может переопределить hours‑follow‑up.
- Goal‑keeper: `current_goal` сохраняется при перебивках; ответ на перебивку возвращает к цели.

### Session Memory v1.1 (conversation.context.session_memory)
**Назначение:** удерживать краткую память о вопросах/целях без точных цитат.

**Структура:**
- `mode` — режим памяти (session/compact).
- `slots` — подтверждённые/активные слоты (branch/service/datetime).
- `summary` — краткая сводка без новых фактов/советов.
- `last_updated` / `last_updated_at` — отметки обновления.
- `ttl` / `ttl_hours` — срок жизни памяти (по умолчанию 24h).
- `last_question_type` — последний тип вопроса (hours/pricing/duration/booking/consult/info_bundle/other).
- `pending_slots` — какие слоты ещё нужны (service/datetime/branch/etc).
- `active_goal` — текущая цель (info_bundle/consult/booking/other).
- `goal_stack` — стек целей (до 3), чтобы возвращать цель после перебивок.
- `unanswered_questions` — список вопросов, на которые ещё не ответили.

**Точки обновления:**
- после `question_contract` → фиксируем `last_question_type`, пополняем `pending_slots`, обновляем `unanswered_questions`.
- после `intent_router` → обновляем `active_goal` и `slots`.
- после `info/consult/booking` → чистим закрытые `pending_slots`, обновляем `active_goal`, синхронизируем `slots`.

**Reset rules:**
- gap > 24h между сообщениями → полный reset памяти.
- явный текст пользователя “новый запрос” → reset.
- pending/manager_active → сохранить `pending_resume` (snapshot контекста) и восстановить на `pending_ack`.

### Pending Resume (context snapshot)
- При уходе в `pending` сохраняем snapshot (`expected_reply_type`, `intent_queue`, `booking`, `session_memory`).
- На `pending_ack` восстанавливаем snapshot и продолжаем с `pre_pending_goal`.
- На `pending_close`/auto‑close — snapshot удаляется.

### Base‑80 батарея (acceptance)
- 80% входящих классов (по объёму) покрыты перефраз‑battery и 5–6‑ходовыми комбинациями.
- 10–20 перефраз на класс, проверка только инвариантов (facts/must_not), без точных строк.
- Статус “устойчивый хост” невозможен без 100% pass Base‑80.

### Контрактные сценарии (block‑gate)
- **Basic‑20**: базовые вопросы и короткие ответы (включая “да/ок/в субботу”) → блокирующий gate CI.
- **ASR‑battery**: шум/склейка/опечатки → блокирующий gate CI.
- **Long‑chaos (12–15 ходов)**: перебивки, возвраты, pending‑resume → блокирующий gate CI.
- Инварианты проверяются по trace/meta (`class_router`, `expected_reply_type`, `current_goal`, `pending_resume`).

### Policy‑gates (конфиг per client)
- Hard‑LAW всегда эскалирует (оплата: подтверждение/проверка/возвраты, медицинка, жалобы, переносы).
- Policy‑gates (скидки/оплата info) исполняются детерминированно по `client_pack.policy.discounts` и `client_pack.policy.payment_info`.
- Если правило отсутствует/не совпало — эскалация (без попытки торга).

### Booking mode (с/без CRM)
- `booking_mode`: `collect_preferences` (без провайдера) или `confirm_slots` (live‑провайдер).
- `availability_provider`: `none` | `google_calendar` | `bitrix` | `amocrm` | `manual`.
- Если провайдер не задан/недоступен — только сбор предпочтений, **без обещаний слотов**.

### Scheduling core (appointments SoT)
- Источник истины по записям — Postgres (`appointments`); внешние календари = проекции + источник занятости.
- Bot/Console/Telegram используют **один** scheduling service; канал не влияет на бизнес‑логику.
- Команды на запись (create/confirm/cancel/reschedule/check‑in) идут с `expected_version` + idempotency; lost‑update запрещён.
- Синхронизация с провайдерами — **только через outbox**, без прямых вызовов в request‑path.
- Branch‑scope: календарь, токены, настройки и права строго по `branch_id`, с `timezone` на филиале.
- При деградации провайдера — fail‑closed на `collect_preferences` + эскалация, без обещаний слотов.
- Данные бизнеса (мастера, часы, услуги/длительности/буферы) — только из БД/онбординга, без хардкода.

### Behavioral Shield (реализовано)
- Цель: отсечь спам/машинную скорость и токсичные сообщения до LLM.
- Каналы: для WhatsApp нет IP, поэтому ключ — `remote_jid`.
- Реализация: burst/drop (повторы/короткие bursts) + too‑long → silent drop; toxic/nonsense → эскалация.

### Pricing media (P1, план)
- `client_pack.pricing_media.mode`: `text_only` | `image_only` | `text_plus_image`.
- Если задан `image_url` и mode позволяет — бот отправляет прайс‑картинку через ChatFlow media API.
- Фолбэк: при ошибке медиа → текстовый прайс.

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

### Pending‑SLA (ожидание менеджера)
- Через 15 минут в `pending` без ответа менеджера → SLA‑ping клиенту (подтверждение актуальности).
- Ответ клиента:
  - `pending_ack` → handover → resolved, `state=bot_active`.
  - `pending_close` → handover → resolved, `state=bot_active`, бот замьючен.
- Классификация `pending_ack/pending_close`: LLM‑router first, при ошибке/низкой уверенности — детерминированный fallback.
- Auto‑close: 4 часа ожидания без подтверждения → системное закрытие.

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

**InstanceId (канон):**
- `instanceId` во входящем webhook — routing‑token, который мы задаём и используем для `branches.instance_id`.
- Отдельный provider‑ID ChatFlow не храним и не используем; в системе должен быть один canonical instanceId на филиал.

**Хранение:**
- `conversation.branch_id`
- `conversation.context.branch_id` (быстрый доступ)
- `user.metadata.branch_id` (если включено `remember_branch_preference`)

**Trace/meta:**
- `decision_trace` stage `branch_routing` (branch_id, knowledge_tag, routing_source)
- `messages.metadata.decision_meta`: branch_id, knowledge_tag, branch_routing_source

**Гейт:** если `require_branch_for_pricing=true`, без `branch_id` бот не озвучивает цены/скидки/расписание.

---

## 6. База данных — ключевые таблицы

### conversations
```sql
id                  UUID PRIMARY KEY
client_id           UUID
branch_id           UUID  -- ветка/филиал для маршрутизации
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
instance_id         TEXT  -- routing token (ChatFlow)
telegram_chat_id    TEXT  -- Telegram-группа филиала
knowledge_tag       TEXT  -- фильтр для RAG
```

### client_settings (legacy)
```sql
client_id           UUID PRIMARY KEY
telegram_bot_token  TEXT
telegram_chat_id    TEXT  -- fallback (клиентский чат)
manager_scope       TEXT  -- branch/global
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
| Correlation ID | `conversation_id` + `message_id` в decision_meta/trace |

## 12.1 Router SLA + Debug Visibility (P0)
- В decision_trace/meta всегда пишем: `router_llm_ms`, `router_error`, `router_retry`, `router_fallback_reason`.
- В decision_trace/meta всегда пишем: `budget_gate` и `llm_degradation_reason` (budget_exceeded/llm_timeout/llm_skip) при деградации LLM.
- SLO: `router_fallback_rate < 10%`, `timeout_rate < 2%`.
- Нужен минимальный trace‑viewer: фильтры по router_error/fallback/LAW/clarify, топ‑кейсы из knowledge_backlog.

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
| Long-form EVAL | 10-15 сообщений в одном диалоге, проверка `current_goal`/`expected_reply_type`/trace; обязателен перед релизом |

### 13.1 Trace-first CI gate (канон)
- CI проверяет **trace/meta**, а не точные слова ответа.
- Гейт‑поля: `class_router`, `info_sections`, `policy_gate`, `expected_reply_type`.
- Любое отсутствие/несовпадение меты = FAIL.

### 13.2 ASR-noise eval battery
- Набор: транскрипты с опечатками, шумом, склейкой фраз (ASR-noise).
- CI gate: отдельный tier `EVAL_TIER=asr`.
- Уровни шума:
  - **L1 (легкий):** опечатки/омофоны/пунктуация, смысл читается.
  - **L2 (средний):** пропуски служебных слов, перестановки, смешение intents.
  - **L3 (тяжелый):** сильный шум, обрывы фраз, code-switch, неполные услуги.
- Pass-критерии:
  - **L1:** тот же класс и корректные факты; без эскалации по ошибке.
  - **L2:** класс сохраняется **или** корректное уточнение; policy-gates соблюдены.
  - **L3:** безопасный ответ (уточнение/эскалация по правилам), без выдумок.
- Правила интерпретации:
  - сравниваем только trace/meta (не текст).
  - допускаются перефразы и разные формулировки CTA.
  - провал = неверный класс, пропуск policy-gate, пустые/отсутствующие ключи.

### 13.3 Nightly/manual — human-quality
- Ночной/ручной прогон: эмпатия, тон, продажа (human-quality).
- Это **не** CI-гейт; проверка по диалогам/транскриптам.

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
2. POST /webhook/{client_slug} с тестовым payload → не 500
3. Telegram webhook доступен
```

### Staging
Нужен тестовый клиент или второй контейнер на порту 8001.

### Разрешения агентов
**Без апрува:** чтение, тесты, PR
**С апрувом:** мерж, деплой, миграции
**Запрещено:** DROP, force push, temporary hacks

---

## 19. Refactor Plan — webhook pipeline (P1)

### 19.1 Refactor Protocol — legacy de‑godification (P0)

**Goal:** превратить `_legacy.py` в тонкий адаптер и вынести логику по стадиям без изменения поведения.

**Non‑negotiables:**
- Поведение не меняем. Только перенос/упорядочивание кода.
- Порядок стадий фиксирован в разделе “Decision Graph (legacy map)”.
- Любой early return пишет `decision_trace.stage`, если conversation резолвится; placeholder conversation не создаём.
- Один PR = одна группа стадий. Нельзя смешивать разные классы логики.
- CI core/long + live‑check с trace/meta обязательны перед merge.
- Новые файлы не создаём; используем существующие модули `app/routers/webhook/*`.

**Stage contract (минимум):**
- Stage принимает единый `RequestContext`.
- Возвращает `StageResult` с одним из исходов: `continue` / `handled` / `escalated`.
- Побочные эффекты (DB/state/notifications) происходят внутри stage‑модуля, а не в оркестраторе.

**Target end‑state:**
- `_legacy.py` содержит только HTTP‑адаптер + вызов оркестратора (≈100–200 строк).
- Оркестратор — `app/routers/webhook/decision.py`, порядок стадий = канон.
- Все ранние returns покрыты trace‑стадиями при резолве conversation.

### 19.2 Staged Plan — refactor slices (P0)

**Order (не менять; статус фиксируется в `STATE.md`):**
1) **S0 — Trace gaps**: early-return trace coverage (preflight/skip_persist/dedupe/outbox/branch_selection/debounce/handover_confirmation).
2) **S1 — Early gates → modules**: preflight/outbox/dedup/branch_selection/pending из `_legacy.py` в `http.py`, `outbox.py`, `dedup.py`, `branch_selection.py`, `pending.py`.
3) **S2 — Safety gates**: shield/policy/pending/mute в `shield.py`, `policy.py`, `pending.py`, `guards.py`.
4) **S3 — Router/intent/expected_reply**: оркестрация в `decision.py`, `router_sla.py`, `parsing.py`.
5) **S4 — Domain flows**: booking/info/consult в `booking.py`, `info.py`, `response.py`.
6) **S5 — LLM/response + post-hooks**: `response.py` + `context_manager.py`, cleanup side-effects.
7) **S6 — Adapter-only**: `_legacy.py` остаётся только HTTP‑адаптером; `/webhook` и `/message` ведут в общий оркестратор.

**DoD per slice:** CI core/long зелёные + live‑check + trace/meta parity (поведение не меняется).

### 19.3 Pipeline decomposition (P1)

- Цель: уменьшить регрессы и стоимость изменений без смены поведения.
- Границы: HTTP‑слой остаётся в `app/routers/webhook/_legacy.py`, логика переносится по стадиям.
- Декомпозиция:
  - `app/routers/webhook/guards.py` — opt‑out/mute/re‑engage + routing gates.
  - `app/routers/webhook/shield.py` — spam/toxic/too_long.
  - `app/routers/webhook/router_sla.py` + `parsing.py` — LLM router + expected_reply orchestration.
  - `app/routers/webhook/policy.py` — policy‑gates (discount/payment).
  - `app/routers/webhook/info.py` — info‑bundle + truth/multi‑truth.
  - `app/routers/webhook/booking.py` — booking flow + expected_reply.
  - `app/routers/webhook/response.py` — response post‑processing (CTA/quiet hours).
  - `app/routers/webhook/context_manager.py` — summary/consult return.
  - `app/routers/webhook/decision.py` — оркестратор стадий.
- Контекст: единый `RequestContext` (dataclass) вместо разрозненных dict‑ов.
- Инварианты: поведение не меняем; CI core/long зелёные; trace/meta сохраняются.

---

*Последнее обновление: 2026-01-07*
