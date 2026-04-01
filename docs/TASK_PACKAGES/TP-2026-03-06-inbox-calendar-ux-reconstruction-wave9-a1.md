# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-PARTB-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-PARTB-A1

## Название/цель
Сделать очередь в `Заявках` управляемой для supervisor/admin и понятной для менеджера на масштабе: добавить role-aware queue views и настраиваемые поля списка, не создавая новый экран и не дублируя существующие фильтры.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: continue inside existing PR `#932`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/lib/inbox-workspace.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - `CaseList.tsx` already has search, status, sort, bulk actions and advanced filters, but у него нет operator-grade quick views для supervisor/admin.
  - Вид списка сохраняется на 24 часа, но сохраняются только базовые фильтры; named queue view и отображаемые поля не фиксируются как workspace preference.
  - Compact queue card показывает фиксированный набор метаданных, поэтому supervisor не может быстро переключить акцент на владельца/канал/активность без перегруза интерфейса.
  - Table layout уже содержит owner/channel/activity columns, но ими нельзя управлять через UI и они не адаптированы под разные роли.

## One web search (mandatory before implementation)
- **Query (exact):** `HubSpot help desk views official documentation`
- **Date/time (local):** `2026-03-06T11:12:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/create-and-manage-help-desk-views`
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
- **Ready solutions found:** зрелые help desk queues используют сохранённые views для типовых операционных наборов и дают агенту возможность настраивать видимые поля без перехода в отдельный админ-экран.
- **Decision (`reuse/integrate/build`):** `integrate` — встроить quick views и field toggles прямо в текущий `CaseList`, переиспользуя существующие фильтры и workspace persistence.
- **Rejected options:** новый supervisor-only route; отдельный settings screen для queue columns; backend-heavy queue governance до завершения Part A UI contract.
- **Source quality:** high-signal primary source = official HubSpot knowledge base docs.

## Root cause (mandatory)
- **Symptom:** очередь уже удобна для одиночной работы с кейсом, но supervisor/admin всё ещё не может быстро переключиться на типовые операционные срезы без ручной комбинации фильтров и визуального шума.
- **Minimal reproduction:** открыть `Заявки`, попытаться поочерёдно найти `без владельца`, `на паузе`, `только мои`, `проблемы доставки`, а затем перестроить список под owner/channel/activity without losing current context.
- **Evidence:** `CaseList.tsx` exposes only low-level filters + bulk actions; no saved views or field governance layer is present.
- **Five Whys:**
  1. Почему очередь ещё не supervisor-grade? Потому что каждый операционный срез собирается вручную.
  2. Почему existing filters недостаточны? Потому что они хороши как низкоуровневые controls, но не как быстрые рабочие режимы.
  3. Почему нужна настройка полей? Потому что разным ролям нужен разный акцент: owner/channel/activity vs минимальный chat-first список.
  4. Почему это не должно быть новым экраном? Потому что по ТЗ нужно оптимизировать текущие вкладки, а не плодить дублирующие разделы.
  5. Почему Part A bounded? Потому что сначала нужен queue governance layer в уже существующем списке; routing/admin views остаются на Part B.
- **Root cause statement:** в очереди отсутствует слой role-aware governance над уже существующими фильтрами и списковыми полями.
- **Fix mechanism:** добавить named queue views + configurable visible fields c workspace persistence поверх текущего `CaseList`.

## Reuse-first plan (mandatory)
- **Reuse:** текущие query filters, compact/table rendering, bulk toolbar, workspace persistence, role data from `InboxView`.
- **Integrate:** ввести governance layer в `CaseList` без нового route или дублирующей очереди.
- **Build only if needed:** только новые local view definitions, visible-field prefs и компактный UI для переключения.

## Invariant
- Не ломать текущие filters, bulk actions и selected case behavior.
- Не создавать новый top-level экран или supervisor-only вкладку.
- Не прятать критичные сигналы SLA/ошибок за кастомизацией полей.
- Не превращать queue views в неочевидную конфигурацию; default first-screen должен остаться понятным менеджеру.

## Scope
- добавить role-aware quick views: `Все открытые`, `Мои`, `Требуют ответа`, `Пауза`, `Проблемы доставки`, `Без владельца` (для supervisor/admin);
- добавить настраиваемые поля списка/таблицы с сохранением в workspace scope;
- сохранить governance prefs на 24 часа вместе с остальными queue prefs;
- показать active view summary без дублирования существующих фильтров;
- закрыть change deterministic e2e mock lane.

## Out of scope
- Новая backend routing model.
- SLA policy redesign.
- Supervisor mass-routing rules.
- New analytics dashboard.

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Создать Wave9 TP и перевести session canon на новый active block.
2. Расширить workspace prefs для named queue view и visible fields.
3. Добавить governance layer в `CaseList` и передать role context из `InboxView`.
4. Обновить deterministic inspect-case lane на queue view/field toggle assertions.
5. Запушить изменения в PR `#932`.

## DoD
- Supervisor/admin получает быстрые queue views без ручной сборки фильтров.
- Manager не теряет понятный default list, но может быстро переключиться на типовые режимы.
- Видимые поля списка настраиваются и восстанавливаются из workspace prefs.
- Bulk actions и selection продолжают работать в governance views.
- `inspect_case` mock lane покрывает новый governance layer.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Lint + build + Playwright output.
- Updated session log with Wave9 Part A status.

## Release safety (mandatory)
- **Rollout:** continue in PR `#932`; governance layer sits on top of current queue behavior.
- **Go/no-go:** queue views do not break selection/bulk actions and default list remains readable for managers.
- **Rollback:** revert Wave9 Part A diff; current queue behavior remains intact.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave9 Part A checks.

## No-go
- Добавлять отдельный supervisor route.
- Размножать параллельные фильтры и duplicate buttons for the same behavior.
- Прятать обязательные SLA/issue signals behind disabled-by-default fields.

## Риски/блокеры
- Queue view и ручные фильтры могут конфликтовать, если не зафиксировать precedence ясно.
- Persisted field prefs не должны ломать manager default readability.
- E2E mock lane должен оставаться детерминированным даже с несколькими queue items.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: queue views пока остаются UI-governance layer over current list; backend routing/admin views ещё не внедрены.
- `Why not in this block`: это уже Wave9 Part B и требует отдельного bounded design.
- `Risk if deferred`: supervisor получит быстрые views, но не полноценный routing/admin control tower.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`, `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `Expiry/trigger to stop deferral`: если после Part A supervisor всё ещё не может безопасно управлять ownership/routing rules на масштабе, Part B становится обязательным перед закрытием Wave9.

## Next-block contract (mandatory)
- `Next block objective`: открыть Wave9 Part B на routing/admin views после green closure Part A.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave9 Part A must keep queue readability, selection and bulk actions intact.
- `Owner role for closure`: Brain / Top Architect.
