# TP-2026-03-15-console-owner-scope-gate-unification-a5

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-SCOPE-GATE-UNIFICATION-A5`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-SYNC-STATE-UNIFICATION-A4`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-SYNC-STATE-UNIFICATION-A4`
- `UNLOCKS`: one shared owner branch/client scope-repair contract for `Knowledge` and `Проверка консультанта`, reducing further UX drift and duplicated invalidation logic.

## Название/цель
Убрать дублирование owner scope-gate между `Knowledge` и `Проверка консультанта`: вынести общий branch-context gate/apply logic в переиспользуемый компонент/хук, синхронизировать copy и invalidation semantics, и зафиксировать базу для дальнейшего упрощения owner/admin surfaces.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-console-knowledge-sync-state-unification-a4.md`

## Git / worktree
- `Branch`: `feat/2026-03-15-console-owner-scope-gate-unification-a5`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-console-owner-scope-gate-unification-a5`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Knowledge` has page-local branch/context repair logic in `console-web/src/app/knowledge/page.tsx:1539-1686`, including local storage write, `console-me` invalidation/refetch, and success-copy.
- `Проверка консультанта` repeats a second page-local implementation in `console-web/src/app/business/consultant-verification/page.tsx:126-139` and its branch-gate rendering at `:264-305`.
- Both pages now solve the same owner problem, but with separate components, state names (`branchId` vs `branchDraftId`), action texts, and invalidation sets.
- `UX-51` remains open in `docs/CONSOLE_AUDIT/UX_BACKLOG.md` specifically because future pages can drift again on branch/client repair UX and cache invalidation semantics.
- The latest sync-state fix (`PR #969`) repaired one contradiction, but left the duplicate scope-gate implementations intact; without unification, the next scope-related fix will likely fork behavior again.

## One web search (mandatory before implementation)
- **Query (exact):** `site:react.dev latest reusing logic between components custom hooks`
- **Date/time (local):** `2026-03-15T11:20:00+05:00`
- **Sources opened (from this query):**
  - `https://react.dev/learn/reusing-logic-with-custom-hooks`
- **Ready solutions found:** React recommends extracting duplicated component logic into specific custom Hooks/components so callers stay declarative and the shared logic stays pure and centrally maintained.
- **Decision:** `integrate` — extract one shared owner scope-gate hook/component for branch context repair, rather than keeping two pages with near-identical local state and invalidation code.
- **Rejected options:** copy/paste a third page-level variant, hiding differences with copy only, or centralizing only the JSX while leaving invalidation logic duplicated.
- **Source quality:** primary/high-signal source = official React docs.

## Root cause (mandatory)
- **Symptom:** owner-facing pages keep needing separate fixes for the same branch/client context problem, and each fix increases the chance of future drift in text, invalidation, and repair behavior.
- **Minimal reproduction:**
  1. Open `Knowledge` with missing/invalid selected branch and observe one repair flow.
  2. Open `Проверка консультанта` with the same context issue and observe a similar but separate repair flow.
  3. Change invalidation/copy/state on one page.
  4. The other page remains semantically close but behaviorally different.
- **Evidence:** code refs above plus open backlog item `UX-51`.
- **Five Whys (or equivalent):**
  1. Why do scope-gate fixes keep needing to be made twice? Because the logic is duplicated on two pages.
  2. Why is the logic duplicated? Because it was added as page-local orchestration during separate stabilization blocks.
  3. Why does that create product drift? Because each page independently controls state names, copy, and query invalidation.
  4. Why is that risky now? Because scope selection is a prerequisite for owner trust flows and any inconsistency breaks confidence immediately.
  5. Why wasn't it extracted earlier? Because previous blocks prioritized fixing dead-ends and sync contradictions before structural reuse.
- **Root cause statement:** owner branch-context repair remains implemented as two page-local orchestration flows, so fixes to scope-gate behavior, copy, or query invalidation can diverge again with every subsequent change.
- **Fix mechanism:** extract one shared owner scope-gate hook/component that owns branch selection/apply/invalidation semantics, then adopt it in both `Knowledge` and `Проверка консультанта`.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `writeConsoleContextScopeToStorage`, `console-me` query, branch option data from `authApi.getMe()`, and current invalidation semantics from both pages.
- **External reuse:** React custom-hook guidance for reusing pure component logic.
- **Why not build from scratch:** the current pages already have the correct primitives; the problem is duplication, not missing capability.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted frontend lint/build + `1` targeted Playwright suite for the first extraction slice.
- **Fail-fast / scenario lock:** stop after the first drift/regression without a new RCA delta.
- **Stop condition:** both owner pages use the same scope-gate logic and deterministic UI proof stays green.
- **Escalation path:** Brain / Top Architect if a second rerun is needed without new evidence.

## Invariant
- Do not change the underlying Console context storage contract.
- Do not weaken the sync-state fail-closed behavior.
- Do not add new owner/admin diagnostics in this block.
- Do not split scope-gate behavior by page once the shared primitive exists.

## Scope
- Extract a shared owner scope-gate primitive (component + focused hook/helper if needed).
- Migrate `Knowledge` and `Проверка консультанта` to that shared primitive.
- Keep branch apply invalidation semantics identical across both pages.
- Align owner-facing copy where the intent is the same.
- Add deterministic regression proof for both pages using the shared gate.
- Sync canon docs/state/backlog.

## Out of scope
- Full IA decomposition of `Knowledge` and `Проверка консультанта`.
- New scope-gate support for unrelated pages.
- Backend contract changes.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/components/*` (new shared owner scope-gate primitive)
- `console-web/src/lib/*` (shared helper/hook if needed)
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-console-owner-scope-gate-unification-a5.md`

## Plan
1. Start a clean dedicated session/worktree from `origin/main`.
2. Extract one shared owner scope-gate primitive that owns branch selection draft state, apply action, and context invalidation/refetch semantics.
3. Replace page-local gate implementations in `Knowledge` and `Проверка консультанта` with the shared primitive.
4. Add/extend deterministic Playwright coverage so both pages prove the same gate behavior.
5. Sync canon docs/state/backlog and prepare PR.

## DoD
- `Knowledge` and `Проверка консультанта` no longer keep separate page-local branch apply flows.
- Both pages reuse the same apply/invalidation semantics and owner-facing gate structure.
- Targeted frontend checks and Playwright proof are green.
- Canon docs/state reflect `UX-51` progress and remaining `UX-52` debt.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-console-owner-scope-gate-unification-a5/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx --file src/components/ConsoleOwnerScopeGate.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-scope-gate-unification-a5/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-scope-gate-unification-a5/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'consultant verification branch gate|knowledge scope gate'`
- `cd /home/zhan/worktrees/2026-03-15-console-owner-scope-gate-unification-a5 && SESSION_AGENT=a5 scripts/session_check.sh`

## Evidence
- Code diff showing both pages consume one shared gate primitive.
- Deterministic frontend proof for both pages.
- Updated `STATE.md` entry before merge.

## Release safety (mandatory for non-doc changes)
- Strategy: frontend-only structural reuse; keep backend contracts untouched.
- Go/no-go signals:
  - both pages still recover missing branch context,
  - no regression in sync-blocked consultant verification,
  - no regression in `Knowledge` branch apply flow.
- Rollback: revert the PR; page-local behavior from current main remains known-good.
- Post-release monitoring window: first 48h after merge; watch owner reports about branch selection dead-ends or wrong scope after applying context.

## Rollback
- Revert the feature branch merge.
- Restore current page-local scope-gate implementations if needed.

## No-go
- No backend changes.
- No adding a third scope-gate variant.
- No partial extraction that still leaves duplicated invalidation logic on both pages.

## Risks/Blockers
- `Knowledge` page is large; extraction must stay narrow to avoid accidental unrelated refactors.
- Existing mocked Playwright helpers may need slight adaptation to work with the shared component.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `Knowledge` and `Проверка консультанта` remain overloaded owner/admin surfaces even after scope-gate extraction.
- Sync-state presenter is still page-adjacent rather than part of a larger owner surface decomposition.

### Why not in this block
- This block is limited to removing duplicate scope-gate behavior; full surface decomposition is the next structural step.

### Risk if deferred
- Owner screens remain denser than necessary even if scope drift is reduced.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-surface-decomposition-a5`

### Expiry/trigger to stop deferral
- If another owner-facing fix touches both pages after this extraction, surface decomposition becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Separate owner vs admin responsibility on `Knowledge` / `Проверка консультанта` so primary owner paths are limited to readiness, proof, and remediation.

### First deterministic check command
- `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx`

### Blocked-by conditions
- Shared scope-gate extraction must land first.
- Need confirmation that no new branch-context contradictions remain after extraction.

### Owner role for closure
- Brain / Top Architect
