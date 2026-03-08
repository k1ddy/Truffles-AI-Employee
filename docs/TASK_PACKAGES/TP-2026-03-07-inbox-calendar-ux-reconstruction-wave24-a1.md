# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE24-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE23-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE23-A1
- `UNLOCKS`: queue-state-backed saved views, managed team presets, and shareable queue URLs

## Название/цель
Построить server-owned `Queue State Canon` для `Заявки` и `Записи`, чтобы operational queue state перестал быть browser-local набором флагов и стал единым контрактом для current state, будущих saved views, managed presets, shareable URLs и explainable routing.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected: `Part A queue-state schema/storage`, `Part B frontend rollout + URL codec`
- `Cleanup`: Brain / Top Architect after the queue-state foundation is merged and verified

## FACT pre-check (before implementation)
- Inbox queue prefs are persisted only through `readInboxCaseListPrefs`/`writeInboxCaseListPrefs` in browser storage: `console-web/src/lib/inbox-workspace.ts:171`, `console-web/src/lib/inbox-workspace.ts:175`.
- `CaseList` builds `/cases` requests directly from local React state and browser-restored prefs, not from a server-owned queue object: `console-web/src/components/CaseList.tsx:645`, `console-web/src/components/CaseList.tsx:955`, `console-web/src/lib/inbox-case-filters.ts:214`.
- Calendar queue prefs are also browser-local, and the shareable route carries only context ids: `console-web/src/app/calendar/page.tsx:70`, `console-web/src/app/calendar/page.tsx:133`, `console-web/src/app/calendar/page.tsx:148`.
- Backend `/cases` rejects unknown query params and exposes only the current filter surface, so any future `view_id`/`preset_id` must be designed intentionally: `truffles-api/app/routers/console.py:11022`.
- Backend `/bookings` has a stable list contract, but no owner/due/history queue-state layer yet: `truffles-api/app/routers/calendar.py:1017`, `truffles-api/app/routers/calendar.py:136`.
- Routing remains hard-coded to `least_open_cases`, so future automation should not start before a better operational state model exists: `truffles-api/app/schemas/console.py:1087`, `truffles-api/app/routers/console.py:6174`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management best practices managing queues at scale filters views`
- **Date/time (local):** `2026-03-07T17:41:40+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
  - `https://knowledge.hubspot.com/help-desk/search-for-tickets-in-help-desk`
- **Ready solutions found:** queue systems work best when the base queue slice is explicit, secondary filters remain explicit refinements, and the resulting view is reproducible rather than trapped in browser-local state.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse existing `/cases` and `/bookings` execution filters, but wrap them in a canonical server-owned queue-state contract and URL/state precedence model.
- **Rejected options:** start with saved-view naming before canon exists; store queue state only in localStorage; serialize the whole queue state as an opaque blob in URLs.
- **Source quality:** high-signal primary sources = official Atlassian and HubSpot documentation.

## Root cause (mandatory)
- **Symptom:** operators can use the current inbox/calendar surfaces, but cannot reliably reproduce or govern the same queue state across sessions, colleagues, or future automation layers.
- **Minimal reproduction:** set a useful queue in `Заявки` or `Записи`, reload in another browser/operator, or try to express the same state as a stable URL or an admin-managed preset.
- **Evidence:** `console-web/src/lib/inbox-workspace.ts:6`, `console-web/src/components/CaseList.tsx:645`, `console-web/src/app/calendar/page.tsx:175`, `truffles-api/app/routers/console.py:11022`, `truffles-api/app/routers/calendar.py:1017`.
- **Five Whys:**
  1. Why is queue state not reproducible? Because it is browser-local.
  2. Why is that a problem? Because shared handoff/presets need a server-owned object.
  3. Why can't URLs solve it now? Because routes carry context, not canonical queue state.
  4. Why can't we jump straight to saved views? Because there is no shared queue-state canon underneath.
  5. Why is routing also blocked? Because richer routing should consume stable operational state, not fragmented local UI state.
- **Root cause statement:** queue state is currently mixed across local storage, route context, and strict server query params without one canonical server-owned representation, so the platform cannot safely layer reproducible views, team defaults, or richer automation.
- **Fix mechanism:** introduce a formal `Queue State Canon`, separate shareable operational state from local presentation state, add server-backed current-state storage plus URL precedence, and keep current `/cases` and `/bookings` contracts as the execution engines.

## Reuse-first plan (mandatory)
- **Reuse:** existing `/cases` filters and queue-view semantics, existing `/bookings` list filters, current workspace scopes, current case/calendar UI surfaces, existing deterministic/e2e harnesses.
- **Integrate:** server-backed queue-state schema/storage + query-state adapters + URL codec layered onto current routes.
- **Build only if needed:** one new backend model/migration/API surface for current queue state; no saved-view catalog yet.

## Invariant
- No regression of current queue semantics or Wave22 forbidden-state guarantees.
- No mutation side-effects by `conversation -> latest case`; explicit `case_id` remains the only safe mutation anchor.
- Role gating and owner-scope normalization stay deterministic before request emission.
- `selected case`, side panel mode, and similar local workspace context must not be silently mixed into future shared/preset queue state.

## Scope
- `Part A queue-state schema/storage`:
  - define canonical server-owned queue state for `cases` and `calendar`
  - separate operational `query_state` from local `workspace_presentation_state`
  - add read/write API for current queue state per operator scope and surface
- `Part B frontend rollout + URL codec`:
  - make `CaseList` and `CalendarPage` read/write canonical queue state
  - define precedence `URL -> server current state -> local migration fallback`
  - keep localStorage only as bounded migration fallback, not source of truth

## Out of scope
- naming/saving multiple personal views
- admin-managed presets/defaults
- share-by-`view_id` catalog
- richer routing policies beyond the current operator flow

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/models/*` (new queue-state model if needed)
- `truffles-api/migrations/*` (new queue-state migration)
- `truffles-api/tests/*` (new queue-state API/contract coverage)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/lib/inbox-case-filters.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/inspect_case.spec.ts`

## Queue-state canon (mandatory)
- `Operational query state` (shareable/preset-eligible):
  - `surface`: `cases | calendar`
  - `mode_scope`: for cases `open | resolved | all`; for calendar current `attention | all`
  - `base_view`: cases `queue_view`; calendar `lane`
  - `owner_scope`: explicit owner axis where supported
  - `refinements`: query, status, branch/date filters, diagnostics, explicit sort override
  - `version`: canonical schema version
- `Workspace presentation state` (local-only unless later approved):
  - selected case
  - side panel open mode
  - visible columns/fields
  - collapsed drawers/panels
  - transient form state
- `Precedence`:
  - explicit URL state wins for reproducible opens
  - server current state is the default restore source
  - localStorage is migration fallback only and must be normalized before use

## Plan (1..N)
1. Define backend schema/model for canonical queue state and its scope resolution.
2. Add bounded read/write API for current queue state per surface/operator scope.
3. Refactor inbox/calendar frontend to consume canonical queue state.
4. Add URL codec for operational query state only.
5. Extend deterministic + e2e coverage for precedence, restore, and request emission.

## DoD
- Inbox/calendar current queue state is no longer localStorage-only.
- The same operator scope can restore the same queue state on a fresh browser session from the server contract.
- Canonical queue URLs can reproduce queue state without depending on previous browser storage.
- Local workspace context remains separate from shareable/preset-eligible state.
- Existing `/cases` and `/bookings` execution semantics remain green under deterministic tests.

## Checks
- `cd truffles-api && pytest -q tests/test_console_queue_state_api.py tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/console.py app/routers/calendar.py app/schemas/console.py tests/test_console_queue_state_api.py tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/inbox-workspace.ts --file src/lib/inbox-case-filters.ts --file src/components/CaseList.tsx --file src/app/calendar/page.tsx --file src/lib/calendar-bookings.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line --workers=1`

## Evidence
- backend schema/migration/API diff for queue-state canon
- updated OpenAPI contract
- frontend queue-state restore/URL behavior diff
- deterministic/e2e output proving precedence and reproducibility

## Release safety (mandatory)
- **Rollout:** additive and backward-compatible; localStorage fallback remains available during migration.
- **Go/no-go:** merge only if inbox/calendar still load correctly without saved views/presets enabled.
- **Rollback:** revert the bounded Wave24 PR and fall back to current local-state behavior.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave24 checks
- ensure inbox/calendar still operate on the previous local-state path

## No-go
- Build saved-view UI before queue-state canon exists.
- Put `selected case` or side-panel state into the shared queue-state object by default.
- Replace explicit query params with opaque URL blobs as the main contract.
- Expand routing policy in the same block.

## Риски/блокеры
- Mixing presentation state back into operational queue state would recreate the same defect under a new name.
- If backend storage scope is too broad or too narrow, restores will feel random to operators.
- If Wave24 tries to include named views and team presets, the block will likely sprawl and lose determinism.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: named saved views, managed team presets, shareable catalog-level URLs, bookings supervisor-grade follow-up ownership/history, and richer routing remain future layers.
- `Why not in this block`: Wave24 is the foundation block; it must stop at queue-state canon and reproducible current-state behavior.
- `Risk if deferred`: those features stay unavailable, but the foundation becomes safe enough to add them without duplicating state models.
- `Linked follow-up Task Package(s)`: create the next follow-up TP only after Wave24 closure evidence is green.
- `Expiry/trigger to stop deferral`: if Wave24 lands and operators still manually rebuild the same queue states, the next block must immediately open around saved views/presets.

## Next-block contract (mandatory)
- `Next block objective`: layer named saved views and governed presets on top of the proven queue-state canon.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Queue State Canon|Operational query state|Workspace presentation state|Precedence" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `Blocked-by conditions`: none before execution; during implementation the block is blocked by any regression in Wave22 semantic guarantees or queue loadability.
- `Owner role for closure`: Brain / Top Architect.
