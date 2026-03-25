# Inbox + Calendar UX/Logic Audit (A1)

Block
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-LOGIC-AUDIT-A1`
- Parent: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- Date: `2026-03-08`

Goal
- Produce one factual audit of `Заявки` and `Записи` after Waves24-30: what is logically solid, what is visually broken, and what exact execution order removes the remaining operator debt.

What is already solid
- Server-owned queue state, personal saved views, team presets, shareable URLs, booking follow-up governance, and routing profiles are now real backend contracts rather than UI-local heuristics.
- Backend correctness coverage for those contracts is strong.
- The remaining product defect has shifted from missing truth to poor interaction architecture.

Deterministic evidence
- `wc -l console-web/src/components/CaseList.tsx console-web/src/app/calendar/page.tsx` -> `3291`, `2354`
- `cd truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_calendar_noshow_followup_router.py tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py` -> `103 passed`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3101 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|manager history modes hide queue views and keep owner scope role-gated|manage and apply action macro|action feedback hides raw sync reason codes and keeps reopen internal-only|booking no-show reopens resolved case and preserves case-booking semantics"` -> `4 passed`, `1 failed`
- Failing Playwright assertion: `console-web/e2e/inspect_case.spec.ts:1319` expected `inbox-list` width `> 300`, received `0`
- The failing page snapshot still shows a loaded queue surface with stacked operator controls before the list items: `console-web/test-results/inspect_case-inspect-first-case-chromium/error-context.md`

Research principles integrated
- Atlassian queue guidance: keep a small number of high-value queues and avoid cluttering first-screen queue surfaces.
- HubSpot/Zendesk view guidance: views should focus work; shared/admin-managed views are a governance layer, not the primary task surface itself.
- Decision: keep personal/shared views and queue modes, but move management and secondary configuration off the first screen.

Findings
1. `CaseList` first screen is control-heavy before the queue becomes the primary object.
   - Evidence: `console-web/src/components/CaseList.tsx:1961`, `console-web/src/components/CaseList.tsx:2013`, `console-web/src/components/CaseList.tsx:2054`, `console-web/src/components/CaseList.tsx:2404`
2. `CaseList` mixes too many domains in one filter block: mode scope, queue view, saved views, search/owner scope, summary chips, display prefs, advanced filters, persistence notes.
   - Evidence: `console-web/src/components/CaseList.tsx:2054`, `console-web/src/components/CaseList.tsx:2497`, `console-web/src/components/CaseList.tsx:2551`, `console-web/src/components/CaseList.tsx:2582`
3. Saved-view management in `Заявки` exposes too many CTAs inline and competes with the queue itself.
   - Evidence: `console-web/src/components/CaseList.tsx:2065`, `console-web/src/components/CaseList.tsx:2084`, `console-web/src/components/CaseList.tsx:2119`, `console-web/src/components/CaseList.tsx:2267`
4. `Заявки` exposes redundant clearing/toggling semantics: header collapse, filter toggle, clear-all, and chip-level clear coexist without one obvious primary filter model.
   - Evidence: `console-web/src/components/CaseList.tsx:1987`, `console-web/src/components/CaseList.tsx:2433`, `console-web/src/components/CaseList.tsx:2442`, `console-web/src/components/CaseList.tsx:2497`
5. `Заявки` bulk flows compete with queue filters and list content because action forms expand inline below the same rail.
   - Evidence: `console-web/src/components/CaseList.tsx:2710`, `console-web/src/components/CaseList.tsx:2773`, `console-web/src/components/CaseList.tsx:2826`, `console-web/src/components/CaseList.tsx:2931`
6. `Записи` first screen repeats the same anti-pattern: queue mode, lane, filter grid, and saved-view management live in one control card.
   - Evidence: `console-web/src/app/calendar/page.tsx:1634`, `console-web/src/app/calendar/page.tsx:1693`, `console-web/src/app/calendar/page.tsx:1740`
7. `Записи` booking cards leak the full booking state machine: visit status actions, no-show follow-up actions, and follow-up governance form all stack inside each record.
   - Evidence: `console-web/src/app/calendar/page.tsx:2124`, `console-web/src/app/calendar/page.tsx:2190`, `console-web/src/app/calendar/page.tsx:2208`, `console-web/src/app/calendar/page.tsx:2258`
8. Interaction architecture is still tied to god-components.
   - Evidence: `CaseList` mixes queue-state fetch/persist with render orchestration (`console-web/src/components/CaseList.tsx:749`, `console-web/src/components/CaseList.tsx:1768`); `calendar/page.tsx` does the same (`console-web/src/app/calendar/page.tsx:362`, `console-web/src/app/calendar/page.tsx:767`).
9. Frontend workflow coverage lags behind backend contract coverage.
   - Evidence: backend suites are green (`103 passed`), but `console-web/e2e` has no direct saved-view/share-link/follow-up-governance assertions beyond the older queue/history checks; targeted operator lane is only partially green (`4/5`).
10. The current surfaces are beyond “cosmetic cleanup”; the defect is architectural.
   - Evidence: both files are still multi-thousand-line surface orchestrators and the first-screen snapshot already shows wrapped layers before the operator reaches the primary list/chat object.

Root-cause clusters
- `R1 Surface orchestration leak`: one component owns queue semantics, persistence, saved-view governance, bulk workflows, and render hierarchy.
- `R2 Missing primary/secondary action hierarchy`: management actions and configuration live next to daily queue actions.
- `R3 State-machine leakage`: the UI shows internal policy/dirty/targeting/governance states inline instead of one primary business action.
- `R4 Coverage asymmetry`: backend proof is stronger than operator interaction proof.

What should move off first screen
- `Заявки`
  - Saved-view management, share-link, default/delete/targeting, and composer -> dedicated side sheet.
  - Advanced filters -> filter drawer with one clear-all.
  - Visible-fields and auto-refresh -> compact “View settings” panel.
  - Bulk reassign/route/snooze forms -> action sheet; keep only selection summary inline.
- `Записи`
  - Saved-view management and share-link -> side sheet.
  - Status/follow-up-owner/overdue filters -> filter drawer; keep only search and one primary mode inline.
  - Follow-up governance form -> secondary sheet or expandable panel triggered from a single primary CTA on the booking card.

Functional/test assessment
- Backend logic is not the weak point right now.
- Frontend workflow proof is incomplete for:
  - saved view create/apply/update/delete/default;
  - managed preset targeting/defaults;
  - shareable queue URL restore precedence;
  - calendar follow-up governance edit flow;
  - routing-profile-disabled manual reassignment/bulk flows;
  - layout integrity across medium-width desktop states.
- The targeted Playwright run also proved an immediate layout/assertion gap: `inbox-list` width assertion failed even while the queue content was present.

Execution order to remove the defect
1. `Wave33 Inbox surface decomposition`
   - Extract `QueueHeader`, `FiltersDrawer`, `SavedViewsSheet`, `DisplaySettingsPanel`, `BulkActionSheet` from `CaseList`/`InboxView`.
   - DoD: first screen shows queue mode, queue slice, search, owner scope, refresh; no saved-view management or bulk forms inline.
2. `Wave34 Calendar surface decomposition`
   - Split queue triage from scheduling and governance; add `QueueHeader`, `QueueFiltersDrawer`, `SavedViewsSheet`, `BookingActionSheet`.
   - DoD: booking cards expose one primary next action plus overflow/secondary panel, not the full state machine inline.
3. `Wave35 Operator proof lane`
   - Add Playwright coverage for saved views/presets/share URLs/follow-up governance/routing-profile-disabled assignment and layout assertions for `1280px` + narrower desktop widths.
   - DoD: layout assertions are deterministic and the current `inspect first case` width failure is resolved.

Decision
- Do not continue routing v2 or more operator features before Waves33-35.
- The next correct investment is interaction architecture and operator proof, not another server feature layer.

References
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/test-results/inspect_case-inspect-first-case-chromium/error-context.md`
