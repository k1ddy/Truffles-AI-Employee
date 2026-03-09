# TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE38-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE37-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE34-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE36-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE37-A1`
- `UNLOCKS`: final Calendar post-merge closeout, explicit backlog re-entry decision, and a bounded API follow-up only if the rebuilt operator lifecycle still cannot hold after this block

## Название/цель
Закрыть оставшийся post-merge product gap на вкладке `Записи` после merged `Wave37`: убрать фрустрацию от рассинхронизированных фильтров, сделать ввод телефона быстрым и предсказуемым, а также довести lifecycle записи до полного operator-grade контракта с редактированием, переносом и отменой без скрытых багов и нелогичного поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `CA_ID`: `UX-35`, `UX-36`, `UX-37`

## Git / worktree
- `Branch`: `feat/2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred; execution split is mandatory inside the block: `Part A filter-state contract`, `Part B phone/composer hardening`, `Part C booking edit/cancel lifecycle`, `Part D operator proof + visual acceptance`. Next part is blocked until the previous one is green.
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Wave37` merged into `origin/main` on `2026-03-09` (`merge commit 0e0b319d`), but new operator evidence immediately exposed three remaining Calendar defects that still block an operator-grade closeout:
  - filters feel desynchronized and frustrating during use;
  - phone input in the booking composer fights normal typing/deletion;
  - an already created booking still cannot be edited or cancelled from the operator UI.
- The current Calendar filter state still has too many competing truth sources and persistence paths:
  - URL hydration: `console-web/src/app/calendar/page.tsx:537`, `console-web/src/lib/queue-state.ts:553`
  - local workspace hydration: `console-web/src/app/calendar/page.tsx:816`
  - server queue-state hydration: `console-web/src/app/calendar/page.tsx:597`, `console-web/src/app/calendar/page.tsx:861`
  - live URL rewrite on every applied state change: `console-web/src/app/calendar/page.tsx:988`, `console-web/src/lib/queue-state.ts:642`
  - live queue-state writeback after debounce: `console-web/src/app/calendar/page.tsx:1021`
- The current phone input still rewrites operator text on each keystroke instead of preserving an editable raw value:
  - normalization: `console-web/src/app/calendar/page.tsx:265`
  - destructive formatting: `console-web/src/app/calendar/page.tsx:282`
  - input binding: `console-web/src/app/calendar/page.tsx:3395`
- The current Calendar UI still exposes no edit/cancel lifecycle for an existing booking even though the backend already has partial capability:
  - booking action panel currently exposes only status / no-show / follow-up governance groups: `console-web/src/app/calendar/page.tsx:3593`, `console-web/src/app/calendar/page.tsx:3620`, `console-web/src/app/calendar/page.tsx:3751`
  - `calendar-booking-cancel` in the composer only closes the draft surface, it does not cancel an existing booking: `console-web/src/app/calendar/page.tsx:3454`
  - backend cancel endpoint already exists: `truffles-api/app/routers/calendar.py:1321`, `truffles-api/app/services/appointment_service.py:330`
  - backend edit/reschedule route does not exist in the Console contract today; service layer exposes `create`, `cancel`, and `update_appointment_status`, but no Console-facing booking update contract: `truffles-api/app/services/appointment_service.py:227`, `truffles-api/app/services/appointment_service.py:330`, `truffles-api/app/services/appointment_service.py:415`
- Current proof is still incomplete for the new defect cluster because `console-web/e2e/calendar-operator.spec.ts` proves create/follow-up/layout recovery, but does not yet prove applied-vs-draft filter semantics, phone deletion ergonomics, or edit/cancel lifecycle.

## One web search (mandatory before implementation)
- **Query (exact):** `site:developer.mozilla.org input tel inputmode autocomplete tel`
- **Date/time (local):** `2026-03-09T10:47:19+05:00`
- **Sources opened:**
  - `https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/tel`
  - `https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/inputmode`
- **Ready solutions found:** official HTML guidance confirms that telephone inputs should use `type="tel"` / `inputmode="tel"` for keypad hints, but actual validation and normalization remain application-owned. That directly supports a raw-value plus normalized-preview model instead of destructive reformatting during typing.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the current calendar composer surface, but replace the current on-change phone rewrite with a raw editable value + normalized preview/submit contract, and apply the same explicit-state discipline to filter application.
- **Rejected options:** continuing with aggressive on-change formatting; treating `type="tel"` as sufficient validation; leaving filter writes as multi-source live side effects; shipping booking cancel as backend-only capability without operator UI.
- **Source quality:** high-signal primary source = MDN HTML reference.

## Root cause (mandatory)
- **Symptom:** after merged `Wave37`, operators still report friction in three primary jobs: applying filters confidently, entering/correcting a phone number, and changing/cancelling a booking that was just created.
- **Minimal reproduction:**
  1. Open `/calendar`, change several filters, then continue typing/searching or switching queue mode; the visible state, URL, and persisted state can feel out of sync because there is no explicit draft/applied boundary.
  2. Open the booking composer and type/delete a phone number in a common format such as `8 (701) 555-44-33`; the input reformats on every keystroke and makes correction/deletion unnatural.
  3. Create a booking, then try to fix a wrong service/time/phone or cancel the booking from the booking card/action panel; there is no full operator path for that lifecycle.
- **Evidence:** user acceptance feedback on `2026-03-09`, current Calendar state/persistence code in `console-web/src/app/calendar/page.tsx`, current queue-state helpers in `console-web/src/lib/queue-state.ts`, and the backend/UI lifecycle split noted above.
- **Five Whys:**
  1. Why do filters feel desynchronized? Because Calendar currently hydrates from URL/server/local state and writes back to URL/server/local state without an explicit applied-state transaction boundary.
  2. Why does the phone field feel broken? Because the field owns only one formatted value, so typing, deleting, and cursor intent are overridden by formatter logic.
  3. Why can a created booking not be corrected safely? Because the current operator lifecycle stops at `create/status/no-show/governance`; it never completed `edit/reschedule/cancel` for the Console path.
  4. Why did this survive `Wave37`? Because `Wave37` correctly prioritized time discoverability and guardrails for creation, but it did not yet include filter-state architecture or the full booking lifecycle contract.
  5. Why is this still a product blocker instead of minor polish? Because it affects the three core operator jobs after opening Calendar: find the right records, enter reliable contact data, and safely fix/cancel an appointment.
- **Root cause statement:** the remaining bug cluster is not one UI typo. Calendar still lacks two explicit product contracts: a deterministic `draft -> apply` filter model and a complete booking lifecycle model. The phone field bug is the same class of problem at field level: implicit formatting logic overrides the operator's intent instead of respecting it.
- **Fix mechanism:** introduce one applied filter snapshot contract, split raw/normalized phone input, add bounded booking update/cancel contracts and UI, and prove the whole result with deterministic valid/invalid workflow coverage plus visual review.

## Reuse-first plan (mandatory)
- **Reuse:** current Calendar route, queue-state/saved-view contract, existing booking composer surface, existing cancel endpoint, existing appointment sync support for `create/update/cancel` actions, and the current Playwright mock harness.
- **Integrate:** convert the current Calendar state handling into an explicit filter reducer / applied snapshot pattern, reuse the composer in both `create` and `edit` modes, and reuse the existing backend cancel path rather than inventing a second cancellation contract.
- **Build only if needed:** bounded Console booking update route and shared backend helper extraction only where the current API surface does not expose existing reschedule/cancel capabilities cleanly enough for the operator UI.

## Invariant
- Do not reopen routing v2, assignee capability modeling, or unrelated global Console backlog while Calendar still fails operator basics.
- Do not regress the `Wave37` service-first create flow or hide time discoverability again.
- Do not keep destructive input formatting that prevents normal typing/deletion.
- Do not keep filters as simultaneous live URL/server/local writes without a single applied-state contract.
- Do not ship booking edit/cancel without deterministic tests for valid and invalid lifecycle paths.
- Do not merge if Calendar cards/case links and the case-bookings panel drift from the new lifecycle semantics.

## Scope
- Calendar-only post-merge hardening:
  - deterministic filter application/reset/persistence contract;
  - raw + normalized phone input contract in the booking composer;
  - booking edit/reschedule/cancel lifecycle from Calendar cards/action panel;
  - case-linked booking lifecycle consistency where the same booking appears in `CaseBookingsPanel`;
  - dedicated operator proof and visual acceptance for the new lifecycle paths.

## Out of scope
- Inbox redesign
- routing v2 or routing-profile changes
- global Console backlog items (`UX-08`, `UX-20`, `UX-26`)
- CRM/customer history platform work beyond bounded booking assistance
- bot-side booking reschedule policy changes outside the Console operator path

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/app/calendar/_components/*` (new extracted components allowed)
- `console-web/src/app/calendar/_lib/*` (new extracted hooks/helpers allowed)
- `console-web/src/components/CaseBookingsPanel.tsx`
- `console-web/src/lib/queue-state.ts`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/calendar-operator.spec.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/app/services/tool_registry_service.py` (only if shared reschedule/cancel helper extraction is required)
- `truffles-api/tests/test_calendar_bookings_router.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Delivery split / PR contract (mandatory)
- `Part A — Filter-state contract`
  - introduce explicit `draft` vs `applied` filter state;
  - make URL/local/server persistence write only `applied` snapshot;
  - add `Применить` / `Сбросить` semantics and deterministic incompatible-filter resets.
- `Part B — Phone/composer hardening`
  - replace destructive phone formatting with raw editable value + normalized preview;
  - preserve create-flow clarity and prevent invalid payloads before submit.
- `Part C — Booking lifecycle completion`
  - add edit/reschedule and cancel controls for existing bookings;
  - add bounded backend update contract and wire it through Calendar cards/panels and case-linked views.
- `Part D — Proof + visual acceptance`
  - extend deterministic Playwright proof to the new filter, phone, edit, reschedule, and cancel flows;
  - record visual inspection artifacts for all primary lifecycle states.

## Filter-state contract (mandatory)
- The Calendar queue must have one explicit `applied` snapshot that alone drives:
  - data fetches;
  - summary chips;
  - URL params;
  - local workspace prefs;
  - `/queue-state/current` writes.
- Panel controls may mutate `draft` state freely, but nothing operator-visible outside the panel may change until `Применить`.
- `Сбросить` must revert `draft` back to the current `applied` snapshot, not to hardcoded defaults unless the operator explicitly requests full reset.
- Switching `queueMode` / `queueLane` / case-context mode must clear incompatible filters deterministically and tell the operator what changed.
- Saved views must hydrate both `draft` and `applied` as one atomic snapshot; no partial live merge.
- Browser back/forward and reload must restore the same applied snapshot reproducibly.

## Phone-input contract (mandatory)
- The form must store an editable raw phone value separately from normalized submit data.
- Supported operator inputs must include at minimum:
  - `+7 701 555 44 33`
  - `8 701 555 44 33`
  - `87015554433`
  - paste with spaces, brackets, or dashes.
- Backspace, delete-from-middle, and select-all-delete must work naturally.
- The UI must show one of three states:
  - neutral hint when empty;
  - normalized preview when valid;
  - explicit field error when not yet valid.
- Submit must remain disabled until the normalized phone is coherent.

## Booking lifecycle contract (mandatory)
- Existing bookings must expose operator actions:
  - `Изменить запись`
  - `Отменить запись`
  - existing visit-status and no-show follow-up actions remain intact.
- `Изменить запись` must reuse the booking composer in `edit` mode with current values prefilled.
- Editable fields:
  - service
  - specialist
  - date
  - time
  - customer name
  - customer phone
  - notes
- Changing service/specialist/date must reset dependent slot state deterministically.
- `Отменить запись` must use the existing backend cancel path with confirmation and optional reason.
- Cancel/edit availability must be explicit by status; completed/cancelled/no-show bookings cannot silently accept invalid edits.
- Queue list, case-linked bookings, and booking action panel must all refresh consistently after edit/cancel.
- If the Console route needs a bounded update contract, prefer `PATCH /calendar/bookings/{booking_id}` and reuse existing reschedule/update sync semantics instead of inventing a second sync path.

## Visual inspection protocol (mandatory)
1. After every completed part, capture Calendar at `1024px`, `1280px`, and `1440px` widths.
2. Mandatory states:
   - queue first screen with dirty/applied filter state;
   - filters panel before apply and after apply;
   - booking composer phone valid/invalid states;
   - edit-booking flow;
   - cancel confirmation;
   - action panel after successful cancel/edit;
   - medium-width state with filters and edit flow open.
3. Each capture must be checked for:
   - no clipped or overflowed controls;
   - obvious primary action;
   - no duplicated destructive buttons;
   - no raw technical text;
   - no layout collision between queue and lifecycle panels.
4. Part closure is blocked until the visual checklist is explicitly clean.

## Test matrix (mandatory)
- `Filters / queue-state`:
  - draft changes do not fetch until `Применить`;
  - `Сбросить` returns to last applied snapshot;
  - URL reload restores applied snapshot;
  - back/forward restores applied snapshot;
  - saved view load/save stays deterministic;
  - switching `ops/history` or case-context clears incompatible filters predictably.
- `Phone input / composer`:
  - digit-by-digit typing;
  - paste in common local formats;
  - delete to empty;
  - delete from the middle;
  - invalid phone blocks submit;
  - valid phone normalizes correctly.
- `Create/edit/reschedule`:
  - create valid booking;
  - edit customer fields only;
  - edit service -> specialist/slot reset;
  - edit specialist -> slot reset;
  - edit date -> slot reload;
  - slot conflict / no slot available;
  - successful save updates queue and case-linked view.
- `Cancel lifecycle`:
  - cancel scheduled booking with reason;
  - cancel without reason;
  - already cancelled booking blocked;
  - cancelled booking visible in the cancelled filter;
  - case-linked booking summary updates correctly.
- `Regression and layout`:
  - no-show lifecycle still works;
  - follow-up governance still safe-labeled;
  - medium-width layout stays usable;
  - no duplicate button-name ambiguity in deterministic lanes.
- `Server boundary`:
  - router tests for booking update/cancel validation;
  - OpenAPI/generated types stay in sync if contract changes;
  - sync enqueue path stays correct for create/update/cancel.

## Plan (1..N)
1. Open `Wave38` on top of merged `origin/main`, sync canon, and record the new operator-reported defect cluster in `STATE.md` and backlog.
2. Extract Calendar queue/filter state into an explicit `draft -> applied` reducer/hook contract.
3. Replace current live filter side effects with transactional `apply/reset` behavior for URL/local/server persistence.
4. Split phone handling into raw editable value plus normalized preview/submit contract.
5. Reuse the existing booking composer for `edit` mode and wire deterministic dependent-state resets there too.
6. Expose booking cancel in the operator UI using the existing cancel backend contract.
7. Add a bounded Console booking update route if needed, reusing existing reschedule/update sync semantics rather than duplicating them.
8. Extend Calendar and case-linked booking surfaces so the same lifecycle is available and coherent in both places.
9. Extend Playwright and router coverage for the full valid/invalid matrix.
10. Run visual inspection after each part, sync canon, and do not move to other backlog work before the new closeout is green.

## DoD
- Calendar filters feel deterministic: draft edits are explicit, applied state is authoritative, and reload/back/saved-view flows are reproducible.
- Phone input allows normal typing, deletion, and paste without fighting the operator.
- Existing bookings can be edited/rescheduled and cancelled safely from the operator UI.
- Queue cards, action panels, and case-linked bookings reflect lifecycle changes consistently.
- The full valid/invalid matrix is green, including medium-width layout and visual review.
- No attempt is made to return to `UX-08` / `UX-20` / `UX-26` before this block is explicitly closed.

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/components/CaseBookingsPanel.tsx --file src/lib/queue-state.ts --file src/lib/calendar-bookings.ts --file e2e/calendar-operator.spec.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && npm run generate:api` (if contract/types change)
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/calendar-operator.spec.ts --project chromium`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "calendar|booking|follow-up|medium-width|filter|cancel|edit"`
- `cd truffles-api && pytest -q tests/test_calendar_bookings_router.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/calendar.py app/services/appointment_service.py app/services/tool_registry_service.py tests/test_calendar_bookings_router.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` (if contract changes)
- visual captures for all mandatory states at `1024px`, `1280px`, `1440px`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Progress log
- `2026-03-09` — `Wave38` opened after merged `Wave37`:
  - new operator evidence recorded: filters still feel desynchronized, phone typing/deletion remains frustrating, and created bookings still lack edit/cancel lifecycle;
  - new TP created with mandatory split `Part A filter-state contract`, `Part B phone/composer hardening`, `Part C booking lifecycle completion`, `Part D operator proof + visual acceptance`;
  - canon synced so `Wave38` becomes the only valid next block before any return to the non-Calendar backlog.

- `2026-03-09` — `Wave38 Part A` completed locally:
  - rebuilt Calendar filter handling around one explicit contract: queue/list/URL/server persistence now read only the applied snapshot, while the filter panel keeps its own draft until `Применить`;
  - `Сбросить изменения` now restores the current applied state instead of silently clearing live filters, and the filter panel explains that queue/list/link changes happen only after apply;
  - deterministic Playwright proof now asserts that draft edits do not leak into `/queue-state/current` before apply, and that reset returns the panel to the current applied state;
  - visual inspection is clean at `1280px` and `1024px` for dirty-draft and applied-filter states: `/tmp/wave38-part-a-filters-draft-1280.png`, `/tmp/wave38-part-a-filters-applied-1280.png`, `/tmp/wave38-part-a-filters-draft-1024.png`;
  - local evidence:
    - `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file e2e/calendar-operator.spec.ts` (`pass`)
    - `cd console-web && npm run build` (`pass`)
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/calendar-operator.spec.ts --project chromium` (`6 passed`)
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium` (`14 passed, 1 skipped`)

## Evidence
- New TP: `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- Synced canon pointers in `STATE.md`, master TP, backlog, session log, and session index
- `Wave38 Part A` local evidence in `console-web/src/app/calendar/page.tsx`, `console-web/e2e/calendar-operator.spec.ts`, `/tmp/wave38-part-a-filters-draft-1280.png`, `/tmp/wave38-part-a-filters-applied-1280.png`, `/tmp/wave38-part-a-filters-draft-1024.png`
- One-web-search record with MDN sources
- Future closeout evidence for this block must include Playwright artifacts, visual captures, router/OpenAPI checks, and PR link(s)

## Release safety (mandatory)
- **Rollout:** no rollback of `Wave37`; this block is a forward hardening pass on top of merged `main`.
- **Go/no-go:** no merge until filter state, phone input, and booking lifecycle are all green in both deterministic proof and visual acceptance.
- **Rollback:** revert the `Wave38` PR if the hardening introduces a regression; do not silently remove operator actions/guardrails as a workaround.

## Rollback
- `git revert REVISION_SHA`
- rerun Calendar lint/build/tests and the dedicated operator lane
- verify that `main` returns to the previous merged `Wave37` state while the follow-up TP remains open

## No-go
- No more live multi-source filter writes without an explicit applied-state boundary.
- No phone formatter that rewrites operator text destructively on every keystroke.
- No backend-only cancel capability without operator UI.
- No edit flow that can keep a stale service/specialist/slot combination.
- No return to other backlog work before this block is explicitly closed.

## Риски/блокеры
- Filter-state cleanup may require extracting a dedicated hook/reducer out of `calendar/page.tsx` to avoid another god-file cycle.
- Booking edit/update may require shared backend helper extraction so Console and tool-registry flows do not fork lifecycle logic.
- External calendar sync semantics for update/cancel must stay coherent; otherwise the Console may look correct while external truth drifts.
- If tests cover only happy paths again, this block will repeat the same post-merge failure mode as `Wave36`/`Wave37`.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: actionable-owner sourcing still comes from the generic `/agents` feed, and customer history/CRM assistance remains minimal outside linked-case context.
- `Why not in this block`: the immediate blocker is operator reliability in Calendar itself; widening owner/customer data contracts before fixing filter/lifecycle fundamentals would spread scope without closing the job.
- `Risk if deferred`: if real production data still proves too weak for action-owner clarity or repeat-booking assistance after `Wave38`, a bounded API follow-up will still be required.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`, and a bounded API follow-up only if `Wave38` proves current data contracts insufficient.
- `Expiry/trigger to stop deferral`: if `Wave38` still cannot make filters deterministic or booking edit/cancel reliable with current APIs, open the bounded API follow-up immediately instead of weakening the operator contract.

## Next-block contract (mandatory)
- `Next block objective`: execute `Wave38 Part A` first (filter-state contract), then `Part B`, `Part C`, and `Part D`; only after that decide whether a bounded Calendar API follow-up is needed or whether work can return to `UX-08` / `UX-20` / `UX-26`.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave38|draft -> applied|calendar-operator.spec.ts|phone input|edit/cancel" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md STATE.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: any attempt to skip explicit filter-state architecture, keep destructive phone formatting, ship edit/cancel without backend contract and proof, or move to other backlog work before `Wave38` closes.
- `Owner role for closure`: Brain / Top Architect.
