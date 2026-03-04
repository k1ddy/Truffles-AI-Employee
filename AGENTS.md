# AGENTS — Принципы работы (Truffles)

**Читай это первым. Каждую сессию.**

Цель этого файла: чтобы **люди и агенты** работали одинаково: *без догадок*, *без god-файлов*, *без «рефакторим всю систему»*, *с доказательствами*.

---

## 0) Workspace anchor (обязательно)

- Канонический репозиторий: `/home/zhan/truffles-main`
- Все канонические документы (`AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `TECH.md`) — **внутри repo**.
- Старт сессии: `cd /home/zhan/truffles-main` → `docs/SESSION_START_PROMPT.txt` → `scripts/session_start.sh`.
- Если есть конфликт между этим файлом и repo‑доками, следуй repo‑докам.

---

## 0) Truffles в одной формуле

**Truffles = LLM Policy Core (действия/слоты/исход) + Deterministic Safety (LAW/policy/валидация) + Tools/Packs (факты) + Escalation (человек) + Data in KZ**.
LLM принимает решение (FACT/COLLECT/HANDOFF) и формулирует ответ; safety‑слой валидирует выход, соблюдает hard‑policy/LAW и исполняет tools/packs.

**Контракт продукта (каждое user-сообщение должно привести к одному исходу):**
- **FACT** — короткий ответ строго из data packs (truth-first).
- **COLLECT** — сбор слотов/контактов/предпочтений (lead/booking).
- **HANDOFF** — передача человеку с прозрачным статусом (pending/manager_active).

**Escalation — не провал.** Это продукт внутри продукта (очередь, статусы, SLA, модерация, обучение).

---

## 0.1 Semantic-First Charter (обязательно)

- **LLM-first semantic ownership:** смысл хода (intent/action/slots/fact_refs) определяет один semantic owner — policy-core LLM.
- **Deterministic only at boundaries:** детерминизм применяется только для LAW/safety, schema validation, capability/protocol gate, idempotency/outbox/state.
- **Запрет semantic hardcode в core:** phrase/regex branching по user text в core-файлах запрещён как способ управления бизнес-смыслом.
- **Pack/tenant as data, not code:** доменные различия живут в packs/capabilities/manifests, а не в core-ветках.
- **Graceful degrade budget:** сбой/недоступность LLM допустимы только в контролируемом degrade-path с reason-code и trace/meta evidence; acceptance оценивает это как исключение, а не основной путь.
- **Контрактная приёмка:** качество принимается по `action/tool/trace/meta/outcome`, а не по byte-identical тексту ответа.

---


## 0.2 Проект (что продаем)

| Что | Ответ |
|-----|-------|
| Ценность клиенту | Ответ в 11 вечера, не ждать до утра |
| Ценность бизнесу | Менеджер не нужен 24/7, бот закрывает 80% вопросов |
| Продаем | "Консультант + запись + эскалация", НЕ "AI" |
| Первая ниша | салоны красоты (KZ/CIS) |

**UX-позиция:** Telegram = операционный UI/алерты; источник истины = БД/сервис; Web Console = целевой профессиональный интерфейс.

---

## 1) Канон и источники истины

**Порядок чтения (всегда):**
1) `STATE.md` — NOW / факты / блокеры / evidence
2) `STRUCTURE.md` — где что лежит и как добавлять
3) `STRATEGY/REQUIREMENTS.md` — запреты, обещания, границы
4) `SPECS/*` по задаче (ARCHITECTURE/CONSULTANT/ESCALATION и т.д.)
5) `TECH.md` + `SPECS/SYSTEM_REFERENCE.md` — реализация, команды, схемы
6) `docs/SESSION_START_PROMPT.txt` — протокол ролей и Task Package

**Правило “FACT vs PLAN”:**
- Запись в `STATE.md` считается **FACT** только если рядом есть **evidence** (CI/логи/SQL/trace).
- Если evidence нет → это **PLAN** или **GAP**.

**Запрещено “добывать evidence руками”** (чистить БД/trace ради красивой картинки).

### 1.1 Canon + Quality Gates (обязательно)
- **Canon Sync Gate:** `/home/zhan/AGENTS.md` и `truffles-main/AGENTS.md` не должны расходиться по каноническим правилам (формула, quality contract, stop-the-line, fitness). Расхождение = GAP, запуск сессии/CI блокируется до синхронизации.
- **Context Integrity Gate:** каждая новая сессия должна иметь `context_integrity_gate: required`; Task Package без секций `Residual architecture debt (mandatory)` и `Next-block contract (mandatory)` блокируется `session_check/session_gate`.
- **Quality Validity Gate:** quality-run считается валидным только при `infra_valid=true` и `semantic_valid=true`.
- **Hard Preflight Gate:** при невалидном preflight (`webhook_secret`/branch/env/judge key) run = `INVALID`; сравнение метрик и baseline для такого run запрещены.
- **Baseline Integrity Gate:** canonical baseline обновляется только если `infra_valid=true`, `semantic_valid=true`, `judge.enabled=true`.
- **Quality Constant Gate:** ограничения по времени/токенам/бюджету не могут снижать продуктовые и архитектурные требования (LAW/safety/invariants/acceptance thresholds/обязательные проверки). Если требуемый контур недоступен, статус = `BLOCKED`, а не "упрощенный pass".
- **No Shortcut Gate:** запрещено вводить обходные/костыльные решения в default runtime path (временные phrase-hardcode, silent fallback, ослабление gate/oracle) как способ "успеть в бюджет".
- **Budget Interpretation Gate:** бюджет влияет только на порядок и частоту запусков (cadence), но не на качество критериев, не на контракт продукта и не на целевую архитектуру.
- **Anti Test-Fitting Gate:** запрещено добавлять/усиливать `must_include` как основной oracle без эквивалентных контрактных проверок в `decision_meta/decision_trace`.
- **Demo-Neutral Gate:** demo-pack (`demo_salon`) используется только как канарейка; runtime-core остаётся pack-agnostic.
- **Lexicon/Regex Delta Gate:** расширение словарей/regex допустимо только вместе с изменением резолвера и контрактных тестов.
- **Semantic Ownership Gate:** post-hoc semantic rewrite вне whitelist reason-codes считается нарушением контракта.
- **Boundary Determinism Gate:** детерминированные ветки не подменяют semantic-owner решение; они только валидируют/блокируют/деградируют контрактно.
- **Graceful Degrade Gate:** degrade-path должен быть наблюдаемым (`reason_code`, `decision_meta`, `decision_trace`) и не становиться основным маршрутом.

---

## 2) Роли и власть

| Роль | Что делает | Чего НЕ делает |
|------|------------|----------------|
| **Жанбол (Owner)** | Решения, приоритеты, финальное слово, бизнес | Писать/поддерживать код |
| **Top Architect** | Курс, инварианты, DoD, DEC, архитектура; делает merge и фиксирует `STATE.md` | Делать задачи руками |
| **Brain (PM+Tech Lead)** | Формирует Task Package, координирует, принимает результат, делает merge | Менять архитектуру без Top Architect |
| **Hands (DEV/QA/OPS/DOCS)** | Реализация/тесты/доки строго по Task Package | Менять курс, “улучшать по-своему”, делать merge |

**Правило вопросов:** если роль заблокирована — задаёт вопросы вверх (Brain/Architect/Owner), **не делает предположения**.

**Git-власть:** Brain и Top Architect могут мержить в main и катить релиз. Hands могут коммитить/пушить только в свою ветку (если это разрешено в Task Package) и обязаны приложить status/diff/evidence.

---

## 3) Один рабочий протокол (для всех)

### 3.1 One-issue flow
**1 проблема → 1 правка → 1 проверка → 1 запись в `STATE.md` (до merge для core/поведенческих изменений).**
Проблема должна быть из `STATE.md` (NOW/GAP) или оформлена как GAP до старта.

### 3.2 Не создавай — обновляй
Перед созданием нового файла:
1) Есть ли уже место? → см. `STRUCTURE.md`
2) Можно ли добавить в существующий? → добавь

Если создал новый файл:
1) внеси в `STRUCTURE.md`
2) внеси в `STATE.md` (карта документов)

### 3.3 Итог каждой сессии
Результат = артефакт + проверка + evidence.
- Код/доки без проверок = не результат.
- “Кажется работает” = GAP.
- Новая фича = минимум один тест (Playwright/Schemathesis/k6/unit) или явный waiver в Task Package.
- Для core/поведенческих изменений smoke/простые тесты недостаточны: обязателен local-first realism-контур (LLM + tools + chaos) до любых CI-выводов.

---

## 4) Question Gate

**Обязателен для Architect/Brain и рекомендуется всем.**

Перед тем как спрашивать:
1) Проверить репозиторий: `STATE.md`, `AGENTS.md`, `STRUCTURE.md`, `SPECS/*`, код.
2) Перед SSH проверить окружение: если `pwd` = `/home/zhan/truffles-main` и public IP совпадает с IP в `TECH.md` — ты уже на проде, SSH не нужен. Быстрая проверка: `hostname; whoami; pwd; curl -s https://ifconfig.me`.
3) Проверить факты в среде: docker/БД/CI/логи (если есть доступ — проверяй сам).
4) Если ответ найден — **не спрашивать**.
5) Если ответа нет — задать вопрос и зафиксировать GAP.

**Важно:** вопросы могут быть “простыми”. Главное — они по фактам.

---

## 5) Task Package (обязателен всегда)

**Без Task Package Hands работу не начинают.**

Минимум, который обязан быть в задаче:
1) **Invariant**: что не должно стать хуже (что защищаем).
2) **Scope / Out of scope**.
3) **Touch-list**: файлы/таблицы, которые можно менять.
4) **Plan**: шаги 1..N.
5) **DoD**: критерии приёмки.
6) **Checks**: тесты/команды (для новых фич — минимум один тест или waiver).
7) **Evidence**: что сохраняем (CI run URL + логи/SQL/trace) и кто фиксирует запись в `STATE.md` (Brain или Top Architect, до merge при изменениях поведения/core).
8) **Rollback**: как откатить.
9) **No-go**: что запрещено.
10) **Canon refs**: owner‑doc(и) + ссылка на `STATE.md` NOW/GAP; **CA_ID** если фикс закрывает CA‑пункт.
11) **Residual architecture debt (mandatory)**: что остаётся техническим долгом после блока и почему.
12) **Next-block contract (mandatory)**: точный следующий блок, его первый deterministic check и блокирующие условия.

Шаблон (копируй в задачу):
- Название/цель (1–2 предложения)
- Canon refs (owner‑doc + `STATE.md` NOW/GAP + CA_ID при наличии)
- Invariant
- Scope
- Out of scope
- Touch-list (файлы/таблицы)
- Plan (1..N)
- DoD
- Checks
- Evidence
- Rollback
- No-go
- Риски/блокеры
- Residual architecture debt (mandatory)
- Next-block contract (mandatory)

### 5.1 External Research Gate (обязательно)
- Для каждой нетривиальной реализации/фикса до начала кода обязателен **ровно один точный web-search**.
- Search фиксируется в Task Package секции `One web search (mandatory before implementation)`:
  - точная строка запроса,
  - дата/время,
  - открытые источники,
  - найденные готовые решения,
  - решение `reuse/integrate/build` и причина,
  - отклонённые варианты.
- Качество источников: минимум один источник должен быть из high-signal класса (официальная документация, стандарт, вендорный reference, primary source).
- Source quality фиксируется в том же разделе `One web search` (не допускается пустой список источников).
- Дополнительные query запрещены без явного согласования Brain/Top Architect и записи в TP.

### 5.2 Root Cause Gate (обязательно)
- Фиксы по поведению/надежности начинаются с root-cause, а не с симптома.
- В Task Package обязательна секция `Root cause (mandatory)`:
  - symptom,
  - minimal reproduction,
  - evidence,
  - Five Whys (или эквивалентная структурированная RCA),
  - root cause statement,
  - fix mechanism.
- Если root cause не доказан, статус блока = `BLOCKED` до фиксации гипотез и плана проверки.

### 5.3 Reuse-First Gate (обязательно)
- По умолчанию стратегия: **reuse -> integrate -> configure -> build**.
- Новая реализация допускается только после явной фиксации в TP, почему reuse/integration не подходят (функционал, лицензия, безопасность, производительность, платформенные ограничения).
- Конфигурация tenant/branch/env должна оставаться в data/config слоях; runtime-core hardcode запрещён.

### 5.4 Iteration Discipline Gate (обязательно)
- Каждый дорогой прогон (LLM quality/long suites/load) обязан иметь:
  - гипотезу,
  - ожидаемый измеримый эффект,
  - stop condition.
- Две подряд итерации без новой evidence => stop-the-line, возврат к RCA/research.
- Запрещено ослаблять acceptance-гейты/thresholds для «ускорения».

### 5.5 Context Continuity Gate (обязательно)
- В каждом TP обязательны секции:
  - `Residual architecture debt (mandatory)`:
    - `Current residuals accepted in this block`
    - `Why not in this block`
    - `Risk if deferred`
    - `Linked follow-up Task Package(s)`
    - `Expiry/trigger to stop deferral`
  - `Next-block contract (mandatory)`:
    - `Next block objective`
    - `First deterministic check command`
    - `Blocked-by conditions`
    - `Owner role for closure`
- Для новых сессий `context_integrity_gate` всегда создаётся как `required` через `scripts/session_start.sh`.
- В блоке нельзя закрывать задачу без явного follow-up TP ID, если residual-debt остаётся.

---

## 6) Stop-the-line (жёсткие запреты)

**Стоп немедленно, если:**
- CI красный (CI fail важнее локального pass).
- CI завис: нет новых логов >10 минут или workflow застрял в concurrency >10 минут → отменить run, зафиксировать как infra, перезапустить.
- Появились неожиданные файлы в diff.
- Нет tests + live-check + trace/meta там, где они обязательны.
- Есть предупреждения/ошибки в логах, которые мы игнорируем.
- Для "экономии времени/токенов" предлагается снизить acceptance-бар, отключить обязательный gate или ослабить контрактный oracle вместо исправления root cause.
- Для prod-impacting изменения отсутствует staged rollout/canary plan, go/no-go сигналы или проверяемый rollback путь.

**Пакет при CI fail (обязателен):**
- run URL
- failed job
- failed step
- 5–15 строк ошибки
- точная команда
- матрица окружения (OS/runtime)

**CI cheat (кратко):**
- PR → без deploy/livecheck; main → полный пайплайн; manual → `workflow_dispatch` с `run_long/run_livecheck` (см. `TECH.md` → CI).

**Запрещено:**
- менять БД/trace ради evidence (например, чистка `decision_trace`).
- подгонять поведение под тесты через хардкоды (EVAL = доказательство, не цель).
- “тихо” менять политику/обещания (REQUIREMENTS) без явного решения.
- подменять LLM-first семантику keyword/regex логикой в core вместо контрактных resolver/capability механизмов.
- использовать бюджетные ограничения как обоснование для архитектурного/продуктового downgrade.
- оставлять обходной путь в production как "временный" без owner, срока удаления и отдельного rollback-плана.

### 6.4 Release Safety Gate (обязательно)
- Любое prod-impacting изменение должно содержать `Release safety` в TP:
  - стратегия rollout (`canary`/`blue-green`/flags),
  - go/no-go сигналы,
  - rollback процедура и проверка.
- Продвижение rollout без фактических сигналов запрещено.
- При устойчивой деградации надежности (SLO/error-budget breach) feature rollout останавливается до восстановления baseline.

### 6.5 Runtime Hygiene Gate (обязательно)
- Цель: исключить накопление runtime-дублей/мусора, которые приводят к OOM, swap pressure и disk pressure.
- Перед cleanup обязателен baseline-срез evidence:
  - `date`
  - `free -h`
  - `df -h /`
  - `docker ps --format '{{.Names}}' | wc -l`
  - `docker system df`
- Разрешено удалять без отдельного эскалационного решения только stale runtime clones по шаблонам `^truffles-api-` и `^firebreak-hq1-runtime` (по умолчанию старше 48 часов), если это не противоречит активному TP.
- Удаление core-контейнеров (`truffles-api`, `truffles-postgres`, `truffles-redis`, `truffles-console-keycloak`, `truffles-prometheus`, `truffles-grafana`, `truffles-traefik`) без явного TP/owner-решения запрещено.
- Любой долгий prune (`docker image prune`, `docker builder prune`) запускается с `timeout` и логированием в файл; если операция зависла/нет прогресса более 10 минут — stop-the-line, зафиксировать как infra GAP.
- После cleanup обязателен post-state evidence тем же набором метрик + `docker image ls -f dangling=true -q | wc -l`.
- Профилактика обязательна:
  - ежедневный runtime hygiene job (stale clones + dangling images + journal vacuum),
  - еженедельный deep cleanup build cache.
- Канонический entrypoint: `/usr/local/bin/truffles-runtime-hygiene.sh`; cron-манифест: `/etc/cron.d/truffles-runtime-hygiene`.

### 6.1 Local-first validation law (обязательно)
- Любая правка core‑поведения сначала проходит локальный реалистичный контур; без этого PR/приёмка = BLOCKED.
- Порядок неизменный: `local realism` -> `local contract checks (deterministic boundaries)` -> `CI deterministic smoke`.
- CI не заменяет локальную проверку поведения; CI подтверждает воспроизводимость и ловит базовые регрессии.
- Если нет `OPENAI_API_KEY` (или явного `--judge-api-key`) для LLM quality, статус проверки = `BLOCKED`, а не “упрощённый pass”.
- Judge key: по умолчанию judge использует `OPENAI_API_KEY`; отдельный ключ задаётся `--judge-api-key`.
- Deterministic проверки обязаны защищать границы контракта, а не заменять собой semantic reasoning.

### 6.2 Локальный обязательный контур (core behavior)
- Не гоняй pytest внутри прод‑контейнера `truffles-api` с прод‑`.env`.
- Для контейнерных тестов используй `scripts/test_api_container.sh` (предпочтительно) или `docker compose ...docker-compose.test.yml`.
- Перед quality-прогоном обязателен preflight (`infra_valid=true`), затем semantic-контур.
- Минимальный обязательный набор для core‑правок:
  - `pytest -q truffles-api/tests/test_message_endpoint.py`
  - `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
  - `pytest -q truffles-api/tests/test_demo_salon_eval.py`
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id booking-lock-<id>`
- Для booking/e2e обязателен evidence не только по метрикам:
  - `decision_trace` c `booking_commit`/`booking_interrupt`,
  - `decision_meta` последнего inbound,
  - `appointment_id`/status и сохранность `specialist`.

### 6.3 Booking quality anti-drift loop (обязательно для bugfix)
**Ценность тестирования (зачем):**
- Мы тестируем не “чтобы получить красивые цифры”, а чтобы ловить реальные регрессии в core‑поведении.
- Сравниваем только сопоставимые прогоны, иначе метрики шумят и решения становятся случайными.
- Цель цикла: быстрый и доказуемый ответ на вопрос “правка улучшила поведение или нет”.

**Что делаем (как):**
1) **Lock-run (один раз):** фиксируем baseline с неизменными параметрами; принимаем только валидный run (`infra_valid=true`, `semantic_valid=true`, `judge.enabled=true`); сохраняем `scenarios.json`, `summary.json`, `brief.md`.
2) **Replay-run (на каждую правку):** запускаем только по lock-сценариям (`--scenarios-file`) и сравниваем только с lock-summary (`--baseline-summary`), с fail-fast (`--max-failures`) для скорости; обязательно `--reset-before-dialog`, чтобы не тянуть state/trace из прошлых прогонов.
3) **Handoff:** в session/STATE кладём `summary.json` + `brief.md` + top-failures + replay command.

**Короткая памятка (не нарушать):**
- Нельзя сравнивать прогоны с разными сценариями/seed/параметрами.
- Нельзя делать replay без `--reset-before-dialog` (иначе ложный дрейф из старых conversation/trace).
- Нельзя обновлять baseline маленькими случайными прогонами.
- Нельзя начинать новый фикс без `brief.md` от предыдущего прогона.
- Нельзя использовать `INVALID` run (`infra_valid=false`) для сравнения и baseline.
- Если реплей хуже baseline — stop-the-line, сначала root cause, потом новый фикс.
- Перед каждым новым run обязателен индекс артефактов и блокировка повторов:
  - все quality-прогоны фиксируются в `run_manifest.json` и индексе `/tmp/booking_quality/_index` (по часу и по типу `lock/replay/full`),
  - новый run запрещён, если предыдущий в том же режиме `incomplete/invalid/failed` или `manual_audit != done`,
  - запрещено повторять один и тот же run_id или fingerprint без явного forensic override.

**Командный шаблон (single entrypoint, без скрытого поиска):**
- acceptance lock: `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-<id> --pg-checklist /tmp/booking_quality/pg_checklist-<id>.json -- --base-url <url> --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- acceptance replay: `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-<id> -- --base-url <url> --client-slug demo_salon --scenarios-file /tmp/booking_quality/booking-lock-<id>/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-<id>/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
- acceptance full: `scripts/llm_quality_guarded.sh --mode full --run-id booking-full-<id> -- --base-url <url> --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-<id>/summary.json`
- post-run audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/<run-id> --status done --strict-artifacts`
- direct `python3 ops/diagnose.py llm-quality ...` разрешён только для `dev/forensic` и не является acceptance-evidence.
- отчёт по артефактам: `scripts/quality_artifact_report.py --hours 24 --show-commands`
- подробный SOP/quickstart (`lock/replay/full/resume/guard blocks`): `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` (section `Guarded llm-quality quickstart (single entrypoint)`).

**Локальные тесты:**
- локально запускаются в первую очередь и определяют качество поведения.
- CI и live-check идут после локального realism-контура и не могут его заменить.

**Гигиена проверки:**
- DoD для core‑поведения принимается только после локального полного контура + evidence (trace/meta/tool outcomes).
- После этого CI-run используется как подтверждение воспроизводимости и anti-drift.
- Не принимать DoD, если проверка делалась через `docker cp` или запуск контейнера с `-v` (исключения — только если это явно прописано в Task Package).


**Кто обновляет `STATE.md`:** **Brain и Top Architect**; для изменений поведения/core — **до merge в рамках PR**, плюс финальная запись в конце сессии.

---

## 7) Git / Branch / Worktree (обязательно)

- Один worktree/терминал = одна ветка. Не работать в чужой ветке.
- В Task Package обязательно указать: Branch, Worktree path, Base ref, Merge policy, Cleanup.
- Rebase запрещён; только merge из base.
- Любые неожиданные файлы/изменения → STOP и вопрос.
- Cleanup после merge делает Brain или Top Architect (удалить ветку + worktree).

### 7.1 Session log (обязательно)
- Каждая сессия фиксируется в `docs/SESSIONS/SESSION-<id>.md` и `docs/SESSION_INDEX.md` **до** начала правок.
- Task Package готов до старта сессии; без него `scripts/session_start.sh` не запускать.
- Старт сессии: `scripts/session_start.sh --session-id ... --task-package docs/TASK_PACKAGES/TP-....md` (создаёт worktree/branch + лог; Task Package должен существовать).
- Чтобы не копить незакомиченные session-артефакты, можно включать авто-коммит: `SESSION_AUTO_COMMIT=1 scripts/session_start.sh ...` (фиксирует session log + index в ветке).
- Если `docs/SESSION_INDEX.md` дрейфит/конфликтует — пересобрать его из `docs/SESSIONS/*` скриптом `scripts/session_index_rebuild.sh`.
- После compaction/амнезии: использовать `scripts/session_resume.sh` и продолжать в указанном worktree (новую сессию не создавать). Новый `session_start` разрешён только с `--force-new` и осознанным параллельным процессом.
- `session_id` обязателен и должен включать суффикс агента: `YYYY-MM-DD-<slug>-<agent>` (пример: `2026-01-27-contracts-a1`).
- `SESSION_AGENT` обязателен (например: `a1`, `a2`, `a3`). `session_start`/`session_resume`/`session_check` блокируют кросс‑агентные сессии.
- Для списка всех сессий использовать `scripts/session_resume.sh --all`; по умолчанию резюмируется только свой агент.
- Перед commit/push обязателен `scripts/session_check.sh` (хуки блокируют без него).
- Закрытие: `scripts/session_end.sh --status done` и cleanup worktree/branch.
- Коммит закрытия: `SESSION_ALLOW_DONE=1 git commit ...` (иначе pre-commit блокирует статус `done`).
- Статус `done` ставится **в том же коммите**, где внесены рабочие изменения. Отдельный commit/PR только ради закрытия запрещён. Для doc-only — один commit и fast-forward push в `main`.
- Неправильное закрытие ловит `scripts/session_audit.sh` → статус `needs_fix`.
- Doc-only fast path: разрешены только `docs/**`, `STATE.md`, `STRUCTURE.md`, `AGENTS.md`; такие изменения пушатся напрямую в `main` (fast-forward) без PR. PR допустим только при `ALLOW_DOC_ONLY_PR=1` (конфликты/исключения).
- Doc-only в `main` требует `docs/SESSIONS/*` + `docs/SESSION_INDEX.md` в том же коммите (session_check блокирует без них).

### 7.2 Research-gate adoption matrix (обязательно)
- Допустимые режимы для `research_gate`, `root_cause_gate`, `reuse_gate`, `release_safety_gate`, `context_integrity_gate`: `required | optional | off`.
- `required`: `session_check`/`session_gate` блокируют commit/push/CI при нарушении TP-контракта.
- `optional`: секции не блокируют поток, но учитываются в `session_audit` coverage.
- `off`: секция не проверяется.
- Новые сессии создаются с `required` по всем пяти gate-полям (через `scripts/session_start.sh`).
- Backward compatibility: если в legacy-сессии задан только `research_gate: required` без явных `root_cause/reuse/release`, применяется bundled enforcement как `required` для этих секций.
- Перевод legacy-сессий в `required` выполняется поэтапно: сначала обновление session metadata + TP, затем включение блокирующего режима.
- Контроль покрытия выполняется через `scripts/session_audit.sh` (сводка gate adoption обязательна в evidence для process-blocks).

---

## 8) Live-check протокол (WA/Telegram)

- Если у роли нет WA-клиента/allowlist → статус **BLOCKED** для live-outbound (сообщить сразу).
- **Исключение CA‑13:** допускается симуляция inbound (`/webhook` или instance→instance) при наличии inbound row в БД (decision_meta/trace) и заблокированном outbound; в `STATE.md` пометка `simulated`.
- Не просить Жанбола отправлять сообщения ради проверки.
- Live-check выполняют Hands/OPS с тестовым JID из allowlist‑пула (один suite → один JID).
- Sender‑JID для live‑check не должен совпадать с номером филиала; inbound от branch‑номеров игнорируется (анти bot‑to‑bot loop).
- Разрешена симуляция instance→instance при live‑check, **только если inbound реально записан в БД** (decision_meta/trace) и соблюдён safety‑контур; для CA‑13 — см. исключение выше.
- JID allowlist = тестовые WA‑номера; instance_id нужен только для ChatFlow send‑text (см. `SPECS/SYSTEM_REFERENCE.md`).
- Быстрый запуск: `ops/diagnose.py send-and-explain` (или `ops/chatflow_send.py` + `ops/diagnose.py explain`).

**Evidence live-check (минимум):**
- `conversation_id`
- фрагмент `decision_trace` (или ссылка/вывод команды)
- `decision_meta` на последнем inbound
- если есть outbox — статус (queued/sent/failed)

**Правило проверки:** текст ответа не сравниваем — только `decision_meta/trace` (см. `SPECS/SYSTEM_REFERENCE.md` §5.8.1).

---

## 9) Fitness Functions (инварианты, которые нельзя нарушать)

> Любая правка в core-пайплайне должна либо **сохранять** эти инварианты, либо **обновлять** их тесты сознательно.

### P0 — остановить “рефактор-петлю”
1) **`_legacy.py` = adapter-only** (запрет оркестрации/логики).
2) **Trace retention не выкидывает business-critical stages** (например, booking_interrupt/multi_truth).
3) **Gate must fire**: у каждой стадии из auto‑registry (из `_record_decision_trace` в коде) есть тест‑кейс или зафиксированный waiver.
4) **Routing token обязателен для multi-branch**: нет токена → безопасная деградация, не угадайка.
5) **Outbox idempotency + auto-heal**: повторный inbound не создаёт двойной send; stuck PROCESSING лечится.
6) **Media async send + signed URL + TTL**: manager→client медиа не блокирует webhook.

### P1 — качество и анти-дрейф
7) **Trace пишется на каждом раннем возврате** (preflight/dedupe/outbox/branch_selection/pending...).
8) **decision_meta обязателен** на user-сообщении (минимальная схема).
9) **policy rules-as-data**: строгая схема + валидные ссылки на секции/KB.
10) **env contract / fail-fast**: критичные env валидируются и отражаются в `/admin/health`.
11) **provider adapter contract tests + mock provider** (анти vendor lock-in на уровне логики).

### P2 — дисциплина команды
12) **No orchestration in entrypoints** (роутеры тонкие).
13) **Stage order snapshot** (порядок стадий меняется только сознательно).
14) **PR Task Package gate** (PR к core без Task Package не мержится).
15) **Local-first realism gate** (core‑поведение без локального LLM+tools+chaos evidence не принимается).

### P3 — semantic-first architecture
16) **Single semantic owner per turn** (policy-core LLM определяет смысл, downstream не переопределяет его произвольно).
17) **No business semantics in core regex/phrases** (доменные смыслы живут в packs/resolvers/capabilities).
18) **Deterministic boundaries only** (validation/safety/capability/idempotency/outbox, без semantic захвата маршрутизации).
19) **Graceful degrade observability** (каждый degrade имеет `reason_code` + trace/meta и учитывается в error budget, а не маскируется).
20) **No Budget-Driven Quality Downgrade** (бюджет не снижает acceptance-критерии и не меняет целевой контракт продукта).
21) **No Workaround-as-Architecture** (временный workaround не может становиться default-путем платформы).

### P4 — research-driven execution
22) **External Research Before Code** (до реализации есть 1 точный search + зафиксированное решение `reuse/integrate/build`).
23) **Root Cause Before Fix** (фиксы по надежности/поведению подтверждают механизм, а не только симптом).
24) **Reuse-First by Default** (новая реализация только при явном обосновании невозможности reuse/integration).
25) **Release Safety as Contract** (prod-impacting блоки без staged rollout + rollback + go/no-go не принимаются).

---

## 10) Архитектурная граница: “не перестраивай всю систему без DEC”

**Большие перестройки (например, Messaging Fabric / Provider Gateway как слой платформы) — только через DEC + новый DoD.**

Разрешено без DEC:
- refactor без изменения поведения,
- добавление/усиление fitness functions,
- стабилизация trace/meta/outbox/media/routing,
- улучшение SOP/диагностики.

Запрещено без DEC:
- “переписать всё красиво”,
- менять контракт стадий/решений без тестов и evidence.

---

## 11) Формат отчёта и приёмка

### 11.1 Что сдаёт Hands
В отчёте всегда:
- `git status -sb`
- `git diff --stat`
- Что изменили (1–3 bullets)
- Сводка строго по фактическому diff (никаких несвязанных изменений)
- Как проверили (команды)
- Evidence (CI run + кусок логов/SQL/trace)

### 11.2 Что проверяет Brain при приёмке (3 пункта)
1) **Гейты/безопасность** не нарушены (LAW/OOD/booking).
2) **Данные**: decision_meta/trace пишутся и валидны.
3) **Проверки**: есть локальный realism-контур (LLM+tools+chaos) + deterministic тесты + evidence; CI/live-check подтверждают, но не подменяют локальную проверку.

---

## 12) 5 ошибок, которые не повторять

1) **Экономлю на качестве.** Качество — константа.
2) **Гоняюсь за тенью.** Сначала проверить: это вообще правильный вопрос?
3) **Быстрые фиксы без причины.** Сначала WHY, потом HOW.
4) **Соглашаюсь со всем.** Если плохо — сказать прямо.
5) **Подгон под тесты/хардкод.** Логика единая; данные — только в packs.

---

## 13) Компания (для справки)

- ТОО "Truffles", БИН 230640035188
- Директор: Насурла Жанбол
- Telegram: @ent3rprise
- Тел: +7 775 984 19 26
