# IMPERIUM_BLUEPRINT_v1
**Date:** 2025-12-21  
**Owner:** Жанбол (CEO)  
**Scope:** “Империя” как **Company OS** для Truffles, с первым вертикалом = **multi-tenant WhatsApp auto-responder**.

---

## 0) TL;DR — что строим
Мы строим **не “ещё один чат-бот”**, а **самозамкнутый операционный контур**, в котором система сама:
1) подключает нового заказчика (tenant),
2) собирает/версионирует знания (KB),
3) обслуживает диалоги и эскалирует,
4) мониторит качество/доступность,
5) превращает сбои в инциденты,
6) выпускает безопасные фиксы через PR→CI→canary→rollout/rollback,
7) отчитывается CEO в Telegram.

Пока “Империя MVP” = **операционная автономность** вокруг существующего прод-стека.

---

## 1) Границы и принципы

### 1.1 Принципы
- **No Crutches:** любые правки/фиксы идут через артефакты, миграции, CI и аудит.  
- **Stateful truth:** истина в Postgres (tenant config, KB versions, incidents, audit).  
- **Observability-first:** если что-то ломается — об этом узнают в Telegram, и есть трасса в БД.  
- **Quality>Speed:** лучше “эскалация”, чем “позор”.

### 1.2 Не-цели (v1)
- Полная автономная финмодель/бухгалтерия/HR.
- Автономные “платные действия” (billing/платежи) без verify.
- Мультиканал (Instagram Direct) — только подготовка интерфейса, не прод.

---

## 2) Фактическая база (текущее состояние)
### 2.1 Прод рантайм (Docker)
- Server: `5.188.241.234`, ssh `-p 222` user `zhan`
- Core services: `truffles-api` (FastAPI), `n8n`, `n8n-worker`, `postgres:15`, `qdrant`, `redis`, `pgadmin`, `bge-m3`
- Networks: `proxy-net` (public routing), `internal-net` (internal services)

### 2.2 Основные эндпоинты API
- `POST /webhook` — WhatsApp inbound (ChatFlow/n8n)
- `POST /telegram-webhook` — вход для менеджерских ответов/кнопок
- `GET /health`, `GET /admin/health`, `GET /db-check`, `POST /admin/outbox/process`, `POST /reminders/process`

### 2.3 Tenancy (DEC-001)
- Shared multi-tenant (tenant resolved by `client_slug`, stored by `client_id`)

### 2.4 WhatsApp / ChatFlow
- Inbound: `/webhook` с webhook secret, ACK-first (enqueue outbox), inbound dedup = redis + `message_dedup`
- Outbound: `send-text` endpoint, timeout 30s, retries/backoff + msg_id idempotency (в webhook/outbox)

### 2.5 KB и RAG (DEC-005)
- Embeddings: `BAAI/bge-m3` dim=1024 (bge-m3 container)
- Qdrant: collection `truffles_knowledge`
- Postgres уже содержит `knowledge_versions` и `knowledge_sync_logs` (хорошая база для версионирования)

---

## 3) CEO Decisions (зафиксировано)
- **DEC-001 Tenancy:** Shared multi-tenant; tenant_id everywhere  
- **DEC-002 Webhook security:** webhook secret обязателен  
- **DEC-003 Autonomy:** low-risk write auto; high-risk requires verify  
- **DEC-004 Release:** canary by tenant  
- **DEC-005 KB storage:** Postgres stores KB versions/sources; Qdrant is index-only  
- **DEC-006 GCP:** freeze; focus on prod Docker  
- **DEC-007 Phase 0 Release:** LAW gate + truth-first + ACK-first/outbox + coalescing + EVAL green + prod smoke-check  

### 3.1 Добавить новое решение (предлагаю): DEC-007 “Write-Risk Policy”
Чтобы DEC-003 был исполнимым, нужна политика риска действий:

**Low-risk (AUTO):**
- писать внутренние записи: lead notes, теги, incident, audit_log
- отправлять алерт оператору/CEO в Telegram
- создавать/обновлять KB *черновик* (draft) без выката в stable
- переключать tenant в canary *только по команде CEO* (это уже verify)

**High-risk (VERIFY):**
- изменения прод-поведения для stable-tenants
- изменение промптов/KB в stable channel
- любые массовые рассылки/важные сообщения клиентам заказчика
- любые действия, влияющие на деньги/подписки/условия

---

## 4) Архитектура “Company OS” (минимальная)
### 4.1 Компоненты-агенты (логические роли)
1) **Onboarder** — подключение tenant (ChatFlow tokens, settings, initial KB sync)
2) **KB Builder** — структурирование ответов/доков в версии KB (draft→stable)
3) **Sentinel** — мониторинг доступности и качества (health + “silent failures”)
4) **QA/QC Gate** — анти-позорный шлюз (блок/эскалируй)
5) **Fixer** — PR→CI→Deploy→Verify, rollback, отчёт
6) **Operator/CS** (люди/CEO) — verify high-risk и разбор сложных кейсов

### 4.2 Control Plane (Telegram)
Telegram = “панель CEO”.
MVP команды (минимум):
- `/status <tenant>` — health + last errors + send success rate
- `/incident <id>` — показать RCA bundle (trace/log/context)
- `/deploy canary <tenant>` — включить canary-channel
- `/deploy stable <tenant>` — выкатить stable (после verify)
- `/rollback <tenant>` — откатить на stable
- `/kb promote <tenant> <kb_version>` — promote draft→stable (verify)

---

## 5) “Империя MVP” = закрыть P0 GAPS
Ниже — порядок работ. Он важен: некоторые вещи делают Fixer возможным.

### Milestone M0: “Не стыдно в проде” (1–3 дня)
**Goal:** убрать “слепоту” и “открытые двери”.

1) **GAP-001 Webhook auth** (DONE)
- MVP: HMAC signature + timestamp header per tenant secret (client_settings)
- DoD: 401 on missing/invalid, 200 on valid; тесты на подпись.

2) **GAP-007 Alerting configured** (DONE)
- выставить `ALERT_BOT_TOKEN/ALERT_CHAT_ID`
- добавить `/alerts/test` или startup warning (если нет env)
- DoD: тестовый алерт приходит в Telegram.

3) **GAP-004 Qdrant API key mismatch** (DONE)
- выровнять переменные окружения (`QDRANT_API_KEY` vs `QDRANT__SERVICE__API_KEY`)
- DoD: RAG стабильно возвращает results; при отсутствии ключа — loud error.

### Milestone M1: “Никогда не молчим” (2–5 дней)
**Goal:** исключить “бот не ответил” из-за таймаутов/дублей/сбоев.

4) **GAP-010 Ack-first outbox** (DONE)
- webhook пишет inbound в outbox/status и отвечает <200ms
- worker доставляет ответ и помечает статус
- DoD: latency webhook <200ms; outbox delivery; trace entry.

5) **GAP-011 Outbound idempotency** (PARTIAL: only webhook/outbox)
- idempotency key = message_id (или composite tenant+message_id)
- DoD: повторная доставка не приводит к двойному send.

6) **GAP-005 Retries/backoff на ChatFlow outbound** (DONE)
- 3 попытки экспоненциально, лог final failure
- DoD: тесты/симуляция 500 → retry → success.

### Milestone M2: “Fixer loop” (2–4 дня)
**Goal:** агенты могут безопасно чинить через PR.

7) **GAP-003 CI workflows**
- `.github/workflows/ci.yml`: ruff + pytest
- DoD: PR запускает CI, падает на ошибках.

8) **GAP-002 Canary by tenant**
- `release_channel` в `client_settings` (`stable|canary`)
- gate behaviors/prompts/KB by channel
- DoD: canary tenant видит новое, stable — нет; можно вернуть обратно.

9) **GAP-012 Rollback strategy doc**
- `docs/ROLLBACK.md` + команды
- DoD: описан откат image + flip channel.

### Milestone M3: “Анти-позорный QC” (после M0–M2)
**Goal:** закрыть главный страх — галлюцинации/оффтоп/тролли.

10) **GAP-006 QC stage**
MVP подход (без overengineering):
- QC rules first: запрещённые темы, “не по салону”, токсичность, уверенность ниже порога
- если QC fail → короткий ответ + эскалация в Telegram topic
- позже: QC LLM (вторая модель) как усиление
- DoD: unsafe/offtopic блокируется; safe проходит; есть unit tests на кейсы.

---

## 6) “Sentinel” (непрерывный мониторинг)
**GAP-013 Sentinel not implemented**

MVP Sentinel (как отдельный контейнер или n8n cron):
- ping `/health`
- ping `/db-check`
- check Qdrant collection + points_count
- check “inbound received but no outbound” по outbox/status
- если fail → alert_service → Telegram

DoD:
- Sentinel детектит падение Qdrant/DB/ChatFlow и шлёт алерт
- Pass path не шумит.

---

## 7) Данные и аудит: как сделать систему “доказуемой”
Сейчас в БД уже есть таблицы `audit_log`, `error_logs`, `message_traces`, `knowledge_versions`, `knowledge_sync_logs`.
Но они не wired → нужно “проводку”.

### 7.1 Wiring (GAP-008/009)
- На каждый message-turn писать `message_traces`:
  - tenant_id, conversation_id, message_id
  - timings: rag_ms, llm_ms, send_ms
  - scores: rag_confidence, intent_confidence
  - decisions: escalated?, qc_pass?
- На каждый exception писать `error_logs` с correlation_id
- На manager actions/handovers писать `audit_log` (actor, tenant_id, action, payload)

DoD: можно собрать RCA любого инцидента из БД без “угадываний”.

---

## 8) Онбординг клиента (Unit of Value #1)
Цель: “скинул token → всё само”.

### 8.1 MVP онбординга (semi-auto)
Шаги:
1) CEO даёт `client_slug`, ChatFlow token/instance_id, Telegram topic/chat_id
2) система создаёт/обновляет `clients` + `client_settings`
3) запускает initial KB sync → создаёт `knowledge_versions` (draft)
4) переключает tenant в stable, включает monitoring

DoD:
- новый tenant отвечает на “простые вопросы” из KB
- есть трасса и алерты
- можно быстро выключить/rollback.

---

## 9) План работ в формате PR-ов (как “Империя” будет работать)
Рекомендуемый порядок PR:
1) PR-001: Webhook Auth (GAP-001) — DONE
2) PR-002: Alerting Env + /alerts/test (GAP-007) — DONE
3) PR-003: Qdrant key fix (GAP-004) — DONE
4) PR-004: Outbox + Ack-first (GAP-010) — DONE
5) PR-005: Outbound idempotency (GAP-011) — PARTIAL
6) PR-006: Outbound retries/backoff (GAP-005) — DONE
7) PR-007: CI workflows (GAP-003)
8) PR-008: Tenant canary channel (GAP-002) + docs/ROLLBACK.md (GAP-012)
9) PR-009: QC stage MVP (GAP-006)
10) PR-010: Sentinel MVP (GAP-013)
11) PR-011: Audit/trace wiring (GAP-008/009)

---

## 10) Definition of Done (DoD) для “Империи MVP”
Империя MVP считается достигнутой, когда:
- (Security) `/webhook` защищён и тестируется
- (Reliability) webhook ack <200ms; доставка через outbox; no silent drops
- (Observability) алерты доходят в Telegram; есть трасса в БД
- (Release) есть CI; есть canary per tenant; есть rollback doc
- (Quality) есть QC gate, который предотвращает “позор” и эскалирует
- (Ops) Sentinel мониторит и поднимает инциденты автоматически
- (CEO UX) ты можешь управлять tenant release channel и получать статусы в Telegram

---

## 11) Следующий шаг (что сделать прямо сейчас)
1) Добавь DEC-007 (Write-Risk Policy) в `docs/IMPERIUM_DECISIONS.yaml`
2) Запусти работу по PR-001…PR-003 (это минимальная “обвязка”, без которой всё остальное опасно)

---
