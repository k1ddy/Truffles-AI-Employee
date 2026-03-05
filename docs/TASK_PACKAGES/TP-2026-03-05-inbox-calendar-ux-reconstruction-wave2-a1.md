# TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE2-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE1-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE3-A1

## Название/цель
Довести UX вкладок `Заявки` и `Записи` до операционного уровня: убрать визуальный шум активной заявки, усилить календарь как очередь действий менеджера и упростить терминологию для не-технических пользователей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/utils/labels.ts`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Baseline findings`:
  - В календаре отсутствовал operator queue-toolbar (lane/filter/search), из-за чего triage был медленным.
  - В `Заявке` дублировались SLA-индикаторы, а верхний блок занимал первый экран.
  - UX-29..UX-33 были не полностью закрыты в action-first формате.

## One web search (mandatory before implementation)
- **Query (exact):** `salesforce quick actions implementation guide action labels minimalism best practices`
- **Date/time (local):** `2026-03-05T08:06:00+05:00`
- **Sources opened:**
  - `https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/actions_impl_guide.pdf`
- **Ready solutions found:**
  - Action labels должны быть task-oriented и короткими.
  - Action layout должен показывать только первичные действия.
  - Перегруженный action bar ухудшает скорость triage.
- **Decision (`reuse/integrate/build`):** `integrate` — применить принципы к существующим `Заявки/Записи` без новой top-level IA.
- **Rejected options:** отдельный новый модуль вместо доработки текущих вкладок.
- **Source quality:** high-signal primary source = official Salesforce documentation PDF.

## Root cause (mandatory)
- **Symptom:** менеджер тратит лишние клики и скролл в сценарии `Заявки -> Записи -> Заявки`.
- **Minimal reproduction:** открыть кейс с `needs_reply=true`, перейти в `Записи`, попытаться выделить срочные записи и вернуться к чату.
- **Evidence:** `calendar/page.tsx` (до wave2 не было queue-toolbar) + `CaseConversation.tsx` (до wave2 был избыточный верхний блок и дубли SLA).
- **Five Whys:**
  1. Почему медленный triage? Нет компактного operator filtering.
  2. Почему теряется фокус? В `Заявке` слишком много вторичных блоков до чата.
  3. Почему действия неочевидны? SLA/статусы читались как технические метки.
  4. Почему это осталось после wave1? Wave1 закрыл linkage, но не весь queue UX.
  5. Почему это бизнес-критично? Рост времени ответа и снижение конверсии заявка->запись.
- **Root cause statement:** после закрытия контрактной связки не хватало action-first operator UX в календаре и компактного first-screen в заявке.
- **Fix mechanism:** queue-toolbar + attention reasons + SLA/action simplification без изменения IA.

## Reuse-first plan (mandatory)
- **Reuse:** существующие `calendar`/`case` компоненты и текущий booking contract.
- **Integrate:** локальные queue-фильтры и action hints в действующие компоненты.
- **Build only if needed:** точечные элементы управления очередью, без новых страниц.

## Invariant
- Не добавлять новые top-level вкладки.
- Не ломать flow создания/изменения записей.
- Не вводить semantic hardcode в backend core policy.

## Scope
- `Записи`: queue toolbar (lane + status + search) и причины внимания по записи.
- `Заявки`: убрать SLA-дублирование и усилить action-first подсказку.
- Обновить e2e-проверку `inspect_case` для queue-controls.
- Зафиксировать факт-статус UX-29..UX-33.

## Out of scope
- Полная декомпозиция `calendar/page.tsx` на модули.
- Новые backend endpoints для bulk-операций.
- Изменение глобальной IA console.

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

## Plan (1..N)
1. Добавить queue filters и attention reasons в `calendar/page.tsx`.
2. Упростить SLA/action presentation в `CaseConversation.tsx`.
3. Унифицировать SLA/action copy в `labels.ts`.
4. Обновить `inspect_case.spec.ts` для новых queue-controls.
5. Прогнать lint + e2e и зафиксировать evidence.

## DoD
- В `Записях` triage возможен по action-режиму без перехода на другие экраны.
- В карточке записи видна причина внимания.
- В `Заявке` нет SLA-дублирования и чат доступен раньше по первому экрану.
- E2E `inspect_case` покрывает queue-controls.
- UX-29..UX-33 отражены fact-based статусами.

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseConversation.tsx --file src/utils/labels.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`

## Evidence
- Git diff по touch-list.
- Output checks.
- Скриншоты `case_inspection.png`, `calendar_case_context.png`.

## Release safety (mandatory)
- **Rollout:** без feature-флага в рамках текущих вкладок.
- **Go/no-go:** lint + `inspect_case` e2e green.
- **Rollback:** `git revert` block commit и повтор checks.

## Rollback
- `git revert REVISION_SHA`
- Повтор `npm run lint` + `playwright test`.

## No-go
- Добавление новой вкладки вместо оптимизации существующих.
- Дублирование одинаковых действий на экране.
- Ослабление acceptance-checks.

## Риски/блокеры
- Доступность `http://localhost:3100` для e2e.
- Необходимость обновления e2e-ожиданий после copy/layout изменений.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: формального backend queue-priority контракта пока нет.
- `Why not in this block`: wave2 закрывает UI/UX слой, не data-contract layer.
- `Risk if deferred`: часть решений остается эвристической при масштабировании очереди.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md`.
- `Expiry/trigger to stop deferral`: следующая P0 жалоба на SLA/priority semantics.

## Next-block contract (mandatory)
- `Next block objective`: wave3 — формализовать queue semantics и устранить эвристическую связь case-booking.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_openapi_calendar_contract.py tests/test_calendar_bookings_router.py tests/test_console_cases_helpers.py`
- `Blocked-by conditions`: wave2 evidence (lint + e2e + screenshots) должен быть сохранен и проверяем.
- `Owner role for closure`: Brain / Top Architect.
