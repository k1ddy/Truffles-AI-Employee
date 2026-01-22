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
5) Если `STATE.md` NOW не помещается в 1 экран или нет следующих шагов — STOP и запросить Brain или Top Architect обновление брифа.

**Правила evidence:**
- Единственный источник фактов — `STATE.md` (PASS/FAIL с conv_id/trace/SQL/CI).
- Статусы в CA‑plan — только статусы аудита; `verified/gap` всегда с ссылкой на `STATE.md`.
- Если live‑check невозможен → статус **BLOCKED**, без подмены. **Исключение CA‑13:** допускается simulated inbound (`/webhook` или instance→instance) при наличии inbound row в БД + `decision_meta/trace`; в `STATE.md` пометка `simulated`.

**Карта инструментов (что запускать):**
- `ops/diagnose.py livecheck` — реальный inbound через ChatFlow, маркеры для SQL evidence.
- `ops/diagnose.py` — health/metrics/outbox snapshot.
- `ops/diagnose.py send-text` — одноразовая отправка через ChatFlow send‑text.
- `ops/diagnose.py send-and-explain` — отправка + быстрый `explain`.
- `ops/chatflow_send.py` — минимальный sender‑скрипт (без diagnose).
- `ops/diagnose.py explain` — быстрый разбор конкретного сообщения (decision_meta/trace + outbox).
- `ops/diagnose.py trace-bundle` — полный пакет (decision_meta/trace + outbox rows + latency).
- `ops/diagnose.py deploy-verify` — проверка версии деплоя (`/admin/version`) и совпадения commit.
- `ops/sync_client.py` — validate/sync client packs (truth → Qdrant).
- `/home/zhan/restart_api.sh` — restart API контейнера.
- SQL evidence: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "<SQL>"`.

## 0.2 Fast Debug SOP (5 минут)

**Цель:** быстро понять, где “молчит” бот и почему.

1) **Проверить вход** (1 команда):
   ```bash
   python3 ops/diagnose.py explain --client-slug demo_salon --text "LC-MARKER" --minutes 120
   ```
   - Если `no inbound messages found` → webhook не дошёл.  
   - If you do not know `client_slug`, use `--receiver-phone` to auto-resolve it from `branches.phone`.
2) **Проверить outbox** (в выводе explain):
   - `outbox_summary.status` = `SENT` → ответ ушёл.
   - `outbox_summary.count = 0` → ответа не создавали (gate/skip/мьют).
3) **Проверить трассу** (в выводе explain):
   - `decision_meta.action/source` + `decision_trace` дают полный ход решения.

**Если inbound не найден:**
```bash
python3 ops/diagnose.py explain --client-slug demo_salon --text "LC-MARKER" --traefik
```

**TL;DR**
- Нет inbound → проблема между ChatFlow и API.  
- Есть inbound, нет outbox → gate/мьют/эскалация.  
- Outbox SENT, но ответа нет → проблема провайдера (ChatFlow/WA).

**Где фиксировать изменения:**
- Статус/evidence → `STATE.md` (Brain или Top Architect; для core/поведенческих изменений — до merge в рамках PR, плюс финальная запись в конце сессии).
- Статус аудита → `STRATEGY/TECH_ROADMAP.md` (Top Architect, со ссылкой на `STATE.md`).
- Процессы/инварианты → `SPECS/*` или `STRATEGY/*` (owner‑docs).

## 0.1 Термины и сущности (единый словарь)

- **Заказчик:** бизнес‑владелец (компания), платит за сервис.
- **Клиент / tenant:** запись в `clients` (логическая единица в системе).
- **Филиал / branch:** запись в `branches` (подразделение клиента).
- **client_slug:** идентификатор в URL `/webhook/{client_slug}` (должен соответствовать клиенту в БД).
- **Receiver‑номер:** входящий номер салона (ChatFlow instance).
- **Sender‑JID:** тестовый номер, который пишет на receiver (используется в live‑checks).
- **instanceId:** ChatFlow instance ID receiver‑номера; используется для routing и хранится в `branches.instance_id`.
- **remote_jid:** JID отправителя (sender), на него уходит ответ.
- **allowlist:** список sender‑JID, на которые разрешён outbox в `TEST_MODE`.

**Правило:** instanceId хранится **в БД**, не в git; sender‑JID пул фиксируется в SOP и env allowlist.
**Важно:** query‑param `instanceId` **переопределяет** `metadata.instanceId` при входе.

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

## 2.1 Внешние системы и быстрые проверки

**Цель:** не “верить на слово”, а уметь быстро доказать состояние ключевых интеграций.

- **GitHub Actions + GHCR:** CI run → образ в GHCR → `/admin/version` совпадает с SHA деплоя.
- **ChatFlow (WhatsApp):** outbound = `send-text`; inbound валиден только через реальный WA → `/webhook/{client_slug}`.
- **Telegram:** алерты через `/alerts/test`, менеджерские ответы через `/telegram-webhook`.
- **Qdrant:** `ops/sync_client.py --validate/--sync`, проверка коллекций.
- **Redis:** outbox/debounce; контроль через `/admin/metrics` (latency, retries).
- **Postgres:** факты/evidence только через SQL (messages, conversations, outbox, handovers).

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
6) **STATE.md** обновляет Brain или Top Architect с evidence **до merge** для core/поведенческих изменений; финальная запись — в конце сессии.

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
- **Brain или Top Architect:** снимает evidence из БД и фиксирует в `STATE.md` (для core/поведенческих изменений — до merge).
- **Top Architect:** обновляет статус аудита в `STRATEGY/TECH_ROADMAP.md` (CA‑plan) только со ссылкой на `STATE.md`.

**Перед запуском (обязательно):**
- **Определения (фиксируем):**
  - **JID allowlist** = список тестовых WA‑номеров (JID), на которые **разрешено** слать сообщения для проверок.
  - **instance_id** = ChatFlow instance, привязанный к конкретному тестовому номеру; нужен **только** для
    ChatFlow send‑text (instance→instance).
  - **instance→instance** = отправка через ChatFlow send‑text с instance A на JID instance B; live‑check валиден,
    **если есть inbound row в БД** + `decision_meta/trace`.
- **CI livecheck** = прямой `/webhook` + allowlist + `TEST_MODE=1` (instance_id опционален).
- **CA‑13 исключение:** допускается simulated inbound (`/webhook` или instance→instance) **без allowlist**, если inbound записан в БД и outbound заблокирован; в `STATE.md` пометка `simulated`.
- **Receiver (inbound номер салона):**
  - `demo_salon` → `77055740455@s.whatsapp.net` (instanceId берём из ChatFlow, может меняться).
- **Sender JID‑пул (тестовые отправители; sender‑only, не в `branches.phone`):**
  - `clean_auto` → `77785890765@s.whatsapp.net` (instanceId: `eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6IkNsZWFuIn0=`, ChatFlow send‑text).
  - `clean_manual` → `77015705555@s.whatsapp.net` (ручной отправитель).
  - Добавлять новые sender‑JID по мере появления (allowlist).
- **Важно:** `clean_auto` — **sender‑only**. Если написать **на него**, бот не ответит. Используем его как **отправителя** в ChatFlow send‑text → **receiver‑номер** салона, затем проверяем inbound row в БД.
- Inbound от branch‑номеров (sender совпал с `branches.phone`) игнорируется preflight‑гейтом — так мы исключаем bot‑to‑bot loop.
- Используем **пул тестовых JID** (внешние номера). Один suite → один JID, чтобы не текло `pending/expected_reply_type`.
- Self‑send в ChatFlow не гарантирует доставку на телефон. **Разрешена симуляция instance→instance**, если inbound реально записан в БД.
- Делаем короткий ping на тестовый номер. Если не дошло — **STOP**, чинить доставку.
- Проверяем согласованность instance_id:
  - `clients.config.instance_id` — outbound instance (ChatFlow).
  - `branches.instance_id` — routing token для branch.
  - `instanceId` в webhook query — routing token (должен совпадать с `branches.instance_id`).
- Для симуляции instance→instance: **live считается валидным только при наличии inbound row** + `decision_meta/trace` в БД.

**Быстрая отправка + explain (1 команда):**
```bash
python3 ops/diagnose.py send-and-explain \
  --instance-id <CLEAN_INSTANCE_ID> \
  --jid 77055740455@s.whatsapp.net \
  --receiver-phone "+77055740455"
```

**Альтернатива (2 шага):**
```bash
python3 ops/chatflow_send.py \
  --instance-id <CLEAN_INSTANCE_ID> \
  --jid 77055740455@s.whatsapp.net \
  --marker-prefix LC-QUICK

python3 ops/diagnose.py explain --receiver-phone "+77055740455" --text "LC-QUICK"
```

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

**CA‑01 — ожидаемые реакции (канон):**
- **Refund/Payment:** ответ бота `По оплате уточню у администратора — передам администратору ваш вопрос.`  
  `decision_meta`: `action=escalate`, `policy_gate=hard_law`, `policy_section=payment_info`, `intent=payment`.
- **Reschedule:** ответ бота `Перенос записи подтверждает администратор. Передам ваш запрос.`  
  `decision_meta`: `action=escalate`, `policy_gate=hard_law`, `policy_section=reschedule`, `intent=reschedule`.
- **Medical:** ответ бота `По таким вопросам нужна консультация мастера или администратора — передам ваш вопрос.`  
  `decision_meta`: `action=escalate`, `policy_gate=hard_law`, `policy_section=medical`, `intent=medical`.
- **ACK (после каждого кейса):** `ок`/`да`/`жду` → ответ `Хорошо. Напишите, что именно нужно: цена/запись/адрес/мастер.`  
  `decision_meta`: `pending_action=pending_ack`.

**Почему такой процесс:**
- Live‑check требует **реального inbound**: только он пишет `decision_meta` и `decision_trace`.
- Self‑send не доказателен; **instance→instance допустим**, если inbound подтверждён в БД.
- Policy‑кейсы переводят диалог в `pending`; без ACK следующий кейс не попадёт в `policy_gate`.
- Вариативные тексты нужны, чтобы проверить устойчивость к человеческим ошибкам, а не “под шаблон”.

**Как проверяем (процесс):**
1) Выбрать CA‑suite (например, `ca01-core`) и окно запуска.
2) Запустить runner (реальный inbound через ChatFlow → `/webhook/{client_slug}`), suite→JID фиксирован.
3) Brain или Top Architect снимает evidence в БД по marker‑логам (decision_meta + decision_trace).
4) Brain или Top Architect фиксирует PASS/FAIL в `STATE.md` с ссылкой на CA‑ID и артефактами.
5) Top Architect обновляет статус CA‑пункта в `STRATEGY/TECH_ROADMAP.md` с ссылкой на `STATE.md`.
6) Если runner/БД недоступны → статус **BLOCKED**, без фиктивных проверок.

**Принципы:**
- Live‑check валиден при **наличии inbound row в БД** + `decision_meta/trace`.
- Канонический поток: WhatsApp → ChatFlow → `/webhook/{client_slug}`.
- Instance→instance допустим, если inbound подтверждён в БД.
- Любой `verified/gap` в CA‑plan обязан ссылаться на evidence в `STATE.md`.
- Токены/секреты **не** попадают в git/логи.
- **Prod БД не трогаем ради evidence.** Допустимы staging/test DB с явной пометкой окружения в `STATE.md`.
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

---

## 4.4 Onboarding Test SOP (CA‑13/CA‑14)

**Цель:** сделать подключение нового клиента/филиала доказуемым и повторяемым (без “на глаз”).

**Входные данные (фиксируем в Task Package):**
- `client_slug`, `branch_id`, inbound WA‑номер (receiver).
- ChatFlow `instanceId` (может меняться; не хардкодим).
- `webhook_secret` (в git не пишем).
- Sender JID‑пул (тестовые номера, allowlist).

**Шаги:**
1) **DB mapping:** привязать `branches.instance_id` к текущему ChatFlow `instanceId`.
2) **Pack validate/sync:** `ops/sync_client.py --validate` → `--sync` (data packs готовы).
3) **Webhook:** ChatFlow → `/webhook/{client_slug}?webhook_secret=...&instanceId=<current>`.
4) **Inbound proof:** отправить 1 тест‑сообщение с sender‑JID → убедиться в inbound row (metadata.instanceId +
   `decision_meta/trace`).
5) **Live smoke‑suite:** минимум CA‑01/02/03/07 (и CA‑13 для multi‑branch) → evidence в `STATE.md`.
6) **Health/metrics:** `/admin/health` + `/admin/metrics` snapshot → `STATE.md`.

**CA‑13 исключение:** допускается simulated inbound (`/webhook` или instance→instance) без allowlist, если inbound записан в БД и outbound заблокирован; в `STATE.md` пометка `simulated`.

**Evidence (минимум):**
- inbound row с `instanceId` + `decision_meta/trace`;
- `conversation_id` + outbox status;
- ссылки на CI/livecheck артефакты.

**Правило:** если instanceId поменялся в ChatFlow → новый Task Package на обновление `branches.instance_id` и повторный onboarding‑check.

---

## 4.5 Test pools and number roles (CI vs Live)

**Роли номеров:**
- **Receiver (inbound номер салона):** номер, на который пишет пользователь. Его instanceId идёт в webhook и нужен
  для branch routing (`branches.instance_id`).
- **Sender JID‑pool:** тестовые номера, которые пишут на receiver (используются для live‑evidence и изоляции suites).

**Два пула:**
- **CI‑pool (logic):** может быть synthetic; используется только в `/webhook`‑симуляции без реального WA трафика.
- **Live‑pool (real):** только реальные номера; используется для live‑evidence и outbox.

**Правило:** instanceId хранится **в БД** (routing), **не в git**. JID‑pool фиксируется в SOP и env allowlist.

---

## 4.6 Add sender JID to allowlist (процесс)

**Цель:** безопасно расширить пул sender‑JID для live‑checks (изоляция suites).

**Шаги:**
1) Получить sender‑JID (реальный номер для live‑pool).
2) Обновить allowlist в env (`OUTBOUND_ALLOWLIST_JIDS`), без коммита.
3) Запустить CI livecheck → проверить `livecheck-gate.txt`.
4) Зафиксировать evidence в `STATE.md` (run URL + gate).

**Важно:** JID добавляется в allowlist **без создания клиента/филиала**, если он используется только как sender.

---

## 4.7 Add receiver number / instanceId (процесс)

**Цель:** подключить новый inbound номер (клиент/филиал).

**Шаги:**
1) Создать instance в ChatFlow (receiver номер).
2) Настроить webhook: `/webhook/{client_slug}?webhook_secret=...&instanceId=<current>`.
3) Обновить `branches.instance_id` → текущий instanceId (Task Package).
4) Отправить 1 тест‑сообщение → подтвердить inbound row + `decision_meta/trace`.
5) Запустить onboarding smoke‑suite (CA‑01/02/03/07 минимум).

---

## 5. Quality & Validation Framework (обязательный процесс)

**Цель:** единый стандарт качества: доказать корректность, устойчивость и наблюдаемость.

### 5.1 Тестовые уровни (что и зачем)

| Уровень | Что проверяет | Инструмент | Evidence |
| --- | --- | --- | --- |
| L0 (fast) | lint + unit (базовая регрессия) | GitHub Actions (lint/unit) | ссылка на run |
| L1 (core) | детерминизм/регрессии поведения | GitHub Actions (core-eval) | ссылка на run |
| L2 (long/asr) | длинные диалоги + шум/ASR | GitHub Actions (long-eval/asr-eval) | ссылка на run |
| L3 (livecheck) | канон на реальном inbound | CI livecheck + Live-check SOP | `livecheck-*` артефакты + `STATE.md` |
| L4 (nightly) | стресс 10–15 ходов + LLM-вариации | Nightly workflow (planned) | nightly artifacts + summary |

### 5.1.1 Политика CI‑tier (гибкость по всей системе)

**Цель:** быстрые и правильные проверки без “лишнего” прогонов, но с обязательным качеством.

**Правило:** тесты запускаются **по влиянию изменения**, а не “всегда всё”.
**Применение:** правило распространяется **на все** наборы (eval/livecheck/fuzz/perf). Любой новый suite обязан
сразу указать уровень (L1‑L4) + триггеры/labels в Task Package.

**Триггеры:**
- **L0** — всегда на PR и на main (любые изменения).
- **L1** — если менялись `truffles-api/app/**`, `truffles-api/tests/**`, `knowledge/**`, `SPECS/**`,
  `STRATEGY/**`, `ops/**` (любой поведенческий/процессный слой).
- **L2** — если менялись `EVAL.yaml`, `SALON_TRUTH.yaml`, `tests/test_demo_salon_eval.py`,
  либо указан label `run-long`.
- **L3** — только на `main` или вручную через `workflow_dispatch` (`run_livecheck=true`).
- **L4** — nightly (планируется; не блокирует релиз).

**Release gate:** L0 + L1 обязательны; L2 обязателен, если затронуты файлы из L2; L3 выполняется по DoD/CA‑audit.
**Livecheck‑harness:** любые изменения в `.github/workflows/ci.yml` или `ops/diagnose.py` требуют L3 (livecheck)
или явного waiver в Task Package с причиной.

### 5.1.2 Контракт eval‑тестов (без хрупкости)

**Правило:** тесты проверяют **инвариант**, а не конкретный `source`.

**Обязательное:**
- `action` + `intent` + наличие правильной `stage` в trace.
- `source` и `decision` через allowlist (`expected_source_any`, `expected_trace_decision_any`).
- Для LLM: проверять `llm_used` и policy/trace, не текст ответа.

**Запрещено:** “пристрелка” к одному `source`, если канон допускает несколько.
**LLM‑ключи:** CI‑eval не должен зависеть от `OPENAI_API_KEY`. Нужные LLM‑проверки переносятся в L4/nightly или
стабятся так, чтобы trace/meta фиксировали ожидаемую стадию без внешнего API.

### 5.1.3 Redis в CI (детерминизм против скорости)

**Стандарт:** сначала включаем Redis‑service в CI для eval, фиксируем время прогона.

**Fallback:** если L1/L2 становятся слишком медленными — включаем детерминированный режим без Redis
(`REDIS_DISABLED=1` или аналогичный флаг) и фиксируем это в DoD задачи.
**Решение:** выбор режима (Redis on/off) фиксируется в Task Package и подтверждается CI‑таймингами.

### 5.1.4 Nightly gauntlet (planned)

**Цель:** “суровая” проверка устойчивости (10–15 ходов, максимальные вариации, LLM‑тесты).

**Статус:** planned; запуск и DoD — отдельный Task Package.
**Требования (черновик):**
- 10–15 ходов + шум/опечатки/перефразы/ASR‑мусор.
- Минимум 3 варианта на класс (booking/info/consult/OOD).
- LLM‑тесты разрешены, но проверка через meta/trace + агрегаты, не текст.

### 5.2 Fuzz/Soak (симуляция “живого” человека)

**Что это:** автоматический прогон `/webhook` с вариациями текста, ошибок и ритма (не хардкод в коде, а сценарии в runner).

**Статус:** требует отдельного Task Package. Параметры задаются в runner (кол-во, шум, паузы, категории).

**Инварианты (минимум):**
- `decision_meta` и `decision_trace` не пустые.
- Hard‑LAW категории → `policy_gate=hard_law`, `action=escalate`, `llm_used=false`.
- Нет preflight‑reject для валидных сообщений.
- Шум/опечатки/перестановки не должны ломать канон (проверяем meta/trace, не текст).

### 5.3 LLM debug и наблюдаемость

**Что уже есть (runtime evidence):**
- `decision_trace` (conversation.context) — стадии решения.
- `decision_meta` (messages.metadata) — факты, intent, policy, llm flags.
- LLM‑поля: `llm_used`, `llm_timeout`, `llm_cache_hit`, `llm_primary_reason`.
- Метрики: `/admin/metrics` (latency, outbox, SLA), алерты: `/alerts/test`.

**Принцип:** все сомнения проверяются trace/meta/metrics, а не “ощущением”.

### 5.4 Готовность к старту (минимальный порог)

1) CA‑01…CA‑15 = `verified` с evidence в `STATE.md`.  
2) CI L0+L1 зелёные; L2 зелёный, если затронуты файлы L2‑триггеров.  
3) `/admin/version` = HEAD, `/admin/health` OK.  
4) `/alerts/test` доставляет алерт.  
5) Метрики фиксируются в `STATE.md` (p50/p90 + fallback_rate).  

### 5.5 OSS toolchain (стандарт, без велосипедов)

**Выбор инструментов (современный OSS‑стек):**
- **Contract/Fuzz:** Schemathesis (OpenAPI‑fuzz, на базе Hypothesis).
- **Property‑based:** Hypothesis (инварианты логики).
- **Load/Soak:** k6 (контейнер, deterministic сценарии).
- **Observability:** OpenTelemetry + Prometheus + Grafana + Loki/Tempo.
- **Tracing/Debug:** decision_trace + decision_meta (runtime evidence).

**Правило:** инструменты не заменяют канон; они дают повторяемые доказательства.

### 5.5.1 LLM testing policy (детерминизм + статистика)

**Блокирующие (deterministic) гейты:**
- Факты/консалт из pack: `llm_used=false`, `source=pack`, `consult_playbook_id` присутствует.
- Hard‑LAW/Policy: LLM не вызывается, `policy_gate` фиксируется.

**Неблокирующие (statistical) проверки:**
- Ночной eval‑прогон: семантическое соответствие по рубрике/эмбеддингам (без сравнения текста).
- Результат фиксируется в артефактах + краткое summary в `STATE.md` как risk‑note (без смены статуса CA).

**Почему:** LLM‑текст недетерминирован; проверяем поведение через meta/trace и агрегированные метрики качества.

### 5.5.2 Known risks and fixes (процесс/тестирование)

- **Термины путаются (JID vs instanceId vs remote_jid vs CI/live):** фиксируются в 4.3, в отчётах всегда указывать тип.
- **Течёт состояние между suite‑ами:** использовать JID‑пул (one suite → one JID) или обязательный reset‑шаг.
- **instanceId дрейфует в ChatFlow:** обновлять `branches.instance_id` отдельным Task Package + повторный onboarding‑check.
- **CI vs реальный inbound смешаны:** CI = `/webhook` + meta/trace; live‑evidence = inbound row + meta/trace.
- **Demo‑only данные дают ложное чувство готовности:** добавлять test tenants/branches и пак‑валидацию в CI.
- **LLM текст недетерминирован:** проверки через meta/trace + статистические eval‑метрики, не через literal‑текст.
- **Allowlist неверный → риск писать живым людям:** `TEST_MODE=1` + allowlist gate + gate‑лог в CI.

### 5.5.3 k6 load/soak (manual gate)

- **Цель:** поймать регрессию по задержкам/ошибкам на “горячих” Console эндпоинтах (p95/5xx).
- **Когда запускать:** перед релизом после изменений в Console API/фильтрах/пагинации/индексах; перед подключением крупного клиента; при подозрении на деградацию.
- **Когда обновлять сценарий:** добавлен новый “горячий” эндпоинт или изменились фильтры/параметры; изменились SLO/пороги.
- **Evidence:** k6 summary + команда запуска в `STATE.md`.

### 5.6 Повторяемый процесс запуска (один сценарий для всех ролей)

1) **CI L0+L1** → ссылка на run (без этого STOP); **L2** обязателен при L2‑триггерах.  
2) **CA live‑check** → evidence в `STATE.md` (conv_id/trace/meta).  
3) **Fuzz/Soak** → метрики стабильности + sampling evidence.  
4) **Review evidence** → только после этого обновляем CA‑статус в `STRATEGY/TECH_ROADMAP.md`.

Runner печатает JSON‑лог (marker, case_id, sent_at, expected_policy_section).  
Marker формат: `LC:<suite>:<case_id>:<timestamp>:<seq>`.

### 5.7 Webhook fuzz SOP (safe runner)

**Цель:** безопасный и детерминированный прогон `/webhook/{client_slug}` без риска отправки на чужие номера.

**Режимы:**
- `logic` (default): уникальный JID на кейс, `--skip-outbox` по умолчанию.
- `state`: **JID‑pool** из allowlist; один JID на suite/запуск, outbox включён для проверки pending/manager.
- Если кейс содержит `turns`, все ходы идут в один и тот же JID (диалог внутри кейса).

**Safety gate:**
- `--allowlist-jids` (comma list) обязателен при включённом outbox.
- Любая попытка outbox с JID вне allowlist → STOP.
- `logic` режим требует `TEST_MODE=1` (outbound guard).

**Выбор кейсов:**
- `--case-ids` = список case_id через запятую (например `LAW_MEDICAL,INFO_HOURS`).
- Диалоговый кейс задаётся через `turns` (список сообщений); каждый ход получает отдельный `FZ:` marker.

**Примеры:**
```bash
python3 ops/diagnose.py webhook-fuzz \
  --mode logic \
  --client-slug demo_salon \
  --count 10 \
  --seed 42 \
  --webhook-secret "$WEBHOOK_SECRET"
```

```bash
python3 ops/diagnose.py webhook-fuzz \
  --mode state \
  --client-slug demo_salon \
  --case-ids LAW_COMPLAINT \
  --remote-jid 77015705555@s.whatsapp.net \
  --allowlist-jids 77015705555@s.whatsapp.net,7701XXXXXXX@s.whatsapp.net \
  --webhook-secret "$WEBHOOK_SECRET" \
  --admin-token "$ALERTS_ADMIN_TOKEN"
```

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
SELECT m.id, m.created_at, m.content,
       m.metadata->>'messageId' AS message_id,
       m.metadata->'decision_meta' AS decision_meta,
       c.id AS conversation_id
FROM messages m
JOIN conversations c ON c.id = m.conversation_id
WHERE m.role = 'user'
  AND m.content ILIKE '%FZ:%'
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

### 5.8 Ожидаемые исходы (чтобы не путаться)

**Logic‑mode (`webhook-fuzz --mode logic`):**
- Цель: проверить decision_graph без pending/менеджера.
- Ожидаемо: 1 inbound → decision_meta + decision_trace (в БД).
- Outbox по умолчанию выключен, поэтому сообщений в WhatsApp не будет.

**State‑mode (`webhook-fuzz --mode state`):**
- Цель: проверить pending/manager поведения.
- Ожидаемо: после hard‑law эскалации ответы идут как `Администратор подключится...`.
- Повторные inbound могут **не** проходить decision_graph (это нормально).

**Live‑check (WhatsApp реальный inbound):**
- Цель: доказать канон на реальной доставке (ChatFlow → /webhook).
- Ожидаемо: decision_meta + decision_trace, фиксируется в `STATE.md`.
- Ручное действие: отправка сообщений делает только владелец тестового номера.

**Важно:** outbox coalescing и debounce могут давать меньше ответов, чем inbound. Это не баг, если trace/meta в БД корректны.

### 5.8.1 Правила дизайна тестов (anchors + dialogs + noise)

**Цель:** тесты проверяют смысл и устойчивость, а не “запоминание фраз”.

**Anchors (минимум):**
- На каждый CA — 2–4 **якорных** фразы, чтобы гарантировать срабатывание гейта.
- Якоря = детерминизм. **Текст ответа не сравниваем**, только meta/trace.

**Dialogs (6–10 шагов):**
- Для booking/consult/pending обязателен dialog‑suite на 6–10 шагов.
- Каждый шаг фиксирует meta/trace + контекст (`expected_reply_type`, `current_goal`, `service_hint`, `info_sections`).
- Между suite‑ами: reset‑шаг или отдельный JID из пула (чтобы не текло состояние).

**Noise/chaos:**
- Перестановка слов, опечатки, смена темы, смешанные интенты.
- Проверяем только meta/trace (без сравнения ответа).

**ASR‑noise:**
- Транскрипции с ошибками (слитные слова, пропуски, кириллица/латиница).
- Требования: meta/trace пишутся; канон не ломается; LLM‑гейты соблюдаются.

**Onboarding data quality:**
- Негативные pack‑кейсы обязаны падать в `sync_client.py --validate`.
- При неполных данных — fail‑closed (эскалация/уточнение), без “выдумки”.

### 5.9 Safety‑контур (обязательная защита)

**Правило:** автопрогоны не пишут живым людям.

**Обязательные условия в проде:**
- `TEST_MODE=1` (блокирует outbound вне allowlist).
- `OUTBOUND_ALLOWLIST_JIDS` — comma list тестовых JID (пул).
- Любая попытка отправки вне allowlist → STOP и GAP.

### 5.10 “Frozen” план действий (не менять без Top Architect)

**Единственный план:** CA‑01…CA‑15 в `STRATEGY/TECH_ROADMAP.md`.  
**Как идём:** один CA‑ID за раз → evidence в `STATE.md` → статус в CA‑plan.

**Последовательность выполнения:**
1) Safety‑контур (env + allowlist доказаны).  
2) CA‑01 полностью (refund/payment/reschedule/medical + ACK).  
3) Observability‑контур (OTel + Prometheus/Grafana + Loki/Tempo).  
4) Automated quality‑контур (Schemathesis + Hypothesis + k6).  
5) Evidence‑контур (ежедневный snapshot + автологи).  
6) CA‑02…CA‑15 по порядку.

**Почему так:** иначе получаем “слепые” тесты, регрессии и ручной хаос.

### 5.11 Риски и ограничения (принятые)

**CI покрывает все CA‑инварианты:** для пунктов с live‑evidence используется CI live‑check job.  
**Live‑check в CI на проде:** разрешён только в dev‑фазе и **только** при safety‑контуре (allowlist + TEST_MODE).  
**После готовности:** владелец делает выборочный live‑check на живых клиентах.

### 5.12 CI live‑check policy (dev‑phase)

**Разрешение:** включать только при явном флаге (например `CI_LIVECHECK_ENABLED=1`).  
**Обязательные гейты:**
- `TEST_MODE=1`
- `OUTBOUND_ALLOWLIST_JIDS` — comma list тестовых JID (пул)
- Для CA‑09: `QDRANT_COLLECTION` должен оканчиваться на `_ci` (если env пуст — default `truffles_knowledge_ci` в TEST_MODE).
- Guard: при `TEST_MODE=1` и коллекции не `_ci` learning блокируется (`learning_mode=blocked`).
- Только тестовый `client_slug` и test‑instance; любые другие → STOP.
- `instanceId` в payload должен совпадать с `branches.instance_id` (DB); рассинхрон с `clients.config.instance_id` фиксируем как GAP.
- Малый объём (4–10 сообщений), фиксированный seed, без спама.

**Детерминизм suites:**
- **One suite → one JID:** для параллели нужен allowlist ≥ 4; иначе фиксируем `ALLOWLIST_TOO_SHORT` и включаем fallback.
- **Reset перед suite:** каждый suite обязан пройти reset/clear‑meta шаг; без reset → STOP.
- **Adaptive poll_timeout:** минимум =
  `OUTBOX_COALESCE_SECONDS + OUTBOX_WORKER_INTERVAL_SECONDS + (CHATFLOW_RETRY_ATTEMPTS * CHATFLOW_RETRY_BACKOFF_SECONDS) + 10s`.
  Значение и входные параметры логируются в `livecheck-run-*.log`.

**Fail‑fast gate (контур готовности):**
- `/admin/health` OK, `OUTBOX_WORKER_ENABLED=1` **или** активен cron‑контур (явно).
- `ALERTS_ADMIN_TOKEN` доступен; `/admin/metrics` отвечает.
- При провале — CI прекращается с причиной `ENV_NOT_READY` (без “таймаутов”).

**Диагностика падений:**
- В артефактах должны быть `remote_jid`, `conversation_id`, `last_decision_meta` и последний `decision_trace` stage.

**CI job:** `ci-livecheck` в `.github/workflows/ci.yml` → `ops/diagnose.py livecheck-auto` suites: `ca01-core`, `ca02-policy`, `ca03-info`, `ca04-service`, `ca05-booking`, `ca06-consult`, `ca07-ood`, `ca08-state`, `ca09-manager`, `ca10-outbox`.
- Запуск: 4 параллельные группы (`pool-a/b/c/d`), каждая со своим JID из allowlist (желательно ≥4 JID).
- Fallback: если allowlist < 4, `pool-a` запускает все suites последовательно, `pool-b/c/d` пропускаются.
- Артефакты: `livecheck-artifacts-<group>/*` + `livecheck-evidence-<group>.md`.
- **Livecheck Only (workflow):** `.github/workflows/livecheck-only.yml` — ручной rerun без полного CI; делает `deploy-verify` и гоняет suites (параллельно).
**Evidence artifact:** `livecheck-evidence.md` (генерируется из jsonl + gate через `ops/diagnose.py emit-evidence`).
**CA‑03 (ca03-info):** truth‑first info_bundle → `decision_meta.fact_source=truth`, `info_sections`+`fact_intents`, `info_combined` (address+hours), `llm_used=false`, `source` ∈ {`truth_gate`,`class_router`}, trace `stage` ∈ {`truth_gate`,`info_class`}.
**CA‑04 (ca04-service):** service matcher → `decision_meta.action=reply`, `intent` ∈ {`service_match`,`service_not_found`}, `fact_source=service_matcher`, `fact_intents` contains `service_match`/`service_not_found`, `source=service_matcher`, `llm_used=false`, trace `stage=service_matcher`, `decision` = intent, `fact_source=service_matcher`.
**CA‑05 (ca05-booking):** booking‑first → `expected_reply_type=service_choice` после “хочу записаться”, затем `expected_reply_type=time` и `booking.service` заполнен после сервиса; interrupt‑вопрос → `booking_info_interrupt=true`, `booking_info_intents` непустой, trace `stage=booking_interrupt` с `info_intents`.

**Важно:** CI‑livecheck покрывает CA‑инварианты в dev‑фазе; финальный live‑check на живых клиентах — вручную.

### 5.13 CA‑Matrix (suite/mode/evidence)

**Назначение:** единая матрица CA → suite → mode → required meta/trace → evidence source.

**Suite:** имя набора в `ops/diagnose.py` (`livecheck-auto` или `webhook-fuzz`).  
**Mode:** `logic` / `state` / `live` (см. 5.8).  
**Manual:** suite отсутствует, evidence собирается вручную.

| CA-ID | Suite | Mode | Required decision_meta | Required decision_trace | Evidence source |
| --- | --- | --- | --- | --- | --- |
| CA-01 | `ca01-core` | live | action=escalate; policy_gate=hard_law; policy_section ∈ {refund,payment_info,reschedule,medical}; intent; risk_level; llm_used=false | stage=policy_gate; policy_gate=hard_law; policy_section | `livecheck-ca01-core.jsonl` + `livecheck-gate.txt` + SQL/`STATE.md` |
| CA-02 | `ca02-policy` | live | policy_gate ∈ {discounts,hard_law}; policy_section; action; risk_level; llm_used=false | stage=policy_gate; policy_type; risk_level; policy_section | `livecheck-ca02-policy.jsonl` + `livecheck-gate.txt` + CI core |
| CA-03 | `ca03-info` | live | fact_source=truth; info_sections; fact_intents; info_combined (address+hours); llm_used=false; source ∈ {truth_gate,class_router} | stage ∈ {truth_gate,info_class}; fact_source=truth; info_sections/intents | `livecheck-ca03-info.jsonl` + `livecheck-gate.txt` + CI core |
| CA-04 | `ca04-service` | live | action=reply; intent ∈ {service_match,service_not_found}; fact_source=service_matcher; fact_intents; llm_used=false; source=service_matcher | stage=service_matcher; decision=intent; fact_source=service_matcher | `livecheck-ca04-service.jsonl` + `livecheck-gate.txt` + CI core |
| CA-05 | `ca05-booking` | live | expected_reply_type (service_choice→time); booking.service; booking_info_interrupt=true; booking_info_intents | stage=booking_interrupt; info_intents | `livecheck-ca05-booking.jsonl` + `livecheck-gate.txt` + CI booking |
| CA-06 | `ca06-consult` | live | consult_reply: consult_playbook_id + source=pack; short_circuit: fact_source ∈ {truth,service_matcher}; llm_used=false | stage=consult_flow (decision=consult_reply/short_circuit); consult_playbook_id | `livecheck-ca06-consult.jsonl` + `livecheck-gate.txt` + CI consult |
| CA-07 | `ca07-ood` | live | action ∈ {out_of_domain,smalltalk}; source ∈ {guard,router,fast_intent}; llm_used=false | stage ∈ {out_of_domain,fast_intent,smalltalk} | `livecheck-ca07-ood.jsonl` + `livecheck-gate.txt` + CI core |
| CA-08 | `ca08-state` | live | action=escalate; pending_action=pending_ack | stage ∈ {pending_sla,pending_resume} | `livecheck-ca08-state.jsonl` + `livecheck-gate.txt` + SQL state/handover |
| CA-09 | `ca09-manager` | live | action=escalate; policy_gate=hard_law | stage=policy_gate (hard_law) | `livecheck-ca09-manager.jsonl` + `livecheck-gate.txt` + Telegram/DB/Qdrant |
| CA-10 | `ca10-outbox` | live | n/a | stage ∈ {outbox,dedup} (if traced) | `livecheck-ca10-outbox.jsonl` + `livecheck-gate.txt` + SQL outbox |
| CA-11 | manual | state | decision_meta present on user messages | critical stages retained in decision_trace | SQL audit (decision_trace retention) |
| CA-12 | manual | logic | router_* meta + budget/llm_degradation flags | stages budget_gate/llm_degradation | `/admin/metrics` + SQL meta/trace |
| CA-13 | manual | live | branch_id; knowledge_tag | trace/rag filter evidence | live-check **or** simulated inbound + SQL trace/meta (`simulated` in `STATE.md`) |
| CA-14 | manual | logic | n/a | n/a | `ops/sync_client.py --validate` + Qdrant sync + `/admin/version` |
| CA-15 | manual | logic | n/a | n/a | `/admin/health` + `/admin/metrics` + `/alerts/test` + no_response alerts |

### 5.13.1 Trace stage registry (single source of truth)

- **Источник стадий:** stage‑литералы, переданные в `_record_decision_trace` в `truffles-api/app/routers/webhook/`.
- **CI‑сканер:** извлекает stage‑множество из кода и использует его как единственный источник правды.
- **Gate:** каждая стадия должна быть “зажжена” тестом **или** перечислена в waiver‑списке с причиной и сроком.
- **Новые стадии:** без теста/waiver → CI красный.

**Авто‑evidence:**  
`python3 ops/diagnose.py emit-evidence --input-dir artifacts --gate artifacts/livecheck-gate.txt --output artifacts/livecheck-evidence.md`

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

### Decision pipeline (code-accurate, webhook → response)
**Источник правды (код):**
- `truffles-api/app/routers/webhook/http.py` (HTTP вход, preflight)
- `truffles-api/app/routers/webhook/decision.py` (оркестрация)
- `truffles-api/app/routers/webhook/outbox.py` (enqueue + outbox worker helpers)
- `truffles-api/app/contracts/decision.py` (Decision Graph stages)
- `truffles-api/app/services/chatflow_service.py` (outbound send-text)
- `truffles-api/app/workers/outbox.py` (outbox worker loop; legacy loop был в `app/main.py`)

**Пошаговый поток (с эффектом каждого шага):**
1) **HTTP ingress** (`handle_webhook` / `handle_webhook_direct`)  
   - Вызывает `legacy._handle_webhook_payload(... enqueue_only=True)`.  
   - Эффект: ACK-first режим всегда включен для входящего webhook.

2) **Preflight** (`http._run_preflight`)  
   - Проверки: клиент, секрет, remote_jid, пустой текст, sender=branch phone, instanceId/branch routing.  
   - Эффект: ранний `WebhookResponse` при reject/drop + trace `stage=preflight` (если разговор можно разрешить).

3) **Dedupe + persist user message** (`decision._handle_dedup_gate`, `save_message`)  
   - Dedupe по `message_id`/`inbound_message_id`.  
   - Эффект: нет дублей, user-message сохранен, `decision_meta.trace_id` записан.

4) **ACK-first enqueue** (`outbox._handle_enqueue_only_accept`)  
   - При PENDING/MANAGER_ACTIVE — fast-forward в Telegram (если настроено).  
   - `enqueue_outbox_message` -> `outbox_messages` (PENDING).  
   - Trace: `stage=outbox`, `decision=enqueue_only`.  
   - Эффект: HTTP ответ сразу, тяжелая логика уходит в outbox.

5) **Outbox worker** (`app/workers/outbox.py` → `run_worker`)  
   - `claim_pending_outbox_batches` → `webhook._process_outbox_rows`.  
   - Эффект: каждое outbox-сообщение вызывает `_handle_webhook_payload(skip_persist=True)`.

6) **Skip-persist prep** (`outbox._prepare_skip_persist`)  
   - Загружает conversation/user/saved_message, media policy.  
   - Эффект: если данных нет → ранний return + trace `stage=skip_persist`.

7) **Decision plan trace** (`build_context_contract`, `build_decision_plan`)  
   - Trace: `stage=contract` (context) + `stage=decision_graph` для каждой стадии  
     (`state/risk/expected/semantic/data/action/response/update`).  
   - Эффект: фиксируем “план” как доказательство хода.

8) **Основные gate-ы (порядок в коде)**  
   - expected reply → branch selection → shield → session timeout  
   - forward pending to Telegram → manager_active → reengage/mute  
   - ASR confirmation → pending gate → media gate → debounce  
   - handover confirmation → booking signal → hard_law gate  
   - intent decomposition → opt_out mute → policy escalation  
   - fast_intent/smalltalk → class router → domain flows (consult/info/booking)  
   - LLM primary + truth gate fallback  
   - Эффект: ранние `WebhookResponse` при каждом gate, с trace/meta.

9) **Ответ и фиксация** (`_send_and_save`)  
   - `_finalize_bot_response` (quiet hours), contracts (fact/action/response).  
   - `save_message(role="assistant")` + `send_bot_response` (ChatFlow).  
   - Эффект: запись ответа в БД и отправка наружу; trace/meta закрывают доказательство.

10) **Outbox status** (`mark_outbox_status`)  
    - `SENT`/`FAILED` + backoff retries.  
    - Эффект: idempotency + auto-heal (P0 фитнес‑функция).

**Как читать роль каждого шага “по строкам”:**
- Для каждого `return WebhookResponse` → это ранний выход и смысл gate-а.  
- Для каждого `_record_decision_trace` → это “смысл” стадии (что именно доказано).  
- Для каждого `_record_message_decision_meta` → это контракт фактов на user-message.

### Gate Ledger (условие → эффект → trace/meta)
| Order | Gate / function (file) | Condition (summary) | Effect / next step | Trace / meta |
| --- | --- | --- | --- | --- |
| 1 | **Question contract / expected reply** (`decision._apply_expected_reply_contract`) | expected_reply_type present | Match/short‑circuit or continue | `stage=question_contract`, `expected_reply_*` in meta |
| 2 | **Branch selection** (`branch_selection._handle_branch_selection_gate`) | branch_mode ask_user/hybrid, >1 branch | Prompt/select branch and return | `stage=branch_selection`, decision=prompt/selected |
| 3 | **Shield** (`shield._handle_shield_gate`) | spam/too_long or toxic/nonsense | Drop or escalate; early return | `stage=shield`, decision=drop/escalate |
| 4 | **Session timeout reset** (`dedup._apply_session_timeout_reset`) | last_message_at > SESSION_TIMEOUT_HOURS | Reset mute/context | (no stage; log only) |
| 5 | **Manager active** (`pending._handle_manager_active_gate`) | state=MANAGER_ACTIVE | Early return (no bot reply) | (no stage) |
| 6 | **Reengage/mute** (`guards._handle_reengage_and_mute_gate`) | reengage confirmation or muted | Resume or skip | `stage=routing`, decision=reengage_confirmed/muted_skip/... |
| 7 | **Pending gate** (`pending._handle_pending_gate`) | state=PENDING/manager | SLA ping/ack/close/wait | `stage=pending_sla/pending_resume/pending_wait/pending_status` |
| 8 | **Media gate** (`decision` media checks) | unsupported/rejected media | Early reply | `stage=media`, decision=unsupported/rejected |
| 9 | **Debounce gate** (`dedup._handle_debounce_gate`) | bursty inputs | Skip intermediates | `stage=debounce`, decision=skip/manager_active |
| 10 | **Handover confirm** (`pending._handle_handover_confirmation_gate`) | pending confirmation | Escalate or clarify | `stage=handover_confirmation`, decision=confirmed/declined |
| 11 | **Hard‑LAW** (`policy._handle_hard_law_gate`) | hard_law match | Escalate/reply | `stage=policy_gate`, policy_gate=hard_law |
| 12 | **Policy gate** (`policy._handle_policy_escalation_gate`) | policy_pack match | Escalate/reply | `stage=policy_gate`, policy_gate={...} |
| 13 | **Opt‑out mute** (`guards._handle_opt_out_mute_gate`) | opt_out_in_batch | Mute (first/second) | `stage=rejection`, decision=muted_first/muted_second |
| 14 | **Fast intent / smalltalk** (`decision` fast intent) | greeting/thanks/ack | Short reply | `stage=fast_intent` / `stage=smalltalk` |
| 15 | **Consult flow** (`response._handle_consult_flow`) | consult_intent or consult_context | Reply/clarify/escalate | `stage=consult_flow`, `stage=consult_context`, `stage=consult` |
| 16 | **Info flow** (`info._handle_info_flow`) | info_class intents | Reply / truth‑gate | `stage=info_class`, `stage=truth_gate` |
| 17 | **Booking flow** (`booking._handle_booking_flow`) | booking_signal/booking_active | Reply/interrupt | `stage=booking`, `stage=booking_interrupt`, `stage=truth_gate` |
| 18 | **LLM primary + fallback** (`response._handle_llm_primary`) | LLM path enabled | ai_response/clarify/escalate | `stage=llm_guard`, `stage=ai_response`, `stage=llm_degradation` |

### Determinism Inventory (лексиконы + правила)
**Rules‑as‑data (packs):**
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`  
  Policy keywords (payment/reschedule/cancel/medical/legal/complaint/discount), explicit/override keywords.
- `truffles-api/app/knowledge/demo_salon/INTENTS_PHRASES_DEMO_SALON.yaml`  
  Phrase intents + offtopic examples (используется в `phrase_match_intent`).

**Code lexicons / regex (детерминированные списки):**
- `truffles-api/app/routers/webhook/decision.py`  
  `SHIELD_TOXIC_PATTERNS`, `SHIELD_MEANINGFUL_PATTERN`, `HYGIENE_KEYWORDS`,  
  `BOOKING_REQUEST_KEYWORDS`, `SERVICE_KEYWORDS`, `DATE_KEYWORDS`,  
  `is_handover_status_question` keywords.
- `truffles-api/app/routers/webhook/shield.py`  
  Использует `SHIELD_TOXIC_PATTERNS`/`SHIELD_MEANINGFUL_PATTERN`.
- `truffles-api/app/services/ai_service.py`  
  `BOT_STATUS_KEYWORDS`, `REFUSAL_PHRASES`, fallback intent keywords.
- `truffles-api/app/services/demo_salon_knowledge.py`  
  `phrase_match_intent`, `_OFFTOPIC_KEYWORDS`, price/faq keywords,  
  policy section matching by phrases/keywords.
- `truffles-api/app/routers/webhook/policy.py`  
  Keyword‑match по policy pack + guard overrides.

**Deterministic gates (не лексиконы):**
- Preflight: `http._run_preflight` (client/secret/instanceId/branch)  
- Dedupe + Debounce: `dedup._handle_dedup_gate`, `dedup._handle_debounce_gate`  
- Pending/mute/reengage: `pending._handle_pending_gate`, `guards._handle_reengage_and_mute_gate`  
- Outbox idempotency: `outbox._handle_enqueue_only_accept`, `outbox_service.*`

### RU/KZ/mixed: как улучшать без перебора всех комбинаций
**Цель:** повысить устойчивость к смешанным языкам и опечаткам, не увеличивая словари “в лоб”.

1) **Единая нормализация**  
   - Канонизация пробелов/пунктуации + `casefold`.  
   - Транслитерация KZ‑латиница↔кириллица.  
   - Канон‑маппинг казахских букв (ә/а, ғ/г, қ/к, ң/н, ө/о, ұ/у, ү/у, һ/х) в одну форму.

2) **Lexicon v2 в packs (rules‑as‑data)**  
   - Вынести кодовые списки в pack: intent → aliases (ru/kz/mixed),  
     weight/priority, optional regex.  
   - В коде оставить только “движок” матчинга и порог score.

3) **Лёгкая морфология (детерминированно)**  
   - RU: стемминг/суффикс‑правила (офлайн расширение → packs).  
   - KZ: минимальные суффикс‑шаблоны (также офлайн, фиксированный список).

4) **Scoring вместо “точного совпадения”**  
   - Токены/стемы/алиасы → score.  
   - Пороговое решение (deterministic): score ≥ threshold.

5) **Trace/meta для объяснимости**  
   - decision_meta: `lexicon_hit`, `lexicon_score`, `lexicon_version`, `lang_detected`.  
   - Это даёт воспроизводимость и контроль при изменениях.

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
