# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE27-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE26-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE26-A1
- `UNLOCKS`: supervisor-grade booking governance and queue handoff links without rebuilding queue state again

## Название/цель
Добавить shareable queue URLs для `Заявки` и `Записи` поверх Wave24-26 canon, чтобы ссылка воспроизводила конкретный queue state через явные query params и `view_id`, а handoff не зависел от localStorage или устных инструкций.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: bounded split allowed: `Part A contract/read path`, `Part B URL sync + share UX`
- `Cleanup`: Brain / Top Architect after Wave27 is merged and verified

## FACT pre-check (before implementation)
- Wave24 already made queue state server-owned and URL-parseable by explicit query params, but there is still no queue-link layer for handoff: `console-web/src/lib/queue-state.ts`, `truffles-api/app/routers/console.py`.
- Wave25/26 already provide one saved-view catalog for personal and team-managed queue states, but selection stays local to the current operator unless they manually rebuild filters: `truffles-api/app/models/console_saved_view.py`, `truffles-api/app/services/console_saved_views.py`, `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`.
- The only merged PR on this branch is `#947`; the current unmerged queue-view work is now tracked by `PR #948`: `https://github.com/k1ddy/Truffles-AI-Employee/pull/948`.

## One web search (mandatory before implementation)
- **Query (exact):** `Atlassian Jira Service Management queue URL shared filters official docs`
- **Date/time (local):** `2026-03-07T20:08:18+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
- **Ready solutions found:** mature help-desk queue links keep the queue definition explicit and reproducible, so opening a shared link lands on the same queue slice rather than a browser-local reconstruction.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse explicit queue query params from Wave24 and saved-view ids from Wave25/26 instead of inventing a second URL codec or opaque blob format.
- **Rejected options:** opaque JSON/base64 queue blobs in query string; relying on localStorage restore for shared links; creating a separate `shared_link` server object before queue URLs are proven.
- **Source quality:** high-signal primary source = official Atlassian documentation.

## Root cause (mandatory)
- **Symptom:** useful queue states can now be saved, but handoff still requires “нажми сюда, потом выбери это”, because neither `Заявки` nor `Записи` expose a reproducible share URL contract.
- **Minimal reproduction:** operator selects a saved view or assembles an ad-hoc queue slice, then needs to send the exact queue state to another operator or supervisor.
- **Evidence:** `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`, `console-web/src/lib/queue-state.ts`.
- **Five Whys:**
  1. Why is handoff still manual? Because queue state is not serialized back into a shareable URL.
  2. Why is saved-view selection alone insufficient? Because the active selection is local React state and may include unsaved refinements.
  3. Why not serialize everything as an opaque blob? Because that breaks inspectability, supportability, and the Wave24 canon.
  4. Why not add routing next instead? Because routing needs stable human-operable queue links before automation can safely layer on top.
  5. Why is `view_id + explicit params` the right next layer? Because it reuses the canonical queue state and gives deterministic, inspectable URLs for both saved and unsaved slices.
- **Root cause statement:** the queue-state canon exists, but the runtime never projects the active queue state into a durable URL contract, so saved views and ad-hoc slices remain non-shareable across operators.
- **Fix mechanism:** add `view_id`-aware queue URL semantics, support read access to a specific saved view, sync active queue state into explicit URL params, and expose a one-click share/copy UX in both queue surfaces.

## Reuse-first plan (mandatory)
- **Reuse:** Wave24 queue query-param canon, Wave25/26 saved-view catalog and ACL, current queue-state payload builders.
- **Integrate:** add a read endpoint for one saved view, reuse explicit queue params as the shared contract, and layer URL sync/copy actions into existing queue controls.
- **Build only if needed:** minimal helper logic for `view_id`, URL param stripping, and share-link copy UX; no opaque serializer and no new server object.

## Invariant
- Queue URLs must stay explicit and inspectable; no opaque payload blobs.
- `view_id` must reference the same saved-view object from Wave25/26, not a parallel link model.
- Shared links must still work when the referenced saved view is inaccessible or later changed, by carrying explicit queue params.
- URL state must not absorb local-only presentation state such as selected case, open drawers, visible columns, or transient composer values.
- Rich routing and booking follow-up ownership remain out of scope.

## Scope
- `Part A contract/read path`:
  - add read access to one saved view by `view_id`
  - define `view_id` handling for cases/calendar restore without breaking Wave24 precedence
  - keep explicit queue params as the durable share contract
- `Part B URL sync + share UX`:
  - sync current queue state into the browser URL for `Заявки` and `Записи`
  - include `view_id` in the URL when the current state is anchored to a saved view
  - add copy/share actions in both queue surfaces

## Out of scope
- richer routing / policy scoring
- booking history/archive and follow-up owner governance
- dedicated audit history for link opens
- signed public share links outside authenticated console

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_saved_views_api.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/types/api.generated.ts`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Shareable queue URL canon (mandatory)
- `Explicit params stay canonical`:
  - cases keep queue params like `status`, `queue_view`, `assignee_id`, `branch_id`, `q`, date filters, diagnostics, `sort_by`
  - calendar keeps queue params like `date`, `lane`, `status`, `q`
- `Saved-view anchor`:
  - optional `view_id` points to the same personal/team saved-view object
  - `view_id` never replaces explicit queue params as the durable reproduction contract
- `Restore precedence`:
  - explicit URL queue params
  - URL `view_id` when it resolves
  - server current state
  - managed team default
  - personal default
  - local fallback
- `Excluded from URL`:
  - selected case id in inbox queue state model
  - side panel mode / visible columns
  - cursor, pagination, bulk selection, transient forms

## Plan (1..N)
1. Add backend read contract for a single saved view and cover access semantics.
2. Extend queue-state helpers with `view_id`, queue-param stripping, and share-link builders.
3. Wire cases/calendar restore precedence to honor URL params first and `view_id` second.
4. Sync active queue state back into the browser URL and add copy-link actions in both surfaces.
5. Re-run deterministic checks, sync docs/session state, and push PR updates.

## DoD
- A copied queue URL reproduces the same queue slice in `Заявки` and `Записи` without relying on localStorage.
- URLs may include `view_id`, but explicit queue params remain sufficient to reproduce the state even if that view is unavailable.
- Opening a URL with only `view_id` applies the referenced saved view when access exists.
- Local-only presentation state remains excluded from the URL contract.
- Wave24-26 behavior remains green.

## Checks
- `cd truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/lib/queue-state.ts --file src/components/CaseList.tsx --file src/app/calendar/page.tsx`
- `cd console-web && npm run build`

## Evidence
- router/schema/OpenAPI diff proving `view_id` read contract
- frontend diff proving queue URL sync/copy and restore precedence
- deterministic outputs proving backend access semantics and contract sync

## Release safety (mandatory)
- **Rollout:** additive; if URL has no queue params and no `view_id`, Wave26 defaults/current-state behavior remains unchanged.
- **Go/no-go:** merge only if loading cases/calendar from a plain route still restores the expected current/default state and copied URLs reproduce the queue slice.
- **Rollback:** revert the Wave27 commit(s) and fall back to Wave26 saved-view/default behavior.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave27 checks
- confirm Wave26 personal/team presets still save/apply/default correctly

## No-go
- Do not introduce opaque URL blobs or server-generated share tokens.
- Do not create a separate shared-link model disconnected from saved views.
- Do not put selected case / panel / visible-field state into queue URLs.
- Do not start richer routing or booking-governance work in this block.

## Риски/блокеры
- If URL sync overwrites unrelated route params, case-context calendar mode will regress.
- If `view_id` becomes mandatory for reproduction, personal-view links will break for other operators.
- If queue URLs include local presentation state, supervisor links will become noisy and brittle.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: booking follow-up owner/due/history governance and richer routing remain deferred.
- `Why not in this block`: Wave27 is strictly about reproducible human-operable queue links on top of the existing queue-state canon.
- `Risk if deferred`: routing is still less explainable and bookings queue governance is still not supervisor-grade, but human handoff becomes deterministic.
- `Linked follow-up Task Package(s)`: next block must harden bookings into supervisor-grade governance before richer routing expands.
- `Expiry/trigger to stop deferral`: once Wave27 is green, any further routing or supervisor work must reuse the queue URL canon and the same saved-view ids instead of inventing new ad-hoc state channels.

## Next-block contract (mandatory)
- `Next block objective`: add supervisor-grade booking governance (`follow-up owner`, `due`, `history/archive`) so routing can act on explicit operational ownership rather than inferred booking attention.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Shareable queue URL canon|Restore precedence|view_id" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1.md`
- `Blocked-by conditions`: any regression in Wave24 current-state restore, any attempt to make URL reproduction depend on opaque blobs, or any route-param conflict with calendar case-context mode.
- `Owner role for closure`: Brain / Top Architect.
