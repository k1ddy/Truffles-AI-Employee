# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE29-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE28-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE28-A1
- `UNLOCKS`: richer routing v2 / optional auto-apply only after v1 scoring proves stable

## Название/цель
Реализовать `Wave29 richer routing v1` как explainable, recommendation-first policy contract поверх уже явных queue-state и booking governance сигналов. Новый policy не должен молча подменять `least_open_cases`: оператор явно выбирает его в текущих reassignment surfaces и получает серверное объяснение решения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: same PR branch, additive bounded diff only
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Existing routing contract still supports only `least_open_cases`: `truffles-api/app/schemas/console.py`, `truffles-api/app/routers/console.py`, `console-web/src/types/api.generated.ts`.
- Wave28 made booking follow-up ownership/due explicit on `appointments`, so routing can now consume real `NO_SHOW` accountability instead of inferring from raw booking status alone: `truffles-api/app/models/appointment.py`, `truffles-api/app/routers/calendar.py`, `truffles-api/app/services/appointment_service.py`.
- Reassignment UI already has explicit policy actions, but it still hardcodes `least_open_cases` and does not expose policy selection or richer explainability: `console-web/src/components/CaseConversation.tsx`, `console-web/src/components/CaseList.tsx`, `console-web/src/lib/api-client.ts`.
- Current active delivery PR is `#948`: `https://github.com/k1ddy/Truffles-AI-Employee/pull/948`.

## One web search (mandatory before implementation)
- **Query (exact):** `Dynamics 365 Customer Service unified routing assignment methods skills presence capacity prioritization`
- **Date/time (local):** `2026-03-08T07:25:41+05:00`
- **Sources opened:**
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/overview-unified-routing`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-skill-based-routing`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/assignment-methods`
- **Ready solutions found:** mature service-desk routing separates eligibility and workload from assignment method, keeps prioritization server-owned, and treats skills/presence/capacity as explicit signals instead of UI heuristics.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse current eligible-assignee and load queries, reuse Wave28 booking governance signals, and build one bounded explainable scoring policy that uses only signals already owned by the server.
- **Rejected options:** fake skill/availability fields without backend ownership; silent default replacement of `least_open_cases`; background auto-routing on queue refresh.
- **Source quality:** high-signal primary source = official Microsoft Learn documentation.

## Root cause (mandatory)
- **Symptom:** after Waves 24-28 the queue is governable and shareable, but routing still mostly answers only one question: “who has fewer open cases right now?”
- **Minimal reproduction:** open an active case linked to a `NO_SHOW` booking with explicit `follow_up_owner_id`/`follow_up_due_at`, then compare the current policy recommendation with the operationally correct owner continuity or SLA-sensitive handoff.
- **Evidence:** `truffles-api/app/routers/console.py`, `truffles-api/app/schemas/console.py`, `truffles-api/app/models/appointment.py`, `console-web/src/components/CaseConversation.tsx`, `console-web/src/components/CaseList.tsx`.
- **Five Whys:**
  1. Why is routing still too shallow? Because the only policy is `least_open_cases`.
  2. Why is that now insufficient? Because the platform already carries richer server-owned signals: follow-up owner, due time, overdue backlog, and case SLA risk.
  3. Why can’t UI heuristics patch it? Because routing must stay server-owned, auditable, and identical across single-case and bulk flows.
  4. Why not jump straight to skills/presence? Because those signals are not yet modeled server-side for console assignee options.
  5. Why is explicit explainability required? Because supervisors need to trust and debug the policy before any future auto-apply wave.
- **Root cause statement:** routing maturity is blocked not by lack of UI controls, but by the absence of a second, server-owned scoring policy that consumes the explicit governance signals already introduced in Waves 24-28.
- **Fix mechanism:** add an opt-in policy `follow_up_sla_balance` with explicit score/explainability fields, feed it real booking follow-up and case SLA signals on the backend, and expose a small policy selector in existing reassignment surfaces.

## Reuse-first plan (mandatory)
- **Reuse:** current assignee eligibility/load queries, existing reassign and bulk-action endpoints, Wave28 booking governance data, existing audit/idempotency flow, current reassignment UI panels.
- **Integrate:** add richer routing evaluation on top of current case/booking state and thread it through `GET /cases/{case_id}/assignees`, `POST /cases/{case_id}/reassign`, and `POST /cases/bulk`.
- **Build only if needed:** one bounded routing helper/service, one score breakdown schema, and minimal UI selector state.

## Invariant
- `least_open_cases` must remain available as explicit fallback.
- No routing signal may be inferred from `conversation -> latest case`; booking signals remain tied to explicit `appointments.case_id`.
- No fake `skills`, `presence`, or `availability` fields may be introduced in the routing path.
- New policy must remain recommendation-first; no hidden background auto-apply.
- Existing manual reassignment and bulk routing behavior must not regress.

## Scope
- Backend:
  - add routing policy literal `follow_up_sla_balance`
  - compute booking routing context from explicit `NO_SHOW` follow-up owner/due/overdue state
  - compute case SLA-sensitive load weighting from existing server health signals
  - return explainability fields (`reason`, `score`, breakdown) in routing decision
  - support optional `policy` query param on `/cases/{case_id}/assignees`
- Frontend:
  - expose explicit policy selection in current single-case and bulk routing surfaces
  - default the UI selector to `follow_up_sla_balance` while keeping backend default backward-compatible
  - surface the richer server explanation without introducing a new page/tab

## Out of scope
- real skill-based or presence-based routing
- hidden auto-routing on inbox refresh
- a new supervisor routing dashboard
- appointment queue auto-reassignment
- changing saved-view/share-URL canon

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/console_case_routing.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/types/api.generated.ts`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Routing policy canon (mandatory)
- `Policies supported`:
  - `least_open_cases`
  - `follow_up_sla_balance`
- `Signals allowed in Wave29`:
  - eligible assignee branch/client membership
  - current open-case load
  - current case owner continuity
  - linked booking `NO_SHOW` follow-up owner
  - linked booking follow-up due timestamp / overdue state
  - case SLA risk from existing server health signals
- `Signals explicitly excluded`:
  - skills
  - presence / availability
  - speculative manual preferences not stored on server
- `Explainability minimum`:
  - `policy`
  - `reason_code`
  - `reason_summary`
  - `recommended_score`
  - `current_score` when present
  - bounded `score_breakdown`

## Plan (1..N)
1. Create Wave29 TP and switch session canon to the new routing block.
2. Implement a bounded backend routing helper with booking + SLA-aware scoring and backward-compatible policy normalization.
3. Extend routing schema/OpenAPI and wire the policy through assignee list, single-case reassign, and bulk route paths.
4. Add explicit policy selectors in `CaseConversation` and `CaseList`, defaulting the UI to `follow_up_sla_balance`.
5. Re-run targeted tests/build, update session/master docs, and push the PR branch.

## DoD
- Backend supports `follow_up_sla_balance` without regressing `least_open_cases`.
- Routing decisions expose explainable score fields and reasons.
- Single-case and bulk routing can explicitly use the new policy from current UI surfaces.
- Linked booking follow-up ownership/due state actually influences routing where applicable.
- Targeted backend/frontend checks are green.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py app/services/console_case_routing.py tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx`
- `cd console-web && npm run build`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- backend diff showing new policy contract and explainability fields
- targeted tests proving follow-up continuity / SLA weighting decisions
- frontend diff proving explicit policy selection in current routing surfaces
- OpenAPI/generated-types sync and session canon updates

## Release safety (mandatory)
- **Rollout:** opt-in through explicit policy selector in current routing actions; legacy policy stays available.
- **Go/no-go:** merge only if `least_open_cases` still works unchanged, new policy is explainable, and no cross-branch routing regression appears.
- **Rollback:** revert Wave29 diff; current Wave12/Wave24-28 routing and queue contracts remain intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave29 checks
- confirm `least_open_cases` paths still pass

## No-go
- Do not make `follow_up_sla_balance` the silent backend default.
- Do not encode booking routing via frontend-only heuristics.
- Do not introduce placeholder skills/presence fields just to satisfy the product narrative.
- Do not bypass explicit booking ownership/due semantics in favor of raw `NO_SHOW` status alone.

## Риски/блокеры
- If SLA weighting is too aggressive, routing may thrash ownership instead of helping supervisors.
- If follow-up continuity is too weak, the new policy degenerates back into `least_open_cases`.
- If explainability is thin, the team will not trust the new policy enough for a future v2 rollout.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no real skills/presence/capacity signals yet; no auto-apply.
- `Why not in this block`: those signals are not modeled in current assignee contract and would create fake maturity if guessed now.
- `Risk if deferred`: richer routing remains useful but not yet workforce-grade for real availability balancing.
- `Linked follow-up Task Package(s)`: future Wave30 for skills/presence/capacity only if Wave29 explainable scoring proves useful and the underlying server data model exists.
- `Expiry/trigger to stop deferral`: once assignee availability/skills become server-owned, `least_open_cases` and `follow_up_sla_balance` are no longer sufficient as the top policy set.

## Next-block contract (mandatory)
- `Next block objective`: validate whether Wave29 explainable routing is stable enough for richer routing v2 or whether the next necessary investment is assignee capability/presence modeling.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "follow_up_sla_balance|Routing policy canon|Explainability minimum" docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md`
- `Blocked-by conditions`: any regression in Wave24-28 queue-state/saved-view/share-link/governance contracts, or any attempt to fake missing skills/presence signals, blocks the block immediately.
- `Owner role for closure`: Brain / Top Architect.
