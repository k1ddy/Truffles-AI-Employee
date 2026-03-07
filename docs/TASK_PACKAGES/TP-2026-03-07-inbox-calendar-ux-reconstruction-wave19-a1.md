# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE18-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE20-A1, CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE21-A1, CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1

## Название/цель
Зафиксировать новую семантическую модель вкладки `Заявки` как единого operator workspace, связанного с ботом, менеджером и календарём `Записи`. Цель блока — перевести требования Owner в явный продуктовый контракт: откуда появляется заявка, что именно должен понять менеджер, как это связано с записью клиента, как это закрывается и как попадает в историю/архив.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: docs-only planning block; implementation goes through follow-up wave PRs
- `Cleanup`: Brain / Top Architect after closure of follow-up implementation waves

## FACT pre-check (before implementation)
- `Заявки` по-прежнему ориентированы в первую очередь на open-queue, а не на полную операционную цепочку `bot -> case -> manager -> booking -> archive/history`: `console-web/src/components/CaseList.tsx:255`, `console-web/src/lib/inbox-case-filters.ts:70`, `truffles-api/app/routers/console.py:9016`.
- Доступ к закрытым и старым заявкам не вынесен в first-screen contract; `resolved` и `all statuses` спрятаны в advanced-слой вместо того, чтобы быть частью основной рабочей модели: `console-web/src/components/CaseList.tsx:1278`.
- Семантическая связь заявки с календарём уже существует на уровне `case_id` и context-navigation, но операторская панель ещё не выражает всю причинно-следственную цепочку, по которой заявка появилась из поведения бота и привела к записи/изменению записи: `console-web/src/components/CaseConversation.tsx`, `console-web/src/components/CaseBookingsPanel.tsx`, `truffles-api/app/models/appointment.py`.
- Вкладка не различает явно два разных режима работы: `операционная очередь` и `история/архив`, поэтому менеджер и администратор получают конфликтующую UX-модель.

## One web search (mandatory before implementation)
- **Query (exact):** `site:knowledge.hubspot.com help desk search for tickets status owner closed tickets and site:support.atlassian.com jira service management what are queues`
- **Date/time (local):** `2026-03-07T10:05:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/search-for-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- **Ready solutions found:** лидирующие helpdesk-системы всегда разделяют `views/queues` и `filters`, держат `status/owner/search` на первом экране, а историю/закрытые заявки не прячут за второстепенным disclosure-control.
- **Decision (`reuse/integrate/build`):** `integrate` — сохранить текущие маршруты и уже реализованную связку `Заявки ↔ Записи`, но пересобрать продуктовую модель панели так, чтобы она явно отражала полную цепочку обработки заявки и истории.
- **Rejected options:** лечить проблему ещё одной локальной правкой фильтров; оставлять `history/archive` как скрытое состояние advanced-панели; решать это только стилями.
- **Source quality:** high-signal primary sources = official HubSpot, Atlassian, Zendesk docs.

## Root cause (mandatory)
- **Symptom:** менеджер и администратор не могут предсказуемо работать со всей жизнью заявки — от эскалации бота до записи клиента и закрытия/повторного открытия — потому что панель `Заявки` показывает только часть операционного контура.
- **Minimal reproduction:** открыть `Заявки`, попытаться понять, откуда взялась заявка, что уже сделал бот, есть ли связанная запись, как найти закрытую или старую заявку, и как вернуться из истории обратно в операционный режим без потери контекста.
- **Evidence:** `console-web/src/components/CaseList.tsx:255`, `console-web/src/components/CaseList.tsx:1278`, `console-web/src/lib/inbox-case-filters.ts:70`, `truffles-api/app/routers/console.py:9016`, `truffles-api/app/schemas/console.py:1010`.
- **Five Whys:**
  1. Почему панель ощущается неполной? Потому что она построена как queue rail, а не как полный operator workspace.
  2. Почему это ломает бизнес-логику? Потому что `case` на платформе — это не просто чат, а ручной контур после действий бота, часто связанный с записью клиента.
  3. Почему менеджер теряет нить? Потому что интерфейс не показывает ясно, где `операционная работа сейчас`, где `история`, где `результат работы бота`, где `результат по записи`.
  4. Почему фильтр-фиксы не решают это полностью? Потому что проблема не только в фильтрах, а в информационной архитектуре и state model всей вкладки.
  5. Почему это приводит к багам и ложным состояниям? Потому что система не ограничивает forbidden states на уровне общей semantic chain.
- **Root cause statement:** `Заявки` ещё не оформлены как единый семантический рабочий экран, связанный с ботом, ручной обработкой менеджера, календарём записей и архивной историей; из-за этого UI и state transitions противоречат реальной бизнес-цепочке.
- **Fix mechanism:** сначала зафиксировать общую semantic model и atomic decomposition, затем реализовать отдельными wave-блоками `operator IA`, `cross-surface case-booking chain` и `forbidden-state validation`.

## Reuse-first plan (mandatory)
- **Reuse:** текущий case model, booking linkage, open/queue semantics, case action endpoints, workspace navigation.
- **Integrate:** явная information architecture поверх уже реализованных surface и backend contracts.
- **Build only if needed:** новые backend list params/history fields только там, где текущего контракта недостаточно для истории и бесшовной связи с календарём.

## Invariant
- Нельзя сломать уже реализованную связку `Заявки ↔ Записи`.
- Нельзя терять факт, что заявка появляется как следствие поведения бота и ручного handoff.
- Нельзя вводить новый UI, который допускает скрытые или противоречивые состояния между case, booking и archive/history.

## Scope
- Раскрыть общую идею и semantic chain продукта для `Заявки`.
- Разложить remaining work на атомарные implementation blocks.
- Зафиксировать forbidden states и cross-surface invariants.

## Out of scope
- Реализация продуктовых изменений в этом блоке.
- Новый route-level redesign всей console вне `Заявки/Записи`.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Semantic chain contract (mandatory)
1. `Бот -> Заявка`
- заявка возникает как результат неудачного/неполного автоматического решения или явного handoff;
- менеджер должен видеть, что уже сделал бот, чего не хватает, и какой следующий шаг ожидается.

2. `Заявка -> Работа менеджера`
- менеджер работает не с абстрактным чатом, а с операционной задачей;
- UI обязан показывать: owner, next action, текущий этап, связь с записью, историю решения.

3. `Заявка -> Запись`
- если разговор привёл к записи, это не отдельная несвязанная сущность;
- booking status и case status должны объяснять друг друга, а не жить в разных мирах.

4. `Закрытие -> История`
- закрытая заявка не исчезает из операционной модели;
- она должна быть доступна как history/archive mode с предсказуемым поиском и сортировкой.

5. `Переоткрытие / изменение записи`
- reopen, reschedule, cancel, no-show follow-up не должны рвать цепочку case-booking-history;
- система обязана исключать ложные переходы и silent resets.

## Manager/Admin convenience model (mandatory)
- `Менеджер`:
  - first-screen: `Открытые / Закрытые / Все`, поиск, ответственный `Мои/Все`, текущий next action;
  - внутри заявки: чат, текущий business state, booking context, безопасные действия, история.
- `Администратор / supervisor`:
  - всё выше + доступ к чужим владельцам, `без владельца`, history/archive lookup, supervisor slices, контроль повторных открытий и проблемных записей.

## Forbidden states (mandatory)
- `queue view` применяется поверх `Закрытые` или `Все` как будто это open queue.
- Case закрыта, но booking остаётся в активном требующем внимания состоянии без объяснимого статуса.
- Booking изменена/отменена, а case/business status не отражает это изменение.
- Reopen делает case активной, но история/owner/SLA/booking-context теряются или противоречат друг другу.
- Роль менеджера видит/эмитит supervisor-only filters.
- История заявок зависит от скрытого advanced-toggle и кажется «пустой» при реальном наличии данных.

## Required follow-up decomposition (mandatory)
- `Wave20` — `Inbox Panel IA + Modes`
  - first-screen `Открытые / Закрытые / Все`
  - queue views only for open-mode
  - explicit filter drawer
  - archive/history cards and sort model
- `Wave21` — `Cross-surface Semantic Integration`
  - заявка как продолжение действий бота
  - case/booking/status chain
  - бесшовные переходы и общий смысл между `Заявки` и `Записи`
- `Wave22` — `Forbidden-state Prevention + Acceptance Matrix`
  - deterministic matrix по allowed/forbidden states
  - live validation без fake-pass
  - regression-proof contract для manager/admin scenarios

## Plan (1..N)
1. Обновить master TP под новую semantic model.
2. Создать atomic follow-up TPs (`Wave20`, `Wave21`, `Wave22`).
3. Перевести session canon на новый planning block.
4. После согласования начинать реализацию только по follow-up implementation TP.

## DoD
- Общая идея Owner раскрыта в явной semantic chain.
- Remaining work разделён на атомарные, полнообъёмные implementation blocks.
- Для каждого follow-up блока зафиксирован scope, DoD, forbidden states и next-block linkage.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Semantic chain contract|Forbidden states|Required follow-up decomposition" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- Git diff по docs touch-list.
- Session log with updated active TP.

## Rollback
- `git checkout -- docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- revert linked master/session doc updates

## No-go
- Продолжать UX-polish без общей semantic model.
- Реализовывать history/archive отдельно от case-booking chain.
- Считать вкладку `Заявки` просто списком чатов.

## Риски/блокеры
- Current `Wave18` PR fixes correctness, but not the full semantic operating model.
- Implementation can drift again if `Wave20/21/22` are mixed into one oversized PR.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: product implementation is still pending.
- `Why not in this block`: this is the decomposition/contract block required before safe implementation.
- `Risk if deferred`: any further spot-fix risks repeating the same architectural mistake.
- `Linked follow-up Task Package(s)`: `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`, `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`, `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`.
- `Expiry/trigger to stop deferral`: no further inbox UX/code changes without choosing one of the linked follow-up TPs.

## Next-block contract (mandatory)
- `Next block objective`: implement first-screen operator IA for `Заявки` with explicit `Открытые / Закрытые / Все` and separate queue/history semantics.
- `First deterministic check command`: `cd console-web && rg -n "Открытые|Закрытые|Все" src/components/CaseList.tsx`
- `Blocked-by conditions`: none after Wave18 merged via `PR #940`; Wave20 is the active implementation block.
- `Owner role for closure`: Brain / Top Architect.
