# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-PARTB-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-PARTB-A1

## Название/цель
Довести связку `Заявки` + `Записи` до единого operator workspace shell: менеджер должен открыть связанные записи по заявке внутри текущего рабочего экрана, увидеть ближайшие визиты и выполнить базовые действия без route-level ухода из чата.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred for `Part A`; `Part B` only after green evidence and updated canon
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseView.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/ConsoleShell.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - `CaseConversation.tsx` still exposes `Записи по заявке` as direct link to `/calendar?...`, so primary operator flow leaves the current workspace.
  - `InboxView.tsx` already preserves selected case and filters inside inbox scope, but that continuity is partially wasted because calendar work still happens on another route.
  - `calendar/page.tsx` already contains linked-booking actions and case context banner, so the business logic exists; the main gap is workspace composition, not missing booking semantics.
  - `Wave1-Wave7` already removed most duplicate actions and SLA noise, so remaining friction is the route boundary itself.

## One web search (mandatory before implementation)
- **Query (exact):** `agent workspace split view tickets conversations help desk official docs Zendesk HubSpot`
- **Date/time (local):** `2026-03-06T10:28:51+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/route-tickets-in-help-desk`
- **Ready solutions found:** operator help desks keep the active ticket thread and related work context in one workspace, using a secondary panel/sidebar for linked details/actions while preserving a path to the full queue view.
- **Decision (`reuse/integrate/build`):** `integrate` — добавить case-linked bookings panel inside current inbox shell and keep `/calendar` as secondary full-screen route.
- **Rejected options:** полный перенос календаря в новый top-level screen; iframe/embed чужого route; modal-only flow, который ломает mobile/operator usage.
- **Source quality:** high-signal primary source = official HubSpot knowledge base docs.

## Root cause (mandatory)
- **Symptom:** менеджер все еще теряет фокус при переходе из заявки в записи, хотя данные уже связаны через `case_id` и контекст возвращается назад.
- **Minimal reproduction:** открыть любую заявку, нажать `Записи по заявке`, попасть на `/calendar`, затем возвращаться обратно в чат, чтобы продолжить работу по заявке.
- **Evidence:** `console-web/src/components/CaseConversation.tsx` uses direct `/calendar?...` link; `console-web/src/app/calendar/page.tsx` renders the booking workspace only on a separate route.
- **Five Whys:**
  1. Почему лишние движения все еще есть? Потому что записи открываются на другом маршруте.
  2. Почему это важно, если `case_id` уже передается? Потому что сохранение id не убирает визуальное и когнитивное переключение менеджера.
  3. Почему нельзя считать это мелким UX-штрихом? Потому что основной бизнес-сценарий `диалог -> запись/статус визита -> обратно в диалог` остается разорванным.
  4. Почему не нужен полный rewrite календаря? Потому что booking semantics и linked-case actions уже реализованы; не хватает workspace shell поверх них.
  5. Почему блок нужно делать bounded? Потому что сначала нужен единый shell для case-linked bookings, а не повторная сборка всего календаря внутри inbox.
- **Root cause statement:** route-level separation между `Заявками` и `Записями` остается последним крупным UX-разрывом в основном операторском сценарии, несмотря на уже готовую связанную бизнес-логику.
- **Fix mechanism:** встроить case-linked bookings panel в текущий inbox workspace, переиспользовать существующие booking actions и оставить full calendar как secondary CTA.

## Reuse-first plan (mandatory)
- **Reuse:** текущие linked booking contracts (`case_id`, `conversation_id`), booking action semantics из `calendar/page.tsx`, inbox side-column layout and state, `inspect_case` mock/live lane.
- **Integrate:** вынести shared booking helpers в reusable layer и подключить новый case-linked bookings panel в `InboxView`/`CaseView`.
- **Build only if needed:** отдельный panel component и минимальный workspace-shell state для переключения `Детали` / `Записи`.

## Invariant
- Не ломать текущий `/calendar` route и его queue controls.
- Не терять текущий inbox draft/message context при открытии связанных записей.
- Не дублировать booking logic отдельной второй реализацией с другой бизнес-семантикой.
- Не убирать доступ к `CaseDetailsPanel`; записи должны стать соседним workspace mode, а не destructive replacement.

## Scope
- `Part A (this TP)`:
  - добавить в inbox/case workspace secondary panel mode `Записи` рядом с текущими `Детали`;
  - показать case-linked bookings без route change;
  - переиспользовать существующие booking status actions (`Пришел`, `Не пришел`, `Связались`, `Перезаписали`) в embedded panel;
  - оставить CTA `Открыть полный календарь` как secondary escape hatch;
  - закрыть новый flow целевым e2e mock check.
- `Part B (follow-up, mandatory split)`:
  - сохранить/восстанавливать active workspace tab/context при переходе в full calendar и обратно;
  - довести queue position/context preservation между full calendar и inbox workspace.

## Out of scope
- Полный перенос slot picker и create-booking flow внутрь inbox workspace.
- Новый top-level route или отдельная вкладка для workspace shell.
- Scheduler redesign, supervisor queue governance, routing/admin logic.
- Full calendar IA rewrite.

## Touch-list
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseView.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseBookingsPanel.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `console-web/calendar_case_context.png`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Открыть Wave8 TP и перевести session canon на новый active block.
2. Вынести shared booking helpers/types из `calendar/page.tsx` в reusable module.
3. Добавить `CaseBookingsPanel` и встроить его в `InboxView`/`CaseView` как alternate side-panel mode.
4. Переключить `Записи по заявке` с primary route-link на workspace action with full-calendar fallback CTA.
5. Зафиксировать новый single-workspace flow в `inspect_case` и обновить evidence screenshot.

## DoD
- Менеджер открывает связанные записи по заявке внутри текущего workspace без route change.
- В panel доступны ключевые linked-booking actions без потери draft/chat context.
- `CaseDetailsPanel` остается доступным как соседний режим.
- Full calendar route продолжает работать и остается доступен как secondary CTA.
- `inspect_case` mock lane покрывает embedded bookings panel.

## Checks
- `cd console-web && npm run lint -- --file src/components/InboxView.tsx --file src/components/CaseView.tsx --file src/components/CaseConversation.tsx --file src/components/CaseBookingsPanel.tsx --file src/components/ConsoleShell.tsx --file src/lib/calendar-bookings.ts --file src/app/calendar/page.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Lint + build + Playwright output.
- Updated screenshot showing embedded bookings workspace.
- Session log with active Wave8 block.

## Release safety (mandatory)
- **Rollout:** inbox workspace enhancement over existing booking contracts; `/calendar` remains intact as fallback route.
- **Go/no-go:** embedded bookings panel works, draft persists, calendar route still opens, no regression in current inspect-case path.
- **Rollback:** revert the Wave8 Part A diff; operators fall back to the already working route-based calendar flow.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave8 Part A checks.

## No-go
- Ломать current `/calendar` page ради нового shell.
- Делать вторую независимую реализацию booking actions with different labels/rules.
- Убирать details panel без replacement that preserves diagnostics/context.
- Прятать full calendar access entirely.

## Риски/блокеры
- Нужно сохранить mobile/desktop readability при добавлении second side-panel mode.
- Нельзя потерять draft или selected case при переключении между panel modes.
- Есть риск повторного дублирования booking helper logic, если не вынести shared layer аккуратно.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: full queue/date/specialist scheduling still lives on `/calendar`; workspace tab/context persistence across route transitions is not finished.
- `Why not in this block`: Part A закрывает primary same-screen flow, Part B добивает preservation and route-bridge semantics.
- `Risk if deferred`: основной сценарий станет лучше, но secondary переход в full calendar всё еще может терять часть UI-state.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`, `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `Expiry/trigger to stop deferral`: если после Part A менеджер по-прежнему вынужден часто уходить в full calendar и теряет context on return, Part B becomes mandatory before claiming Wave8 closed.

## Next-block contract (mandatory)
- `Next block objective`: открыть Wave8 Part B и зафиксировать queue position/context preservation between inbox workspace and full calendar route.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave8 Part A must keep embedded panel green and must not regress `/calendar` or current case selection persistence.
- `Owner role for closure`: Brain / Top Architect.
