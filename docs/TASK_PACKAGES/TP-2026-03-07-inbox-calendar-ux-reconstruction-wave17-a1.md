# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-CLOSEOUT-A1

## Название/цель
Исправить конфликтующую модель фильтров во вкладке `Заявки`. Цель — разделить `queue view`, `owner scope`, `advanced diagnostics`, `presentation` и убрать UX/логическую конкуренцию между фильтрами, которая сейчас создаёт ложное ощущение хаоса и мешает triage.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected if the filter-contract fix and final rail UX do not fit safely into one PR
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Queue views and manual filters mutate the same `filters` state, so selecting a view rewrites manual scope fields and vice versa: `console-web/src/components/CaseList.tsx:535`, `console-web/src/components/CaseList.tsx:1012`.
- The owner axis is duplicated across three controls (`Мои`, owner select, `Без владельца`), all writing to the same fields with manual resets: `console-web/src/components/CaseList.tsx:1253`, `console-web/src/components/CaseList.tsx:1281`, `console-web/src/components/CaseList.tsx:1390`.
- Queue summary already admits the conflict by surfacing `Есть ручные фильтры поверх режима`, which means the model is competing with itself instead of being explicit: `console-web/src/components/CaseList.tsx:1436`.
- Queue views still encode owner semantics (`mine`, `unassigned`) even though owner filtering also exists separately, so one business axis is represented twice: `console-web/src/components/CaseList.tsx:260`, `console-web/src/components/CaseList.tsx:432`.
- `snoozed` currently has an inconsistent view contract (`applyFilters` vs `matchesFilters`), which proves the current model is brittle: `console-web/src/components/CaseList.tsx:350`, `console-web/src/components/CaseList.tsx:360`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management best practices for managing queues at scale`
- **Date/time (local):** `2026-03-07T08:54:00+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/prioritize-your-queues-by-using-groups/`
- **Ready solutions found:** strong queue systems separate queue/view semantics from secondary filters, keep prioritization grouped and limited, and reduce first-screen filter noise instead of stacking equivalent controls on one rail.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the current inbox route and backend queue contract, but split the frontend filter model into distinct layers with a smaller first-screen control surface.
- **Rejected options:** keep duplicated owner controls and only rename them; add more explanatory helper text; move the whole queue into a new top-level tab.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** filters in `Заявки` interfere with each other logically and visually; managers cannot reliably tell which filter is the main queue mode and which is just a temporary refinement.
- **Minimal reproduction:** open `Заявки`, switch queue view, then use `Мои`, owner select, `Без владельца`, sort, and advanced filters; the visible state changes, but multiple controls are describing the same axis differently.
- **Evidence:** `console-web/src/components/CaseList.tsx:535`, `console-web/src/components/CaseList.tsx:641`, `console-web/src/components/CaseList.tsx:1012`, `console-web/src/components/CaseList.tsx:1182`, `console-web/src/components/CaseList.tsx:1436`.
- **Five Whys:**
  1. Why do filters conflict? Because queue mode and manual filters write into the same mutable object.
  2. Why is that confusing? Because owner scope exists both as queue presets and as explicit filters.
  3. Why does UX feel noisy? Because too many controls of equal visual weight compete on the first screen.
  4. Why does this hurt business logic? Because managers cannot trust whether they are seeing a true queue mode or a stale local override.
  5. Why not solve with copy only? Because the conflict is in the state model and IA, not in wording alone.
- **Root cause statement:** the inbox rail currently mixes queue semantics, ownership scope, diagnostics, and presentation preferences in one shared filter state, so the same business axis is represented multiple times and different controls override each other.
- **Fix mechanism:** separate filter layers, collapse owner controls into one scope selector, remove owner-specific queue views, and reduce first-screen controls to queue mode + search + owner scope with explicit chips for active refinements.

## Reuse-first plan (mandatory)
- **Reuse:** current backend `/cases` query params, queue views (`needs_reply`, `waiting_client`, `snoozed`, `delivery`), workspace persistence helpers, compact card layout.
- **Integrate:** rebuild `CaseList` state model and rail IA on top of existing server semantics.
- **Build only if needed:** add minimal helper types/functions for `ownerScope`, `active chips`, and `request filter composition`.

## Invariant
- Do not regress current queue loading, case selection, bulk actions, or workspace context preservation.
- Keep `queue_view` server-owned for semantic slices.
- Every visible filter control must map to one clear business axis.
- No fake simplification that merely hides state conflicts.

## Scope
- `Part A filter contract`:
  - separate `queue view` from `owner scope` and `advanced diagnostics`;
  - collapse `Мои` / owner select / `Без владельца` into one owner-scope control;
  - remove owner-specific queue views from the top rail;
  - stop queue view switching from rewriting owner scope.
- `Part B rail UX cleanup`:
  - keep only `queue mode + search + owner scope` on first screen;
  - move status/sort/diagnostics/date range into advanced refinement;
  - add explicit active chips for applied refinements;
  - clean up persistence to avoid restoring stale conflicting filter combinations.

## Out of scope
- Backend queue semantics rewrite.
- New analytics/reporting surfaces.
- New routing policies.
- Cross-tab redesign outside `Заявки`.

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Split the filter contract into queue view, owner scope, advanced filters, and presentation prefs.
2. Replace duplicated owner controls with one scope selector.
3. Rework first-screen rail controls around queue view + search + owner scope.
4. Move the rest into advanced refinement and explicit chips.
5. Refresh screenshots and deterministic coverage.

## DoD
- Queue view no longer rewrites owner scope.
- There is only one primary owner-scope control.
- `Мои` / `Без владельца` are not duplicated as queue views.
- First-screen controls are reduced and easier to scan.
- Active refinements are explicit and removable.
- Deterministic checks and screenshot evidence pass.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for touch-list.
- Local Playwright output.
- Updated screenshot for inbox rail.
- Session log with `Part A/Part B` closure status.

## Release safety (mandatory)
- **Rollout:** UI-only bounded rollout on existing inbox rail.
- **Go/no-go:** merge only if queue selection, filter persistence, and bulk actions remain stable.
- **Rollback:** revert the bounded Wave17 commit/PR.

## Rollback
- `git revert REVISION_SHA`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## No-go
- Keeping duplicate owner semantics in both queue views and manual filters.
- Solving the conflict only with helper text.
- Hiding critical filter state in persistence without explicit UI.
- Reintroducing local-only approximation of queue semantics.

## Риски/блокеры
- `CaseList.tsx` is large; bounded extraction may be needed to keep maintainability.
- Workspace persistence can mask improvements if old prefs are reused without migration.
- Test fixtures may need updates because queue view IDs and owner control semantics will change.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no backend-side saved views model; no per-role customizable queue presets.
- `Why not in this block`: this block fixes the operator contract and first-screen UX first.
- `Risk if deferred`: the queue can still feel locally configurable rather than operationally governed.
- `Linked follow-up Task Package(s)`: `TBD Wave17 closeout / possible Wave18 saved views if needed after operator validation`
- `Expiry/trigger to stop deferral`: if managers still need explanation for how queue mode differs from owner scope after this block, the redesign is not complete.

## Next-block contract (mandatory)
- `Next block objective`: finish Wave17 by landing the new filter contract and final rail cleanup, then reassess whether only live validation remains open in the master program.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `Blocked-by conditions`: regressions in queue selection, persistence, or bulk toolbar.
- `Owner role for closure`: Brain / Top Architect.
