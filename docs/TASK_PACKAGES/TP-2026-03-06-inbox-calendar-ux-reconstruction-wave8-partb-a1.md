# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-PARTB-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-A1

## Название/цель
Дожать Wave8 до бесшовного рабочего цикла: при переходе из embedded `Записи` в полный календарь и обратно менеджер должен вернуться в ту же заявку и в тот же workspace mode без потери контекста, а case-mode календаря не должен прятать связанные записи из-за сброшенной даты.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: continue inside existing PR `#932`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/lib/inbox-workspace.ts`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseBookingsPanel.tsx`
  - `console-web/src/app/calendar/page.tsx`
  - `console-web/src/app/cases/[id]/page.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Embedded bookings panel already works inside the case workspace, but `Открыть полный календарь` still leaves no explicit contract for how to restore panel mode on return.
  - `calendar/page.tsx` still sends `Открыть заявку` and back navigation to `/cases/:id` without panel context, so user returns to the chat shell but loses the active `Записи` mode.
  - `calendar/page.tsx` still initializes `selectedDate` to today even in case-focused mode, so linked bookings on other dates can appear missing.
  - `InboxView` persists selected case and list filters, but not active side-panel mode.

## One web search (mandatory before implementation)
- **Query (exact):** `HubSpot help desk views filters queue official documentation`
- **Date/time (local):** `2026-03-06T10:49:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/create-and-manage-help-desk-views`
- **Ready solutions found:** operator help desks persist the current work view and filter state, so agents can leave a full queue/table view and return to the same working context instead of restarting triage from default filters.
- **Decision (`reuse/integrate/build`):** `integrate` — расширить уже существующий `inbox-workspace` persistence layer на panel mode и calendar case-context prefs вместо добавления нового routing subsystem.
- **Rejected options:** новый route-level state store; глобальный Redux-like workspace coordinator; хранение return context only in brittle in-memory component state.
- **Source quality:** high-signal primary source = official HubSpot knowledge base docs.

## Root cause (mandatory)
- **Symptom:** после перехода в полный календарь менеджер теряет active `Записи` mode и часть case-context, а case-focused calendar иногда показывает пустой список из-за дефолтной даты.
- **Minimal reproduction:** открыть `Записи по заявке` в embedded panel -> нажать `Открыть полный календарь` -> открыть связанную заявку обратно; пользователь снова попадает в обычный case screen without bookings panel. Отдельно: открыть full calendar в case mode для записи на другой дате и увидеть пустой список при дефолтном today filter.
- **Evidence:** `InboxView` stores selected case only; `calendar/page.tsx` links back to `/cases/:id`; `selectedDate` defaults to `today` even when `focusedConversationId`/`focusedCaseId` exist.
- **Five Whys:**
  1. Почему ещё есть friction после Part A? Потому что cross-route return contract не формализован.
  2. Почему embedded panel недостаточно? Потому что менеджеру всё ещё нужен полный календарь для общего обзора и queue actions.
  3. Почему возврат в `/cases/:id` не решает проблему? Потому что сам case route не знает, какой workspace mode должен восстановиться.
  4. Почему case calendar иногда пустой при наличии записей? Потому что case context и date filter живут отдельно и today filter побеждает linked-case semantics.
  5. Почему это нужно делать сейчас? Потому что без этого Wave8 нельзя считать закрытым: основной цикл всё ещё рвётся на route boundary.
- **Root cause statement:** часть workspace state (`active panel mode`, `calendar case prefs`) не имеет персистентного контракта между inbox route и full calendar route.
- **Fix mechanism:** расширить существующий workspace persistence слой, прокинуть explicit return-panel contract в calendar links и сохранять calendar prefs per workspace scope.

## Reuse-first plan (mandatory)
- **Reuse:** `buildInboxWorkspaceScope`, selected-case persistence, existing case/calendar query params (`case_id`, `conversation_id`), current embedded bookings panel, current inspect_case route-mock lane.
- **Integrate:** добавить panel-mode storage и calendar case-context prefs в `inbox-workspace.ts`, а затем подключить их в `InboxView` и `calendar/page.tsx`.
- **Build only if needed:** только минимальные helpers для case/calendar href и case-context prefs.

## Invariant
- Не ломать уже работающий embedded bookings panel.
- Не убирать full calendar route и его queue controls.
- Не сбрасывать selected case или inbox queue filters при возврате из календаря.
- Не скрывать связанные записи в case-mode только потому, что пользователь не выбрал дату.

## Scope
- восстановить active panel mode (`Записи`/`Детали`) при возврате из full calendar в заявку;
- сохранить calendar case-context prefs (`selectedDate`, `lane`, `status`) на workspace scope;
- в case-mode календаря показывать все даты по умолчанию, пока менеджер не выберет конкретную дату;
- обновить return links `Открыть заявку` / `Вернуться в заявку` / linked case cards так, чтобы bookings mode восстанавливался детерминированно;
- закрыть flow проверкой `case -> embedded bookings -> full calendar -> case(bookings)`.

## Out of scope
- Full scheduler redesign.
- Новые booking actions.
- Supervisor/admin queue governance.
- Persisting every temporary input in full calendar form.

## Touch-list
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseBookingsPanel.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/app/cases/[id]/page.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Создать Wave8 Part B TP и перевести session canon на новый active block.
2. Расширить `inbox-workspace.ts` на side-panel и calendar case-context persistence.
3. На `InboxView` восстановить initial panel from query/storage и сохранять его при переключении.
4. На `calendar/page.tsx` подключить case-context prefs и explicit return-panel links.
5. Обновить `inspect_case` на полный return-loop assertion.

## DoD
- После перехода из embedded bookings в full calendar и обратно заявка открывается сразу в `Записи` mode.
- Calendar case-context не теряет queue lane/status/date prefs в пределах workspace scope.
- В case-mode full calendar по умолчанию не прячет связанные записи из-за today filter.
- Existing embedded panel and calendar route remain green.

## Checks
- `cd console-web && npm run lint -- --file src/lib/inbox-workspace.ts --file src/components/InboxView.tsx --file src/components/CaseConversation.tsx --file src/components/CaseBookingsPanel.tsx --file src/app/calendar/page.tsx --file src/app/cases/[id]/page.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Lint + build + Playwright output.
- Updated session log referencing PR `#932` and Wave8 Part B.

## Release safety (mandatory)
- **Rollout:** continue in existing PR `#932`; route-level fallback remains `/calendar` and `/cases/:id`.
- **Go/no-go:** return-loop green, no regression in embedded bookings panel, no regression in full calendar queue controls.
- **Rollback:** revert the Part B diff; system falls back to Part A behavior.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave8 Part B checks.

## No-go
- Хранить return state only in ephemeral component refs.
- Привязывать restore logic к одному hardcoded route path without scope.
- Возвращать пользователя в обычный case screen, если он явно вышел в full calendar из bookings mode.

## Риски/блокеры
- Нельзя создать race between query-param initialization and storage restoration.
- Нужно не сломать default all-calendar flow без case context.
- Persisted prefs должны быть scope-aware, иначе owner/admin с несколькими branch scopes получат загрязнение состояния.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: full create-booking wizard всё ещё живёт только в full calendar route; nav sidebar still opens generic `/calendar` without contextual case handoff.
- `Why not in this block`: это уже либо отдельный scheduler block, либо broader navigation IA revision.
- `Risk if deferred`: full calendar remains secondary route instead of true multi-tab workspace, but primary operator loop будет бесшовным.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`, `TBD wave9`.
- `Expiry/trigger to stop deferral`: если после этого блока менеджеру всё ещё нужен частый ручной reset filters/panel after route return, нужно отдельное nav-context TP.

## Next-block contract (mandatory)
- `Next block objective`: перейти к Wave9 supervisor/admin queue governance после green closure Wave8.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave8 Part B must keep PR `#932` green and must not regress the current calendar/full-workspace loop.
- `Owner role for closure`: Brain / Top Architect.
