# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-CLOSEOUT-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-A1
- `UNLOCKS`: none

## Название/цель
Зафиксировать merge-ready verdict по Wave17: действительно ли новая модель фильтров решила конфликт `queue mode vs owner scope vs advanced filters`, и нужен ли отдельный follow-up после `PR #939`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: review current `PR #939`, do not open a new feature PR for this decision block
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `PR #939` is open for Wave17: `https://github.com/k1ddy/Truffles-AI-Employee/pull/939`.
- Filter model is now split into:
  - `queue view`,
  - `owner scope`,
  - `advanced refinements`,
  - `presentation/workspace prefs`.
- Owner-specific queue presets were removed from the primary rail, and the first screen now keeps only `queue mode + search + owner scope`: `console-web/src/components/CaseList.tsx`.
- Local sort reordering was removed; sort is now sent to the server and the queue preserves server order: `console-web/src/components/CaseList.tsx`.
- Deterministic evidence is green locally for the new rail and updated owner-scope contract.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management best practices for managing queues at scale`
- **Date/time (local):** `2026-03-07T08:54:00+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/prioritize-your-queues-by-using-groups/`
- **Ready solutions found:** strong queue systems separate queue/view semantics from secondary filters, reduce first-screen control noise, and keep assignment scope explicit instead of duplicating it in multiple queue modes.
- **Decision (`reuse/integrate/build`):** `reuse` — use the same operator-queue principles and current Wave17 evidence to decide whether a further wave is actually required.
- **Rejected options:** opening another filter wave by default; treating named saved views as mandatory without operator evidence.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** without a closure review, Wave17 can either be merged with hidden gaps or kept open indefinitely because queue/filter UX can always be polished further.
- **Minimal reproduction:** inspect current branch state after Wave17 implementation; the new model is materially cleaner, but without explicit review there is no disciplined answer to whether the original filter-conflict problem is actually closed.
- **Evidence:** `console-web/src/components/CaseList.tsx`, local lint/build/Playwright results, current `PR #939` status.
- **Five Whys:**
  1. Why do we need a review block? Because the user asked for a root-cause fix, not just another UI tweak.
  2. Why not immediately open Wave18? Because that would reintroduce scope growth before proving a remaining blocker exists.
  3. Why must this be business-oriented? Because the problem is operator trust in the queue, not abstract component cleanliness.
  4. Why are residuals allowed? Because optional maturity features like named saved views are not automatically blockers for the current triage workflow.
  5. Why mention follow-up explicitly? Because if a blocker remains, it must become one bounded TP instead of hidden debt.
- **Root cause statement:** Wave17 needs an explicit closeout decision to distinguish between the now-fixed filter-model conflict and optional future queue maturity work.
- **Fix mechanism:** compare implemented Wave17 behavior against the original operator pain and classify any remaining gaps as `blocking` or `accepted residual`.

## Reuse-first plan (mandatory)
- **Reuse:** Wave17 TP, current code/evidence, PR status, screenshot evidence.
- **Integrate:** map the implemented filter model back to the original complaint about filters interfering logically and visually.
- **Build only if needed:** create a follow-up TP only if a business-blocking gap still remains after review.

## Invariant
- Do not reopen the queue/filter scope without a concrete blocker.
- Do not call the problem closed without explicit mapping to the original operator pain.
- Do not introduce a fake future wave just because more queue features are possible.

## Scope
- review Wave17 against the original filter-conflict complaint;
- classify remaining gaps as `blocking` or `accepted residual`;
- decide whether `PR #939` is merge-ready once checks are green;
- decide whether a new follow-up TP is actually needed.

## Out of scope
- New queue features.
- Saved/named views implementation.
- Backend queue semantics redesign.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Review Wave17 against the original queue/filter pain.
2. Classify remaining gaps.
3. Decide merge-go/no-go for `PR #939`.
4. Open a follow-up TP only if the gap is still business-blocking.

## Closure matrix (review output)
| Requirement / pain | Classification | Verdict |
|---|---|---|
| Queue mode and filters fight each other | `closed` | `queue view` no longer rewrites owner scope, and owner scope is no longer duplicated as a queue preset. |
| Too many equal-weight controls on first screen | `closed` | first screen now keeps only queue mode, search, and one owner-scope control. |
| Hidden stale filter state | `closed` | active refinements are explicit as removable chips; persistence migrated to a new normalized model. |
| Sort order is ambiguous between client and server | `closed` | local resorting was removed; sort is sent to the server and server order is preserved. |
| Need more queue maturity later | `accepted residual` | named saved views / managed presets may still be useful later, but they are not blockers for current triage clarity. |

## Merge-ready decision (review output)
- `Decision`: `merge-go`, if `PR #939` required checks are green.
- `Blocking gaps found`: none for the original filter-conflict complaint.
- `Accepted residuals after merge`:
  - no named saved views per manager/team;
  - no role-managed queue presets beyond the current built-in views;
  - no shareable queue URLs / explicit saved filter sets.
- `Need for separate follow-up TP now`: `no`.
- `Trigger for future follow-up`: only if operator validation shows the simplified rail is still insufficient without named/saved views.

## DoD
- Explicit answer whether Wave17 closes the filter-conflict problem.
- Explicit answer whether a Wave18 follow-up is required now.
- Session canon reflects the review decision.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && gh pr view 939 --json statusCheckRollup,mergeStateStatus,url`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- `PR #939` status.
- Existing local Wave17 evidence already recorded in session log.
- Updated closeout-review doc and canon sync.

## Release safety (mandatory)
- **Rollout:** no runtime change in this block; review only.
- **Go/no-go:** merge only if `PR #939` checks are green and no new blocker is found.
- **Rollback:** if review finds a blocker, stop merge and open one bounded follow-up TP instead of merging.

## Rollback
- Revert doc-only review if inconsistent.
- If a blocker is found, reset active block to the new follow-up TP.

## No-go
- Opening a Wave18 by inertia.
- Declaring closure without explicit verdict.
- Treating optional maturity items as blockers without evidence.

## Риски/блокеры
- The only current blocker for merge is PR status/check health, not a newly found product gap.
- There is still a broader program residual outside Wave17: Wave15 live validation remains blocked by missing explicit safe `INSPECT_CASE_LIVE_CASE_ID`, but that is not a Wave17 blocker.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: named saved views and managed queue presets are deferred.
- `Why not in this block`: Wave17 fixed the broken filter model itself; saved views are a later maturity feature, not part of the root-cause fix.
- `Risk if deferred`: some supervisors may later want reusable personal/team views, but current operator clarity is already materially improved.
- `Linked follow-up Task Package(s)`: none now; create only on operator-evidence trigger.
- `Expiry/trigger to stop deferral`: if managers still cannot keep a stable working slice without repeatedly rebuilding the same filter set, open a dedicated saved-views TP.

## Next-block contract (mandatory)
- `Next block objective`: wait for `PR #939` checks, then merge Wave17 if green; do not open a new feature wave by default.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && gh pr view 939 --json statusCheckRollup,mergeStateStatus,url`
- `Blocked-by conditions`: red or stuck required checks in `PR #939`.
- `Owner role for closure`: Brain / Top Architect.
