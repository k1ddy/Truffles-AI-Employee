# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE33-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- `UNLOCKS`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE34-A1`, `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`

## Название/цель
Пересобрать first screen `Заявки` после Wave32 audit: на первом экране оставить только `mode`, `queue slice`, `search`, `owner scope`, `refresh`, а saved views/share/advanced filters/display prefs/bulk forms убрать в secondary surfaces без изменения backend contracts Wave24-30.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: same branch, bounded Inbox-only diff
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Wave32 already proved that the remaining defect in `Заявки` is surface architecture, not missing server truth: `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`.
- `CaseList` still renders saved views/share, advanced filters, display prefs, persistence hints, and bulk forms on the same visible rail as the operator queue: `console-web/src/components/CaseList.tsx:1961`, `console-web/src/components/CaseList.tsx:2054`, `console-web/src/components/CaseList.tsx:2404`, `console-web/src/components/CaseList.tsx:2710`.
- Backend contracts for queue state, saved views, share URLs, follow-up governance, and routing profiles are already green and must stay unchanged in this wave: `103 passed` evidence recorded in `STATE.md` / Wave32 TP.
- Existing e2e selectors already cover the core primary controls (`cases-mode-scopes`, `cases-queue-views`, `cases-filter-search`, `cases-filter-owner-scope`, `cases-refresh`) and will need bounded updates for the moved secondary surfaces: `console-web/e2e/inspect_case.spec.ts`.

## One web search (mandatory before implementation)
- **Query (exact):** `Atlassian Jira Service Management queue best practices filters views reduce clutter official`
- **Date/time (local):** `2026-03-08T10:32:48+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
- **Ready solutions found:** first-screen queue work should stay focused on a small number of high-value working slices; management/configuration views should exist, but as secondary workflow surfaces instead of inline clutter on the live queue.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse current queue-state/saved-view/bulk logic and rebuild only the surface hierarchy around it.
- **Rejected options:** keep adding more inline controls to `CaseList`; solve overload with spacing-only tweaks; introduce a brand-new Inbox route instead of decomposing the existing surface.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** Inbox first screen still feels crowded and action-ambiguous even after Wave24-30 correctness work.
- **Minimal reproduction:** open `Заявки` in compact workspace mode and compare the number of visible control domains before reaching the queue cards: mode, queue slices, saved views/share, search, owner scope, advanced filters, display prefs, persistence hints, and bulk forms all compete in one rail.
- **Evidence:** `console-web/src/components/CaseList.tsx:1961`, `console-web/src/components/CaseList.tsx:2054`, `console-web/src/components/CaseList.tsx:2404`, `console-web/src/components/CaseList.tsx:2710`, `console-web/e2e/inspect_case.spec.ts`, `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`.
- **Five Whys:**
  1. Why is Inbox still noisy? Because multiple workflow domains remain inline on the first visible rail.
  2. Why are they inline? Because Wave24-30 added correct server-owned features without a later surface decomposition step.
  3. Why is that risky now? Because the operator must parse governance/configuration controls before the actual queue.
  4. Why can’t backend correctness solve it? Because the defect is interaction hierarchy, not data correctness.
  5. Why does this need a separate wave? Because moving these controls changes layout, selectors, and operator workflow proof, even if backend stays untouched.
- **Root cause statement:** `CaseList` is still an overgrown operator shell; first-screen queue triage is mixed with secondary configuration and bulk-management surfaces.
- **Fix mechanism:** introduce one bounded secondary control surface for Inbox and demote saved views/share, advanced filters, display prefs, and bulk forms out of the primary first-screen rail.

## Reuse-first plan (mandatory)
- **Reuse:** existing `CaseList` query/filter state, `inbox-case-filters` contract, saved-view/share helpers in `queue-state.ts`, bulk action mutations, and current inbox route/layout.
- **Integrate:** build a secondary control panel/sheet around the existing state handlers instead of changing API contracts.
- **Build only if needed:** minimal new panel state and layout wiring inside Inbox UI.

## Invariant
- Do not change Wave24-30 backend/API contracts.
- Do not reintroduce new first-screen controls beyond `mode`, `queue slice`, `search`, `owner scope`, `refresh`.
- Do not remove saved views/share/bulk capability; move them to secondary surfaces.
- Do not merge Calendar decomposition into this block.
- Do not leave bulk forms inline below the first-screen queue rail.

## Scope
- Inbox only:
  - simplify `CaseList` first screen to the five primary controls;
  - move saved views/share/targeting/composer into a secondary control surface;
  - move advanced filters and view settings into the same secondary control surface;
  - demote bulk forms to a secondary action surface while preserving checkbox selection in the list;
  - update deterministic Playwright coverage for the new entrypoints/selectors.

## Out of scope
- Calendar first-screen decomposition (`Wave34`)
- new queue semantics or backend filters
- routing v2 / new routing inputs
- redesign of case conversation/details surfaces

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/e2e/smoke.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Surface decomposition contract (mandatory)
- `Primary first screen must include only`:
  - `cases-mode-scopes`
  - `cases-queue-views` (only in open mode)
  - `cases-filter-search`
  - `cases-filter-owner-scope`
  - `cases-refresh`
- `Secondary surfaces must own`:
  - saved views + share link + targeting + composer
  - advanced filters + clear-all
  - visible fields + auto-refresh + persistence hint
  - bulk action forms (`reassign`, `route`, `snooze`)
- `Allowed first-screen leftovers`:
  - informational count/status labels
  - passive queue/search/filter summary
  - bulk selection count without inline forms

## Plan (1..N)
1. Create Wave33 TP and switch active session/master canon to the new block.
2. Rebuild `CaseList` first-screen render so only the five primary controls stay inline.
3. Move saved views/share, advanced filters, display prefs, and bulk forms into bounded secondary panel/sheet flows.
4. Update `inspect_case` and smoke coverage to use the new secondary-surface entrypoints.
5. Re-run targeted frontend checks and sync session/state/master docs.

## DoD
- First-screen Inbox queue shows only `mode`, `queue slice`, `search`, `owner scope`, `refresh` as interactive primary controls.
- Saved views/share/targeting/composer are no longer inline on the first screen.
- Bulk forms are no longer inline below the queue rail.
- Playwright deterministic lane is updated and green for the new entrypoints.
- No backend or contract diffs are required for this wave.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file e2e/inspect_case.spec.ts --file e2e/smoke.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3101 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|manager history modes hide queue views and keep owner scope role-gated|manage and apply action macro|action feedback hides raw sync reason codes and keeps reopen internal-only|booking no-show reopens resolved case and preserves case-booking semantics"`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- UI diff showing first-screen reduction in `CaseList`
- deterministic Playwright evidence for new secondary-surface entrypoints
- session/state/master doc updates proving Wave33 is the active block

## Release safety (mandatory)
- **Rollout:** frontend-only surface decomposition in existing Inbox route; no backend rollout.
- **Go/no-go:** merge only if first-screen controls are reduced without regressing current operator flows and targeted Playwright stays green.
- **Rollback:** revert Wave33 diff; current Wave24-30 contracts remain intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave33 frontend checks
- confirm Inbox first screen returns to the previous inline layout

## No-go
- Do not leave saved views/share inline “for convenience”.
- Do not move Calendar scope into this block.
- Do not solve the problem with CSS-only spacing while keeping the same inline domains.
- Do not weaken Playwright assertions instead of updating them to the new secondary surfaces.

## Риски/блокеры
- If the secondary panel entrypoint is too noisy, the first-screen simplification will be cosmetic only.
- If selectors drift without deterministic updates, Wave35 proof will start from a broken baseline.
- If bulk actions lose discoverability entirely, the operator loop will regress despite cleaner layout.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: Calendar surface density and full operator workflow/layout proof remain open after Wave33.
- `Why not in this block`: this wave is intentionally Inbox-only to keep the decomposition bounded and reviewable.
- `Risk if deferred`: Calendar will still leak too many controls and workflow/layout regressions will remain under-proven.
- `Linked follow-up Task Package(s)`: `Wave34` (Calendar surface decomposition), `Wave35` (operator workflow/layout proof).
- `Expiry/trigger to stop deferral`: any further Inbox/Calendar feature accretion without Wave34/Wave35 follow-up is a stop-the-line violation.

## Next-block contract (mandatory)
- `Next block objective`: execute Wave34 Calendar surface decomposition with the same primary/secondary surface discipline.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave33|Wave34|Wave35|UX-34|UX-35|UX-36" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: any re-expansion of Inbox first-screen controls, or any attempt to skip operator-proof updates after layout changes, blocks the block immediately.
- `Owner role for closure`: Brain / Top Architect.
