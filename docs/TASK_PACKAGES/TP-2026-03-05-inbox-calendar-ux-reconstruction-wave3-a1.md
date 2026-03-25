# TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE3-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE2-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE4-A1

## Название/цель
Закрыть backend/data-contract пробелы между `Заявки` и `Записи`: формализовать queue semantics, убрать эвристическую связку кейса и записи и обеспечить масштабируемый triage через server-side фильтры и пагинацию.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/models/appointment.py`
  - `truffles-api/app/models/handover.py`
  - `truffles-api/app/routers/calendar.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `truffles-api/tests/test_calendar_bookings_router.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/components/CaseList.tsx`
- `Baseline findings`:
  - В `appointments` нет явного `case_id`, часть связки держится на `conversation_id` и выборе "последнего кейса".
  - `GET /calendar/bookings` возвращает list-only ответ без cursor/has_more.
  - SLA/priority в кейсе не имеет формального server-side контракта (`due_at/priority_tier/reason_code`).

## One web search (mandatory before implementation)
- **Query (exact):** `Dynamics 365 Customer Service SLA KPI due date queue prioritization assignment`
- **Date/time (local):** `2026-03-05T09:37:36+05:00`
- **Sources opened:**
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-service-level-agreements`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/queues-omnichannel`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-assignment-rules`
- **Ready solutions found:** SLA/priority должны храниться как формальный контракт с due-time и routing priority, а не только как текстовые ярлыки в UI.
- **Decision (`reuse/integrate/build`):** `integrate` — расширить текущие модели/контракты и существующие endpoints вместо отдельного scheduling модуля.
- **Rejected options:** хранить приоритет только в UI state без backend контракта.
- **Source quality:** high-signal primary source = official Microsoft Learn documentation.

## Root cause (mandatory)
- **Symptom:** после UI-улучшений оператор все еще не имеет надежного backend-сигнала "что делать первым".
- **Minimal reproduction:** несколько кейсов и записей с разной срочностью; triage зависит от ручной оценки и возрастных меток.
- **Evidence:** отсутствуют поля queue-priority в case read-model и cursor-pagination в bookings.
- **Five Whys:**
  1. Почему срочность неоднозначна? Нет единого backend контракта приоритета/дедлайна.
  2. Почему связь кейс-запись иногда неточна? Связка частично эвристическая.
  3. Почему падает управляемость при росте очереди? Нет серверных lane-фильтров и cursor-выдачи.
  4. Почему менеджер видит "непонятные цифры"? UI вынужден компенсировать отсутствие контрактного action signal.
  5. Почему это бизнес-критично? Растет риск пропуска важных клиентов и падает SLA-предсказуемость.
- **Root cause statement:** отсутствует контрактный слой operator queue semantics и строгая linkage-модель case-booking.
- **Fix mechanism:** ввести case-linked booking model + queue priority projection + server-side фильтрацию и курсоры.

## Reuse-first plan (mandatory)
- **Reuse:** текущие таблицы `handover_cases/appointments`, роуты `console/calendar`, существующий UI queue layout wave2.
- **Integrate:** добавить недостающие поля и query-параметры в существующие контракты.
- **Build only if needed:** только необходимые миграции, read-model поля и contract tests.

## Invariant
- Не меняем semantic ownership policy-core.
- Не добавляем новые top-level вкладки.
- Не ломаем совместимость существующих flows создания/изменения записи.

## Scope
- Backend модель:
  - добавить `appointments.case_id` (nullable + index) и запись явной связи при create/update booking.
  - добавить queue/read-model поля в case response: `priority_tier`, `attention_reason`, `target_response_at`.
- Backend API:
  - добавить server-side фильтры/сортировку для `GET /calendar/bookings` (`lane`, `status`, `needs_action`, `case_id`, `conversation_id`).
  - добавить cursor-pagination (`cursor`, `has_more`) в контракт списка записей.
- Frontend consume:
  - перевести `calendar/page.tsx` и `CaseList.tsx` на новые поля и server-side queue-mode.
- Контрактные тесты:
  - обновить/добавить API + OpenAPI + router tests по новым полям/фильтрам.

## Out of scope
- Realtime transport (SSE/WebSocket).
- Полная декомпозиция больших frontend файлов.
- Массовые bulk-операции записей.

## Touch-list
- `truffles-api/app/models/appointment.py`
- `truffles-api/app/models/handover.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `truffles-api/tests/test_calendar_bookings_router.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/CaseList.tsx`

## Plan (1..N)
1. Добавить миграцию и model-слой для `appointments.case_id` + backfill-safe поведение.
2. Расширить case/bookings контракты queue fields + cursor.
3. Внедрить server-side queue filters и deterministic сортировку.
4. Обновить frontend consume новых контрактов.
5. Обновить contract tests и targeted UI checks.
6. Подготовить evidence и передать контракт в wave4.

## DoD
- Каждая запись имеет явную связь с кейсом (`case_id`) либо явно помечена как orphan с reason.
- `GET /calendar/bookings` поддерживает cursor-pagination и server-side queue filtering.
- Queue-priority и attention reason выдаются backend контрактно, а не формируются только в UI.
- Frontend queue mode использует серверные фильтры без regressions.
- OpenAPI/router tests green и отражают новые поля.

## Checks
- `cd truffles-api && pytest -q tests/test_console_openapi_calendar_contract.py tests/test_calendar_bookings_router.py tests/test_console_cases_helpers.py`
- `cd truffles-api && pytest -q tests/test_calendar_noshow_followup_router.py`
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseList.tsx`

## Evidence
- Миграция + diff по touch-list.
- Output checks.
- Пример API ответа `calendar/bookings` с `cursor/has_more/case_id`.
- Скриншот queue mode после переключения на server-side filters.

## Release safety (mandatory)
- **Rollout:** staged rollout по филиалам (canary 1 branch -> 25% -> 100%).
- **Go/no-go:** contract tests + no regression в `inspect_case` + корректный backfill.
- **Rollback:** откат миграции и revert PR с сохранением совместимости старого ответа.

## Rollback
- Revert wave3 PR.
- Откат миграции `appointments.case_id` по approved rollback-сценарию.
- Повтор checks для подтверждения baseline.

## No-go
- Оставить эвристическую связь как основной прод-путь.
- Ввести queue priority только визуально без backend поля.
- Merge при failing contract tests.

## Риски/блокеры
- Сложность безопасного backfill исторических appointments.
- Риск рассинхронизации UI и API при частичном rollout.
- Риск увеличения latency при новых server-side фильтрах без индексов.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: realtime push и единый action audit еще не реализованы.
- `Why not in this block`: wave3 закрывает контракт и данные; transport/observability вынесены в wave4.
- `Risk if deferred`: UI остается на polling и может отставать при пиковых нагрузках.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`.
- `Expiry/trigger to stop deferral`: рост queue lag > 5s на боевом canary.

## Next-block contract (mandatory)
- `Next block objective`: wave4 — realtime updates + observability + production rollout safety.
- `First deterministic check command`: `cd console-web && INSPECT_CASE_USE_MOCKS=0 PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`
- `Blocked-by conditions`: wave3 API contracts/migrations должны быть полностью green и зафиксированы evidence.
- `Owner role for closure`: Brain / Top Architect.
