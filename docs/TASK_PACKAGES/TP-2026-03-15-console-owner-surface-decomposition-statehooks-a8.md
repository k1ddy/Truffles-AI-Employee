# TP-2026-03-15-console-owner-surface-decomposition-statehooks-a8

## Title / Goal
Сделать третий и завершающий срез `UX-52`: вынести page-level query/mutation orchestration из `Knowledge` и `ConsultantVerificationWorkspace` в page-local hooks, чтобы route shells перестали быть state god-files.

## Canon refs
- `AGENTS.md`
- `STATE.md` NOW: `UX-52` slice A7 landed and moved dense lane JSX out of the pages, but state ownership still remains in large parent containers.
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` → `UX-52`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-surface-decomposition-partb-a7.md`
- CA_ID: `UX-52`

## Git / worktree
- `Branch`: `feat/2026-03-15-console-owner-surface-decomposition-statehooks-a8`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-statehooks-a8`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `console-web/src/app/knowledge/page.tsx` is still `2530` LOC after A7 and owns all local state, queries, mutations, and derived flags for branch gating, draft workflow, fleet tools, sync actions, and publish flow.
- `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx` is still `630` LOC after A7 and owns all session state, queries, mutations, replay/finding/compare handlers, and derived labels.
- The remaining `UX-52` debt is no longer JSX density first; it is state-orchestration density concentrated in route-level containers.

## One web search (mandatory before implementation)
- **Query (exact):** `site:react.dev reusing logic with custom hooks`
- **Date/time (local):** `2026-03-15T12:33:00+05:00`
- **Sources opened (from this query):**
  - `https://react.dev/learn/reusing-logic-with-custom-hooks`
- **Ready solutions found:** React recommends extracting component-specific reusable/stateful logic into custom hooks while keeping UI composition in the components that render it.
- **Decision:** `integrate` — move `Knowledge` and consultant verification orchestration into page-local custom hooks, but keep route ownership and backend contracts unchanged.
- **Rejected options:** introduce a global store; split the feature into new routes before finishing local maintainability; keep orchestration in components and continue only moving JSX around.
- **Source quality:** primary/high-signal source = official React documentation.

## Root cause (mandatory)
- **Symptom:** even after A7, future owner/admin fixes still need to touch large parent containers because the state, query, and mutation orchestration remains centralized there.
- **Minimal reproduction:**
  1. Run `wc -l console-web/src/app/knowledge/page.tsx console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx`.
  2. Run `rg -n "useMutation|useQuery|useMemo|useCallback|useState"` on both files.
  3. Observe that the lane components are smaller now, but the parent files still own almost every async/data transition.
- **Evidence:** `knowledge/page.tsx` still contains dozens of state/query/mutation declarations and helper callbacks; `ConsultantVerificationWorkspace.tsx` still contains all session/query/mutation handlers; `UX-52` remains `In Progress` after A7.
- **Five Whys (or equivalent):**
  1. Why are future edits still expensive? Because the async/data transitions remain concentrated in the parent containers.
  2. Why were they left there after A7? Because A7 intentionally focused on JSX and lane separation first.
  3. Why is that still a problem? Because every bugfix still has to reason about a large mixed orchestration surface.
  4. Why is that risky? Because small owner-path changes can accidentally affect unrelated mutation/query flows.
  5. Why fix it now? Because the structural split is incomplete until state ownership is also decomposed.
- **Root cause statement:** The remaining maintainability debt is state-orchestration concentration: large owner containers still co-own too many local states, queries, mutations, and derived flags, so change risk remains high even after JSX extraction.
- **Fix mechanism:** Extract page-local custom hooks for `Knowledge` and consultant verification orchestration, returning grouped state/actions/view-model slices while keeping rendering in the existing page/workspace shells.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse the lane/stage components from A7 and keep existing API clients, presentation helpers, and scope-gate primitives; only move orchestration into hooks.
- **External reuse:** reuse the official React custom-hook pattern from the single web search; no new external state library is introduced.

## Invariant
- No backend/API behavior changes.
- No owner-facing workflow change in publish/validate/sync/compare/finding behavior.
- Existing targeted Playwright semantics must remain valid.

## Scope
- Extract page-local orchestration from `console-web/src/app/knowledge/page.tsx` into a dedicated hook/module.
- Extract consultant verification orchestration from `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx` into a dedicated hook/module.
- Keep current lane/stage components and route structure.
- Update docs/state/backlog for `UX-52` closure progress.

## Out of scope
- Backend changes.
- New UX features.
- New global stores or route splits.
- Rewriting existing lane/stage components beyond what is needed to consume the hooks.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/knowledge/_components/*`
- `console-web/src/app/knowledge/_hooks/*`
- `console-web/src/app/business/consultant-verification/_components/*`
- `console-web/src/app/business/consultant-verification/_hooks/*`
- `console-web/e2e/owner-admin-business.spec.ts`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-surface-decomposition-statehooks-a8.md`
- `docs/SESSIONS/SESSION-2026-03-15-console-owner-surface-decomposition-statehooks-a8.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Start new session/worktree from updated `main`.
2. Extract `Knowledge` orchestration into a page-local custom hook and keep `page.tsx` as route shell + access/scope handling.
3. Extract consultant verification orchestration into a page-local custom hook and keep `Workspace.tsx` as composition shell.
4. Update docs/backlog/state with residual debt and next-block contract.
5. Run targeted lint/build/Playwright evidence and prepare PR handoff.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` full `npm run build` and `1` targeted Playwright lane after lint is green.
- `Lint` may be rerun as needed for fast feedback.

## DoD
- `Knowledge` route shell no longer owns the bulk of query/mutation orchestration.
- `ConsultantVerificationWorkspace` no longer owns the bulk of session/query/mutation orchestration.
- New hooks group state/actions clearly enough that the next owner/admin fix can target one hook or one lane component.
- Targeted Playwright for owner paths still passes.
- Canon/docs/session artifacts are updated.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-statehooks-a8/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/knowledge/_hooks/*.ts --file src/app/knowledge/_components/*.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx --file src/app/business/consultant-verification/_hooks/*.ts --file src/app/business/consultant-verification/_components/*.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-statehooks-a8/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-statehooks-a8/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 PLAYWRIGHT_WEB_SERVER=0 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'knowledge owner flow decomposition|consultant verification decomposed lanes'`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-surface-decomposition-statehooks-a8 && SESSION_AGENT=a8 scripts/session_check.sh`

## Evidence
- Updated code refs for new hooks and thinner route shells.
- Lint/build/Playwright outputs.
- Updated `STATE.md`, `STRUCTURE.md`, backlog, TP, session log, session index.

## Rollback
- Revert the PR/commit for this block.
- No migrations or data rollback needed.

## No-go
- No backend/API changes.
- No global store introduction.
- No new owner-facing controls or semantics.
- No hidden mutation side-effects moving between pages.

## Risks / blockers
- Hook extraction can accidentally over-couple unrelated concerns if the returned API is not grouped by lane/stage.
- Existing tests need to remain route-level, not hook-internal only.

## Release safety (mandatory for non-doc changes)
- **Strategy:** normal Console web rollout after PR merge; no flag change because behavior stays UI-local.
- **Go/no-go signals:** targeted lint/build green; targeted Playwright still passes; owner path semantics unchanged on `Knowledge` and consultant verification.
- **Rollback:** revert the PR/commit for this block and redeploy the previous web bundle.
- **Post-release monitoring window:** `24h` focused on owner/admin regressions in `Knowledge` and consultant verification flows.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- The route shells are now thin, but the new page-local hooks (`useKnowledgeStudioState.ts`, `useConsultantVerificationWorkspaceState.ts`) are still large orchestration owners.
- Knowledge fleet/readiness and consultant verification session/findings/compare concerns are isolated from the pages now, but they are not yet split by domain/stage inside the hooks.

### Why not in this block
- This block intentionally stopped once the route shells stopped being state god-files.
- Splitting the new hooks by domain/stage would be another bounded maintainability slice and was not required to prove that owner route shells could become thin without changing behavior.

### Risk if deferred
- Future fixes now avoid page-level blast radius, but they can still require editing large hooks that mix unrelated async/state transitions.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-state-hook-domain-split-a9.md`

### Expiry/trigger to stop deferral
- If a later owner/admin change still has to touch unrelated parts of `useKnowledgeStudioState.ts` or `useConsultantVerificationWorkspaceState.ts` for one bugfix, hook domain-splitting becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Split the new page-local hooks by domain/stage if owner/admin work continues to touch unrelated orchestration concerns in one file.

### First deterministic check command
- `cd /home/zhan/truffles-main && wc -l console-web/src/app/knowledge/_hooks/useKnowledgeStudioState.ts console-web/src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts`

### Blocked-by conditions
- This state-hook extraction block must land first.
- Targeted Playwright must prove the owner path still works after orchestration moves behind hooks.

### Owner role for closure
- Brain / Top Architect
