# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE34-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE33-A1`
- `UNLOCKS`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE35-A1`

## Название/цель
Пересобрать first screen `Записи` после Wave32/Wave33: отделить queue triage от filters, saved views/share, booking governance/actions и scheduling, чтобы оператор видел на первом экране только управление очередью и не разбирал scheduling/governance формы до открытия secondary surfaces.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: same branch, bounded Calendar-first diff
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Wave32 audit already proved that the remaining `Записи` defect is surface density and action hierarchy, not missing backend truth: `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`.
- Wave33 already decomposed `Заявки`; the next owner-approved block is equivalent decomposition for `Записи` before any operator-proof closeout: `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `calendar/page.tsx` still mixes scheduling setup, queue triage, filter grid, saved views/share, and inline booking governance/actions on the first visible screen: `console-web/src/app/calendar/page.tsx:1368`, `console-web/src/app/calendar/page.tsx:1634`, `console-web/src/app/calendar/page.tsx:1740`, `console-web/src/app/calendar/page.tsx:2258`.
- Existing workflow proof already touches calendar from `inspect_case.spec.ts`, so the deterministic lane can be updated without inventing a new acceptance harness: `console-web/e2e/inspect_case.spec.ts:1526`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.microsoft.com Microsoft Bookings calendar manage bookings`
- **Date/time (local):** `2026-03-08T11:27:00+05:00`
- **Sources opened:**
  - `https://support.microsoft.com/en-us/office/set-up-a-booking-calendar-for-a-business-or-department-in-microsoft-teams-d9d4faef-be86-4d2e-acb3-2281236a4a78`
  - `https://support.microsoft.com/en-us/office/customize-your-booking-page-116d7a84-a7a0-4911-a1e9-debb2cca7c43`
- **Ready solutions found:** official Microsoft Bookings guidance separates the operational `Schedule` experience from booking-page customization/scheduling policy management, which supports keeping live queue triage distinct from configuration/governance surfaces.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse the current queue-state/saved-view/follow-up/scheduling logic and rebuild only the surface hierarchy around it.
- **Rejected options:** keep all controls inline and only restyle spacing; fork a separate Calendar route for governance; merge Inbox and Calendar decomposition into one oversized diff.
- **Source quality:** high-signal primary sources = official Microsoft Support documentation.

## Root cause (mandatory)
- **Symptom:** `Записи` still feels crowded and form-first even after queue-state/share/governance correctness work.
- **Minimal reproduction:** open `/calendar` in a manager workflow and compare the first visible screen: specialist/date scheduling controls sit left, while queue mode/lane, filters, saved views/share, and booking cards with inline visit/follow-up/governance actions all compete on the same screen.
- **Evidence:** `console-web/src/app/calendar/page.tsx:1368`, `console-web/src/app/calendar/page.tsx:1634`, `console-web/src/app/calendar/page.tsx:1740`, `console-web/src/app/calendar/page.tsx:2190`, `console-web/src/app/calendar/page.tsx:2258`, `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`.
- **Five Whys:**
  1. Why is Calendar still noisy? Because queue triage, scheduling, saved views, and governance/actions still share one visible surface.
  2. Why do they share one surface? Because Waves24-30 added the right capabilities without a later surface decomposition pass.
  3. Why is that a real operator risk? Because managers must parse setup/configuration before they can triage appointments needing action.
  4. Why can’t backend correctness fix it? Because the defect is interaction hierarchy and visual density, not missing state.
  5. Why does this need a dedicated wave? Because moving these controls changes page layout, card entrypoints, and workflow assertions even when APIs stay stable.
- **Root cause statement:** `calendar/page.tsx` is still an overgrown mixed-purpose screen: scheduling setup, queue triage, and booking governance/actions are inline instead of being separated into primary and secondary operator surfaces.
- **Fix mechanism:** keep only queue triage on the first screen, move filters/saved views/share into a secondary panel, move scheduling into a dedicated secondary surface, and demote inline booking governance/actions into a booking action/detail sheet.

## Reuse-first plan (mandatory)
- **Reuse:** current calendar queue state, saved views/share helpers, booking list queries, follow-up governance mutation, booking status/follow-up mutations, and current `inspect_case` flow.
- **Integrate:** add secondary panel/sheet state and entrypoints inside `calendar/page.tsx` rather than creating new routes or contracts.
- **Build only if needed:** minimal new UI state for panel/sheet open modes and compact card action entrypoints.

## Invariant
- Do not change Wave24-30 backend/API contracts.
- Do not reopen Inbox scope in this block.
- Do not remove saved views/share/governance/scheduling capabilities; move them to secondary surfaces.
- Do not keep per-booking governance forms inline on the card list.
- Do not weaken the existing calendar-linked `inspect_case` proof instead of updating it.

## Scope
- Calendar only:
  - keep first-screen queue triage compact and explicit;
  - move queue filters and saved views/share into secondary surfaces;
  - move scheduling controls and booking creation form into a dedicated secondary surface;
  - move visit-status/no-show/governance controls out of inline card noise into a secondary sheet/panel per booking;
  - update deterministic Playwright coverage for the new entrypoints.

## Out of scope
- Inbox changes
- new booking/router/backend semantics
- Wave35 full operator proof matrix
- new calendar routes or model changes

## Touch-list
- `console-web/src/app/calendar/page.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Surface decomposition contract (mandatory)
- `Primary first screen must include only`:
  - queue mode
  - queue lane
  - queue summary chips
  - one compact entrypoint to secondary panels
  - booking cards as triage rows
- `Secondary surfaces must own`:
  - queue filters (`status`, `follow-up owner`, `overdue`, optional search if needed)
  - saved views/share/targeting/composer
  - scheduling setup + slot selection + booking form
  - per-booking governance/actions (`visit status`, `no-show follow-up`, governance owner/due`)
- `Allowed first-screen leftovers`:
  - passive history/case-context hints
  - passive booking metadata chips on cards
  - open-case link

## Plan (1..N)
1. Create Wave34 TP and switch active canon/session references to the new block.
2. Rebuild `calendar/page.tsx` so the first screen is queue-triage-first instead of form-first.
3. Move filters and saved views/share into a bounded secondary panel.
4. Move scheduling setup/form and per-booking governance/actions into secondary sheets/panels.
5. Update deterministic Playwright workflow proof and rerun targeted checks.

## DoD
- Calendar first screen no longer mixes scheduling setup, saved views/share, and inline governance forms with queue triage.
- Queue triage remains usable without opening any secondary surface.
- Scheduling remains available but is opened explicitly from a secondary surface.
- Per-booking governance/actions are reachable from booking cards without full inline forms on the list.
- Deterministic `inspect_case` calendar-linked lane is updated and green.

## Checks
- `cd console-web && npm run lint -- --file src/app/calendar/page.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3102 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|booking no-show reopens resolved case and preserves case-booking semantics"`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- UI diff showing first-screen Calendar decomposition
- deterministic Playwright evidence for the updated calendar entrypoints
- canon/session/state updates showing Wave34 as the active block

## Release safety (mandatory)
- **Rollout:** frontend-only surface decomposition inside the existing Calendar page.
- **Go/no-go:** merge only if queue triage remains readable and the calendar-linked deterministic workflow lane stays green.
- **Rollback:** revert Wave34 diff; existing queue-state/governance contracts remain intact.

## Rollback
- `git revert REVISION_SHA`
- rerun Wave34 frontend checks
- confirm Calendar returns to the previous inline layout

## No-go
- Do not keep saved views/share inline “temporarily”.
- Do not leave scheduling setup as the dominant left-column first-screen block.
- Do not keep follow-up governance forms expanded on every eligible booking card.
- Do not solve density only with CSS compaction while preserving the same inline domains.

## Риски/блокеры
- If scheduling entrypoints become too hidden, booking creation may regress despite cleaner queue triage.
- If booking actions move but card summaries stay too verbose, vertical density will remain a real defect.
- If calendar assertions are not updated precisely, Wave35 will inherit a false baseline.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: full operator workflow/layout proof and medium-width assertions remain open after Wave34.
- `Why not in this block`: Wave34 is intentionally a bounded surface decomposition; Wave35 is the explicit proof/closeout block.
- `Risk if deferred`: the new surface hierarchy could drift without robust workflow proof across saved views/share/governance/routing restrictions.
- `Linked follow-up Task Package(s)`: `Wave35`.
- `Expiry/trigger to stop deferral`: any additional Inbox/Calendar UX feature work without Wave35 proof is a stop-the-line violation.

## Next-block contract (mandatory)
- `Next block objective`: execute Wave35 operator workflow + layout proof on top of completed Wave33/Wave34 decomposition.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave34|Wave35|UX-35|UX-36" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: any re-expansion of Calendar first-screen controls, or any attempt to skip workflow/layout proof after the layout change, blocks the block immediately.
- `Owner role for closure`: Brain / Top Architect.
