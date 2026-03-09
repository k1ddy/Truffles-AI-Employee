# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE37-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE36-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE34-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE36-A1`
- `UNLOCKS`: Calendar acceptance closeout, optional bounded follow-up for actionable-owner API only if current `/agents` truth remains insufficient after the rebuild

## Название/цель
Довести вкладку `Записи` до реального operator-grade состояния после merged `Wave36`, не откатывая предыдущие изменения: полностью пересобрать сценарий создания записи вокруг явного выбора услуги/времени, убрать неинтуитивные и технические термины, ввести сильные guardrails против неправильного ввода и закрыть acceptance не happy-pathом, а полной матрицей valid/invalid workflow + layout proof.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split expected and mandatory: `Part A booking entry + slot discoverability`, `Part B terminology/guardrails/actions`, `Part C operator proof + visual acceptance`. `Part B` and `Part C` are blocked until the previous part is green.
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Real operator feedback after `Wave36` merge invalidated the previous acceptance claim: on `2026-03-08` the merged Calendar still fails the primary booking job — the operator cannot reliably reach/select time when creating a booking, terminology/options remain unclear, and the overall flow is still not self-explanatory.
- Current code still hides time slots behind an implicit four-condition gate instead of an explicit operator-led step:
  - slot query only runs when `selectedSpecialist && bookingDate && specialistHasConfiguredServices && selectedService`: `console-web/src/app/calendar/page.tsx:1019`, `console-web/src/app/calendar/page.tsx:1022`
  - the UI then shows only passive empty text states (`Сначала выберите...` / `слотов нет`) rather than a guided next action: `console-web/src/app/calendar/page.tsx:2829`, `console-web/src/app/calendar/page.tsx:2833`, `console-web/src/app/calendar/page.tsx:2843`
- Booking creation still lives inside the overloaded secondary scheduling sheet instead of a focused create-booking flow, so queue triage, booking creation, and action governance compete for the same attention budget: `console-web/src/app/calendar/page.tsx:2515`, `console-web/src/app/calendar/page.tsx:2678`, `console-web/src/app/calendar/page.tsx:2999`
- The current guided order is `мастер -> услуга -> день -> слот -> клиент`, but the backend slot contract is duration-driven and the operator problem is time discoverability. That makes `service-first` the safer primary model for Wave37 because service duration is the earliest non-negotiable truth for slot search.
- Follow-up language is safer than before but still not operator-final: the UI still exposes an internal concept (`follow-up`) instead of a consistently business-readable action language, and the filter/action blocks still mix queue triage with governance terminology: `console-web/src/app/calendar/page.tsx:1139`, `console-web/src/app/calendar/page.tsx:2271`, `console-web/src/app/calendar/page.tsx:3294`
- Current proof is insufficient because the green mock lane did not assert the real operator question "как выбрать время и понять, что делать дальше". That gap allowed merged code with passing targeted tests to remain non-operable.

## One web search (mandatory before implementation)
- **Query (exact):** `site:design-system.service.gov.uk validation error summary hint text select date input`
- **Date/time (local):** `2026-03-08T18:00:56+05:00`
- **Sources opened:**
  - `https://design-system.service.gov.uk/components/error-summary/`
  - `https://design-system.service.gov.uk/components/hint-text/`
  - `https://design-system.service.gov.uk/components/select/`
  - `https://design-system.service.gov.uk/components/date-input/`
- **Ready solutions found:** high-signal guidance consistently says that form flows must expose explicit labels and hints, keep constrained choices as actual choices instead of guesswork, show error summary plus field-local errors, and make date/time expectations visible before submit rather than after failure.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the existing `/calendar` route and the current backend specialist/slot/follow-up contracts where they are already correct, but rebuild the operator flow around explicit steps, constrained inputs, inline guidance, and visible blocked states.
- **Rejected options:** another cosmetic pass over the current side sheet; relying on toasts/backend errors to teach the operator what is required; reopening routing or unrelated global Console backlog before Calendar acceptance is real.
- **Source quality:** high-signal primary source = official GOV.UK Design System documentation.

## Root cause (mandatory)
- **Symptom:** after `Wave36` merged, real operator usage still reports the Calendar tab as confusing and partially broken: time selection is not discoverable, terminology is still not intuitive, and the form does not sufficiently prevent or explain wrong input.
- **Minimal reproduction:** open `/calendar`, start creating a booking from the current scheduling surface, try to reach a time choice without already knowing the internal prerequisite order, then inspect follow-up filters/actions and the client data section. The operator can easily end up in a state where time is simply absent, the next step is unclear, and terminology does not explain the action model.
- **Evidence:** `console-web/src/app/calendar/page.tsx:1019`, `console-web/src/app/calendar/page.tsx:1022`, `console-web/src/app/calendar/page.tsx:2829`, `console-web/src/app/calendar/page.tsx:2833`, `console-web/src/app/calendar/page.tsx:2843`, `console-web/src/app/calendar/page.tsx:2999`, user acceptance feedback on `2026-03-08` captured in `STATE.md` and the active session log.
- **Five Whys:**
  1. Why is time selection effectively "missing" for operators? Because slot loading is gated by hidden prerequisites and the UI does not lead the operator through them explicitly.
  2. Why does that happen even after a guided composer was added? Because the composer is still structured around system prerequisites, not around the operator's mental model of "услуга -> когда -> кто может -> кого записываем".
  3. Why is the flow still hard to understand? Because booking creation remains embedded in a busy secondary surface that also carries queue context and governance noise.
  4. Why did tests not stop this? Because the current proof mostly validated technical happy paths and layout slices, not the full operator journey including discoverability, blocked states, and misuse paths.
  5. Why is this still a product bug and not mere copy polish? Because the primary business job of the tab is fast, reliable booking creation, and that job is currently not safely operable.
- **Root cause statement:** `Wave36` improved surface safety and backend validation, but it did not change the Calendar interaction model deeply enough. The booking flow is still system-shaped instead of operator-shaped: slot availability hides behind implicit conditions, creation competes with other sheet content, and the acceptance suite did not prove real discoverability or misuse resistance.
- **Fix mechanism:** rebuild the Calendar create-booking path around a focused, explicit service-first operator journey; separate booking creation from secondary governance noise; make every blocked state visible and actionable; harden field-level guidance and server boundaries; and replace the current proof gap with a dedicated operator acceptance matrix that covers valid, invalid, and layout behaviors.

## Reuse-first plan (mandatory)
- **Reuse:** existing `/calendar/bookings`, `/calendar/slots`, `/calendar/specialists`, queue-state/saved-view/share contracts, follow-up governance mutations, and current router validation for booking payload normalization.
- **Integrate:** extract the create-booking experience into a focused operator flow within the existing Calendar route, reusing the current data sources while changing interaction order, wording, and proof.
- **Build only if needed:** bounded backend additions only if current contracts still allow broken payloads or if the operator cannot be protected without an explicit server-owned signal.

## Invariant
- Do not roll back `Wave36` wholesale; this block is a forward fix from the merged state.
- Do not reopen routing v2, capability modeling, or unrelated Console backlog while Calendar remains non-operable.
- Do not ship another Calendar change that passes only mocked happy-path tests.
- Do not keep booking creation in a form where time selection can silently disappear without an explicit reason and next action.
- Do not leak technical account names, raw ids, or internal governance jargon into the main operator path.
- Do not allow free-text service/specialist/time combinations that bypass constrained choices.

## Scope
- Calendar-only recovery and redesign on top of merged `Wave36`:
  - rebuild the booking entry path into a focused operator flow;
  - switch the primary booking order to `услуга -> мастер -> день -> время -> клиент -> подтверждение`, with smart prefill when a case already provides context;
  - make slot states explicit: `нужно выбрать данные`, `ищем время`, `на этот день времени нет`, `время найдено`, `ошибка загрузки`;
  - simplify and localize all operator copy around follow-up/contact tasks and booking actions;
  - harden validation and wrong-input prevention on every primary field/control;
  - run visual inspection after each implementation phase;
  - close with full valid/invalid workflow proof and medium-width layout proof.

## Out of scope
- Inbox redesign
- routing v2 or new routing inputs
- global Console backlog items (`UX-08`, `UX-20`, `UX-26`)
- a brand-new top-level route outside `/calendar`
- customer CRM/search platform work beyond bounded booking assistance

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/app/calendar/_components/*` (new extracted components allowed)
- `console-web/src/app/calendar/_lib/*` (new extracted helpers/hooks allowed)
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/calendar-operator.spec.ts` (new dedicated operator acceptance lane expected)
- `console-web/e2e/inspect_case.spec.ts`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/tests/test_calendar_bookings_router.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Delivery split / PR contract (mandatory)
- `Part A — Booking entry and time discoverability`
  - isolate booking creation into a focused operator flow/surface inside `/calendar`;
  - switch to service-first logic;
  - make slot loading/empty/error/available states explicit;
  - prove the operator can always understand why time is or is not shown.
- `Part B — Guardrails, copy, and action cleanup`
  - replace remaining jargon with plain action language;
  - harden phone/name/service validation and helper text;
  - simplify follow-up/contact-task and booking action panels;
  - remove weak or visually broken controls.
- `Part C — Acceptance proof`
  - dedicated e2e lane for Calendar operator workflows;
  - full valid/invalid matrix for every primary interaction and sub-object;
  - medium-width and visual inspection evidence before PR close.

## Operator journey contract (mandatory)
- `Entry points`:
  - from queue toolbar: `Новая запись`;
  - from linked case: `Записать клиента` with case prefill;
  - from no-show recovery: `Перезаписать клиента` with linked-booking requirement.
- `Primary create-booking sequence`:
  1. `Услуга` — mandatory, no `Любая услуга` in the create flow.
  2. `Мастер` — only specialists who can perform the chosen service; optional quick choice `Первый доступный` is allowed only if the implementation can prove it deterministically.
  3. `День` — quick chips (`Сегодня`, `Завтра`, ближайшие дни`) plus calendar input fallback.
  4. `Время` — grouped slots (`Утро`, `День`, `Вечер`) or similarly readable grouping; no hidden grid without context.
  5. `Клиент` — name/phone with prefill from case when present.
  6. `Подтверждение` — short summary before final submit.
- `Blocked state language`:
  - every blocked step must say exactly what is missing and what to do next;
  - examples: `Сначала выберите услугу`, `Для этой услуги нет свободных мастеров`, `На этот день свободного времени нет`, `Введите телефон клиента`.
- `Speed helpers`:
  - case prefill one-click action;
  - preserve previously selected service when reopening the flow in the same session if it is still valid;
  - one-click reset for the full draft;
  - optional nearest-available suggestion only if it is explicit, understandable, and test-covered.

## Language and action model (mandatory)
- Replace internal wording with operator language:
  - `follow-up` -> `задача по связи` or `связаться с клиентом` depending on context;
  - `owner` -> `кто отвечает` / `кто связывается` where the business action is contact ownership;
  - `due` -> `связаться до` / `срок связи`.
- Historical technical owners may remain in stored data, but the UI must render only safe labels (`Служебный аккаунт`, `Скрытая учетная запись`, `Не назначено`) and must not expose technical identities as normal choices.
- Calendar filters and action panels must explain the job, not the model. The operator should read the screen as actions (`найти`, `создать`, `связаться`, `обновить результат`), not as governance internals.

## Data-entry and prevention contract (mandatory)
- `Service`: required, chosen from constrained options only.
- `Specialist`: chosen only from specialists who support the selected service.
- `Date`: chosen from today or future dates only; if date has no slots, the UI must say so before submit.
- `Time`: chosen only from real slots; no manual text time entry.
- `Customer name`: required, inline validation on blur and on submit.
- `Customer phone`: masked input plus normalization preview/inline validation; bad phone never reaches API silently.
- `Notes`: optional and visually secondary.
- `Submit`: disabled until the payload is coherent; summary must show all selected values before submit.
- `No-show rebook`: impossible to submit as `rebooked` without an explicit linked booking.

## Visual inspection protocol (mandatory)
1. After every completed part, capture the rebuilt Calendar at `1024px`, `1280px`, and `1440px` widths.
2. Mandatory capture states:
   - queue first screen;
   - filters surface;
   - booking flow step `Услуга`;
   - booking flow step `Время` with available slots;
   - booking flow empty-state (`нет времени`);
   - booking flow validation state (`ошибки заполнения`);
   - booking action / contact-task panel.
3. Each capture must be checked for:
   - no clipped or overflowed controls;
   - readable hierarchy;
   - obvious next action;
   - no mixed-language or raw technical text;
   - no duplicated destructive/primary CTAs.
4. Part closure is blocked until the visual checklist is explicitly clean.

## Test matrix (mandatory)
- `Queue and filters`:
  - open queue, search, follow-up/contact-task filters, overdue-only toggle, medium-width layout;
  - assert no overflow and no clipped copy.
- `Create booking — valid`:
  - from empty calendar;
  - from linked case with prefill;
  - with service -> specialist -> day -> time -> customer -> submit;
  - with empty-day fallback to another day;
  - with reset and re-entry.
- `Create booking — invalid`:
  - no service;
  - no specialist for service;
  - no date;
  - no slot;
  - invalid phone;
  - empty name;
  - specialist changed after time selection (slot must reset);
  - service changed after specialist/time selection (dependent state must reset);
  - slot fetch error;
  - no slots available.
- `Actions and follow-up/contact tasks`:
  - update visit status;
  - no-show follow-up complete;
  - no-show rebook requires linked booking;
  - change responsible person and due date;
  - technical owners remain hidden/safely labeled.
- `Regression and layout`:
  - medium-width visibility of primary queue surfaces;
  - no collision between queue controls and booking flow;
  - no duplicate button-name ambiguity in the deterministic lane.
- `Server boundary`:
  - router tests for booking payload normalization/validation;
  - router tests for no-show rebook guard;
  - OpenAPI and generated types stay in sync if contract changes.

## Plan (1..N)
1. Open `Wave37` on top of merged `main`, sync canon, and mark `Wave36` acceptance as invalidated by real operator evidence.
2. Extract the create-booking path out of the overloaded scheduling sheet into a focused operator flow within `/calendar`.
3. Reorder the booking journey to service-first, with explicit step states and deterministic resets when upstream choices change.
4. Rebuild time selection so the operator always sees one of the explicit slot states (`blocked/loading/empty/error/available`).
5. Simplify Calendar language and action grouping: filters, booking actions, and contact-task ownership/due language.
6. Harden input assistance and prevention: mask/normalize phone, require coherent customer data, prevent invalid combinations before submit.
7. Tighten server validation only where the rebuilt client flow still cannot fail-closed by itself.
8. Add a dedicated Calendar operator e2e lane and extend deterministic router tests for all invalid paths.
9. Run visual inspections after each part and do not advance while layout/copy issues remain.
10. Sync canon/state/session docs and prepare PR(s) only after the full acceptance matrix is green.

## DoD
- The operator can reliably create a booking and explicitly choose time without guessing hidden prerequisites.
- Calendar language is plain, business-readable, and consistent across filters, cards, and action panels.
- Weak or wrong booking input is blocked early with field-local explanation and summary-level guidance.
- Technical owners/accounts do not appear as normal operator options.
- Every major control and sub-object has both valid and invalid deterministic proof.
- Visual inspections for `1024px`, `1280px`, and `1440px` are recorded and clean.
- No further routing/backlog work is started before this acceptance closes.

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/lib/calendar-bookings.ts --file e2e/calendar-operator.spec.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && npm run generate:api` (if contract/types change)
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/calendar-operator.spec.ts --project chromium`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "calendar|booking|follow-up|rebook|medium-width"`
- `cd truffles-api && pytest -q tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/calendar.py app/services/appointment_service.py tests/test_calendar_bookings_router.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` (if API contract changes)
- visual captures for all mandatory states at `1024px`, `1280px`, `1440px`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Progress log
- `2026-03-08` — `Part A` completed locally:
  - booking creation moved out of the overloaded scheduling sheet into a focused right-side composer with a visible 5-step summary;
  - the primary order is now `услуга -> мастер -> день -> время -> клиент`, with deterministic resets when upstream choices change;
  - slot discovery now exposes explicit `blocked/loading/empty/error/ready` states instead of silently hiding time;
  - `inspect_case` mock harness was updated so scheduling opens cleanly after other secondary surfaces and the root route-mock login flow survives the current shell bootstrap reliably;
  - visual captures recorded for queue, filters, initial composer, service-selected state, ready slots, empty state, and validation state at `1024px`, `1280px`, `1440px`: `/tmp/wave37-part-a-calendar-*.png`;
  - local checks are green on the rebuilt flow:
    - `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file e2e/inspect_case.spec.ts`
    - `cd console-web && npm run build`
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "calendar booking flow explains why time is hidden until service and specialist are selected|guided booking composer blocks invalid submit until service name phone and slot are coherent, then creates booking|calendar secondary panels isolate filters and booking actions|medium-width inbox and calendar keep primary queue surfaces visible"`
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|manager history modes hide queue views and keep owner scope role-gated|role-gated owner scope is normalized before first queue request|manage and apply action macro"`
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium`
    - `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`
- `2026-03-08` — `Part B` completed locally:
  - remaining Calendar copy now reads as actions instead of model terms: filters use `кто звонит клиенту` / `только просроченные задачи по звонкам`, no-show cards/panels use `за звонок отвечает` / `позвонить до`, and the booking action panel is grouped as `1. Что с визитом` -> `2. Что решили после неявки` -> `3. Кто отвечает за звонок`;
  - booking composer now shows an explicit `Что делать дальше` panel, a clearer customer step state, normalized phone-preview helper text, safer input constraints, and a submit hint that explains exactly why creation is still blocked;
  - guarded UX regressions caught during validation were fixed locally: the follow-up owner filter expectation was updated to the new plain-language option label, and the phone input now accepts the common operator format `8 (701) 555-44-33` without truncating the normalized preview;
  - refreshed visual captures stayed clean for filters, ready-slot composer, validation state, and the action panel at `1024px`, `1280px`, `1440px`.
- `2026-03-08` — `Part C` completed locally:
  - added the dedicated deterministic operator lane `console-web/e2e/calendar-operator.spec.ts` covering dependent-state resets, reset/re-entry, case prefill, empty-day fallback, slot retry after error, safe follow-up completion, and medium-width layout bounds;
  - reran the mixed `inspect_case` lane to ensure the new dedicated Calendar proof does not regress the existing Inbox/Calendar workflow matrix;
  - refreshed the visual checklist to include the booking action panel alongside queue, filters, composer initial/ready/empty/validation states at `1024px`, `1280px`, and `1440px`: `/tmp/wave37-part-a-calendar-*.png`;
  - local checks are green for the full closeout:
    - `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file e2e/inspect_case.spec.ts --file e2e/calendar-operator.spec.ts`
    - `cd console-web && npm run build`
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/calendar-operator.spec.ts --project chromium`
    - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium`
    - `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

- `2026-03-09` — merged via `PR #959`, but post-merge operator evidence reopened Calendar under `Wave38` for three remaining gaps: explicit filter-state synchronization, natural phone-input ergonomics, and full booking edit/cancel lifecycle completion. `Wave37` is now historical merged scope, not the active acceptance block.

## Evidence
- New `Wave37` TP and synced canon pointers
- visual inspection artifacts for every mandatory state and width
- dedicated Calendar operator Playwright artifacts for valid/invalid workflows
- router/OpenAPI evidence for any bounded validation changes
- git diff showing the forward fix on top of merged `Wave36`, not a rollback

## Release safety (mandatory)
- **Rollout:** forward-fix from merged `main`; no rollback of `Wave36`. Use preview/staging validation first, then merge only after the full acceptance matrix is green.
- **Go/no-go:** the local closeout is now green; merge is still blocked until the PR carries this evidence set intact and review confirms the rebuilt Calendar remains operator-grade on the real branch diff.
- **Rollback:** revert the `Wave37` PR only if the forward fix introduces a new regression; do not reopen `Wave36` behavior by stealth without an explicit owner decision.

## Rollback
- `git revert REVISION_SHA`
- rerun Calendar lint/build/tests and the dedicated operator lane
- verify that `main` returns to the previous merged state while the follow-up TP remains open

## No-go
- No more Calendar acceptance claims based only on mocked happy paths.
- No hidden prerequisite logic without visible blocked-state explanation.
- No `Любая услуга` placeholder path inside create-booking.
- No raw technical owner/account labels in primary operator surfaces.
- No toast-only input-error model.
- No reopening of routing/backlog work before Calendar acceptance is actually closed.

## Риски/блокеры
- If booking creation stays in one overloaded sheet without a focused flow, operator discoverability will regress again.
- If the dedicated e2e lane is not created, `inspect_case.spec.ts` will continue to hide Calendar-specific acceptance gaps inside a mixed scenario file.
- If `/agents` truth still mixes too many actionable and technical identities, an API-level follow-up may be required after UI cleanup.
- If the flow is rebuilt but still keeps service optional, slot discoverability will remain inconsistent because duration remains undefined.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: current staff/actionable-owner sourcing still depends on the generic `/agents` feed; customer lookup/history assist remains minimal outside linked-case prefill.
- `Why not in this block`: the priority is to restore a fully operable Calendar workflow on top of current truth before inventing a second owner directory or CRM layer.
- `Risk if deferred`: the UI may still need one future bounded API follow-up if current owner/customer truth proves insufficient even after the flow is rebuilt.
- `Linked follow-up Task Package(s)`: only if needed after `Wave37`; otherwise no new Calendar follow-up opens before re-checking the global Console backlog.
- `Expiry/trigger to stop deferral`: if `Wave37` cannot hide technical identities safely or cannot make repeat-booking assistance fast enough with current APIs, open the bounded follow-up immediately instead of weakening the operator UX.

## Next-block contract (mandatory)
- `Next block objective`: open/land the `Wave37` PR with the completed Part A/B/C evidence set; after merge, decide whether any bounded Calendar API follow-up is still needed for actionable owners/customer assistance, or return to `UX-08` / `UX-20` / `UX-26`.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave37|slot discoverability|service-first|calendar-operator.spec.ts|post-merge operator evidence" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md STATE.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: PR review finds any remaining raw technical language/owners in the main path, hidden invalid states, missing visual artifacts, or any attempt to move to other backlog work before the `Wave37` PR is accepted.
- `Owner role for closure`: Brain / Top Architect.
