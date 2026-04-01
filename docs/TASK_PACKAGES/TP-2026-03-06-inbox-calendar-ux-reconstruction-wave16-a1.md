# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-LIVE-VALIDATION-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-CLOSEOUT-A1

## Название/цель
Полностью пересобрать перегруженные operator surfaces в `Заявках`: action area вокруг `Передать / Отложить / Вернуть в работу` и левую очередь с фильтрами/карточками. Цель — убрать ложное ощущение «что-то происходит», сократить когнитивную нагрузку и сделать интерфейс читаемым без потери уже внедрённой бизнес-логики.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected if the block does not fit safely into one PR
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- The current action panel mixes business actions and panel toggles in one row: `console-web/src/components/CaseConversation.tsx:973`.
- `Передать` changes into `Скрыть передачу`, so one button changes its meaning from business action to UI-dismiss action.
- The reassign panel is text-dense: long select labels, helper copy, recommendation banner, and three competing CTA buttons live in one constrained block.
- The inbox layout still allocates only `340-380px` to the left rail in the common two-column workspace: `console-web/src/components/InboxView.tsx:228`.
- The left rail still packs queue views, search, filters, summary, and dense cards into the same first screen: `console-web/src/components/CaseList.tsx:1184`, `console-web/src/components/CaseList.tsx:1810`.
- Existing screenshots confirm the problem visually: `console-web/case_inspection.png`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:knowledge.hubspot.com help desk manage tickets in help desk route tickets SLA goals`
- **Date/time (local):** `2026-03-06T18:35:51+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/route-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/snooze-tickets-in-help-desk`
- **Ready solutions found:** clear operator workspaces use one primary action layer, keep assignment details bounded, and treat snooze/queue views as distinct operational states instead of piling all controls into one compressed surface.
- **Decision (`reuse/integrate/build`):** `integrate` — preserve the current tabs and backend contracts, but redesign the current inbox surfaces around hierarchy, density control, and operator-first copy.
- **Rejected options:** add a new top-level tab; keep current surfaces and only tweak labels; move critical actions into hidden menus by default.
- **Source quality:** high-signal primary source = official HubSpot knowledge base.

## Root cause (mandatory)
- **Symptom:** managers experience the action area and left rail as overloaded, cramped, and logically untrustworthy.
- **Minimal reproduction:** open an active case, expand reassignment, and inspect the left rail on desktop split layout.
- **Evidence:** `console-web/src/components/CaseConversation.tsx:705`, `console-web/src/components/CaseConversation.tsx:980`, `console-web/src/components/InboxView.tsx:228`, `console-web/src/components/CaseList.tsx:1184`, `console-web/src/components/CaseList.tsx:1810`, `console-web/case_inspection.png`.
- **Five Whys:**
  1. Why does the action area feel broken? Because too many different intents compete in the same visual band.
  2. Why does reassignment feel fake-smart? Because recommendation, policy routing, helper text, and confirmation all compete without one obvious next step.
  3. Why is the left rail hard to use? Because its width and content density are mismatched.
  4. Why does this hurt business logic? Because managers cannot quickly distinguish next action, supporting context, and optional controls.
  5. Why not solve this with copy-only tweaks? Because the issue is structural: layout hierarchy and interaction model are wrong.
- **Root cause statement:** operator surfaces accumulated multiple valid capabilities without a stable hierarchy, causing cramped layout, ambiguous CTAs, and poor scanability.
- **Fix mechanism:** redesign the current surfaces in bounded steps: first action hierarchy, then queue rail IA and card density.

## Reuse-first plan (mandatory)
- **Reuse:** existing backend action contracts, queue views, business status/SLA indicators, workspace shell, current route structure.
- **Integrate:** redesign `CaseConversation`, `CaseList`, and `InboxView` without adding new routes or duplicating logic.
- **Build only if needed:** helper components for action groups / assignee rows / queue summary if the current files cannot remain readable.

## Invariant
- Keep the current `Заявки` workspace and the already merged business logic.
- Do not hide critical actions behind non-obvious affordances.
- Every visible control must have one clear job.
- Queue cards must remain actionable and support the current workspace loop.

## Scope
- `Part A case action surface`:
  - separate primary, secondary, and dismiss/toggle actions;
  - replace ambiguous `Скрыть передачу` semantics with explicit panel affordance;
  - simplify reassign panel to one obvious next step and lower copy density.
- `Part B queue rail simplification`:
  - widen the left rail for desktop split layouts;
  - move advanced/secondary controls out of the critical first screen;
  - simplify compact queue cards to the minimum operator scan set.

## Out of scope
- New routing algorithms.
- Deep rewrite of backend queue semantics.
- Full mobile redesign beyond regression-safe adaptation.
- New top-level tabs or alternative navigation IA.

## Touch-list
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Use Wave15 feedback contract as the semantic base and sync canon.
2. Implement `Part A`: action hierarchy, panel affordances, reassign panel reduction.
3. Validate action flow locally with screenshot + deterministic lane.
4. Implement `Part B`: left-rail width, filter IA, compact card simplification.
5. Refresh screenshots and deterministic coverage.
6. Close only after the full operator surface is coherent end-to-end.

## DoD
- Active case actions have a visible hierarchy: primary vs secondary vs panel dismiss.
- Reassign panel has one obvious confirmation path and reduced text density.
- Desktop left rail is no longer visually cramped.
- Compact cards show only the minimum operator scan set.
- Existing workspace flow and bulk actions remain intact.
- Deterministic checks and screenshot evidence confirm the new hierarchy.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/utils/labels.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for touch-list.
- Local Playwright output.
- Before/after screenshots showing action area and queue rail.
- Session log updated with Part A / Part B closure.

## Release safety (mandatory)
- **Rollout:** UI-only bounded rollout on existing workspace.
- **Go/no-go:** merge only if queue selection, action flows, and workspace navigation remain intact.
- **Rollback:** revert the bounded Wave16 commit/PR.

## Rollback
- `git revert REVISION_SHA`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## No-go
- Turning panel close/dismiss into a primary business CTA.
- Adding more helper copy to explain a still-overloaded surface.
- Shrinking fonts to fit the same density.
- Regressing bulk actions or workspace context preservation.

## Риски/блокеры
- `CaseConversation.tsx` and `CaseList.tsx` are already large; bounded extraction may be needed to keep the code maintainable.
- Visual simplification can accidentally hide status/context if not validated against real operator scenarios.
- Wave15 live validation may reveal a semantic blocker that must be addressed before UI polish.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no new supervisor analytics/reporting layer; no transport retry UI.
- `Why not in this block`: this block is strictly about operator clarity and surface hierarchy.
- `Risk if deferred`: managers keep spending time parsing the UI instead of acting.
- `Linked follow-up Task Package(s)`: `TBD Wave16 closeout if additional queue reporting or diagnostics become necessary after redesign`
- `Expiry/trigger to stop deferral`: if post-redesign screenshots still require explanatory notes to understand the first screen, the block is not closed.

## Next-block contract (mandatory)
- `Next block objective`: implement the full Wave16 redesign, splitting into `Part A case action surface` then `Part B queue rail simplification` if needed for PR safety.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/InboxView.tsx`
- `Blocked-by conditions`: unresolved Wave15 live semantic blocker.
- `Owner role for closure`: Brain / Top Architect.
