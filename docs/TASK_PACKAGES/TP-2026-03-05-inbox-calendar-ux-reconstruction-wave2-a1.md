# TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE2-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE3-A1

## Название/цель
Довести UX вкладок `Заявки` и `Записи` до операционного уровня: убрать визуальный шум в активной заявке, усилить календарь как очередь действий менеджера и упростить терминологию для не-технических пользователей.

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
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/utils/labels.ts`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `Baseline findings`:
  - В календаре нет операторского queue-toolbar (поиск/lane/filter), из-за чего triage записей медленный.
  - В `Заявке` визуально дублируются SLA-индикаторы и вторичные блоки занимают первый экран.
  - UX backlog фиксирует UX-29..UX-33 как `Open`.

## One web search (mandatory before implementation)
- **Query (exact):** `salesforce quick actions implementation guide action labels minimalism best practices`
- **Date/time (local):** `2026-03-05T08:06:00+05:00`
- **Sources opened:**
  - `https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/actions_impl_guide.pdf`
- **Ready solutions found:**
  - Action labels должны быть task-oriented и короткими.
  - Minimalism в action layouts: только обязательные поля/кнопки.
  - Не перегружать action bar: ограниченный набор приоритетных действий.
- **Decision (`reuse/integrate/build`):** `integrate` — применить те же принципы к существующим `Заявки/Записи` (очередь действий, минимальные первичные действия, понятные labels) без добавления новых top-level разделов.
- **Rejected options:** полный редизайн в отдельный новый модуль (`build`) — слишком высокий риск и выход за текущий блок.
- **Source quality:** high-signal primary source = official Salesforce documentation PDF.

## Root cause (mandatory)
- **Symptom:** менеджер по-прежнему тратит лишние клики и скролл при переходе `Заявки -> Записи -> Заявки`, особенно в сценариях срочного triage.
- **Minimal reproduction:** открыть активную заявку с `needs_reply=true`, перейти в `Записи`, попытаться быстро выделить требующие действия записи и вернуться в чат.
- **Evidence:** текущий `calendar/page.tsx` (нет queue-toolbar) + `CaseConversation.tsx` (дубли SLA блоков и высокий верхний блок).
- **Five Whys:**
  1. Почему медленный triage? Нет компактного операторского фильтра записей на правой панели.
  2. Почему менеджер теряет фокус? На первом экране заявки есть избыточные индикаторы и вторичные блоки.
  3. Почему есть двусмысленность действий? SLA/статусы читаются как технические метки, а не как `что делать`.
  4. Почему это сохраняется после wave1? Wave1 закрыл связь и контракт, но не весь операторский queue UX.
  5. Почему это важно бизнесу? Повышает время ответа и снижает управляемость входящего спроса.
- **Root cause statement:** после закрытия контрактной связки не хватает action-first очереди в `Записях` и компактного first-screen режима в `Заявках`, что замедляет операторский цикл.
- **Fix mechanism:** внедрить queue-toolbar и attention lanes в календаре, убрать SLA-дублирование в заявке, сократить высоту верхней части кейса и унифицировать action labels.

## Reuse-first plan (mandatory)
- **Reuse:** текущие `calendar`/`case` компоненты и существующий контракт bookings.
- **Integrate:** добавить локальные queue-фильтры и action hints в текущие компоненты.
- **Build only if needed:** точечные UI элементы (`queue controls`) без новых страниц/роутов.

## Invariant
- Не добавлять новые top-level вкладки.
- Не ломать существующий flow создания/статусов записей.
- Не вводить semantic hardcode в backend core policy.

## Scope
- `Записи`: добавить queue toolbar (lane + status filter + search) и причины внимания по каждой записи.
- `Заявки`: убрать дублирование SLA badge/countdown и усилить action-first подсказку менеджеру.
- Обновить e2e-спек для проверки новых queue controls в live/mocks режимах.
- Зафиксировать статус по UX backlog пунктам UX-29..UX-33.

## Out of scope
- Полный page decomposition `calendar/page.tsx` (вынос в модули отдельно).
- Новые backend endpoints для bulk-операций.
- Изменение глобальной IA console.

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Plan (1..N)
1. Добавить queue helpers/filters и attention reasons в `calendar/page.tsx`.
2. Упростить SLA/action presentation в `CaseConversation.tsx`.
3. Обновить SLA-label copy в `labels.ts` для единообразного action языка.
4. Обновить `inspect_case.spec.ts` для проверки queue-controls.
5. Обновить evidence в session log и backlog statuses.
6. Прогнать lint + e2e inspect-case.

## DoD
- В `Записях` оператор может фильтровать очередь по action-режиму без перехода на другие страницы.
- В карточке записи явно показано, почему запись требует внимания.
- В `Заявке` убрано SLA-дублирование и усилен первый action hint.
- E2E `inspect_case` проверяет новые queue controls.
- UX backlog статусы UX-29..UX-33 обновлены fact-based (fixed/mitigated/open).

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseConversation.tsx --file src/utils/labels.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts`

## Evidence
- Git diff по touch-list.
- Output checks.
- Обновленные screenshot artifacts (`case_inspection.png`, `calendar_case_context.png`) из e2e прогона.

## Release safety (mandatory)
- **Rollout:** без флага, в текущих вкладках `Заявки/Записи`.
- **Go/no-go:** lint + inspect_case e2e green.
- **Rollback:** `git revert` block commit и повтор checks.

## Rollback
- `git revert REVISION_SHA`
- Повтор `npm run lint` + `playwright test`.

## No-go
- Добавление новой вкладки/раздела вместо оптимизации существующих.
- Дублирование одинаковых действий в разных местах экрана.
- Ослабление acceptance-checks ради скорости.

## Риски/блокеры
- Playwright зависит от доступности `http://localhost:3100`.
- Текстовые изменения могут потребовать обновления снимков/ожиданий e2e.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `calendar/page.tsx` остается монолитным компонентом.
- `Why not in this block`: приоритет — UX оператора и завершение action-first flow.
- `Risk if deferred`: усложнение будущих расширений queue/bulk-операций.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1`.
- `Expiry/trigger to stop deferral`: любое изменение календаря в >3 отдельных зонах.

## Next-block contract (mandatory)
- `Next block objective`: декомпозировать `calendar/page.tsx` на queue/create modules + добавить contract tests по operator lanes.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/app/calendar/page.tsx`
- `Blocked-by conditions`: wave2 checks + e2e artifacts должны быть green и приложены.
- `Owner role for closure`: Brain / Top Architect.
