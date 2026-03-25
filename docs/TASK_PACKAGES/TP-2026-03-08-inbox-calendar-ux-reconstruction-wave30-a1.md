# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE29-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE29-A1
- `UNLOCKS`: bounded routing v2 only after agent routing constraints become server-owned and deterministic

## Название/цель
Реализовать следующий честный слой routing maturity после Wave29: server-owned assignee routing profiles для `Заявки`. Цель блока — добавить admin/team-lead управляемые availability/capacity/manual-restriction сигналы без fake `skills/presence` и без смешивания их с frontend-only state.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: same PR branch, additive bounded diff only
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Wave29 already made routing explainable, but assignee eligibility is still based only on access scope (`agent_memberships` / legacy `agents.branch_id`) and current load; there is no server-owned status/capacity profile for routing: `truffles-api/app/routers/console.py:6080`, `truffles-api/app/services/console_case_routing.py`.
- Current assignee option selection collapses multiple applicable memberships by overwrite order, not by explicit routing-profile precedence; there is no dedicated operational contract for assignment constraints: `truffles-api/app/routers/console.py:6091`.
- Existing server-owned data is enough for one bounded next step:
  - access scope and branch restrictions: `truffles-api/app/services/console_auth.py`, `truffles-api/app/models/agent_membership.py`
  - team admin CRUD already exists: `/console/v1/admin/memberships`, `/console/v1/agents`, `console-web/src/app/team/page.tsx`
  - booking follow-up continuity already exists from Wave28 and can be reused when a profile says `follow_up_only`: `truffles-api/app/routers/calendar.py`, `truffles-api/app/models/appointment.py`
- Missing signals remain missing facts, not implementation gaps:
  - no server-owned assignee skills matrix
  - no assignee presence/online heartbeat
  - no assignee schedule/shift model

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk omnichannel routing agent status capacity official`
- **Date/time (local):** `2026-03-08T08:43:29+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408834888730-Setting-an-agent-s-status-in-omnichannel-routing`
  - `https://support.zendesk.com/hc/en-us/articles/4408829095066-About-omnichannel-routing-and-agent-status`
  - `https://support.zendesk.com/hc/en-us/articles/4408821965210-Understanding-omnichannel-routing`
- **Ready solutions found:** mature routing separates agent availability/status from account enablement, treats capacity as a first-class server-owned limit, and keeps routing eligibility deterministic before assignment scoring.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse current access/membership and reassignment surfaces, then build one bounded routing-profile layer for status/capacity/manual restriction signals instead of faking skills/presence.
- **Rejected options:** disabling whole accounts to pause routing; frontend-only “available/busy” toggles; jumping directly to skill-based routing without a server-owned assignee profile model.
- **Source quality:** high-signal primary source = official Zendesk support documentation.

## Root cause (mandatory)
- **Symptom:** after Wave29 the team can explain *why* a recommendation was chosen, but supervisors still cannot tell the router “do not send new work to this agent now” without bluntly disabling access or mutating membership scope.
- **Minimal reproduction:** list assignees for a case where one manager is still active in Console but should not receive new cases today; the current routing contract still treats that manager as equally eligible if access scope and open-case load allow it.
- **Evidence:** `truffles-api/app/routers/console.py:6080`, `truffles-api/app/services/console_case_routing.py`, `truffles-api/app/models/agent_membership.py`, `console-web/src/app/team/page.tsx`.
- **Five Whys:**
  1. Why does routing still feel operationally incomplete? Because it optimizes only across eligible access + load.
  2. Why is that insufficient? Because supervisors need manual availability/capacity restrictions that are weaker than disabling access and stronger than UI hints.
  3. Why can’t membership edits alone solve it? Because access scope and routing intent are different concerns; rescoping a membership is too blunt and not deterministic enough for routing.
  4. Why not add skills/presence now? Because those signals do not exist as server-owned assignee facts in the current console model.
  5. Why does this block come before routing v2? Because richer automation without server-owned assignee constraints will keep routing into locally “busy/off-shift/follow-up-only” people and remain untrustworthy.
- **Root cause statement:** Wave29 improved scoring, but routing is still missing a dedicated server-owned assignee operational profile for status/capacity/manual restriction signals; access scope alone is not a sufficient routing contract.
- **Fix mechanism:** add scoped `console_routing_profiles`, resolve them deterministically per case branch/client, surface them in assignee options/admin UI, and make both current routing policies honor those server-owned constraints.

## Reuse-first plan (mandatory)
- **Reuse:** current agent/membership auth model, existing assignee list and reassign endpoints, Wave29 explainable scoring, existing Team admin page and admin API shell.
- **Integrate:** add routing profiles as a separate server-owned model applied after access eligibility and before scoring.
- **Build only if needed:** one new backend model/service/migration, one bounded admin CRUD surface, and minimal Team UI controls for status/capacity.

## Invariant
- Do not invent `skills`, `presence`, or shift availability not already owned by the server.
- Do not overload `agent_memberships` rescope/role changes as the primary “pause routing” mechanism.
- `least_open_cases` and `follow_up_sla_balance` must both honor the same routing-profile constraints.
- Current assignee must stay visible in routing responses even if newly paused/at-capacity; recommendation logic may not silently erase continuity context.
- Existing access control and branch restriction semantics must not regress.

## Scope
- Backend:
  - add server-owned routing profile model per `client_id + agent_id + optional branch_id`
  - support bounded status enum for routing: `available`, `paused`, `follow_up_only`
  - support optional `max_open_case_count`
  - resolve effective profile by precedence `branch profile -> client profile -> default`
  - extend assignee options with routing-profile facts and effective eligibility markers
  - make current routing policies honor `paused`, `follow_up_only`, and capacity limits deterministically
  - add admin list/upsert API for routing profiles in current Team governance plane
- Frontend:
  - show/edit routing profile status + capacity in current `Team -> Пользователи` surface for the selected client
  - surface assignee status/capacity hints in existing reassignment controls without adding a new routing page

## Out of scope
- real skill-based routing
- presence heartbeat / websocket online state
- work schedules / shifts / calendar-based availability for agents
- automatic assignment on queue refresh
- calendar specialist routing or booking specialist auto-selection

## Touch-list
- `truffles-api/app/models/__init__.py`
- `truffles-api/app/models/console_routing_profile.py`
- `truffles-api/migrations/056_add_console_routing_profiles.sql`
- `truffles-api/app/services/console_case_routing.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `truffles-api/tests/test_console_routing_profiles_api.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/team/page.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/types/api.generated.ts`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Routing profile canon (mandatory)
- `Profile scope`:
  - client-level default
  - optional branch override
- `Statuses supported in Wave30`:
  - `available`: eligible for normal routing
  - `paused`: not eligible for new recommendation, but current-owner context remains visible
  - `follow_up_only`: eligible only for explicit follow-up continuity scenarios or when already current owner
- `Capacity semantics`:
  - `max_open_case_count = null` means no explicit cap
  - when current open case count reaches/exceeds cap, the assignee is not eligible for new recommendation unless current-owner continuity applies
- `Eligibility minimum`:
  - access eligibility still comes first
  - effective routing profile applies second
  - scoring policy applies last
- `Explainability minimum`:
  - assignee option exposes routing status, capacity, and whether the option is eligible for recommendation
  - routing reason may mention profile/capacity exclusion when it affects the recommendation set

## Plan (1..N)
1. Create Wave30 TP and switch active session/master canon to the new block.
2. Implement `console_routing_profiles` model, migration, service helpers, and admin API.
3. Extend assignee option contract and routing evaluation so both existing policies honor status/capacity/follow-up-only constraints deterministically.
4. Wire minimal Team admin controls and reassignment hints in existing surfaces.
5. Re-run targeted checks, sync OpenAPI/types/docs, and push the branch.

## DoD
- Supervisors can pause routing or cap open-case intake for an assignee without disabling the whole account.
- Both current routing policies honor server-owned routing profiles.
- `follow_up_only` works only on explicit continuity cases, not on guessed heuristics.
- Team page exposes bounded routing-profile controls in the current governance surface.
- Targeted backend/frontend checks are green.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/models/console_routing_profile.py app/models/__init__.py app/schemas/console.py app/services/console_routing_profiles.py app/services/console_case_routing.py app/routers/console.py tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/app/team/page.tsx --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx`
- `cd console-web && npm run build`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- backend diff showing routing-profile model/admin API and deterministic eligibility resolution
- targeted tests proving paused/capacity/follow-up-only behavior
- Team UI diff showing bounded routing-profile controls
- OpenAPI/generated-types sync and session canon updates

## Implementation outcome
- `Wave30` implemented locally:
  - backend adds `console_routing_profiles` model + migration + service with deterministic precedence `branch override -> client profile -> default`;
  - admin API now exposes list/upsert/delete for routing profiles, so branch overrides can be removed instead of silently shadowing client defaults forever;
  - assignee options now expose `routing_status`, `routing_profile_source`, `max_open_case_count`, `at_capacity`, `assignment_eligible`, and `assignment_block_reason_code`;
  - both routing policies and manual reassignment now honor paused/capacity/follow-up-only constraints, while preserving current-owner continuity;
  - Team page now exposes bounded routing-profile governance in the existing users surface, and reassignment UIs now show disabled/hinted assignee states instead of pretending every visible assignee is assignable.
- Local evidence:
  - `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py tests/test_console_openapi_calendar_contract.py` → `87 passed`
  - `cd truffles-api && ruff check app/models/console_routing_profile.py app/models/__init__.py app/schemas/console.py app/services/console_routing_profiles.py app/services/console_case_routing.py app/routers/console.py tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py tests/test_console_openapi_calendar_contract.py` → `pass`
  - `cd truffles-api && python3 scripts/generate_openapi.py --check` → `pass`
  - `cd console-web && npm run generate:api` → `pass`
  - `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/app/team/page.tsx --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx` → `pass`
  - `cd console-web && npm run build` → `pass`
  - `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh` → `Session OK`

## Release safety (mandatory)
- **Rollout:** admin-managed, opt-in routing constraints; default remains `available` with no cap for agents without an explicit profile.
- **Go/no-go:** merge only if existing routing still works for agents with no profile and if profile-constrained routing is deterministic in tests.
- **Rollback:** revert Wave30 diff; Wave29 explainable routing remains the active routing maturity layer.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave30 checks
- confirm assignee list and routing recommendation paths behave as before when no profiles exist

## No-go
- Do not model skills/presence in this block.
- Do not require supervisors to disable accounts just to pause routing.
- Do not make routing-profile state browser-local.
- Do not let capacity/status rules silently hide the current assignee from explainability output.

## Риски/блокеры
- If profile precedence is ambiguous, routing will become less trustworthy than Wave29.
- If Team UI becomes overbuilt, this block will sprawl into workforce-management scope.
- If paused/capacity semantics are too aggressive, manual reassignment could become harder instead of clearer.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no real skills matrix, no live presence/heartbeat, no shift schedule model, no auto-apply routing.
- `Why not in this block`: those signals are still absent from the server data model and would create fake maturity if guessed now.
- `Risk if deferred`: routing becomes more governable, but still not workforce-grade for true skill/presence balancing.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `Expiry/trigger to stop deferral`: once assignee skills or presence become real server-owned facts, Wave30 constraints alone are no longer sufficient.

## Next-block contract (mandatory)
- `Next block objective`: open `Wave31` only if Brain/Top Architect can prove new real capability inputs or a bounded routing v2 need beyond Wave30 routing profiles.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave31|capability|routing v2" docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `Blocked-by conditions`: any regression in Wave24-29 contracts, or any attempt to fake missing skills/presence as UI-only state, blocks the block immediately.
- `Owner role for closure`: Brain / Top Architect.
