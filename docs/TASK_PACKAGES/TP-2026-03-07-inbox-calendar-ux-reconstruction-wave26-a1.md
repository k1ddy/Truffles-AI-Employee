# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE26-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE25-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE25-A1
- `UNLOCKS`: shareable queue URLs and governed handoff links on top of the same saved-view object

## Название/цель
Добавить managed team presets для `Заявки` и `Записи` поверх личных saved views, чтобы owner/admin задавал branch/role-specific operational defaults и команда входила в единый операционный контур без локального drift.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: bounded split allowed: `Part A managed preset backend + contract`, `Part B frontend governance/default rollout`
- `Cleanup`: Brain / Top Architect after Wave26 is merged and verified

## FACT pre-check (before implementation)
- Wave24 canon is already server-owned and stable: `truffles-api/app/services/console_queue_state.py`, `console-web/src/lib/queue-state.ts`.
- Wave25 personal named saved views are already implemented on top of the canon, but they are still agent-owned and cannot impose a shared team operating contour: `truffles-api/app/models/console_saved_view.py`, `truffles-api/app/services/console_saved_views.py`, `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`.
- The product gap remains exactly the owner-approved one: personal views alone are useful, but they do not give owner/admin a governed default queue mode per branch/role.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.zendesk.com shared views default views admins agents team support`
- **Date/time (local):** `2026-03-07T20:06:00+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- **Ready solutions found:** mature help-desk products separate personal views from admin-managed/shared views, keep both as server-owned objects, and apply shared defaults as an operating baseline instead of browser-local preference.
- **Decision (`reuse/integrate/build`):** `integrate` — extend the exact Wave25 saved-view object with managed ownership/targeting fields instead of creating a parallel preset model.
- **Rejected options:** a separate `team_presets` table with duplicated queue payload semantics; frontend-only team defaults; letting personal defaults outrank team-governed defaults.
- **Source quality:** high-signal primary source = official Zendesk documentation.

## Root cause (mandatory)
- **Symptom:** after Wave25, each operator can save personal queue views, but owner/admin still cannot set a governed default operating contour for a branch or role.
- **Minimal reproduction:** owner wants branch `Almaty Downtown` managers to land on `Требуют ответа`, while supervisors land on `Все открытые`; today each user can still define only personal defaults and the team does not converge on one shared default state.
- **Evidence:** `truffles-api/app/models/console_saved_view.py`, `truffles-api/app/services/console_saved_views.py`, `console-web/src/components/CaseList.tsx`, `console-web/src/app/calendar/page.tsx`.
- **Five Whys:**
  1. Why do teams still drift after personal saved views? Because all saved objects are agent-owned.
  2. Why is agent ownership insufficient? Because branch/role defaults must be administered, not inferred from personal preference.
  3. Why can’t current-state restore solve this? Because current-state is “last used”, not a governed default.
  4. Why not build separate team presets? Because that would fork the queue-state model immediately after Wave25 proved it.
  5. Why is managed ownership the right next layer? Because it reuses the saved-view canon and adds the missing governance dimension with bounded ACL/targeting.
- **Root cause statement:** the saved-view object still lacks managed ownership and branch/role targeting, so the platform cannot express shared/default queue baselines for a team.
- **Fix mechanism:** extend the saved-view object with managed scope plus target branch/role semantics, make owner/admin CRUD server-owned team presets, and let restore precedence prefer team-managed defaults over personal defaults when there is no current state.

## Reuse-first plan (mandatory)
- **Reuse:** Wave24 queue-state canon, Wave25 saved-view CRUD object, console RBAC/team permissions, current inbox/calendar save/apply helpers.
- **Integrate:** add `scope + created_by + target_branch + target_role` to the saved-view object and reuse the same endpoints with bounded ACL/visibility rules.
- **Build only if needed:** only the minimal targeting/default-selection logic and frontend admin controls; no shareable URL layer and no routing work here.

## Invariant
- Queue-state canon stays singular; no second preset payload model is allowed.
- Team presets must be managed server-side and must not depend on browser-local state.
- Team-managed defaults must outrank personal defaults, but must not outrank explicit URL overrides or existing current-state restores.
- Personal views remain available and editable by the owning agent.
- Shareable URLs and routing automation remain out of scope.

## Scope
- `Part A managed preset backend + contract`:
  - extend saved-view storage with managed ownership and target branch/role fields
  - list both personal and applicable team presets through the existing catalog endpoint
  - enforce owner/admin-only create/update/delete for managed presets
  - define deterministic default precedence for applicable team presets
- `Part B frontend governance/default rollout`:
  - surface team presets in the existing saved-view catalog
  - allow owner/admin to save/update/delete team presets
  - allow owner/admin to assign branch/role targeting and managed default semantics
  - apply managed defaults in inbox/calendar restore only when current-state is absent

## Out of scope
- shareable `view_id` URLs
- audit/event history for preset mutations
- per-user opt-out from team defaults
- richer routing / follow-up owner / supervisor-grade booking governance

## Touch-list
- `truffles-api/app/models/*`
- `truffles-api/app/services/console_saved_views.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/migrations/*`
- `truffles-api/tests/*`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/types/api.generated.ts`

## Managed preset canon (mandatory)
- `Same object, different ownership`:
  - personal saved view = `scope=personal`, owned by one agent
  - managed team preset = `scope=team`, created/maintained by owner/admin, visible to matching branch/role readers
- `Targeting fields`:
  - `target_branch_id` nullable
  - `target_role` nullable
  - `created_by_agent_id` required for managed accountability
- `Default precedence`:
  - `URL override`
  - `server current state`
  - `managed team default` (most specific applicable)
  - `personal default`
  - `local fallback`
- `Excluded from payload`:
  - selected case / panel
  - visible columns / local UI presentation
  - cursor / pagination / transient form state

## Plan (1..N)
1. Extend saved-view storage/service with managed ownership and targeting semantics.
2. Add router/schema changes and deterministic tests for list/apply/default/ACL behavior.
3. Wire frontend catalog to surface personal + team presets in one list with labels.
4. Add owner/admin controls for saving managed presets and targeting branch/role/defaults.
5. Re-run deterministic/backend/frontend checks and sync canon docs.

## DoD
- Owner/admin can create, update, and delete managed team presets for `cases` and `calendar`.
- Readers see personal views plus only the team presets applicable to their branch/role scope.
- Team default restore beats personal default restore when current-state is absent.
- Personal and managed presets still share one saved-view object and one canonical queue payload.
- Existing Wave24/Wave25 behaviors remain green.

## Checks
- `cd truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/models app/services/console_saved_views.py app/routers/console.py app/schemas/console.py tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/queue-state.ts --file src/lib/api-client.ts --file src/components/CaseList.tsx --file src/app/calendar/page.tsx`
- `cd console-web && npm run build`

## Evidence
- migration/model/service diff showing managed scope + targeting
- frontend diff showing managed preset labels/controls/default precedence
- deterministic outputs proving ACL + precedence + contract sync

## Release safety (mandatory)
- **Rollout:** additive on top of Wave25; if no managed presets exist, Wave25 personal behavior must remain unchanged.
- **Go/no-go:** merge only if personal saved views still work and readers without team-write permission can read but not mutate managed presets.
- **Rollback:** revert Wave26 commit(s) and keep Wave25 personal saved views intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave26 checks
- confirm Wave25 personal saved views still save/apply/default correctly

## No-go
- Do not create a second preset table/model with duplicated queue payload semantics.
- Do not allow team defaults to outrank explicit URL overrides or current-state restore.
- Do not move shareable URLs or routing policy into this block.
- Do not leak browser-only presentation state into managed presets.

## Риски/блокеры
- If team presets are modeled separately from saved views, Wave25 canon immediately forks.
- If managed defaults lose to personal defaults, the governance value is mostly lost.
- If branch/role applicability is ambiguous, restore behavior will feel random and untrustworthy.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: shareable queue URLs, bookings supervisor-grade governance, and richer routing remain deferred.
- `Why not in this block`: managed ownership/targeting is the minimum governance layer needed before shareable links and routing automation.
- `Risk if deferred`: handoff still needs manual explanation and routing still lacks governed operating slices, but branch/role defaults become explicit and reusable.
- `Linked follow-up Task Package(s)`: next block must be shareable queue URLs built on the same `view_id` object.
- `Expiry/trigger to stop deferral`: once Wave26 is green, any further queue collaboration work must reuse `view_id` rather than inventing opaque URL blobs or a third preset model.

## Next-block contract (mandatory)
- `Next block objective`: add shareable queue URLs backed by `view_id` and explicit override precedence on top of the same managed/personal saved-view catalog.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Managed preset canon|Default precedence|scope=team" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md`
- `Blocked-by conditions`: any regression in Wave24 current-state restore, any attempt to split managed presets into a separate payload model, or any unresolved ambiguity in team-vs-personal default precedence.
- `Owner role for closure`: Brain / Top Architect.
