# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE21-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE20-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1

## Название/цель
Сделать семантическую цепочку `бот -> заявка -> менеджер -> запись -> итог/история` явной и бесшовной в продукте, чтобы менеджер и администратор всегда понимали причину заявки, текущее состояние ручной работы и связь с календарём записей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected: `Part A semantic badges/context`, `Part B booking-state propagation`
- `Cleanup`: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:knowledge.hubspot.com help desk ticket details conversation context related records booking-like workflows and site:support.zendesk.com views ticket context`
- **Date/time (local):** `2026-03-07T10:05:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- **Ready solutions found:** strong operator products keep the active conversation, related record context, owner and outcome in one workspace and do not force the agent to infer relationships from scattered screens.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse current case-bookings panel and case actions, but make the semantic relationship explicit in UI and state propagation.
- **Rejected options:** leaving booking context as secondary-only detail; handling booking outcomes separately from case business state.
- **Source quality:** high-signal primary sources = official HubSpot and Zendesk docs.

## Root cause (mandatory)
- **Symptom:** even after linking routes, the user can still lose the logical story of why a case exists and how it relates to a booking outcome.
- **Minimal reproduction:** open a case created from bot escalation, navigate to booking actions, then try to explain the case status and booking status as one coherent story.
- **Evidence:** current product has linked navigation but not a full semantic chain contract across surfaces.
- **Five Whys:** the surfaces are connected technically, but not yet unified around one operator story.
- **Root cause statement:** route linkage exists, but shared semantic ownership of bot outcome, case lifecycle and booking lifecycle is incomplete.
- **Fix mechanism:** add shared context badges/fields, align state propagation rules, and make case/business statuses explain booking-related outcomes.

## Invariant
- One operator story across surfaces.
- No contradictory case and booking states.
- No hidden system-only reason codes on the main operator path.

## Scope
- clarify case origin from bot/handoff
- surface booking linkage and booking outcome meaning in case workspace
- align case status changes and booking state changes where business logic requires it

## Out of scope
- new booking engine semantics outside current product scope
- new bot policy-core changes outside console workflow contract

## Touch-list
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseBookingsPanel.tsx`
- `console-web/src/components/CaseDetailsPanel.tsx`
- `console-web/src/app/calendar/page.tsx`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/appointment.py`
- `console-web/e2e/inspect_case.spec.ts`

## DoD
- Менеджер видит, почему заявка существует и что уже сделал бот.
- Booking context объясняет case state, а не дублирует/противоречит ему.
- Key booking outcomes (`confirmed`, `rescheduled`, `cancelled`, `no_show follow-up`) имеют понятное отражение в case/business flow.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseBookingsPanel.tsx --file src/app/calendar/page.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## Evidence
- screenshots from case workspace and calendar context
- deterministic case->booking->case loop proof

## Rollback
- revert bounded Wave21 PR

## No-go
- Separate booking outcomes from case business meaning.
- Introduce new status text that contradicts existing action-driven SLA model.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: full forbidden-state matrix and live evidence stay for Wave22.
- `Why not in this block`: semantic integration must land before exhaustive validation.
- `Risk if deferred`: without Wave22, regressions can reappear in edge states.
- `Linked follow-up Task Package(s)`: `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`.
- `Expiry/trigger to stop deferral`: any newly found contradictory case/booking state after Wave21 triggers immediate Wave22 execution.

## Next-block contract (mandatory)
- `Next block objective`: prove that the new integrated model excludes bad states for manager/admin paths.
- `First deterministic check command`: `cd console-web && rg -n "case-bookings|business_status|sla_action_state" src/components src/app`
- `Blocked-by conditions`: missing state-transition agreement between case status and booking outcomes.
- `Owner role for closure`: Brain / Top Architect.
