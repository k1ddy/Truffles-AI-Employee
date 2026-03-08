# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE18-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-CLOSEOUT-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE18-CLOSEOUT-A1

## Название/цель
Исправить correctness фильтров во вкладке `Заявки` не как UI-polish, а как строгий `filter-state contract`. Цель — формально определить допустимые состояния и приоритеты `queue view / owner scope / refinements / persistence / role constraints`, затем привести код к этому контракту и доказать это deterministic-проверками.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected if the contract extraction and the final UI/correctness rollout do not fit safely into one PR
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `queue view` still mutates refinement fields via `applyFilters`, so one axis can silently rewrite another: `console-web/src/components/CaseList.tsx:309`, `console-web/src/components/CaseList.tsx:330`, `console-web/src/components/CaseList.tsx:351`, `console-web/src/components/CaseList.tsx:372`, `console-web/src/components/CaseList.tsx:393`, `console-web/src/components/CaseList.tsx:1071`.
- Advanced controls are partially disabled exactly when refinements are active, which makes the rail feel contradictory instead of explicit: `console-web/src/components/CaseList.tsx:620`, `console-web/src/components/CaseList.tsx:1290`, `console-web/src/components/CaseList.tsx:1333`.
- Role restrictions are enforced by a post-render effect that silently rewrites `ownerScope`, instead of by a pre-query contract, so invalid owner combinations can briefly exist in state: `console-web/src/components/CaseList.tsx:690`.
- Persistence still stores a mixed state bag (`filters`, `ownerScope`, view flags) without a declared persistence contract by axis; this risks stale restores even after Wave17 cleanup: `console-web/src/components/CaseList.tsx:101`, `console-web/src/components/CaseList.tsx:523`, `console-web/src/components/CaseList.tsx:1023`, `console-web/src/lib/inbox-workspace.ts:37`.
- Current e2e coverage proves some happy paths, but it does not prove the full matrix of allowed/forbidden combinations or emitted query params for each axis.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management best practices for managing queues at scale filters`
- **Date/time (local):** `2026-03-07T09:34:00+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
- **Ready solutions found:** queue/view semantics should stay distinct from secondary dropdown filters; queue focus must reduce mental load, while search and dropdown filters refine the current queue instead of overwriting it.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the existing inbox route and server queue semantics, but replace the current implicit state logic with an explicit filter contract and deterministic validation matrix.
- **Rejected options:** another visual-only cleanup; adding helper text instead of fixing precedence; leaving silent state rewrites in effects.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** filters still produce logically inconsistent outcomes; managers cannot reliably predict what the queue should show after changing mode, owner, refinements, or reopening the workspace.
- **Minimal reproduction:** on `Заявки`, switch queue modes, set owner scope, add status/date/diagnostic refinements, collapse/restore the filter rail, and reload the workspace under different roles; some state transitions silently reset or disable other axes.
- **Evidence:** `console-web/src/components/CaseList.tsx:309`, `console-web/src/components/CaseList.tsx:620`, `console-web/src/components/CaseList.tsx:690`, `console-web/src/components/CaseList.tsx:1071`, `console-web/src/lib/inbox-workspace.ts:37`.
- **Five Whys:**
  1. Why do filters still feel wrong after Wave17? Because the UI is cleaner, but the precedence/state model is still implicit.
  2. Why is that dangerous? Because one control can still mutate another axis without an explicit business rule.
  3. Why do users experience this as “неправильно работает”? Because the queue result changes for reasons they cannot infer from the visible controls.
  4. Why is the current implementation hard to trust? Because some invalid combinations are corrected after render by side effects instead of being impossible by contract.
  5. Why wasn't this solved by Wave17? Because Wave17 addressed the surface model, but not the full state machine and allowed-combination matrix.
- **Root cause statement:** the inbox rail still lacks a formal filter-state contract with explicit precedence, allowed combinations, role gating, and persistence rules, so state transitions remain partially implicit and can violate business logic.
- **Fix mechanism:** define a pure filter-state contract, move normalization/transition logic into deterministic helpers, enforce role and persistence rules before querying, and validate all key combinations through targeted deterministic tests.

## Reuse-first plan (mandatory)
- **Reuse:** existing `/cases` server query params, current queue view ids, workspace storage keys, Playwright inspect-case harness.
- **Integrate:** extract pure transition/query helpers and rewire `CaseList` to consume them.
- **Build only if needed:** add a dedicated helper module for filter-state resolution and a deterministic matrix test surface.

## Invariant
- No silent reset of one filter axis by another without an explicit business rule.
- No post-render correction of invalid role/state combinations.
- No regression of queue loading, case selection, bulk actions, or workspace persistence.
- No PR before the matrix of allowed states is deterministic and green.

## Scope
- `Part A contract extraction`:
  - define canonical axes: `queue_view`, `owner_scope`, `refinements`, `presentation`, `persistence`, `role_constraints`;
  - define precedence/allowed combinations;
  - extract pure helpers for state normalization and request param composition.
- `Part B rollout + verification`:
  - rewire `CaseList` to use the new contract;
  - eliminate silent state rewrites and contradictory disabled states;
  - add deterministic coverage for query-param emission and key UI state transitions.

## Out of scope
- New queue features such as saved views.
- Backend queue semantics redesign.
- New top-level navigation changes.

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/lib/*` (new filter-state helper only if needed)
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Filter-state contract (mandatory)
- `queue_view`:
  - selects the base operational slice only;
  - may define a default sort hint;
  - must not clear owner scope or active refinements.
- `owner_scope`:
  - mutually exclusive: `all | mine | unassigned | agent`;
  - role-gated before query composition, not after render.
- `refinements`:
  - `status`, `branch`, `date_from`, `date_to`, `has_delivery_error`, `has_pending_outbox`, `has_human_lock`, explicit `sort_by` override;
  - always remain explicit chips when active.
- `presentation`:
  - collapsed/open state, visible fields, auto refresh.
- `persistence`:
  - persists only canonical contract values;
  - invalid persisted states must normalize before first query.

## Truth-table slices (mandatory)
1. `queue_view` change keeps `owner_scope` unchanged.
2. `queue_view` change keeps active refinements unchanged unless the refinement itself is invalid by contract.
3. non-privileged role cannot emit `assignee_id` or `unassigned` query params even if stale state was restored.
4. active refinements remain removable and never disable the only path to changing them.
5. `resetAllFilters` resets all axes to canonical defaults.
6. persistence restore emits the same canonical request as a fresh manual selection.

## Plan (1..N)
1. Create the Wave18 TP and sync session/master canon.
2. Extract the filter contract into deterministic helpers.
3. Replace implicit effects/silent resets in `CaseList`.
4. Extend deterministic coverage around key state transitions and query params.
5. Capture refreshed screenshot evidence.

## DoD
- Filter precedence is explicit in code, not inferred from effects.
- Queue view no longer silently rewrites owner/refinement axes.
- Role-gating happens before query emission.
- Advanced filter controls are no longer contradictory when refinements are active.
- Deterministic checks cover the contract matrix, not only one happy path.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for touch-list.
- Deterministic check output.
- Updated screenshot.
- Session log with explicit closure status for Part A / Part B.

## Release safety (mandatory)
- **Rollout:** bounded inbox-only change on the current route.
- **Go/no-go:** merge only if matrix checks are green and no queue/bulk regression appears.
- **Rollback:** revert the bounded Wave18 commit/PR.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave18 checks

## No-go
- Another UI-only pass without a formal state contract.
- Silent state normalization in render/effects where a deterministic pre-query contract is required.
- Declaring correctness without deterministic matrix coverage.

## Риски/блокеры
- `CaseList.tsx` is still large; extraction may need a helper module to keep the contract testable.
- Existing workspace persistence can mask regressions if normalization is not applied before first query.
- Current Playwright lane may need query-level assertions, not only visual assertions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no named saved views; no team-managed queue presets.
- `Why not in this block`: this block is strictly about correctness of the current filter model.
- `Risk if deferred`: optional productivity features remain missing, but correctness and predictability are the current blocker.
- `Linked follow-up Task Package(s)`: none yet; create only if correctness is proven and operators still need saved views.
- `Expiry/trigger to stop deferral`: if correctness is green but managers still rebuild the same slices manually every day, open a saved-views TP.

## Next-block contract (mandatory)
- `Next block objective`: land Wave18 correctness fixes and prove the filter-state contract with deterministic evidence.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `Blocked-by conditions`: unresolved precedence ambiguity or red deterministic checks.
- `Owner role for closure`: Brain / Top Architect.
