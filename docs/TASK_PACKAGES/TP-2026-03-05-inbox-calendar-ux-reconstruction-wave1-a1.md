# TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE1-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE2-A1

## Название/цель
Капитально улучшить UX и бизнес-логику вкладок `Заявки` и `Записи`: связать их в единый рабочий поток менеджера, убрать вводящие в заблуждение SLA-ярлыки, уменьшить лишний скролл и добавить понятные действия без дублирования функций.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/calendar.py`
  - `truffles-api/app/services/appointment_service.py`
  - `truffles-api/app/models/handover.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/utils/labels.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Календарь (`Записи`) не содержал контекстного возврата к заявке и не использовал `conversation_id` для фильтрации очереди.
  - Бэкенд принимал `conversation_id` в `BookingCreate`, но выдача bookings не возвращала `conversation_id/case_id`.
  - В `Заявках` большой блок контекста/аутрича до чата увеличивал скролл до рабочего содержимого.
  - SLA-лейблы вида `В норме / До внимания: 59м / На связи 1м` не объясняли операторское действие.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk agent workspace omnichannel routing best practices for reducing context switching between tickets and scheduling`
- **Date/time (local):** `2026-03-05T07:10:03+05:00`
- **Sources opened:**
  - `https://www.zendesk.com/service/agent-workspace/`
  - `https://www.zendesk.com/service/features/omnichannel-routing/`
  - `https://support.zendesk.com/hc/en-us/articles/4408821224858`
- **Ready solutions found:** единый агентский workspace, контекстные переходы без потери текущего кейса, приоритизация очереди по action-driven статусам вместо абстрактных time-only меток.
- **Decision (`reuse/integrate/build`):** `integrate` — внедрить в текущие вкладки связанный workflow `case-booking` и action-driven SLA copy, без добавления новой вкладки.
- **Rejected options:** отдельный новый модуль/вкладка для "диспетчеризации".

## Root cause (mandatory)
- **Symptom:** менеджер делал лишние переходы между `Заявками` и `Записями`, терял контекст и тратил время на чтение непонятных статусов.
- **Minimal reproduction:** открыть кейс в `Заявках`, затем перейти в `Записи`; отсутствуют прямые контекстные ссылки/фильтры и нельзя быстро вернуться к кейсу/чату.
- **Evidence:** текущие контракты API и UI-поток из FACT pre-check.
- **Five Whys:**
  1. Почему лишние переходы? Нет контрактной связи кейса и брони в выдаче `bookings`.
  2. Почему нет связи в UI? `calendar` не получал/не отображал `conversation_id` и `case_id`.
  3. Почему менеджер скроллил вниз в `Заявках`? Первый экран был перегружен вторичными блоками до чата.
  4. Почему SLA вводил в заблуждение? Лейблы ориентировались на минуты, а не на действие и приоритет.
  5. Почему это критично? Падала скорость обработки лидов и рос риск неверных действий.
- **Root cause statement:** контракты и UI не реализовывали единый action-driven workflow по кейсу/броне.
- **Fix mechanism:** расширить booking read-model (`conversation_id`, `case_id`), добавить фильтр/переходы между вкладками, упростить SLA copy и сократить первый скролл.

## Reuse-first plan (mandatory)
- **Reuse:** текущие роуты `calendar`, `cases`, существующие компоненты Inbox/Calendar, текущие e2e-спеки.
- **Integrate:** добавить недостающую связку и action copy в существующие экраны.
- **Build only if needed:** новые поля ответа и минимальная UI-панель контекста в календаре.

## Invariant
- Никаких semantic hardcode в core/runtime policy.
- `Заявки` остаются источником чата/кейса, `Записи` остаются источником бронирований.
- Улучшения не ломают сценарии создания/редактирования записи.

## Scope
- Добавить `conversation_id` и `case_id` в booking response.
- Добавить фильтр `conversation_id` в `GET /calendar/bookings`.
- Добавить двустороннюю навигацию между `Заявки` и `Записи`.
- Упростить SLA-лейблы на action-language.
- Свернуть вторичные блоки в `Заявках`, чтобы чат был выше в первом экране.
- Сделать screenshot-based проверку UI.

## Out of scope
- Полный редизайн всех вкладок console-web.
- Изменение доменной модели booking beyond linkage fields.
- Новые top-level разделы навигации.

## Touch-list
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`

## Plan (1..N)
1. Расширить backend read-contract по booking linkage + фильтр по `conversation_id`.
2. Обновить frontend API-потребление и добавить context banner/return actions в `calendar`.
3. Обновить `Inbox` layout: чат выше, вторичные блоки collapse by default.
4. Переписать SLA copy на action-language без двусмысленных time-фраз.
5. Добавить/обновить e2e снимки (`Заявки`, `Записи`, переходы).
6. Прогнать targeted тесты и зафиксировать evidence.

## DoD
- Менеджер может из `Заявки` открыть релевантные `Записи` по кейсу и вернуться назад.
- В `Записях` виден и используется контекст кейса (`conversation_id/case_id`).
- Первый экран `Заявки` не требует прокрутки для чтения чата.
- SLA лейблы объясняют действие (что делать), а не только время.
- Цепочка тестов и скриншоты подтверждают отсутствие регрессии.

## Checks
- `cd truffles-api && pytest -q tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && pytest -q tests/test_calendar_noshow_followup_router.py`
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/utils/labels.ts`
- `cd console-web && npx playwright test e2e/inspect_case.spec.ts`

## Evidence
- Git diff по touch-list.
- Output checks.
- Скриншоты Playwright после изменений с `inbox` + `calendar` и переходами.

## Release safety (mandatory)
- **Rollout:** без feature-флага, но в рамках существующих экранов и контрактно-совместимого API-расширения.
- **Go/no-go:** зеленые targeted tests + e2e + визуальная проверка скриншотов.
- **Rollback:** revert commit блока и повтор checks.

## Rollback
- `git revert REVISION_SHA` в рабочей ветке и повторный прогон checks.

## No-go
- Добавление новой вкладки без явной необходимости.
- Дублирование одинаковых действий в `Заявках` и `Записях`.
- Снижение quality gates ради скорости.

## Риски/блокеры
- Возможная зависимость e2e от живого окружения/данных.
- Возможные ожидания старого SLA текста в существующих тестах.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: календарный экран все еще совмещает создание записи и очередь в одном компоненте.
- `Why not in this block`: цель wave1 — связка и UX-поток, а не полная декомпозиция страницы.
- `Risk if deferred`: сложнее безопасно расширять advanced-фильтры и bulk-операции.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md`.
- `Expiry/trigger to stop deferral`: при следующем изменении calendar UI более чем в 3 зонах.

## Next-block contract (mandatory)
- `Next block objective`: wave2 — добавить operator queue toolbar и убрать остаточный визуальный шум активной заявки.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseConversation.tsx --file src/utils/labels.ts`
- `Blocked-by conditions`: wave1 e2e/скриншоты и API contract checks должны быть green.
- `Owner role for closure`: Brain / Top Architect.
