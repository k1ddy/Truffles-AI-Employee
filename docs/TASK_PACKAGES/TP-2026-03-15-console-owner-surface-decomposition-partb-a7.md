# TP-2026-03-15-console-owner-surface-decomposition-partb-a7

## Title / Goal
Сделать второй срез `UX-52`: вынести оставшуюся page-level orchestration из owner/admin экранов `Knowledge` и `Проверка консультанта` в smaller owner/admin-specific components, чтобы следующий owner-fix не требовал снова править god-files.

## Canon refs
- `AGENTS.md`
- `STATE.md` NOW: owner surface decomposition slice A6 landed via `PR #971`, но page-level extraction еще оставался открытым.
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` → `UX-52`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-surface-decomposition-a6.md`
- CA_ID: `UX-52`

## Git / worktree
- `Branch`: `feat/2026-03-15-console-owner-surface-decomposition-partb-a7`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-partb-a7`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `console-web/src/app/knowledge/page.tsx` is `3160` LOC and still contains the bulk of step-panel JSX for draft/validate/preview/publish/history/rollback.
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx` is `1027` LOC and still contains all three visible lanes (`setup`, `transcript`, `review/team tools`) inside one file.
- `UX-52` is still `In Progress` in `docs/CONSOLE_AUDIT/UX_BACKLOG.md`: A6 hid support tools, but the page-level orchestration remained concentrated in two oversized files.

## One web search (mandatory before implementation)
- **Query (exact):** `site:react.dev sharing state between components`
- **Date/time (local):** `2026-03-15T11:48:00+05:00`
- **Sources opened (from this query):**
  - `https://react.dev/learn/sharing-state-between-components`
- **Ready solutions found:** Keep shared mutable state in the nearest common owner and extract child components as controlled/presentational units through props instead of widening state ownership prematurely.
- **Decision:** `integrate` — keep query/mutation state in the current page/workspace owners, but extract dense owner/admin sections into controlled child components with explicit prop contracts.
- **Rejected options:** full global-state rewrite; immediate route split into `/knowledge/admin` and `/verification/admin`; keep all JSX inline and try to fix only with copy/disclosures.
- **Source quality:** primary/high-signal source = official React documentation.

## Root cause (mandatory)
- **Symptom:** `Knowledge` and `ConsultantVerificationWorkspace` remain oversized and still mix orchestration, rendering, and role-specific sections.
- **Minimal reproduction:**
  1. Run `wc -l console-web/src/app/knowledge/page.tsx console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`.
  2. Inspect the return blocks and hook density with `rg -n "useMutation|useQuery|return \(" ...`.
- **Evidence:** `knowledge/page.tsx` = `3160` lines, `ConsultantVerificationWorkspace.tsx` = `1027` lines; both files still hold large JSX blocks plus local state/mutation orchestration; `UX-52` remains open after A6.
- **Five Whys (or equivalent):**
  1. Why do owner-facing fixes keep producing friction? Because the pages are still too dense.
  2. Why are the pages dense? Because orchestration and multiple visual lanes still live in single files.
  3. Why does that matter? Because each small UX fix touches many unrelated concerns and increases regression risk.
  4. Why wasn’t it fixed in A6? Because A6 intentionally only hid secondary tools behind disclosures.
  5. Why is it still blocking? Because the next owner/admin adjustments would again require editing the same oversized files.
- **Root cause statement:** The remaining problem is structural: owner/admin surfaces still keep too much view orchestration in two page-level files, so even after disclosure-based simplification the codebase still concentrates change risk in oversized components.
- **Fix mechanism:** Extract the remaining dense owner/admin sections into controlled child components with explicit props while keeping existing query/mutation ownership in the parent. This reduces page-level churn without changing backend contracts.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse the existing A6 disclosure/panel components (`ConsoleSupportDisclosure`, `KnowledgePackInspectorPanel`, `KnowledgeLearningCandidatesPanel`, `ConsultantVerificationTeamToolsPanel`, `ConsultantVerificationScenarioLibrary`, `ConsultantVerificationSessionSummaryPanel`) and only extract the missing page-level lane wrappers around them.
- **External reuse:** reuse the official React composition pattern from the single web search; no new external package or state library is introduced.

## Invariant
- No backend/API behavior changes.
- `Knowledge` publish/validate/sync semantics remain unchanged.
- `Проверка консультанта` session/finding/compare behavior remains unchanged.
- Owner path must stay simpler, not denser.

## Scope
- Extract the remaining page-level owner/admin JSX blocks from `console-web/src/app/knowledge/page.tsx` and `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`.
- Create smaller, role-aware components with explicit prop contracts.
- Update docs/state/backlog for `UX-52` progress.
- Add targeted Playwright proof for the extracted surfaces.

## Out of scope
- Backend changes.
- New features, new API endpoints, or RBAC changes.
- Route split into separate owner/admin pages.
- Async sync/runtime changes.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/knowledge/_components/*`
- `console-web/src/app/business/consultant-verification/_components/*`
- `console-web/e2e/owner-admin-business.spec.ts`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-surface-decomposition-partb-a7.md`
- `docs/SESSIONS/SESSION-2026-03-15-console-owner-surface-decomposition-partb-a7.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Start new session/worktree from updated `main`.
2. Extract dense `Knowledge` flow blocks into controlled components so `page.tsx` becomes orchestration-first.
3. Extract dense `ConsultantVerificationWorkspace` panels into controlled components so owner lane, transcript lane, and explainer/admin lane are isolated.
4. Update docs/backlog/state with residual debt and next-block contract.
5. Run targeted lint/build/Playwright evidence and prepare PR handoff.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` full `npm run build` and `1` targeted Playwright lane after lint is green.
- `Lint` may be rerun as needed for fast feedback.

## DoD
- `knowledge/page.tsx` materially shrinks and no longer contains the bulk of step-panel JSX.
- `ConsultantVerificationWorkspace.tsx` materially shrinks and no longer contains the bulk of all three lane render blocks.
- New child components are owner/admin-specific and reusable enough to keep future changes local.
- Targeted Playwright for the extracted owner surfaces passes.
- Canon/docs/session artifacts are updated.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-partb-a7/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/knowledge/_components/KnowledgePackInspectorPanel.tsx --file src/app/knowledge/_components/KnowledgeStudioFlow.tsx --file src/app/knowledge/_components/KnowledgeRollbackConfirmDialog.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationTranscriptLane.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationReviewLane.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-partb-a7/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-partb-a7/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'knowledge owner flow decomposition|consultant verification decomposed lanes'`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-partb-a7 && SESSION_AGENT=a7 scripts/session_check.sh`

## Evidence
- Updated code refs for extracted components.
- Lint/build/Playwright outputs.
- Updated `STATE.md`, `STRUCTURE.md`, backlog, TP, session log, session index.

## Rollback
- Revert the PR/commit for this block.
- No migrations or data rollback needed.

## No-go
- No backend/API changes.
- No global store rewrite.
- No new owner-facing controls.
- No hidden semantic behavior changes in the extracted components.

## Risks / blockers
- Prop drilling can grow if extraction is too coarse; keep components controlled and grouped by lane.
- Playwright needs stable selectors after extraction.

## Release safety (mandatory for non-doc changes)
- **Strategy:** normal Console web rollout after PR merge; no flag change because behavior is UI-only and local to owner/admin routes.
- **Go/no-go signals:** targeted lint/build green; targeted Playwright lane proves support/team tools remain reachable; owner path still renders current publish/verification interactions.
- **Rollback:** revert the PR/commit for this block and redeploy the previous web bundle.
- **Post-release monitoring window:** `24h` focused on owner/admin complaints around `Knowledge` and `Проверка консультанта` navigation and disclosure reachability.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Query/mutation ownership will still remain in parent containers after the extraction.
- `Knowledge` page will likely stay larger than ideal because it still owns all workspace state.

### Why not in this block
- Moving orchestration state into hooks or route splits is a larger follow-up and would increase regression risk in this pass.

### Risk if deferred
- Future owner/admin changes can still require touching large orchestrators, just less often.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-surface-decomposition-statehooks-a7`

### Expiry/trigger to stop deferral
- If the next owner/admin fix needs to change state transitions in both pages again, state-hook extraction becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Extract shared query/mutation orchestration into page-local hooks once lane components are stable.

### First deterministic check command
- `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`

### Blocked-by conditions
- This component extraction block must land first.
- Targeted Playwright must prove that owner path and disclosed team/support tools are still reachable.

### Owner role for closure
- Brain / Top Architect
