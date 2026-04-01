# TP-2026-03-15-console-knowledge-sync-state-unification-a4

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-SYNC-STATE-UNIFICATION-A4`
- `PARENT_BLOCK_ID`: `CONSOLE-OWNER-KNOWLEDGE-STABILIZATION-RESET-A4`
- `DEPENDS_ON`: `CONSOLE-OWNER-KNOWLEDGE-STABILIZATION-RESET-A4`
- `UNLOCKS`: owner-safe sync UX that stays truthful after `publish/retry-sync/rollback` and no longer shows contradictory `pending + safe_mode + timed out` states.

## Название/цель
Закрыть корневой дефект sync-state drift между `Knowledge`, `Проверка консультанта` и `console-me`: сделать один источник правды для owner-facing branch knowledge state, убрать stale cache противоречия после `retry-sync/publish/rollback`, и зафиксировать дальнейший курс на упрощение owner/admin surface.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-owner-knowledge-stabilization-reset-a4.md`

## Git / worktree
- `Branch`: `feat/2026-03-15-console-knowledge-sync-state-unification-a4`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-console-knowledge-sync-state-unification-a4`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Knowledge` owner UI still reads sync-state from two different sources:
  - `currentQuery.data.sync_status` / `currentQuery.data.sync_error` in `console-web/src/app/knowledge/page.tsx:1100-1104`
  - `selectedBranchContext.knowledge_safe_mode` / `selectedBranchContext.knowledge_safe_mode_reason` in `console-web/src/app/knowledge/page.tsx:2002-2016`
- `retrySyncMutation` refetches only `knowledge-current/history` and consultant-verification readiness, but does not invalidate/refetch `console-me` (`console-web/src/app/knowledge/page.tsx:1398-1408`), so owner UI can render `sync_status=pending` from one query and stale `safe_mode=true`, `timed out` from another.
- Backend already clears safe mode when queueing sync in `_queue_knowledge_version_sync()` (`truffles-api/app/routers/console.py:19343-19352`) and returns `knowledge_safe_mode` in `/knowledge/current` (`truffles-api/app/routers/console.py:19318-19326`), so the contradiction is primarily client-state drift, not the queue contract itself.
- `Business -> Проверка консультанта` still derives gating from route-level fields instead of a single shared presenter/service (`console-web/src/app/business/consultant-verification/page.tsx:123-131`, `:230-257`).
- User-visible symptom is factual and reproducible: after `Начать синхронизацию`, the screen can show `Синхронизация выполняется`, `Safe mode: включен`, and `Техническая причина: timed out` simultaneously.

## One web search (mandatory before implementation)
- **Query (exact):** `site:tanstack.com/query latest invalidations from mutations stale dependent queries`
- **Date/time (local):** `2026-03-15T10:25:00+05:00`
- **Sources opened (from this query):**
  - `https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations`
- **Ready solutions found:** mutation flows must explicitly invalidate every dependent query that can hold stale server-state, especially when multiple UI surfaces consume overlapping server state.
- **Decision:** `integrate` — keep the existing TanStack Query stack, but make sync-state server-owned and invalidate/refetch every dependent query (`console-me`, `knowledge-current`, `knowledge-history`, consultant-verification readiness) after publish/retry/rollback; stop deriving owner-facing safe mode from stale branch context.
- **Rejected options:** adding more local UI flags, keeping mixed `console-me + knowledge/current` derivation, hiding the contradiction with copy only, or increasing polling/timeouts.
- **Source quality:** primary/high-signal source = official TanStack Query docs.

## Root cause (mandatory)
- **Symptom:** owner-facing screens show contradictory states after async sync actions (`pending` plus old `safe_mode/timed out`), which destroys trust and creates new bug reports even when backend queueing worked correctly.
- **Minimal reproduction:**
  1. Start from a branch where the last sync failed and `knowledge_safe_mode=true`.
  2. On `Knowledge`, click `Повторить синхронизацию` / `Начать синхронизацию`.
  3. Backend queues sync and clears safe mode.
  4. Frontend refetches `knowledge/current`, but not `console-me`.
  5. UI renders `sync_status=pending` from one query and stale `safe_mode_reason=timed out` from another.
- **Evidence:** code refs above plus user-reported screen state.
- **Five Whys (or equivalent):**
  1. Why does owner see contradictory sync state? Because UI reads sync state from two server-state sources with different refresh semantics.
  2. Why do those sources diverge? Because mutations invalidate only the `knowledge-*` queries and leave `console-me` stale.
  3. Why is stale `console-me` still used? Because page-level derivation kept using selected branch context instead of a single sync-state presenter.
  4. Why does this recur after each sync-related change? Because owner/admin pages are overloaded and state ownership was never consolidated.
  5. Why is this now a strategic problem? Because async sync made truthful status possible, but the UI contract still behaves like a mixed local cache + branch context surface.
- **Root cause statement:** owner-facing knowledge sync state has split ownership between `console-me` and `knowledge/current`, and mutation invalidation does not keep these sources coherent, so async sync transitions leak stale safe-mode/error state back into the owner UX.
- **Fix mechanism:** consolidate owner-facing sync-state on one server-owned response/presenter, invalidate every dependent query after mutations, and suppress old failure details while sync is pending.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `/knowledge/current` response already carries `sync_status`, `sync_error`, `knowledge_safe_mode`, and `knowledge_safe_mode_reason`; existing TanStack Query invalidation patterns in `applyConsoleContext()` and branch change flows can be reused.
- **External reuse:** TanStack Query invalidation-from-mutation guidance.
- **Why not build from scratch:** the backend already exposes most of the needed truth; the defect is inconsistent client ownership and route-level presentation drift.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted backend suite + `1` targeted frontend lint/build + `1` targeted Playwright run for the first slice.
- **Fail-fast / scenario lock:** stop after the first repeated contradiction without a new RCA delta.
- **Stop condition:** the reproduced `pending + safe_mode + timed out` contradiction is no longer possible in deterministic frontend proof.
- **Escalation path:** Brain / Top Architect if a second rerun is needed without new evidence.

## Invariant
- Do not weaken async sync job semantics or the fail-closed verification gate.
- Do not reintroduce raw timeout strings as the primary owner message.
- Do not add new owner controls or diagnostics in this block.
- Do not create a second sync-state contract when `/knowledge/current` can be reused.

## Scope
- Unify owner-facing sync-state derivation on `Knowledge` and the verification readiness surface.
- Invalidate/refetch all dependent server-state queries after `publish`, `retry-sync`, and `rollback`.
- Remove stale failure-reason rendering while sync is `pending`.
- Add deterministic regression proof for the exact contradiction scenario.
- Update canon docs/state/backlog to reflect the repaired ownership model and remaining surface-decomposition debt.

## Out of scope
- Full redesign of `Knowledge` IA.
- New admin diagnostics surface.
- Reworking the outbox worker or queue transport.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/tests/test_console_owner_business.py`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-console-knowledge-sync-state-unification-a4.md`

## Plan
1. Start a new dedicated session/worktree from clean `origin/main`.
2. Replace mixed sync-state derivation on `Knowledge` with a single presenter based on `knowledge/current`; keep `console-me` only for scope selection, not for safe-mode/status truth.
3. Update publish/retry/rollback mutation success paths to invalidate/refetch every dependent query, including `console-me`.
4. Align consultant verification readiness presentation to the same bounded state source/presenter and suppress old error detail while `pending`.
5. Add deterministic UI proof for `failed -> retry-sync -> pending` and sync canon docs/state.

## DoD
- After `retry-sync`, owner cannot see `sync_status=pending` together with stale `safe_mode=true` / `timed out` from the previous failure.
- `Knowledge` and `Проверка консультанта` use one bounded sync-state presentation model.
- Mutation success paths refetch all dependent queries needed for consistent owner state.
- Deterministic tests cover the reproduced contradiction.
- Canon docs/state record the repaired ownership model and residual decomposition debt.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-console-knowledge-sync-state-unification-a4/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-console-knowledge-sync-state-unification-a4/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-console-knowledge-sync-state-unification-a4/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'knowledge sync contradiction|consultant verification sync state'`
- `cd /home/zhan/worktrees/2026-03-15-console-knowledge-sync-state-unification-a4 && SESSION_AGENT=a4 scripts/session_check.sh`

## Evidence
- Code diff showing a single owner-facing sync-state source.
- Targeted Playwright proof for the stale safe-mode contradiction.
- Updated `STATE.md` entry with exact commands/results before merge.

## Release safety (mandatory for non-doc changes)
- Strategy: bounded owner-state repair only; keep async sync worker semantics unchanged and fail-closed if status cannot be resolved.
- Go/no-go signals:
  - no mixed pending/failed UI state after retry-sync,
  - consultant verification blocks only on current sync-state,
  - no regression in publish/retry/rollback success UX.
- Rollback: revert the PR; async sync queue contract from `a4` remains durable.
- Post-release monitoring window: first 48h after merge; watch for repeated `pending` states with stale safe-mode copy in owner UI and support reports.

## Rollback
- Revert the feature branch merge.
- Preserve the async sync job model from `a4`; only revert the owner-state presentation changes.

## No-go
- No new features in owner/admin surfaces.
- No local flags that mask stale state without fixing query ownership.
- No copy-only workaround that still leaves mixed `console-me` and `knowledge/current` truth.

## Risks/Blockers
- Existing mocked Playwright coverage may need extension to assert both `console-me` and `knowledge/current` paths.
- Additional pages may also consume stale branch context after mutations and could surface follow-up bugs once this slice lands.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `Knowledge` and verification pages remain oversized and still mix owner/admin concerns.
- Sync-state still lives in route-level presenters rather than a shared extracted module.

### Why not in this block
- The immediate blocker is contradictory owner state after async sync actions; full decomposition is a follow-up structural block.

### Risk if deferred
- Future owner-facing fixes can still reintroduce drift or duplicate presentation logic.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-scope-gate-unification-a4`
- `TP-2026-03-15-console-owner-surface-decomposition-a4`

### Expiry/trigger to stop deferral
- If the next owner-facing bug touches the same page-level sync presentation logic, decomposition becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Extract one shared owner scope + sync-state presenter and then split owner/admin surfaces so diagnostics do not live in the primary owner path.

### First deterministic check command
- `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx`

### Blocked-by conditions
- This block must first prove that sync-state is consistent after async mutations.
- Need post-merge canary evidence that the contradiction is gone.

### Owner role for closure
- Brain / Top Architect
