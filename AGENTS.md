# AGENTS — Принципы работы (Truffles)

**Читай это первым. Каждую сессию.**

Цель этого файла: чтобы **люди и агенты** работали одинаково: *без догадок*, *без god-файлов*, *без «рефакторим всю систему»*, *с доказательствами*.

---

## 0) Truffles в одной формуле

**Truffles = Deterministic Core (факты/правила/решения) + LLM (смысл/язык) + Escalation (человек) + Data in KZ**.

**Контракт продукта (каждое user-сообщение должно привести к одному исходу):**
- **FACT** — короткий ответ строго из data packs (truth-first).
- **COLLECT** — сбор слотов/контактов/предпочтений (lead/booking).
- **HANDOFF** — передача человеку с прозрачным статусом (pending/manager_active).

**Escalation — не провал.** Это продукт внутри продукта (очередь, статусы, SLA, модерация, обучение).

---


## 0.1 Проект (что продаем)

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

---

## 6) Stop-the-line (жёсткие запреты)

**Стоп немедленно, если:**
- CI красный (CI fail важнее локального pass).
- CI завис: нет новых логов >10 минут или workflow застрял в concurrency >10 минут → отменить run, зафиксировать как infra, перезапустить.
- Появились неожиданные файлы в diff.
- Нет tests + live-check + trace/meta там, где они обязательны.
- Есть предупреждения/ошибки в логах, которые мы игнорируем.

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

**Локальные тесты:**
- локально можно запускать для скорости,
- **но** “принято” считается только после CI и/или согласованного live-check.

**Гигиена проверки:**
- DoD принимается только после CI-run (или локальной сборки образа) + рестарта контейнеров и проверки через `docker exec`.
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
- После compaction/амнезии: использовать `scripts/session_resume.sh --agent <suffix>` или `--session-id <id>` и продолжать в указанном worktree (новую сессию не создавать).
- `session_id` обязателен и должен включать суффикс агента: `YYYY-MM-DD-<slug>-<agent>` (пример: `2026-01-27-contracts-a1`).
- Перед commit/push обязателен `scripts/session_check.sh` (хуки блокируют без него).
- Закрытие: `scripts/session_end.sh --status done` и cleanup worktree/branch.
- Коммит закрытия: `SESSION_ALLOW_DONE=1 git commit ...` (иначе pre-commit блокирует статус `done`).
- Статус `done` ставится **в том же коммите**, где внесены рабочие изменения. Отдельный commit/PR только ради закрытия запрещён. Для doc-only — один commit и fast-forward push в `main`.
- Неправильное закрытие ловит `scripts/session_audit.sh` → статус `needs_fix`.
- Doc-only fast path: разрешены только `docs/**`, `STATE.md`, `STRUCTURE.md`, `AGENTS.md`; такие изменения пушатся напрямую в `main` (fast-forward) без PR. PR допустим только при `ALLOW_DOC_ONLY_PR=1` (конфликты/исключения).
- Doc-only в `main` требует `docs/SESSIONS/*` + `docs/SESSION_INDEX.md` в том же коммите (session_check блокирует без них).

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
3) **Проверки**: есть tests + live-check + evidence.

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
