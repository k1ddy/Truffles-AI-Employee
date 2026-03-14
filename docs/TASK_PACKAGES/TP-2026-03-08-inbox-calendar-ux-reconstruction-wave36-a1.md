# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE36-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE31-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE31-A1`
- `UNLOCKS`: operator-grade closeout for `Записи`; no routing-v2 follow-up without explicit new TP

## Название/цель
Полностью пересобрать вкладку `Записи` как operator-grade рабочий экран: убрать сырые и англоязычные follow-up термины, скрыть технические/служебные аккаунты из operator UX, перестроить booking creation как guided flow с fast-fill и защитой от неправильного ввода, и довести все действия до визуально понятного, быстрого и безопасного поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one PR preferred; split allowed only into `Part A operator surface + copy/IA` then `Part B booking form guardrails + proof` if one PR becomes unsafe
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Current `Записи` still leak raw mixed-language operator copy and technical fallback labels:
  - filter chip uses `Follow-up owner: ...` and checkbox label uses `Только просроченный follow-up`: `console-web/src/app/calendar/page.tsx:917`, `console-web/src/app/calendar/page.tsx:923`, `console-web/src/app/calendar/page.tsx:1888`
  - booking cards/panel fall back to `raw agent id fallback` and `Owner:/Due:` copy: `console-web/src/app/calendar/page.tsx:1673`, `console-web/src/app/calendar/page.tsx:1734`, `console-web/src/app/calendar/page.tsx:2511`, `console-web/src/app/calendar/page.tsx:2566`
- Follow-up owner options are sourced from generic `/agents` and currently mapped to `agent.name?.trim() || agent.id`, so operator UX can expose service/technical accounts when they pass role/activity filters: `console-web/src/app/calendar/page.tsx:421`, `console-web/src/app/calendar/page.tsx:434`
- Booking creation still accepts an under-guarded payload from the UI:
  - submit only checks `selectedSlot` + `selectedSpecialist`; service/name/phone can be omitted freely: `console-web/src/app/calendar/page.tsx:1366`
  - API schema allows optional `customer_name`, `customer_phone`, and `service_type` with no stronger calendar-specific rules: `truffles-api/app/routers/calendar.py:121`
- Current scheduling form is not guided enough:
  - service selection stays optional via `Любая услуга`
  - slot choice can precede client-data validation
  - validation feedback is toast-only for conflict/error paths and not inline for wrong input: `console-web/src/app/calendar/page.tsx:2298`, `console-web/src/app/calendar/page.tsx:2423`, `console-web/src/app/calendar/page.tsx:1165`
- The user-reported overflow is credible from markup alone: long checkbox/filter labels are placed in tight `sm:grid-cols-2` cells with no dedicated compact copy or wrap strategy: `console-web/src/app/calendar/page.tsx:1838`, `console-web/src/app/calendar/page.tsx:1882`

## One web search (mandatory before implementation)
- **Query (exact):** `site:design-system.service.gov.uk validation error summary hint text select date input`
- **Date/time (local):** `2026-03-08T13:47:00+05:00`
- **Sources opened:**
  - `https://design-system.service.gov.uk/components/error-summary/`
  - `https://design-system.service.gov.uk/components/hint-text/`
  - `https://design-system.service.gov.uk/components/select/`
  - `https://design-system.service.gov.uk/components/date-input/`
- **Ready solutions found:** official GOV.UK guidance reinforces four relevant rules: use plain labels/hint text instead of placeholder-only explanation; show error summary plus inline field errors; use `select` only for known constrained choices; structure date/time input so the expected input is explicit rather than implicit.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the existing Calendar route and backend contracts where possible, but rebuild the operator surface and booking form around explicit labels, guided constrained choices, and inline validation instead of raw fallback copy and toast-only failure handling.
- **Rejected options:** cosmetic restyle without changing form logic; keeping English/technical follow-up wording; relying on placeholders and backend errors to teach the operator correct input.
- **Source quality:** high-signal primary source = official GOV.UK Design System.

## Root cause (mandatory)
- **Symptom:** `Записи` remains visually noisy, terminology is partially technical/English, and booking creation allows operators to produce weak or wrong data with too little guidance.
- **Minimal reproduction:** open `/calendar`, note the mixed-language follow-up labels, raw owner fallbacks, cramped filter controls, then open scheduling and submit with minimal data — the UI does not guide the operator through a clear, validated booking flow.
- **Evidence:** `console-web/src/app/calendar/page.tsx:421`, `console-web/src/app/calendar/page.tsx:917`, `console-web/src/app/calendar/page.tsx:1673`, `console-web/src/app/calendar/page.tsx:1888`, `console-web/src/app/calendar/page.tsx:2298`, `console-web/src/app/calendar/page.tsx:2423`, `truffles-api/app/routers/calendar.py:121`
- **Five Whys:**
  1. Why does Calendar still feel wrong after Wave34/35? Because first-screen decomposition happened, but operator semantics and data-entry ergonomics were not rebuilt to the same standard.
  2. Why are operators seeing raw/strange terms and accounts? Because generic backend values are still rendered nearly as-is, with weak operator-oriented normalization.
  3. Why can wrong or weak booking data still get through? Because the UI only checks technical minimums and the API schema also keeps customer/service fields broadly optional.
  4. Why is this a product defect, not just polish? Because bad labels and weak guardrails directly slow operators down and let low-quality booking records enter the system.
  5. Why does this need a dedicated full rebuild wave? Because copy, IA, validation, fast-fill assistance, and misuse-proof testing all need to move together; patching one in isolation keeps the tab inconsistent.
- **Root cause statement:** `Записи` was decomposed structurally, but it still lacks an operator-owned semantic and validation layer: raw backend-ish terminology leaks into the UI, generic agent lists leak into follow-up selectors, and booking creation remains too permissive and too weakly guided.
- **Fix mechanism:** rebuild Calendar around plain-language operator copy, filtered/sanitized actionable choices, a guided booking composer with inline validation and assisted defaults, and deterministic tests that cover both valid and invalid interaction paths.

## Reuse-first plan (mandatory)
- **Reuse:** current queue-state/saved-view/share-link contracts, booking queries, specialist/slot APIs, visit-status/follow-up mutations, and `inspect_case.spec.ts` acceptance lane.
- **Integrate:** redesign the Calendar route with extracted UI sections/components and stronger client-side validation over the existing APIs before introducing any backend schema tightening.
- **Build only if needed:** bounded backend validation additions only where current API permissiveness would still allow clearly wrong operator records after the UI rebuild.

## Invariant
- Do not reopen routing v2 or any fake skills/presence work.
- Do not regress existing Wave24-30 backend contracts unless a bounded validation tightening is explicitly needed for data quality.
- Do not expose raw UUID fallbacks or technical account labels in operator-facing selectors/chips when a safer business-readable alternative exists.
- Do not keep booking creation as a free-form submit-anything form.
- Do not rely on toasts as the primary explanation for input errors.

## Scope
- Calendar only:
  - rebuild filter/follow-up copy into plain Russian operator language;
  - sanitize follow-up owner presentation so operator-facing choices exclude or safely mask technical/system accounts;
  - fix overflow/density issues in filter controls and chips;
  - redesign booking creation as a guided composer: specialist -> service -> date -> slot -> client data -> confirm;
  - add inline validation, disabled submit states, and field-level guidance;
  - prefill booking customer data from focused case when available;
  - make booking actions/follow-up actions visually simpler and more business-readable;
  - add deterministic coverage for valid and invalid flows, plus visual inspections after each major phase.

## Out of scope
- Inbox changes
- routing v2 / capability modeling
- new calendar routes or a second IA for the same surface
- unrelated global Console backlog items

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/lib/calendar-bookings.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Operator UX contract (mandatory)
- `Language`:
  - no raw `Follow-up owner`, `Due`, `governance`, `Owner`, `raw agent id fallback` copy in the operator surface;
  - use plain Russian action-oriented labels (`Кто связывается`, `Срок связи`, `Только просроченные`, etc.).
- `Follow-up ownership`:
  - operator sees only understandable actionable people, not technical/service identities;
  - if a technical owner exists historically, show a safe fallback label rather than raw id noise.
- `Booking composer`:
  - guided order: specialist -> service -> date -> slot -> customer;
  - when the specialist has service options, service is required before final submit;
  - customer data fields must be normalized and validated inline;
  - submit is blocked until the record is coherent.
- `Fast-fill`:
  - when `case_id` is present, prefill customer name/phone from the linked case if available;
  - preserve operator speed with smart defaults and one-click resets.
- `Error prevention`:
  - invalid or incomplete input must be explained near the field and in a compact summary area;
  - obvious wrong states should be blocked before API submit.
- `Visual discipline`:
  - no overflow/truncation that breaks primary controls on medium-width desktop;
  - form density must remain readable on desktop and narrower desktop widths.

## Visual inspection protocol (mandatory)
1. After each major phase, run a local browser capture at `1440px` and `1280px` widths.
2. Inspect specifically:
   - first visible queue triage block,
   - filters drawer/sheet,
   - booking composer states,
   - booking action panel,
   - long-label wrapping and control alignment.
3. Record any visual regression before moving to the next phase.

## Test protocol (mandatory)
- Cover valid flows:
  - open calendar queue and use filters without overflow;
  - create a booking through the guided flow;
  - update visit status;
  - close no-show follow-up;
  - update follow-up owner/deadline;
  - restore/copy queue state if touched by the rebuild.
- Cover invalid flows:
  - submit without required service when specialist has service options;
  - submit without coherent customer data;
  - invalid phone formatting / normalization edge cases;
  - wrong follow-up actions for ineligible status;
  - disabled or hidden technical follow-up-owner options.
- Cover layout:
  - medium-width queue controls and booking composer remain readable and inside bounds.

## Plan (1..N)
1. Create Wave36 TP and switch active session/master canon to the new block.
2. Rebuild Calendar copy and IA: plain-language filters/chips/actions, sanitized follow-up-owner presentation, overflow-safe controls.
3. Rebuild booking composer into a guided multi-stage flow with prefill and inline validation.
4. Tighten backend validation only where the rebuilt UI still cannot fully protect data quality.
5. Run visual inspections after each major UI phase.
6. Extend deterministic Playwright/tests for valid + invalid interactions and layout.
7. Sync canon/session/state and prepare the branch for PR.

## DoD
- `Записи` reads as a business/operator surface, not a mixed technical/governance screen.
- No raw technical follow-up labels or raw UUID owner fallbacks remain in the main operator flow.
- Booking creation becomes guided, validated, and significantly harder to misuse.
- Invalid interactions are blocked with inline explanation before or at submit time.
- Visual review is completed after each major phase.
- Deterministic tests cover both correct and incorrect behaviors of all rebuilt controls and their sub-objects.

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file src/lib/calendar-bookings.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd truffles-api && pytest -q tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && ruff check app/routers/calendar.py app/services/appointment_service.py tests/test_calendar_noshow_followup_router.py tests/test_console_openapi_calendar_contract.py`
- visual captures at `1440px` and `1280px` after each major UI phase
- targeted Playwright lanes for valid and invalid calendar interactions
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- calendar UI diff showing the rebuilt operator surface and booking composer
- visual inspection artifacts / screenshots per major phase
- deterministic Playwright evidence for valid and invalid interactions
- any bounded backend validation diff if required
- updated canon/session/state pointers

## Release safety (mandatory)
- **Rollout:** one bounded Calendar-only rebuild behind the existing route; no routing changes.
- **Go/no-go:** merge only if visual inspections and deterministic valid/invalid interaction tests are green.
- **Rollback:** revert the Wave36 diff; previous Calendar surface remains functional.

## Rollback
- `git revert REVISION_SHA`
- rerun Calendar lint/build/tests
- confirm existing queue/action flows recover cleanly

## No-go
- Do not keep English/technical operator copy where a plain Russian action label exists.
- Do not leave technical/service identities directly visible in operator follow-up selectors without explicit reason.
- Do not permit submit-anything booking creation.
- Do not close the wave on happy-path tests only; misuse/invalid flows are mandatory.
- Do not skip visual inspections between phases.

## Риски/блокеры
- If the rebuild remains inside one god-file without extraction discipline, maintainability will regress again quickly.
- If backend validation stays too permissive, the UI alone may not fully protect data quality.
- If technical accounts cannot be cleanly separated from actionable staff in current agent APIs, we will need a bounded fallback presentation rule or API filter.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: generic `/agents` sourcing for follow-up ownership may still need a more explicit server-owned actionable-owner contract later.
- `Why not in this block`: first goal is to stop operator pain and misuse with the minimum bounded truth-preserving redesign.
- `Risk if deferred`: some owner-source ambiguity may remain even after the UI is cleaned up.
- `Linked follow-up Task Package(s)`: open only if Wave36 proves the UI still needs a dedicated actionable-owner API contract.
- `Expiry/trigger to stop deferral`: if Wave36 cannot hide/sanitize technical owner options safely with current data, open the follow-up immediately instead of shipping raw operator noise.

## Next-block contract (mandatory)
- `Next block objective`: close Calendar as an operator-grade surface, then reassess whether any server-side follow-up-owner contract gap remains.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Follow-up owner|Agent |Любая услуга|handleSubmit|customer_phone|service_type" console-web/src/app/calendar/page.tsx truffles-api/app/routers/calendar.py docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md`
- `Blocked-by conditions`: any reintroduction of raw technical copy, any free-form booking submit path without guardrails, or missing misuse tests blocks closure.
- `Owner role for closure`: Brain / Top Architect.
