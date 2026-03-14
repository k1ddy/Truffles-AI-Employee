# TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE39-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE38-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE37-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE38-A1`
- `UNLOCKS`: final Calendar closeout as a bounded action system and only then a return to non-Calendar backlog work (`UX-08`, `UX-20`, `UX-26`)

## Название/цель
Закрыть последний системный риск вкладки `Записи` после merged `Wave38`: превратить Calendar из набора локально связанных панелей в bounded action system с server-owned action contract, fail-closed lifecycle, explicit state machines, and exhaustive proof so managers and the consultant bot cannot trigger accidental, stale, or logically invalid behavior through the tab.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- `CA_ID`: `UX-38`

## Git / worktree
- `Branch`: `feat/2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred, but execution split is mandatory inside the block: `Part A action registry + scenario matrix`, `Part B backend safety contract`, `Part C frontend state machines + fail-closed UI`, `Part D exhaustive proof + visual acceptance`, `Part E observability + post-merge replay`. The next part is blocked until the previous one is green.
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Wave38` is now merged into `origin/main` via `PR #960` (`merge commit f1103dfd` on `2026-03-09`). This means the old primary defects are no longer the active blocker: filters already use one explicit `draft -> applied` contract, phone input preserves raw editing, and existing bookings already support bounded `edit/reschedule/cancel` lifecycle.
- The remaining blocker is now residual bug variance across the whole Calendar action surface rather than one missing happy path. Current code still concentrates too much operator behavior in a few large files:
  - `console-web/src/app/calendar/page.tsx` -> `4193` LOC
  - `console-web/e2e/calendar-operator.spec.ts` -> `1208` LOC
  - `truffles-api/app/routers/calendar.py` -> `1897` LOC
  - `truffles-api/app/services/appointment_service.py` -> `801` LOC
- Current code still has no unified server-owned action contract or optimistic concurrency boundary for Calendar lifecycle actions. Evidence: `rg -n "allowed_actions|If-Match|ETag|VERSION_CONFLICT|BOOKING_VERSION_CONFLICT" console-web/src/app/calendar/page.tsx console-web/src/lib/calendar-bookings.ts truffles-api/app/routers/calendar.py truffles-api/app/services/appointment_service.py` returns no matches on `2026-03-09`.
- Current proof is strong for the repaired `Wave38` flows, but it is still hand-curated rather than driven from one canonical role/status/action matrix. That leaves room for new action combinations to drift even if the main lanes stay green.
- Inference from the current router/UI shape: Calendar still enforces role/status restrictions action-by-action, but it does not yet export a unified actor contract for `manager`, `owner/admin`, and `consultant-bot` actions back to the UI. This is why the next block must be an action-safety envelope instead of another spot fix.

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai/docs XState guards actions transitions React state machine`
- **Date/time (local):** `2026-03-09T14:48:38+05:00`
- **Sources opened:**
  - `https://stately.ai/docs/transitions`
  - `https://stately.ai/docs/guards`
  - `https://stately.ai/docs/actions`
- **Ready solutions found:** official XState/Stately guidance reinforces the exact safety pattern needed here: finite states, explicit events, guarded transitions, and side effects isolated as actions. That maps directly to Calendar's remaining risk, where invalid transitions and hidden side effects currently create bug variance.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the current Calendar product surface and reuse the merged `Wave38` contracts, but refactor the implementation around explicit machine/reducer semantics for filters, booking composer, booking action panel, and follow-up flows. Do not add a heavy new runtime dependency unless extracted local machines cannot stay readable with the current stack.
- **Rejected options:** continuing with ad hoc page-local booleans and inline guards; relying on Playwright happy paths without a canonical action matrix; treating backend role/status checks as sufficient without exporting a UI-safe action contract.
- **Source quality:** high-signal primary source = official Stately/XState documentation.

## Root cause (mandatory)
- **Symptom:** after merged `Wave38`, Calendar works for the repaired primary flows, but operators can still reasonably fear random regressions because the tab does not yet behave like a bounded action system across all actions and sub-actions.
- **Minimal reproduction:**
  1. Open Calendar and move between filters, booking create/edit/cancel, visit-status actions, and no-show follow-up actions; the page still coordinates many transitions through local inline orchestration rather than one central action model.
  2. Start editing a booking while another actor or process changes it; there is no explicit version-conflict contract today, so stale-action handling is not guaranteed.
  3. Compare what the UI enables with what the backend finally accepts; role/status gates exist, but they are not surfaced as one server-owned `allowed_actions` contract with machine-readable blocked reasons.
- **Evidence:** merged `Wave38` code, current file-size concentration above, the no-match contract-gap search above, and the fact that `calendar-operator.spec.ts` is currently hand-authored scenario coverage rather than one generated/derived action matrix.
- **Five Whys:**
  1. Why can bug variance still appear after `Wave38`? Because the tab is still orchestrated as a large page with many local flags and conditional actions instead of a finite action model.
  2. Why do action rules drift between UI and server? Because the backend does not currently return one authoritative `allowed_actions` / blocked-reasons contract for every booking state.
  3. Why are stale edits or accidental double actions still plausible? Because lifecycle mutations do not yet have one explicit optimistic concurrency boundary and idempotent retry story.
  4. Why can tests still miss regressions? Because the proof is not yet derived from one canonical role/status/action matrix that covers invalid paths as aggressively as valid ones.
  5. Why does this remain a product blocker instead of polish? Because Calendar is an operator control surface; random action drift destroys trust even when the main happy path works.
- **Root cause statement:** Calendar's remaining risk is architectural, not cosmetic. The tab still behaves like a collection of loosely coupled forms and panels, while the job requires a closed action system with explicit actors, statuses, transitions, blocked reasons, versioning, and proof.
- **Fix mechanism:** add a canonical Calendar action registry, make the backend the owner of lifecycle permissions and version conflicts, extract frontend flows into explicit state machines/reducers, and prove the full role/status/action matrix with deterministic tests plus visual review.

## Reuse-first plan (mandatory)
- **Reuse:** merged `Wave38` filter contract, phone-input contract, edit/reschedule/cancel lifecycle, current booking composer/action panel surfaces, existing queue-state/saved-view/share URL canon, existing Playwright harness, current `PATCH /calendar/bookings/{booking_id}` and cancel/follow-up routes, existing OpenAPI generation flow.
- **Integrate:** layer one action registry and versioned lifecycle contract over the current backend, and extract the current page into explicit local machines/hooks/components instead of replacing the whole Calendar IA.
- **Build only if needed:** a bounded `allowed_actions` payload model, version-conflict reason codes, mutation idempotency token reuse, and new matrix fixtures/scripts only where the current contract cannot express them cleanly.

## Invariant
- Do not regress the merged `Wave38` operator fixes for filters, phone input, create flow, edit/reschedule/cancel, or follow-up safety.
- Do not reopen routing v2, routing profiles, Inbox redesign, or unrelated global Console backlog while Calendar still lacks a full action-safety envelope.
- Do not add a new top-level route or second Calendar IA.
- Do not let the frontend guess booking lifecycle permissions without a server-owned contract.
- Do not allow stale lifecycle mutations to succeed silently.
- Do not accept "mostly covered" proof; invalid paths must be first-class acceptance criteria.
- Do not let consultant-bot actions overwrite manager-owned operator work without explicit conflict handling and audit.

## Scope
- Calendar-only safety hardening on top of merged `Wave38`:
  - canonical action registry for all operator-visible Calendar actions;
  - server-owned `allowed_actions` / blocked reasons for booking lifecycle actions;
  - optimistic concurrency and duplicate-submit safety for lifecycle mutations;
  - extracted frontend machines/reducers for filters, composer, booking actions, and follow-up flows;
  - exhaustive deterministic proof for valid and invalid role/status/action combinations;
  - action audit / failure-family observability and post-merge replay.

## Out of scope
- Inbox redesign or Inbox routing changes
- routing v2 / capability-input work
- global Console backlog items `UX-08`, `UX-20`, `UX-26`
- large CRM/customer-history platform expansion beyond bounded booking assistance
- consultant-side policy rewrites outside the explicit Calendar action boundary

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/app/calendar/_components/*` (new extracted components allowed)
- `console-web/src/app/calendar/_lib/*` (new extracted hooks/machines/helpers allowed)
- `console-web/src/components/CaseBookingsPanel.tsx`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/calendar-operator.spec.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/e2e/fixtures/*` (new machine-readable action-matrix fixtures allowed)
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/app/schemas/console.py` (only if OpenAPI/shared action payloads need schema extraction)
- `truffles-api/tests/test_calendar_bookings_router.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `truffles-api/tests/test_console_queue_state_api.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Delivery split / PR contract (mandatory)
- `Part A — Action registry + scenario matrix`
  - define the canonical set of Calendar actions, actors, statuses, required fields, blocked reasons, and side effects;
  - make the matrix machine-readable enough that tests can derive from it rather than drift away from it.
- `Part B — Backend safety contract`
  - return `allowed_actions` and blocked reasons for booking lifecycle records;
  - add explicit version/conflict handling and safe retry/double-submit rules for lifecycle mutations.
- `Part C — Frontend state machines + fail-closed UI`
  - extract large inline orchestration out of `calendar/page.tsx`;
  - render action availability from server contract and local machine state instead of scattered booleans.
- `Part D — Exhaustive proof + visual acceptance`
  - expand deterministic proof from happy paths to full role/status/action invalid-path coverage;
  - record visual acceptance after every part and for the final matrix.
- `Part E — Observability + post-merge replay`
  - add failure-family visibility and post-merge replay guard so residual bug families surface immediately instead of through ad hoc operator complaints.

## Calendar action registry contract (mandatory)
- Every operator-visible Calendar action must exist in one canonical registry row with these fields:
  - `action_id`
  - `actor_class` (`manager`, `owner_admin`, `consultant_bot`)
  - `surface` (`queue`, `filter_panel`, `composer`, `action_panel`, `follow_up_panel`, `case_linked_view`)
  - `from_status`
  - `to_status` or `side_effect_only`
  - `required_inputs`
  - `dependent_resets`
  - `server_route` or `local_machine_only`
  - `blocked_reason_codes`
  - `success_receipt`
  - `refresh_targets`
  - `audit_event`
- Mandatory actions in the registry:
  - `apply_filters`
  - `reset_filters`
  - `load_saved_view`
  - `copy_share_url`
  - `create_booking`
  - `edit_booking`
  - `reschedule_booking`
  - `cancel_booking`
  - `mark_checked_in`
  - `mark_completed`
  - `mark_no_show`
  - `record_follow_up_contacted`
  - `record_follow_up_rebooked`
  - `change_follow_up_owner`
  - `change_follow_up_due`
  - `open_case_from_booking`
- Entity-backed actions must not be enabled in UI unless the current payload says they are allowed or supplies a machine-readable blocked reason.
- Purely local actions such as panel open/close may stay local-machine-owned, but they still must be enumerated in the registry if they affect operator state or can discard work.

## Backend safety contract (mandatory)
- Every booking payload used by Calendar action surfaces must expose enough contract to render fail-closed actions:
  - `status`
  - `version` (or equivalent explicit mutation revision)
  - `allowed_actions`
  - `blocked_actions` with reason codes
  - `last_actor_type` or equivalent audit-safe source when relevant
- Lifecycle mutations that can change booking truth must require the current `version` and reject stale updates with `409 BOOKING_VERSION_CONFLICT` (or a tighter existing conflict code if already available and documented).
- Lifecycle mutations in scope:
  - edit/reschedule
  - cancel
  - visit status changes
  - no-show follow-up result
  - no-show follow-up governance
- Double-submit safety is mandatory:
  - UI must disable pending action buttons and guard repeat clicks;
  - backend must treat a retried mutation as safe by version gate and, if needed, a bounded mutation token/idempotency key.
- Consultant-bot boundary is mandatory:
  - bot-origin actions must be explicit in audit/source metadata;
  - bot must not execute operator-only lifecycle actions through the same surface without explicit server permission.
- Queue/list/card detail and case-linked booking surfaces must all refresh from the same authoritative payload after mutation.

## Frontend state-machine contract (mandatory)
- Extract the current page orchestration into explicit bounded modules at minimum for:
  - `useCalendarFiltersMachine`
  - `useBookingComposerMachine`
  - `useBookingActionPanelMachine`
  - `useBookingFollowUpMachine`
- Each machine must define explicit:
  - states
  - events
  - guards
  - side-effect boundaries
  - reset behavior on dependent-field changes
  - dirty-close confirmation rules
- Forbidden examples that must become impossible by construction:
  - selected slot survives after service/specialist/date changed;
  - edit/cancel button remains enabled when server says action is blocked;
  - follow-up `rebooked` can submit without linked booking;
  - draft filter changes mutate live queue state before `Применить`;
  - stale edit silently overwrites fresher booking state.
- `console-web/src/app/calendar/page.tsx` must stop owning queue/filter/composer/action/follow-up orchestration inline. Extraction, not more inlining, is the required direction.

## Observability contract (mandatory)
- Every lifecycle mutation must emit enough evidence for failure-family clustering:
  - `action_id`
  - `actor_class`
  - `booking_id`
  - `old_status`
  - `new_status`
  - `blocked_reason_code`
  - `version_conflict`
  - `linked_case_id`
- Add or reuse metrics/counters for at minimum:
  - `calendar_booking_action_denied_total`
  - `calendar_booking_version_conflict_total`
  - `calendar_booking_double_submit_blocked_total`
  - `calendar_followup_invalid_total`
  - `calendar_filter_apply_total`
  - `calendar_filter_reset_total`
- Post-merge review must classify failures by family, not only by individual screenshots or one-off operator complaints.

## Visual inspection protocol (mandatory)
1. After every completed part, capture Calendar at `1024px`, `1280px`, and `1440px` widths.
2. Mandatory states:
   - queue first screen default;
   - dirty filters before apply and after apply;
   - booking create flow with valid and invalid phone;
   - edit-booking flow;
   - cancel confirmation;
   - blocked status action panel (`completed`, `cancelled`, `no_show`);
   - follow-up panel with guarded `rebooked` path;
   - medium-width state with queue + action surface open.
3. Each capture must confirm:
   - no clipped or overflowed controls;
   - one obvious primary action;
   - disabled actions explain why they are blocked;
   - no duplicated destructive CTA labels;
   - no raw technical/account text;
   - no layout collision between queue, composer, and action/follow-up surfaces.
4. Part closure is blocked until the visual checklist is explicitly clean.

## Test matrix (mandatory)
- `Actor / permission matrix`:
  - manager allowed vs blocked actions;
  - owner/admin extra governance actions;
  - consultant-bot limited/non-operator actions.
- `Status / lifecycle matrix`:
  - `SCHEDULED`
  - `PENDING_CONFIRMATION`
  - `CHECKED_IN`
  - `COMPLETED`
  - `NO_SHOW`
  - `CANCELLED`
  - any additional active statuses present in the current contract.
- `Filters / queue-state`:
  - draft changes do not fetch until apply;
  - reset returns to last applied snapshot;
  - reload/back-forward restores applied snapshot;
  - saved views/share URLs stay deterministic;
  - incompatible filters reset predictably.
- `Create / edit / reschedule`:
  - create valid booking;
  - edit customer fields only;
  - edit service resets specialist/slot;
  - edit specialist resets slot;
  - edit date reloads slot;
  - empty-day / slot-conflict paths;
  - stale-version conflict;
  - safe retry after conflict.
- `Cancel / no-show / follow-up`:
  - cancel active booking with and without reason;
  - cancel blocked when already inactive;
  - no-show follow-up `contacted`;
  - no-show follow-up `rebooked` with and without linked booking;
  - governance owner/due changes respect role restrictions.
- `Safety / resilience`:
  - double submit blocked;
  - pending buttons disable correctly;
  - dirty-close confirm works;
  - queue/card/case-linked views refresh consistently after mutation.
- `Layout / regression`:
  - medium-width `1024px` still usable;
  - no duplicate button-name ambiguity in deterministic lanes;
  - `inspect_case` calendar-linked flows remain green.
- `Server boundary`:
  - router tests for allowed-actions/status validation;
  - OpenAPI/types stay in sync;
  - queue-state API tests remain green if filter payload shape changes.

## Plan (1..N)
1. Sync canon after merged `Wave38` and open `Wave39` as the only active Calendar block.
2. Define the canonical Calendar action registry and machine-readable scenario matrix.
3. Add backend `allowed_actions` / blocked-reasons contract for booking lifecycle payloads.
4. Add optimistic version/conflict handling and safe retry/double-submit rules.
5. Extract Calendar filter/composer/action/follow-up orchestration into explicit local machines/hooks/components.
6. Rewire UI buttons and panels to render from the action contract and machine state.
7. Extend case-linked booking surfaces so they follow the same lifecycle truth.
8. Expand deterministic proof to the full valid/invalid role/status/action matrix.
9. Add action-family observability and post-merge replay checks.
10. Sync canon, keep Wave39 as the only active block, and do not return to non-Calendar backlog until this block is explicitly closed.

## DoD
- Calendar actions are bounded by one explicit registry and no longer drift across scattered booleans.
- Backend owns lifecycle permissions and version conflicts for booking actions used by Calendar.
- Frontend renders fail-closed actions from server truth plus explicit local machine state.
- Stale mutation, double-submit, and invalid transition paths are all covered and green.
- Managers and consultant-bot interactions are separated by explicit actor contract and audit-visible outcomes.
- Visual inspection is clean for all mandatory states at `1024px`, `1280px`, and `1440px`.
- `Wave39` is the only active Calendar block until the full matrix and post-merge replay are green.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "allowed_actions|BOOKING_VERSION_CONFLICT|If-Match|ETag" console-web/src/app/calendar/page.tsx console-web/src/lib/calendar-bookings.ts truffles-api/app/routers/calendar.py truffles-api/app/services/appointment_service.py`
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseBookingsPanel.tsx --file src/lib/calendar-bookings.ts --file src/lib/queue-state.ts --file e2e/calendar-operator.spec.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && npm run generate:api` (if contract/types change)
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/calendar-operator.spec.ts --project chromium`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "calendar|booking|follow-up|medium-width|filter|cancel|edit"`
- `cd truffles-api && pytest -q tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py tests/test_console_queue_state_api.py`
- `cd truffles-api && ruff check app/routers/calendar.py app/services/appointment_service.py app/schemas/console.py tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py tests/test_console_queue_state_api.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` (if contract changes)
- visual captures for all mandatory states at `1024px`, `1280px`, and `1440px`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Progress log
- `2026-03-09` — `Wave39` opened after merged `Wave38`:
  - fetched `origin/main` and confirmed `PR #960` landed as `f1103dfd`;
  - created a new branch `feat/2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1` from merged `origin/main` in the same worktree;
  - recorded the remaining risk as `Calendar action safety envelope`, not another happy-path bugfix;
  - closed `UX-35` / `UX-36` / `UX-37` as merged via `Wave38` and opened `UX-38` for the remaining action-safety work;
  - synced canon so `Wave39` becomes the only valid next block before any return to non-Calendar backlog work.

- `2026-03-09` — `Wave39 Part A` completed locally:
  - created `console-web/src/lib/calendar-action-registry.ts` as the canonical registry for Calendar queue/booking actions, actor classes, blocked-reason codes, and the machine-readable role/status/action scenario matrix;
  - rewired `console-web/src/app/calendar/page.tsx`, `console-web/src/components/CaseBookingsPanel.tsx`, and `console-web/src/lib/calendar-bookings.ts` to read visit/edit/cancel/follow-up availability from the registry instead of duplicating hard-coded status arrays in multiple UI surfaces;
  - added deterministic proof in `console-web/e2e/calendar-operator.spec.ts` that the registry stays aligned with the actor/status matrix while keeping the repaired operator workflow and targeted Inbox/Calendar integration lanes green;
  - completed a visual inspection on the current Calendar surfaces and saved representative captures to `/tmp/wave39-part-a-calendar-page-1280.png`, `/tmp/wave39-part-a-calendar-filters-1280.png`, and `/tmp/wave39-part-a-calendar-actions-1280.png`;
  - validated the sub-block with `lint`, `build`, `calendar-operator.spec.ts` (`11 passed`), targeted `inspect_case.spec.ts` (`4 passed`), and `SESSION_AGENT=a1 scripts/session_check.sh` (`Session OK`).

- `2026-03-09` — `Wave39 Part B` completed locally:
  - added `truffles-api/app/services/calendar_action_contract.py` so the backend now owns canonical booking `allowed_actions` / `blocked_actions` instead of leaving lifecycle truth UI-only;
  - extended `truffles-api/app/routers/calendar.py` and `truffles-api/app/services/appointment_service.py` with explicit booking `version` handling, `BOOKING_VERSION_CONFLICT`, server-enriched `BookingResponse`, and version-safe router-owned follow-up/governance mutations;
  - updated `console-web/src/lib/calendar-bookings.ts`, `console-web/src/app/calendar/page.tsx`, and `console-web/src/components/CaseBookingsPanel.tsx` so every lifecycle mutation sends `booking.version`, renders availability from the server contract when present, and fails closed on stale actions;
  - regenerated `contracts/console_api/openapi.v1.yaml` and `console-web/src/types/api.generated.ts`, then expanded contract/router/e2e proof to cover version conflicts and stale operator actions;
  - completed a visual inspection on the current Calendar surfaces while re-running the operator lane, including the stale-action fail-closed path and medium-width layout; representative captures remain `/tmp/wave39-part-a-calendar-page-1280.png`, `/tmp/wave39-part-a-calendar-filters-1280.png`, and `/tmp/wave39-part-a-calendar-actions-1280.png`;
  - validated the sub-block with backend tests (`57 passed`), `ruff`, OpenAPI drift check, frontend `generate:api`, targeted `lint`, `build`, `calendar-operator.spec.ts` (`12 passed`), and full `inspect_case.spec.ts` (`14 passed, 1 skipped`).

- `2026-03-09` — `Wave39 Part C` completed locally:
  - extracted explicit Calendar local machines into `console-web/src/app/calendar/_lib/useCalendarFiltersMachine.ts`, `console-web/src/app/calendar/_lib/useBookingComposerMachine.ts`, `console-web/src/app/calendar/_lib/useBookingActionPanelMachine.ts`, and `console-web/src/app/calendar/_lib/useBookingFollowUpMachine.ts`;
  - rewired `console-web/src/app/calendar/page.tsx` to consume machine-backed queue/composer/action/follow-up state instead of owning the orchestration inline; dependent resets now live in the machines, and dirty-close confirmation now blocks accidental discard for composer/action-panel drafts;
  - kept the server-owned fail-closed contract from `Part B` intact while updating helper flows in `console-web/e2e/calendar-operator.spec.ts` and `console-web/e2e/inspect_case.spec.ts` to exercise reset/confirm/discard behavior against the extracted machines;
  - completed a clean visual/operator proof sweep on a fresh `next dev` runtime after clearing stale `.next` artifacts that caused a temporary `vendor-chunks/axios.js` dev-cache failure on `/cases/[id]`; this was infra hygiene, not a Calendar product regression;
  - validated the sub-block with targeted frontend `lint`, frontend `build`, `calendar-operator.spec.ts` (`14 passed`), full `inspect_case.spec.ts` (`14 passed, 1 skipped` with `--workers=1` on a clean dev runtime), and green canon/session checks.

- `2026-03-09` — `Wave39 Part D` completed locally:
  - expanded deterministic proof in `console-web/e2e/calendar-operator.spec.ts` to the final operator matrix: route-mock bookings now exercise the server-backed `allowed_actions` / `blocked_actions` path, historical `COMPLETED` / `CANCELLED` states keep explicit blocked-action panels, consultant-bot case actions stay fail-closed, and pending cancel proof confirms one destructive request per click burst;
  - fixed two acceptance gaps surfaced by the new matrix: `console-web/src/app/calendar/page.tsx` now keeps an action surface for historical bookings when edit/cancel are blocked, and card-level `Открыть чат заявки` links now obey `open_case_from_booking` instead of bypassing the server contract;
  - tightened backend contract alignment in `truffles-api/app/services/calendar_action_contract.py` and `truffles-api/tests/test_calendar_bookings_router.py` so consultant-bot payloads no longer expose case actions through the server-owned matrix;
  - completed the required visual acceptance sweep and stored captures in `/tmp/wave39-part-d-operator-captures`: `wave39-queue-default-1280.png`, `wave39-queue-default-1440.png`, `wave39-filters-draft-1280.png`, `wave39-filters-applied-1280.png`, `wave39-phone-invalid-1280.png`, `wave39-phone-valid-1280.png`, `wave39-edit-open-1280.png`, `wave39-cancel-panel-1280.png`, `wave39-no-show-disabled-1280.png`, `wave39-completed-blocked-1280.png`, `wave39-cancelled-blocked-1280.png`, `wave39-follow-up-guarded-1280.png`, and `wave39-medium-width-1024.png`;
  - validated the sub-block with targeted frontend `lint`, frontend `build`, full `calendar-operator.spec.ts` (`17 passed`), full `inspect_case.spec.ts` (`14 passed, 1 skipped`), backend proof (`63 passed`), `ruff`, and `SESSION_AGENT=a1 scripts/session_check.sh` (`Session OK`).

- `2026-03-09` — `Wave39 Part E` completed locally:
  - added Calendar failure-family observability in `truffles-api/app/logging_config.py` and `truffles-api/app/routers/calendar.py`: denied/version-conflict/double-submit/filter/follow-up counters now exist, lifecycle routes record audit observations, and the bounded `POST /calendar/operator-events` endpoint accepts only the specific replay-safe event families required by this block;
  - extended `console-web/src/lib/calendar-bookings.ts` and `console-web/src/app/calendar/page.tsx` so the real operator surfaces emit filter-apply, filter-reset, and double-submit observations instead of leaving replay visibility to ad hoc logs;
  - expanded `console-web/e2e/calendar-operator.spec.ts` with deterministic telemetry proof, including one replay lane that validates filter apply/reset events and `double_submit_blocked` for booking creation while keeping the destructive cancel single-submit proof green;
  - regenerated `contracts/console_api/openapi.v1.yaml` / `console-web/src/types/api.generated.ts`, completed the required visual/operator sweep, and recorded the updated capture set in `/tmp/wave39-part-e-operator-captures`;
  - validated the sub-block with backend tests (`37 passed` + `26 passed`), `ruff`, OpenAPI drift check, frontend `generate:api`, frontend `build`, full `calendar-operator.spec.ts` (`18 passed`), full `inspect_case.spec.ts` (`14 passed, 1 skipped`), and `SESSION_AGENT=a1 scripts/session_check.sh` (`Session OK`).


- `2026-03-09` — `Wave39 PR` opened:
  - committed the full `Wave39` local stack as `b62a3f5f` (`feat(console): close wave39 calendar action safety envelope`);
  - pushed `feat/2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1` to `origin`;
  - opened `PR #961` against `main`: `https://github.com/k1ddy/Truffles-AI-Employee/pull/961`;
  - the next required step is merge closeout plus the bounded post-merge replay on `main`.


- `2026-03-11` — `Wave39 post-merge closeout` completed on `main`:
  - synced `/home/zhan/truffles-main` to `origin/main` and verified merged `Wave39` landed as `710f8faa` (`PR #961`);
  - ran the bounded merged-main replay: backend transition/calendar/openapi lanes all stayed green, and the merged Calendar operator Playwright lanes stayed green without route-mock drift;
  - confirmed the required failure families (`denied`, `version_conflict`, `double_submit_blocked`, `filter_apply`, `filter_reset`) remain observable on merged `main`;
  - `UX-38` is now closed and the next valid backlog block returns to `UX-08` (`runtime health / outbox pressure`).

## Evidence
- merged `Wave38` confirmation: `git fetch origin --prune && git log --oneline --decorate -5 origin/main` -> `f1103dfd Merge pull request #960 from k1ddy/feat/2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1`
- contract-gap confirmation: `rg -n "allowed_actions|If-Match|ETag|VERSION_CONFLICT|BOOKING_VERSION_CONFLICT" console-web/src/app/calendar/page.tsx console-web/src/lib/calendar-bookings.ts truffles-api/app/routers/calendar.py truffles-api/app/services/appointment_service.py` -> no matches on `2026-03-09`
- new TP: `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md`
- synced canon pointers in `STATE.md`, `STRUCTURE.md`, backlog, master TP, session log, and session index
- one-web-search record with official Stately/XState docs
- local Part A evidence: `console-web/src/lib/calendar-action-registry.ts`, `console-web/src/app/calendar/page.tsx`, `console-web/src/components/CaseBookingsPanel.tsx`, `console-web/src/lib/calendar-bookings.ts`, `console-web/e2e/calendar-operator.spec.ts`
- local Part B evidence: `truffles-api/app/routers/calendar.py`, `truffles-api/app/services/appointment_service.py`, `truffles-api/app/services/calendar_action_contract.py`, `truffles-api/tests/test_calendar_bookings_router.py`, `truffles-api/tests/test_calendar_noshow_followup_router.py`, `truffles-api/tests/test_console_openapi_calendar_contract.py`, `contracts/console_api/openapi.v1.yaml`, `console-web/src/types/api.generated.ts`, `console-web/e2e/inspect_case.spec.ts`
- local Part C evidence: `console-web/src/app/calendar/_lib/useCalendarFiltersMachine.ts`, `console-web/src/app/calendar/_lib/useBookingComposerMachine.ts`, `console-web/src/app/calendar/_lib/useBookingActionPanelMachine.ts`, `console-web/src/app/calendar/_lib/useBookingFollowUpMachine.ts`, `console-web/src/app/calendar/page.tsx`, `console-web/e2e/calendar-operator.spec.ts`, `console-web/e2e/inspect_case.spec.ts`
- local Part D evidence: `console-web/src/app/calendar/page.tsx`, `console-web/e2e/calendar-operator.spec.ts`, `console-web/e2e/inspect_case.spec.ts`, `truffles-api/app/services/calendar_action_contract.py`, `truffles-api/tests/test_calendar_bookings_router.py`, `/tmp/wave39-part-d-operator-captures/wave39-queue-default-1280.png`, `/tmp/wave39-part-d-operator-captures/wave39-cancelled-blocked-1280.png`, `/tmp/wave39-part-d-operator-captures/wave39-medium-width-1024.png`
- local Part E evidence: `truffles-api/app/logging_config.py`, `truffles-api/app/routers/calendar.py`, `console-web/src/lib/calendar-bookings.ts`, `console-web/src/app/calendar/page.tsx`, `console-web/e2e/calendar-operator.spec.ts`, `contracts/console_api/openapi.v1.yaml`, `console-web/src/types/api.generated.ts`, `/tmp/wave39-part-e-operator-captures/wave39-queue-default-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-cancel-panel-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-medium-width-1024.png`
- `cd truffles-api && pytest -q tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py` -> `37 passed`
- `cd truffles-api && pytest -q tests/test_console_openapi_calendar_contract.py` -> `26 passed`
- `cd truffles-api && ruff check app/routers/calendar.py app/logging_config.py app/services/calendar_action_contract.py tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py` -> `pass`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> `pass`
- `cd console-web && npm run generate:api` -> `pass`
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/lib/calendar-bookings.ts --file e2e/calendar-operator.spec.ts` -> `pass`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 CALENDAR_OPERATOR_CAPTURE_DIR=/tmp/wave39-part-e-operator-captures npx playwright test e2e/calendar-operator.spec.ts --project chromium` -> `18 passed`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 npx playwright test e2e/inspect_case.spec.ts --project chromium --workers=1` -> `14 passed, 1 skipped`
- visual captures: `/tmp/wave39-part-e-operator-captures/wave39-queue-default-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-queue-default-1440.png`, `/tmp/wave39-part-e-operator-captures/wave39-filters-draft-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-filters-applied-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-phone-invalid-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-phone-valid-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-edit-open-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-cancel-panel-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-no-show-disabled-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-completed-blocked-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-cancelled-blocked-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-follow-up-guarded-1280.png`, `/tmp/wave39-part-e-operator-captures/wave39-medium-width-1024.png`
- PR opened: `PR #961` -> `https://github.com/k1ddy/Truffles-AI-Employee/pull/961`
- post-merge closeout evidence on `main`: `710f8faa`, `cd /home/zhan/truffles-main/truffles-api && pytest -q tests/test_appointment_service_status_transitions.py tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py` (`68 passed`), `cd /home/zhan/truffles-main/truffles-api && ruff check app/routers/calendar.py app/logging_config.py app/services/calendar_action_contract.py app/services/appointment_service.py tests/test_appointment_service_status_transitions.py tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py` (`pass`), `cd /home/zhan/truffles-main/truffles-api && python3 scripts/generate_openapi.py --check` (`pass`), `cd /home/zhan/truffles-main/console-web && npm run generate:api` (`pass`), `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/lib/calendar-bookings.ts --file e2e/calendar-operator.spec.ts --file e2e/inspect_case.spec.ts` (`pass`), `cd /home/zhan/truffles-main/console-web && npm run build` (`pass`), `cd /home/zhan/truffles-main/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 CALENDAR_OPERATOR_CAPTURE_DIR=/tmp/wave39-postmerge-operator-captures npx playwright test e2e/calendar-operator.spec.ts --project chromium` (`18 passed`), `cd /home/zhan/truffles-main/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 npx playwright test e2e/inspect_case.spec.ts --project chromium --workers=1` (`14 passed, 1 skipped`)

## Release safety (mandatory)
- **Rollout:** local-first implementation only; merge only after the full deterministic matrix is green. After merge, run one bounded post-merge replay on `main` and watch failure families for `24h` before declaring Calendar ready for backlog switch.
- **Go/no-go:** no merge if any action family still relies on UI guessing, if stale-version behavior is missing, if invalid paths are untested, or if visual inspection still shows ambiguous/overflowing controls.
- **Rollback:** revert the `Wave39` PR and revalidate the merged `Wave38` baseline. Never "fix" a regression by silently removing operator actions without preserving the action contract.

## Rollback
- `git revert REVISION_SHA`
- rerun the `Wave38` Calendar baseline checks and confirm `PR #960` behavior is restored
- leave `Wave39` TP open with a precise failure family instead of weakening the safety contract

## No-go
- No frontend-only guessing of lifecycle availability for entity-backed actions.
- No unversioned booking mutations once `Wave39` starts touching the lifecycle contract.
- No silent overwrite of fresher booking state.
- No hidden retry/double-submit behavior.
- No return to `UX-08` / `UX-20` / `UX-26` before `Wave39` closes.
- No new top-level route or second Calendar IA as an escape hatch.

## Риски/блокеры
- Extracting machines out of `calendar/page.tsx` may surface more implicit coupling than `Wave38` revealed.
- If version/idempotency needs a storage-backed token instead of a pure revision check, backend scope may expand.
- Case-linked booking surfaces may still hold assumptions that drift from the main Calendar action panel once contract truth becomes stricter.
- If proof remains hand-curated instead of matrix-driven, the block will not actually close the remaining risk.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: Calendar still relies on the generic `/agents` feed for owner choices, and customer-history assistance remains bounded to linked-case context instead of a richer CRM panel.
- `Why not in this block`: the active blocker is action safety and lifecycle determinism, not richer operator intelligence.
- `Risk if deferred`: owner clarity and repeat-booking assistance may still feel thin after `Wave39`, but they should no longer manifest as random action bugs if the safety envelope is correct.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md` and a bounded post-Wave39 API follow-up only if current data contracts still block safe operator behavior after the envelope lands.
- `Expiry/trigger to stop deferral`: if `Wave39` cannot enforce safe actions with current owner/customer data contracts, open the bounded API follow-up immediately instead of weakening the operator contract.

## Next-block contract (mandatory)
- `Next block objective`: open `UX-08` (`runtime health / outbox pressure`) now that `Wave39` is merged and replay-closed, without reopening Calendar routing or operator-safety work.
- `First deterministic check command`: `cd /home/zhan/truffles-main && rg -n "UX-08|runtime health|outbox pressure" docs/CONSOLE_AUDIT/UX_BACKLOG.md STATE.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md && git log --oneline -1`
- `Blocked-by conditions`: any reopened failure family in merged-main runtime replay, or any owner decision to keep Calendar as the active backlog despite the green `Wave39` closeout evidence.
- `Owner role for closure`: Brain / Top Architect.
