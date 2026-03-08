# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE23-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-LIVE-PROOF-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE24-A1

## Название/цель
Провести owner-approved post-closeout анализ оставшихся дефектов и следующего слоя зрелости поверх закрытой программы `Заявки/Записи`, чтобы дальнейшая работа шла не через новые spot-fix правки, а через один server-owned queue-state plan.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-live-proof-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: docs-only follow-up in current worktree; all future product work opens under new bounded TPs/PRs
- `Cleanup`: Brain / Top Architect after the future implementation sequence closes

## FACT pre-check (before implementation)
- Inbox queue state is still persisted only in browser storage (`localStorage`, TTL 24h), not in a server-owned object: `console-web/src/lib/inbox-workspace.ts:6`, `console-web/src/lib/inbox-workspace.ts:171`, `console-web/src/components/CaseList.tsx:955`.
- Calendar queue state is also browser-local and not shareable/reproducible across operators: `console-web/src/app/calendar/page.tsx:133`, `console-web/src/app/calendar/page.tsx:148`.
- URL currently carries case/conversation/panel context, but not canonical queue state for inbox/calendar filters: `console-web/src/app/cases/[id]/page.tsx:1`, `console-web/src/app/calendar/page.tsx:70`.
- `GET /cases` rejects unknown query params and accepts only the current hard-coded filter set, so a future `view_id`/`preset_id` cannot be layered in without an explicit contract change: `truffles-api/app/routers/console.py:11022`.
- `queue_view` is still a strict server enum and routing policy is still a single literal `least_open_cases`: `truffles-api/app/routers/console.py:1180`, `truffles-api/app/schemas/console.py:1087`, `truffles-api/app/routers/console.py:6158`.
- Calendar queue contract is still limited to `lane/status/date/case/conversation`, with no follow-up owner/due/history governance layer: `truffles-api/app/routers/calendar.py:1017`, `truffles-api/app/routers/calendar.py:136`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com "What are queues?" site:support.zendesk.com "Managing your views" site:knowledge.hubspot.com "route tickets in help desk"`
- **Date/time (local):** `2026-03-07T17:41:40+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
  - `https://knowledge.hubspot.com/help-desk/search-for-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/route-tickets-in-help-desk`
- **Ready solutions found:** mature operator products separate base queue semantics from secondary refinements, distinguish personal/shared views, and keep routing server-owned with explainable rules instead of UI-only state.
- **Decision (`reuse/integrate/build`):** `integrate` — formalize one queue-state canon first, then layer personal views, managed team presets, shareable URLs, and only after that expand routing.
- **Rejected options:** start with richer routing first; keep saved views local-only; build separate data models for personal views vs team presets.
- **Source quality:** high-signal primary sources = official Atlassian, Zendesk, and HubSpot documentation.

## Root cause (mandatory)
- **Symptom:** the original semantic reconstruction is closed, but operators still cannot reproduce queue states reliably across people/sessions, admins cannot set governed presets, and routing remains too blind for the next layer of automation.
- **Minimal reproduction:** configure an inbox queue locally, ask another operator to open the same state, or try to route a case by anything more meaningful than `least_open_cases`.
- **Evidence:** `console-web/src/lib/inbox-workspace.ts:6`, `console-web/src/components/CaseList.tsx:645`, `console-web/src/app/calendar/page.tsx:175`, `truffles-api/app/routers/console.py:11022`, `truffles-api/app/routers/console.py:6174`.
- **Five Whys:**
  1. Why are queue states not reproducible? Because queue state is local-first, not server-owned.
  2. Why does that block saved views and handoff? Because there is no canonical shared object behind queue filters.
  3. Why does that block team presets? Because admin defaults would have to target a server object that does not exist.
  4. Why are shareable URLs weak today? Because routes carry context ids, not the queue contract itself.
  5. Why is richer routing still too narrow? Because routing has no stable operational contract to consume beyond current owner load.
- **Root cause statement:** remaining productivity and automation defects stem from the absence of one server-owned queue-state contract that cleanly separates operational query state from local workspace presentation state.
- **Fix mechanism:** document the defect clusters explicitly, lock the implementation order, and open the first bounded execution TP around queue-state canon before any saved-view or routing expansion.

## Invariant
- Do not reopen Wave22 correctness claims while planning future maturity work.
- No mutation side-effects by heuristic `conversation -> latest case`; side-effects stay explicit on `case_id` only.
- Personal views, team presets, and shareable URLs must converge on one state model, not three incompatible ones.
- Richer routing is blocked until queue-state canon and booking follow-up governance are explicit.

## Scope
- classify the remaining defect clusters after Wave22 closure
- define the implementation order for the next maturity layer
- create the first bounded execution TP that removes the main architectural blocker
- sync master/session/state/structure canon to the new plan

## Out of scope
- product/runtime code changes
- reopening the already-closed semantic reconstruction waves
- shipping named views, team presets, shareable URLs, or new routing policies in this block

## Defect clusters (mandatory)
1. `D1 local-only queue state`: inbox/calendar filters persist only per-browser and expire after 24h.
2. `D2 no server-owned saved-view object`: there is no canonical entity for named views or team defaults.
3. `D3 non-shareable queue URLs`: routes carry context ids, not reproducible queue-state semantics.
4. `D4 calendar not yet supervisor-grade`: bookings queue still lacks owner/due/history governance primitives.
5. `D5 routing inputs too narrow`: `least_open_cases` sees open counts only and cannot score business suitability.

## Planned decomposition (mandatory)
- `Wave24` — `Queue State Canon`: server-owned queue-state contract for inbox/calendar, plus URL/state precedence and local-storage migration.
- `Wave25` — `Personal Saved Views`: naming/saving reusable operator views on top of the queue-state canon.
- `Wave26` — `Managed Team Presets`: admin-owned presets/defaults per branch/role/team using the same state model.
- `Wave27` — `Shareable Queue URLs`: reproducible URLs over canonical queue-state/view ids instead of browser-local state.
- `Wave28` — `Bookings Supervisor Grade`: follow-up owner/due/history governance for `Записи` so calendar queue becomes supervisor-safe.
- `Wave29` — `Richer Routing v1`: recommendation-first routing policies using explicit operational signals instead of load-only routing.

## Plan (1..N)
1. Record the concrete post-closeout defect clusters in canon.
2. Localize each defect cluster to current code/contracts.
3. Lock the architectural sequence so future work starts with queue-state canon.
4. Open the first bounded execution TP (`Wave24`).
5. Sync master/session/state/structure pointers to the new follow-up plan.

## DoD
- Remaining defects are expressed as explicit clusters, not vague “future ideas”.
- The first unblocker is documented as `Queue State Canon`, not richer routing.
- The first follow-up execution TP exists and is linked from the closed master program.
- Session/master/state/structure docs point to the same follow-up plan.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Queue State Canon|Defect clusters|Wave24|Wave29" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff over the touch-list.
- Updated master/session/state/structure references.
- `scripts/session_check.sh` output.

## Rollback
- revert the docs-only follow-up commit/changeset in this worktree
- restore previous task-package pointer in `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## No-go
- Start with routing automation before queue-state canon exists.
- Treat localStorage prefs as the long-term source of truth for saved views.
- Split personal/team/shareable state into separate incompatible contracts.
- Reopen the closed semantic program by stealth instead of under a new explicit TP.

## Риски/блокеры
- If Wave24 scope is weakened into another frontend-only cleanup, the same defect family will return.
- If future URLs encode opaque blobs instead of canonical state, handoff/auditability will degrade.
- If calendar supervisor-grade governance is skipped, routing expansion will optimize against an incomplete operating model.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no runtime/product fix shipped yet; this block is planning and canon alignment only.
- `Why not in this block`: the goal here is to prevent another ad-hoc implementation order and make the first technical unblocker explicit.
- `Risk if deferred`: saved views/presets/routing could regress into disconnected feature work with duplicated state models.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`.
- `Expiry/trigger to stop deferral`: no future inbox/calendar maturity feature may start before `Wave24` either closes or is explicitly superseded by a new owner-approved TP.

## Next-block contract (mandatory)
- `Next block objective`: implement `Wave24` and establish one server-owned queue-state canon for inbox/calendar before saved-view and routing expansion.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "readInboxCaseListPrefs|writeInboxCaseListPrefs|readCalendarWorkspacePrefs|writeCalendarWorkspacePrefs|_reject_unknown_query_params|_normalize_case_routing_policy" console-web/src truffles-api/app`
- `Blocked-by conditions`: none for planning closure; implementation starts only when owner approves Wave24 execution.
- `Owner role for closure`: Brain / Top Architect.
