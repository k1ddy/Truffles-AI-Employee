# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE33-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE34-A1`
- `UNLOCKS`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE31-RECHECK-A1`

## Название/цель
Закрыть operator proof после Wave33/Wave34: добавить детерминированное workflow/layout доказательство для rebuilt `Заявки`/`Записи`, чтобы saved views, team presets, share URLs, follow-up governance, routing-profile restrictions и medium-width desktop layout были покрыты реальными operator flows, а не только backend-контрактами.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: two separate stacked PRs already opened for Wave33/Wave34; Wave35 stays on the same worktree as the next bounded proof diff
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Wave33 already removed first-screen Inbox clutter and moved saved views/filters/view/bulk flows into a bounded secondary panel: `console-web/src/components/CaseList.tsx`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`.
- Wave34 already removed first-screen Calendar clutter and moved filters/saved views/scheduling/booking governance into bounded secondary surfaces: `console-web/src/app/calendar/page.tsx`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`.
- The remaining open risk is explicitly `UX-36`: backend queue-state, saved-view, follow-up, and routing-profile contracts are green, but operator workflow/layout proof is incomplete: `STATE.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`.
- The audit explicitly requires Playwright coverage for saved views/presets/share URLs/follow-up governance/routing-profile-disabled assignment and deterministic medium-width layout assertions for `1280px` plus narrower desktop widths: `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:playwright.dev Playwright responsive layout assertions viewport emulation`
- **Date/time (local):** `2026-03-08T12:35:01+05:00`
- **Sources opened:**
  - `https://playwright.dev/docs/test-assertions`
  - `https://playwright.dev/docs/emulation`
- **Ready solutions found:** official Playwright guidance already covers deterministic locator assertions and explicit viewport/device emulation, so Wave35 can stay inside the existing `inspect_case.spec.ts` acceptance lane without inventing a new harness.
- **Decision (`reuse/integrate/build`):** `integrate` — extend the current Playwright mock lane with explicit viewport checks, secondary-surface workflow assertions, and contract-level route mocks for saved views/follow-up governance.
- **Rejected options:** screenshot-only proof without DOM assertions; ad-hoc manual browser validation; a second acceptance file that duplicates the existing `inspect_case` operator lane.
- **Source quality:** high-signal primary sources = official Playwright documentation.

## Root cause (mandatory)
- **Symptom:** Wave33/Wave34 made the UI hierarchy cleaner, but the deterministic operator lane still does not prove that the moved capabilities remain usable and layout-safe.
- **Minimal reproduction:** open the rebuilt Inbox/Calendar surfaces and note that saved views/team presets/share URLs/follow-up governance/routing restrictions can still regress without any backend failure because the existing Playwright lane only covers the older queue/history/business-action path.
- **Evidence:** `STATE.md:12`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`, `console-web/e2e/inspect_case.spec.ts`.
- **Five Whys:**
  1. Why is the main risk still open after Wave33/Wave34? Because the surfaces changed, but the deterministic workflow proof did not expand to all moved controls.
  2. Why can backend tests not close that risk? Because backend suites cannot prove that the operator can still reach and use secondary surfaces correctly.
  3. Why are saved views/share/governance especially risky? Because they were intentionally moved off the first screen and can silently drift behind hidden entrypoints.
  4. Why do routing-profile restrictions need UI proof? Because disabled/unavailable assignment states are product-facing behavior, not only API facts.
  5. Why does this need a dedicated block? Because acceptance now depends on workflow coverage and medium-width layout integrity, not on additional product features.
- **Root cause statement:** the remaining defect is coverage asymmetry: Waves24-30 proved backend truth and Waves33-34 proved surface decomposition, but the operator acceptance lane still under-proves the new secondary-surface workflows and medium-width layout contract.
- **Fix mechanism:** extend the existing deterministic Playwright lane with route-backed saved-view/current-state mocks, explicit share URL restore checks, follow-up governance mutation proof, routing-restriction UI assertions, and medium-width desktop assertions across Inbox and Calendar.

## Reuse-first plan (mandatory)
- **Reuse:** current `inspect_case.spec.ts` mock harness, existing Inbox/Calendar test ids, queue-state helpers, and current Wave33/Wave34 secondary panels.
- **Integrate:** add missing route mocks and focused tests into the same deterministic acceptance file instead of introducing a second operator-proof suite.
- **Build only if needed:** minimal new `data-testid` hooks or copy-safe selectors only where deterministic proof cannot be expressed with current markup.

## Invariant
- Do not reopen Wave33 or Wave34 surface scope except for minimal deterministic hooks required by acceptance.
- Do not change backend/API contracts for queue state, saved views, follow-up governance, or routing profiles.
- Do not replace workflow proof with screenshot-only assertions.
- Do not weaken existing operator-lane assertions to make the suite pass.
- Do not discuss or implement routing v2 in this block.

## Scope
- Extend deterministic Playwright proof for rebuilt Inbox and Calendar surfaces.
- Add route-backed saved-view/current-state mocks where current operator lane is blind.
- Cover saved views, team presets, share URLs, follow-up governance, routing-profile restrictions, and medium-width desktop layouts.
- Keep any UI diff minimal and acceptance-driven.

## Out of scope
- new Inbox/Calendar features
- backend/model/API changes
- routing v2 / capability-input work
- global Console backlog items outside `UX-34`/`UX-35`/`UX-36`

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/app/calendar/page.tsx`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Proof matrix contract (mandatory)
- `Saved views`:
  - create/apply/update/default flow remains reachable from secondary surfaces
  - selected view summary and dirty/reapply semantics still work
- `Team presets`:
  - owner/admin can create or retarget a team preset without reopening first-screen clutter
  - targeting metadata stays visible and applicable in the saved-view surface
- `Share URLs`:
  - copy-link action yields a queue URL with explicit state
  - opening that URL restores the intended queue state on the rebuilt surface
- `Follow-up governance`:
  - no-show follow-up governance save flow works from the booking action panel and stays absent inline
- `Routing-profile restrictions`:
  - disabled/unavailable assignee states remain visible and blocked in single-case and bulk flows
- `Medium-width layout`:
  - Inbox and Calendar keep primary queue surfaces visible at `1280px` and one narrower desktop width
  - secondary controls remain off first screen until their panel is opened

## Plan (1..N)
1. Create Wave35 TP and switch active session/canon references from Wave34 to Wave35.
2. Extend the deterministic mock harness with queue-state/current, saved-view catalog/detail CRUD, follow-up-governance, clipboard, and routing-restriction state where needed.
3. Add Wave35 tests for saved views/team presets/share URLs/follow-up governance/routing restrictions/medium-width layouts.
4. Rerun targeted checks, sync canon/state, and record Wave35 closure evidence.

## DoD
- Deterministic operator lane proves secondary-surface workflows rather than only backend semantics.
- Saved views/team presets/share URLs are covered by at least one real UI flow on rebuilt surfaces.
- Follow-up governance is proven from the booking action panel and not inline on the queue list.
- Routing-profile restrictions are proven as visible blocked states in assignment UX.
- Medium-width Inbox and Calendar layout assertions are deterministic and green.
- Wave35 canon/session/state references are synced before closeout.

## Checks
- `cd console-web && npm run lint -- --file e2e/inspect_case.spec.ts --file src/components/CaseList.tsx --file src/app/calendar/page.tsx`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|saved views|team preset|share url|follow-up governance|routing profile|medium-width|calendar secondary panels isolate filters and booking actions|booking no-show reopens resolved case and preserves case-booking semantics"`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- targeted Playwright run covering the full Wave35 proof matrix
- any minimal UI test-hook diff required for deterministic proof
- updated canon/session/state entries showing Wave35 as active then closed

## Release safety (mandatory)
- **Rollout:** acceptance-only by default; any UI diff must stay minimal and scoped to deterministic proof support.
- **Go/no-go:** merge only if targeted Wave35 Playwright lane is green and first-screen hierarchy remains unchanged.
- **Rollback:** revert the Wave35 diff; Wave33/Wave34 surface decomposition remains intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave35 targeted checks
- confirm the pre-Wave35 operator lane still passes

## No-go
- Do not add new operator features under the label of “proof”.
- Do not hardcode UI behavior only for test selectors.
- Do not move controls back inline just to simplify assertions.
- Do not close Wave35 without medium-width proof and routing-restriction assertions.

## Риски/блокеры
- The current mock lane does not yet emulate queue-state/current and saved-view CRUD, so test harness gaps may hide real UI regressions until they are closed.
- Clipboard/share URL assertions can become flaky if they rely on browser defaults instead of an explicit clipboard stub.
- If routing-restriction mocks are too weak, the proof could miss disabled/unavailable states and falsely close `UX-36`.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `CaseList.tsx` and `calendar/page.tsx` are still large orchestrators even after Wave35 proof.
- `Why not in this block`: this block is acceptance closeout for rebuilt surfaces, not another decomposition wave.
- `Risk if deferred`: maintainability debt remains, but operator UX closure can still be judged separately from future component extraction.
- `Linked follow-up Task Package(s)`: `Wave31` re-check only after Wave35 closure; any later maintainability work must be opened as a separate bounded block.
- `Expiry/trigger to stop deferral`: any new Inbox/Calendar feature or routing-v2 discussion before Wave35 proof is closed is a stop-the-line violation.

## Next-block contract (mandatory)
- `Next block objective`: re-check whether Wave31/routing v2 is actually needed after the full operator-proof lane is green.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave35|Wave31|UX-34|UX-35|UX-36" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `Blocked-by conditions`: any failing Wave35 proof item, any re-inline regression on first screens, or any proposal to start routing v2 without this closure blocks the next block immediately.
- `Owner role for closure`: Brain / Top Architect.
