# TP-2026-03-15-owner-knowledge-stabilization-reset-a4

## Block identity
- `BLOCK_ID`: `CONSOLE-OWNER-KNOWLEDGE-STABILIZATION-RESET-A4`
- `PARENT_BLOCK_ID`: `CONSOLE-CONSULTANT-VERIFICATION-BRANCH-PUBLISH-FLOW-A3`
- `DEPENDS_ON`: `CONSOLE-CONSULTANT-VERIFICATION-BRANCH-PUBLISH-FLOW-A3`
- `UNLOCKS`: owner-safe consultant verification and knowledge authoring that can scale without timeout-driven false negatives or overloaded owner UX

## Название/цель
Остановить деградацию owner/admin потока `Knowledge -> Проверка консультанта`: убрать request-bound sync из owner publish-path, развести owner/admin UX по задачам, и зафиксировать долгосрочный курс так, чтобы дальнейшие правки не усугубляли таймауты, баги и перегруженность интерфейсов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-verification-branch-publish-flow-a3.md`

## Git / worktree
- `Branch`: `feat/2026-03-15-owner-knowledge-stabilization-reset-a4`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase; merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- Knowledge publish is still request-bound and calls heavy sync directly from `publish_knowledge()` in `truffles-api/app/routers/console.py:19424`.
- The current sync path fans out beyond the current branch: `sync_published_branch_docs(..., backfill_other_branches=True)` in `truffles-api/app/routers/console.py:19522`, and `backfill_client_published_branches()` iterates all sibling branches in `truffles-api/app/services/knowledge_registry_service.py:445`.
- The heavy sync path performs multiple blocking network calls in-process with bounded timeouts (`15s`, `60s`, `30s`, `30s`) in `truffles-api/app/services/knowledge_registry_service.py:542`, `:561`, `:583`, `:598`, which explains the repeated owner-visible `timed out` state.
- `console-web/src/app/knowledge/page.tsx` is 3108 LOC and `truffles-api/app/routers/console.py` is 27995 LOC, confirming that both UX and routing are still overloaded enough that each new owner-facing change increases blast radius.
- `console-web/src/app/business/consultant-verification/page.tsx` is now 305 LOC and already mixes scope/status/orchestration concerns with owner trust UX, so leaving it as a page-local control center will continue to produce drift and friction.
- User-reported symptom is now factual: owner sees repeated `Версия опубликована, но синхронизация завершилась с ошибкой: timed out`, increased screen density, and frustration in normal work.

## One web search (mandatory before implementation)
- **Query (exact):** `site:learn.microsoft.com async request-reply pattern background job status retry`
- **Date/time (local):** `2026-03-15T01:15:00+05:00`
- **Sources opened (from this query):**
  - `https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply`
- **Ready solutions found:** long-running user-triggered work should acknowledge quickly, move execution to background processing, expose explicit operation status, and keep retries/status checks separate from the original mutate request.
- **Decision:** `integrate` — move Knowledge sync out of the owner publish request into an explicit async job/status contract, keep owner UX on a small set of truthful states, and stop using publish as the retry mechanism for sync failures.
- **Rejected options:** raising global HTTP timeouts; keeping heavy sync + cross-branch backfill inside owner publish; continuing to surface raw timeout strings as primary owner feedback; adding more owner-page controls on top of already overloaded screens.
- **Source quality:** primary/high-signal source = Microsoft Architecture Center reference pattern.

## Root cause (mandatory)
- **Symptom:** owner-facing Knowledge and consultant-verification flows produce repeated timeout errors, overloaded screens, and rising frustration instead of predictable proof and remediation.
- **Minimal reproduction:**
  1. Publish a branch knowledge draft where Qdrant/index sync is non-trivial.
  2. Observe `publish_knowledge()` commit the version and then block on request-bound sync/backfill.
  3. When sync exceeds timeout budget, owner sees `published + sync_failed` repeatedly and the branch enters `knowledge_safe_mode`.
  4. Open `Knowledge` / `Проверка консультанта` and observe growing owner-facing state density and cross-linked controls.
- **Evidence:** code refs above, user report, and existing runtime audit evidence for `version_id=033ba3b8-a19a-4887-8587-aa761243f29c` (`published` then `knowledge_publish_failed timed out`).
- **Five Whys (or equivalent):**
  1. Why do owners keep seeing timeout-related sync failures? Because sync still runs inside the publish request.
  2. Why does it exceed timeout budgets so often? Because publish also triggers cross-branch backfill and multiple blocking network operations.
  3. Why is the owner experience getting more frustrating? Because the UI compensates with more state and controls instead of reducing the work surface.
  4. Why does every fix feel like more bugs? Because overloaded routes/pages make local fixes bleed into unrelated owner behavior.
  5. Why is this strategic debt now blocking product trust? Because the product is mixing execution orchestration, diagnostics, and owner proof inside the same surfaces.
- **Root cause statement:** the current implementation still treats heavy sync orchestration and owner trust UX as one coupled transaction, so backend timeout pressure leaks directly into owner-facing screens while overloaded page/router surfaces amplify every change.
- **Fix mechanism:** perform a stabilization reset in three layers: move sync to a background job contract, collapse owner UX to a smaller truth-first state model, and separate owner/admin surfaces so diagnostics do not overload the owner workflow.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `knowledge_versions` state, `knowledge_safe_mode`, current publish/draft/verification contracts, and the existing durable outbox worker/event pattern instead of inventing a second background job subsystem.
- **External reuse:** async request-reply / background status pattern from Microsoft Architecture Center.
- **Why not build from scratch:** the product contract is already correct (`publish draft`, `verify`, `retry`, `safe mode`); the problem is execution placement and surface overload, not absence of primitives.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted backend suite + `1` targeted frontend suite + `1` targeted Playwright proof for the first implementation slice.
- **Fail-fast / scenario lock:** stop after the first repeated failure without a new RCA delta.
- **Stop condition:** first implementation slice proves that publish request no longer executes heavy sync inline and owner UI is simplified enough to remove the current timeout-first experience.
- **Escalation path:** Brain / Top Architect if a second rerun is needed without new evidence.

## Invariant
- Do not weaken knowledge validation, compare, or structured-data loss guards.
- Do not allow owner publish/retry to create duplicate published versions.
- Do not hide safe-mode or failed sync from admin diagnostics.
- Do not add more owner-facing control density to `Knowledge` or `Проверка консультанта` while stabilizing them.

## Scope
- Canonize the stabilization/reset program in docs/state/backlog.
- First implementation slice:
  - remove heavy sync from owner publish request path,
  - replace it with explicit async sync job/status + retry contract,
  - reduce owner-facing primary messages to bounded states,
  - trim the current owner UI density on `Knowledge` / `Проверка консультанта` where required by this slice.
- Deterministic tests for job/status contract and owner-facing state rendering.

## Out of scope
- Full redesign of every Console owner page.
- Rewriting the consultant verification runtime or findings/compare system.
- Solving all maintainability debt in `console.py` and `knowledge/page.tsx` in one block.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/models/branch.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
 - `truffles-api/tests/test_knowledge_registry_sync_backfill.py`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-owner-knowledge-stabilization-reset-a4.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Publish the stabilization/reset TP and start a dedicated worktree session.
2. Implement async knowledge sync orchestration for the selected branch only via the durable outbox worker; remove cross-branch backfill from owner publish request path.
3. Introduce explicit operation/status contract for publish/sync/retry that no longer surfaces raw timeout as the primary owner message.
4. Reduce owner primary UX on `Knowledge` and `Проверка консультанта` to bounded state blocks; keep advanced diagnostics out of the primary owner path.
5. Revalidate deterministic backend/frontend/Playwright lanes and sync canon docs/state.

## DoD
- Owner publish request returns quickly without executing the heavy sync fan-out inline.
- Cross-branch backfill is no longer part of the owner publish click path.
- Retry for failed sync does not create a new published knowledge version.
- Owner-facing primary status is reduced to bounded business states instead of raw `timed out` messaging.
- `Проверка консультанта` no longer encourages verification on a branch that is still waiting on or failing sync.
- Targeted backend/frontend/E2E checks are green and the canon documents the new contract plus remaining debt.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/truffles-api && pytest -q tests/test_console_owner_business.py tests/test_console_consultant_verification_api.py -k 'knowledge or consultant_verification or sync'`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/truffles-api && ruff check app/routers/console.py app/schemas/console.py app/services/knowledge_registry_service.py app/services/console_consultant_verification.py tests/test_console_owner_business.py tests/test_console_consultant_verification_api.py`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx --file src/lib/api-client.ts --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep 'knowledge sync|consultant verification readiness'`
- `cd /home/zhan/worktrees/2026-03-15-owner-knowledge-stabilization-reset-a4 && SESSION_AGENT=a4 scripts/session_check.sh`

## Evidence
- Code diff proving publish no longer performs heavy sync inline.
- Backend tests proving branch-only sync job/status/retry semantics.
- Frontend/Playwright proof of simplified owner states.
- Updated `STATE.md` entry with commands/results before merge.

## Release safety (mandatory for non-doc changes)
- Strategy: ship as fail-closed state-machine change; if the async path is unavailable, publish must stay in `pending_sync` instead of pretending ready.
- Go/no-go signals:
  - publish request latency no longer depends on sync completion,
  - retry-sync never creates a new published version,
  - owner screens show bounded state messages instead of raw timeout-first copy.
- Rollback: revert the stabilization PR; existing published versions remain durable.
- Post-release monitoring window: first 72h after merge; watch publish latency, `knowledge_safe_mode`, pending sync backlog, and repeated failed sync jobs.

## Rollback
- Revert the feature branch merge.
- Keep durable version rows; only revert orchestration/UI behavior.

## No-go
- No more owner-facing patches that add controls/messages without reducing current complexity.
- No raising network timeouts as the primary fix.
- No cross-branch backfill in owner publish path.
- No raw infrastructure error strings as the primary owner message.

## Risks/Blockers
- Async job introduction may require bounded schema/service additions.
- Existing frontend assumptions about synchronous publish may need careful state transition updates.
- There may already be production branches stuck in `knowledge_safe_mode`; remediation needs a truthful migration path.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `console.py` and `knowledge/page.tsx` remain oversized even after the first stabilization slice.
- Consultant verification owner/admin surfaces still share too much route-level logic.

### Why not in this block
- The immediate blocker is request-bound sync and owner frustration; full decomposition is a later structural block.

### Risk if deferred
- Future fixes will remain slower and riskier until these files are decomposed.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-console-owner-scope-gate-unification-a4`
- `TP-2026-03-15-console-knowledge-surface-decomposition-a4`

### Expiry/trigger to stop deferral
- If one more owner-facing defect requires touching the same overloaded surfaces, decomposition becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- After the first stabilization slice lands, split owner/admin UX so owner sees only readiness + proof + remediation, while admin keeps diagnostics/findings/compare tooling.

### First deterministic check command
- `cd /home/zhan/truffles-main/console-web && npm run lint -- --file src/app/knowledge/page.tsx --file src/app/business/consultant-verification/page.tsx`

### Blocked-by conditions
- Async knowledge sync/status contract must land first.
- Need post-merge monitoring evidence showing whether timeout family actually drops.

### Owner role for closure
- Brain / Top Architect
