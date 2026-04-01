# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE28-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE27-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE27-A1
- `UNLOCKS`: richer routing inputs for booking follow-up without guessing ownership from raw status alone

## Название/цель
Поднять `Записи` до supervisor-grade governance для no-show follow-up: ввести явные `follow-up owner` и `due time`, а также отдельный `history/archive` mode для booking queue, чтобы supervisors управляли ответственностью и backlog явно, а не через бинарное `done/not done` и ручные объяснения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: bounded split allowed: `Part A follow-up governance contract`, `Part B history mode + UI rollout`
- `Cleanup`: Brain / Top Architect after Wave28 is merged and verified

## FACT pre-check (before implementation)
- Booking no-show follow-up is currently only binary audit-state (`done/result/closed_at/closed_by`) with no explicit owner or due contract: `truffles-api/app/routers/calendar.py:146`, `truffles-api/app/routers/calendar.py:349`, `console-web/src/lib/calendar-bookings.ts:13`.
- `GET /calendar/bookings` exposes `lane/status/date/search`, but there is no first-class filter/state for follow-up owner, overdue due-time, or history/archive mode: `truffles-api/app/routers/calendar.py:1017`, `console-web/src/app/calendar/page.tsx:1418`, `console-web/src/app/calendar/page.tsx:1800`.
- When a visit becomes `NO_SHOW`, the related case can reopen correctly, but booking governance is still implicit: no one is explicitly assigned to the follow-up and there is no server-owned due timestamp to supervise or route later: `truffles-api/app/routers/calendar.py:426`, `truffles-api/app/routers/calendar.py:487`, `truffles-api/app/routers/calendar.py:1211`.
- Wave27 already made queue URLs/share links canonical, so this block must extend the same queue-state canon rather than inventing separate history/follow-up state channels.
- Active delivery PR is `#948`: `https://github.com/k1ddy/Truffles-AI-Employee/pull/948`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management queues SLA assignee due date official`
- **Date/time (local):** `2026-03-07T20:29:26+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
- **Ready solutions found:** mature service-desk queues stay explicit about operational slices and are useful only when agents/supervisors can reopen the same filtered backlog instead of reconstructing responsibility from ad-hoc local state.
- **Decision (`reuse/integrate/build`):** `integrate` — extend the current booking queue contract with explicit follow-up ownership/due semantics and one explicit history mode on top of the existing queue-state/URL canon.
- **Rejected options:** keep follow-up responsibility inside audit payload only; encode history as a hidden local toggle; jump straight to richer routing before ownership/due semantics exist.
- **Source quality:** high-signal primary source = official Atlassian documentation.

## Root cause (mandatory)
- **Symptom:** `Записи` can surface no-show attention, but supervisors still cannot answer “кто владелец follow-up?”, “когда просрочка?”, or “покажи историю визитов отдельно от active queue” without manual reconstruction.
- **Minimal reproduction:** mark a booking as `NO_SHOW`, open the calendar queue as owner/admin, and try to manage follow-up backlog or hand it off to another operator.
- **Evidence:** `truffles-api/app/routers/calendar.py`, `truffles-api/app/services/appointment_service.py`, `console-web/src/app/calendar/page.tsx`, `console-web/src/lib/calendar-bookings.ts`.
- **Five Whys:**
  1. Why is no-show backlog still weak for supervisors? Because follow-up is modeled only as “open/closed”.
  2. Why is that insufficient? Because supervision/routing needs explicit owner and due timestamp.
  3. Why can’t existing lane/status filters solve it? Because they show booking state, not accountability state.
  4. Why is history/archive still weak? Because current queue only distinguishes `attention/all` and date filters, not an explicit historical mode.
  5. Why must this be fixed before richer routing? Because routing should consume explicit ownership/due/history semantics, not infer them from `NO_SHOW` alone.
- **Root cause statement:** booking queue semantics stop at status-level attention and do not encode follow-up accountability (`owner`, `due`) or a first-class history mode, so supervisors cannot govern backlog deterministically and future routing would optimize on incomplete state.
- **Fix mechanism:** persist follow-up owner/due on the booking itself, expose governance filters and response fields, add a bounded supervisor mutation path, and extend calendar queue state/URLs with an explicit history mode.

## Reuse-first plan (mandatory)
- **Reuse:** existing appointment model/router, no-show follow-up audit flow, queue-state canon, saved-view/shareable-URL helpers, and existing `/agents` list contract.
- **Integrate:** store governance fields on `appointments`, reuse calendar queue state for `history` mode and `follow_up_*` filters, and layer supervisor UI into the current calendar queue.
- **Build only if needed:** one bounded governance mutation endpoint and the minimum UI controls for owner/due/history; no routing policy expansion here.

## Invariant
- No follow-up automation may rely on `conversation -> latest case` heuristics; booking/case side-effects remain tied to explicit `case_id`.
- Follow-up ownership and due time must be server-owned, not browser-local.
- History/archive mode must reuse the same queue-state and shareable URL canon from Waves 24-27.
- Rich routing remains out of scope until this explicit governance layer is green.
- Existing booking status transitions, no-show reopen, and rebook linkage semantics must not regress.

## Scope
- `Part A follow-up governance contract`:
  - persist `follow_up_owner_id` and `follow_up_due_at` on bookings
  - expose owner/due/overdue fields in booking response and filters in `/calendar/bookings`
  - add bounded supervisor mutation endpoint for reassignment / due-time update
  - set deterministic defaults when a booking becomes `NO_SHOW`
- `Part B history mode + UI rollout`:
  - add explicit calendar queue mode `ops | history` on the existing queue-state/URL canon
  - surface follow-up owner/due chips and supervisor controls in calendar cards
  - add history mode controls plus queue filters for follow-up owner / overdue

## Out of scope
- richer routing / policy scoring
- booking archive table or physical data move
- public share links or unauthenticated booking URLs
- sticky related-case summary redesign
- full booking activity timeline UI beyond current audit-derived follow-up state

## Touch-list
- `truffles-api/app/models/appointment.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/app/services/console_queue_state.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/migrations/*`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `truffles-api/tests/test_console_queue_state_api.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/types/api.generated.ts`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Booking governance canon (mandatory)
- `Server-owned follow-up fields`:
  - `follow_up_owner_id`
  - `follow_up_due_at`
  - response-only `follow_up_owner_name`
  - response-only `follow_up_overdue`
- `Deterministic NO_SHOW defaults`:
  - when status changes to `NO_SHOW`, follow-up owner defaults to the acting agent if absent
  - when status changes to `NO_SHOW`, follow-up due defaults to a bounded near-term timestamp if absent
- `Calendar queue state additions`:
  - `queue_mode`: `ops | history`
  - `follow_up_owner_id`: optional filter
  - `follow_up_overdue_only`: boolean filter
- `Restore precedence`:
  - explicit URL queue params
  - URL `view_id`
  - server current state
  - managed team default
  - personal default
  - local fallback
- `Excluded from governance contract`:
  - transient composer/form state
  - selected booking card
  - slot picker state
  - richer routing policy selection

## Plan (1..N)
1. Add booking persistence fields + migration and wire response serialization/helpers.
2. Add booking list filters and supervisor mutation endpoint with deterministic tests.
3. Extend calendar queue-state canon/URLs with `queue_mode`, `follow_up_owner_id`, and `follow_up_overdue_only`.
4. Wire calendar UI for history mode, follow-up chips, and supervisor reassignment/due controls.
5. Re-run deterministic checks, sync docs/session state, and push `PR #948` update.

## DoD
- `NO_SHOW` bookings carry explicit follow-up owner and due time in the server response.
- Supervisors can reassign follow-up owner and due time through a bounded calendar mutation path.
- Calendar queue can filter by follow-up owner and overdue follow-up backlog.
- Calendar exposes an explicit `history` mode on the same saved-view/shareable-URL canon.
- Existing no-show reopen/rebook behavior remains green.

## Checks
- `cd truffles-api && pytest -q tests/test_calendar_noshow_followup_router.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/models/appointment.py app/routers/calendar.py app/services/appointment_service.py app/services/console_queue_state.py app/schemas/console.py tests/test_calendar_noshow_followup_router.py tests/test_console_queue_state_api.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/calendar-bookings.ts --file src/lib/queue-state.ts --file src/lib/api-client.ts --file src/app/calendar/page.tsx`
- `cd console-web && npm run build`

## Evidence
- migration/model diff for booking follow-up owner/due fields
- router/schema/OpenAPI diff for governance fields and endpoint
- frontend diff for history mode + follow-up governance controls
- deterministic outputs proving no-show defaults, reassignment, and queue-state sync

## Release safety (mandatory)
- **Rollout:** additive; old bookings without owner/due remain readable and degrade to nullable governance fields until touched.
- **Go/no-go:** merge only if `NO_SHOW` lifecycle, case reopen, and rebook linkage still pass while new governance fields and history mode work.
- **Rollback:** revert Wave28 commit(s) and keep Waves 24-27 queue-state/view/share-link behavior intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave28 checks
- confirm Wave27 shareable queue URLs and Wave26 managed presets still work unchanged

## No-go
- Do not keep follow-up owner/due only in `AppointmentAudit.payload`.
- Do not add a second queue-state model for calendar history mode.
- Do not open richer routing or policy scoring in this block.
- Do not leak selected booking/panel/form state into saved views or share URLs.

## Риски/блокеры
- If owner/due remain implicit, richer routing will optimize on the wrong signal.
- If history mode is implemented as a local-only toggle, share URLs and presets will fork again.
- If supervisor reassignment is too open, ownership can cross branch boundaries incorrectly.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: richer routing/scoring and sticky related-case summary remain deferred.
- `Why not in this block`: Wave28 is strictly the missing governance substrate for bookings, not routing automation.
- `Risk if deferred`: routing still cannot become richer, but bookings queue becomes governable and explainable first.
- `Linked follow-up Task Package(s)`: the next block must be richer routing that consumes explicit booking governance and queue-state canon.
- `Expiry/trigger to stop deferral`: once Wave28 is green, any richer routing proposal must reference explicit `follow_up_owner/due/history` inputs instead of status-only heuristics.

## Next-block contract (mandatory)
- `Next block objective`: implement richer routing v1 as recommendation-first scoring over explicit queue-state, booking follow-up ownership, and SLA risk.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Booking governance canon|queue_mode|follow_up_owner_id|follow_up_due_at" docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md`
- `Blocked-by conditions`: any regression in Waves 24-27 queue-state/share-link canon, or any missing explicit booking owner/due/history evidence, blocks richer routing immediately.
- `Owner role for closure`: Brain / Top Architect.
