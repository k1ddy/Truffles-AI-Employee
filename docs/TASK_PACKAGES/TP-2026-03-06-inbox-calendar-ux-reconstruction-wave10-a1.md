# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-PARTB-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-PARTB-A1

## Название/цель
Сделать передачу заявки менее слепой для supervisor/admin и старших менеджеров: показать фактическую текущую нагрузку по доступным исполнителям прямо в существующих `Передать`/owner-filter surface, без нового routing-экрана и без fake availability.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: continue inside existing PR `#932`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Wave9 Part B already made owner/unassigned queue views server-backed, but the reassignment choice is still blind: dropdowns show only names/roles.
  - Queue assignee endpoint already centralizes allowed assignees for a scope, so workload hints can be added without a new route model.
  - There is no factual load signal in the current reassignment UI; supervisor must guess who is least loaded before assigning.

## One web search (mandatory before implementation)
- **Query (exact):** `Salesforce Omni-Channel routing configurations capacity official documentation`
- **Date/time (local):** `2026-03-06T13:04:08+05:00`
- **Sources opened:**
  - `https://help.salesforce.com/s/articleView?id=sf.omnichannel_about_routing.htm&type=5`
- **Ready solutions found:** mature service desks expose capacity/workload signals near routing decisions; they do not force supervisors to assign blindly from a flat name list.
- **Decision (`reuse/integrate/build`):** `integrate` — extend existing assignee option contracts with factual queue-load counts and surface them in current inbox reassignment controls.
- **Rejected options:** fake availability badges without backend evidence; new routing dashboard; silent auto-routing without operator visibility.
- **Source quality:** high-signal primary source = official Salesforce Help documentation.

## Root cause (mandatory)
- **Symptom:** ownership filters are now correct, but the actual `Передать` action still lacks business context about who can take more work.
- **Minimal reproduction:** open any active case, click `Передать`, and try to choose between several managers with no visible difference except name/role.
- **Evidence:** `ConsoleCaseAssigneeOption` currently contains only identity fields; `CaseConversation` and the bulk toolbar render flat select labels.
- **Five Whys:**
  1. Почему routing still feels incomplete? Потому что supervisor видит backlog, но не видит нагрузку исполнителей в точке передачи.
  2. Почему owner filter alone недостаточен? Потому что он помогает анализировать очередь, но не помогает принять решение внутри действия.
  3. Почему нельзя подменить это fake availability? Потому что в коде нет достоверного presence/capacity сигнала, и ТЗ запрещает вводящие в заблуждение цифры.
  4. Почему нужен backend contract, а не только frontend sorting? Потому что factual load должен считаться на сервере по полной очереди, а не по локально загруженному slice.
  5. Почему блок bounded? Потому что здесь закрывается именно factual load visibility; one-click recommended routing остаётся отдельным Part B.
- **Root cause statement:** reassignment remains blind because assignee contracts expose identity only, without factual open-load signal from the full queue scope.
- **Fix mechanism:** extend assignee option schemas with current open-case load and render these signals in single-case and bulk reassignment surfaces.

## Reuse-first plan (mandatory)
- **Reuse:** existing assignee endpoints, Wave6 reassign flows, Wave9 owner-filter governance, current branch/client scoping.
- **Integrate:** compute load counts inside assignee option builders and reuse the same contract in case-level and queue-level selects.
- **Build only if needed:** only additive count fields and compact UI copy; no new routing engine.

## Invariant
- Do not invent availability/capacity claims that are not backed by data.
- Do not add a new top-level route or separate routing page.
- Do not break current reassign, bulk reassign, or Wave9 owner filters.
- Keep manager-readable defaults simple; extra routing signals should help supervisors, not clutter every surface.

## Scope
- add factual load fields to `ConsoleCaseAssigneeOption`;
- compute open assigned-case counts for assignees within the current queue scope;
- show these counts in `CaseConversation` reassign UI and queue/bulk assignee selects;
- keep labels readable in Russian operator copy;
- cover the new contract in tests and deterministic inspect-case lane.

## Out of scope
- Real-time presence/availability tracking.
- Automatic round-robin execution.
- New routing policy engine or SLA redesign.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Create Wave10 TP and move session canon to the new active block.
2. Extend assignee option schema with factual open-load counts from server-side queue scope.
3. Surface these load hints in single-case `Передать` and queue/bulk assignee selects.
4. Update deterministic tests/OpenAPI/types and inspect-case lane.
5. Push the additive Wave10 Part A slice into PR `#932`.

## DoD
- Reassign surfaces no longer show a flat blind list of managers.
- Assignee options expose factual open-case counts from backend scope.
- Bulk and single-case reassign keep working with the new contract.
- No fake availability/presence wording appears in UI.
- OpenAPI/tests/e2e cover the new fields.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/lib/api-client.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Pytest/OpenAPI/generate-api/lint/build/Playwright outputs.
- Updated session log with Wave10 Part A status.

## Release safety (mandatory)
- **Rollout:** continue in PR `#932`; schema extension is additive and only enriches current routing surfaces.
- **Go/no-go:** current reassign actions remain functional; counts match scope and do not mislead operators.
- **Rollback:** revert Wave10 Part A diff; routing falls back to current flat assignee labels.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave10 Part A checks.

## No-go
- Adding invented `online/offline` or `available` badges without backend evidence.
- Building a new routing page before current tabs are exhausted.
- Sorting or auto-selecting assignees purely on the client from partial queue data.

## Риски/блокеры
- Load counts must respect current scope/branch rules and exclude resolved cases.
- Overlong labels can make selects noisy if copy is not compact.
- Reassign and owner-filter surfaces use the same contract but need different emphasis/order.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: operators will see factual load, but one-click recommended routing and policy automation will still be deferred.
- `Why not in this block`: that needs a separate bounded Part B after factual signals are proven stable.
- `Risk if deferred`: supervisors still choose manually, but they choose from factual workload data instead of guessing.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `Expiry/trigger to stop deferral`: if supervisors still need external spreadsheets/chat to decide reassignment after this merge, a dedicated routing-assist Part B becomes mandatory.

## Next-block contract (mandatory)
- `Next block objective`: decide whether to add one-click recommended assignment after factual load signals land and prove stable in the current inbox workflow.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave10 Part A must not regress Wave6 reassign behavior or Wave9 owner governance.
- `Owner role for closure`: Brain / Top Architect.
