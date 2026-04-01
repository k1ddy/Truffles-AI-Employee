# TP-2026-03-15-consultant-verification-branch-publish-flow-a3

## Block identity
- `BLOCK_ID`: `CONSOLE-CONSULTANT-VERIFICATION-BRANCH-PUBLISH-FLOW-A3`
- `PARENT_BLOCK_ID`: `CONSOLE-CONSULTANT-VERIFICATION-KNOWLEDGE-SAFETY-A921`
- `DEPENDS_ON`: `CONSOLE-CONSULTANT-VERIFICATION-KNOWLEDGE-SAFETY-A921`
- `UNLOCKS`: owner-safe consultant verification rollout and truthful branch-scoped publish UX

## Название/цель
Убрать два owner-facing дефекта, которые подрывают доверие к `Проверка консультанта` и `Knowledge`: тупик `Филиал не выбран` без inline repair-path и ложный `Knowledge publish failed` после уже успешного publish commit. Итог блока — owner может выбрать branch прямо на странице проверки, а publish/sync отображаются как честный двухфазный процесс с retry без повторной публикации.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-14-owner-consultant-verification-knowledge-safety-program-a921.md`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-verification-branch-publish-flow-a3`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3`
- `Base ref`: `origin/main`
- `Merge policy`: one PR after deterministic checks are green; no rebase, merge from `origin/main` only if required
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Проверка консультанта` currently marks the readiness surface as blocked whenever no branch is selected in Console context; the exact owner-facing copy is hardcoded in `truffles-api/app/services/console_consultant_verification.py:592` and `truffles-api/app/services/console_consultant_verification.py:635`.
- `Knowledge` already has an inline branch gate and context apply flow, including branch selector and `Продолжить`, in `console-web/src/app/knowledge/page.tsx:2035`. `Проверка консультанта` does not reuse that flow and only renders passive readiness cards in `console-web/src/app/business/consultant-verification/page.tsx`.
- Publish currently commits the new knowledge version first, then runs sync/indexing, and on any downstream exception raises `KNOWLEDGE_SYNC_FAILED` with the owner-facing text `Knowledge publish failed`; evidence in code: `truffles-api/app/routers/console.py:19525` and `truffles-api/app/routers/console.py:19568`.
- Runtime DB evidence from `2026-03-15` confirms the UX mismatch:
  - `audit_events`: `2026-03-14 19:01:21+00 knowledge_publish_failed version_id=033ba3b8-a19a-4887-8587-aa761243f29c error=timed out`
  - `knowledge_versions`: the same `version_id` is already `published` at `2026-03-14 19:01:15+00`
  - `branches`: branch `b7f75692-951e-421a-aae6-f5db97394799` (`Основной филиал`) is now `knowledge_safe_mode=true` with reason `timed out`
- Inference from the current contract: owner currently gets a false binary message (`publish failed`) for a partial-success state (`published + sync failed`), which encourages unsafe duplicate publish attempts.

## One web search (mandatory before implementation)
- **Query (exact):** `HTTP 202 Accepted asynchronous operation status retry RFC 9110 MDN`
- **Date/time (local):** `2026-03-15T20:14:00+05:00`
- **Sources opened (from this query):**
  - `https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3`
  - `https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/202`
- **Ready solutions found:** official HTTP guidance treats accepted async work as a separate processing phase: the request can be accepted while actual processing completes later and may need a separate status resource or polling surface.
- **Decision:** `integrate` — keep the current knowledge publish contract and consultant verification surface, but split owner semantics into `publish commit` vs `post-publish sync`, return machine-readable sync status, and add explicit retry for sync only. Reuse existing Console context storage/apply flow from `Knowledge` instead of inventing a new selector system.
- **Rejected options:** keeping one synchronous `publish` request with a generic 500; forcing owner to navigate to another tab just to fix branch context; re-publishing a full knowledge version just to retry a timed-out sync.
- **Source quality:** primary/high-signal sources = RFC 9110 and MDN HTTP status reference.

## Root cause (mandatory)
- **Symptom:** owner sees `Филиал не выбран` on `Проверка консультанта` even though the product already knows how to pick/apply a branch elsewhere, and owner sees `Knowledge publish failed` even when the version is already published.
- **Minimal reproduction:**
  1. Open `Business -> Проверка консультанта` without a persisted Console branch context; page renders readiness cards with `Перейти`, but there is no inline branch selection/apply path.
  2. Publish a knowledge draft where version commit succeeds but downstream sync/indexing times out; UI returns generic `Knowledge publish failed`.
- **Evidence:** current code refs above and runtime DB rows for `version_id=033ba3b8-a19a-4887-8587-aa761243f29c`.
- **Five Whys:**
  1. Why does consultant verification stall? Because the backend depends on global branch context, but the page does not provide a repair path.
  2. Why is that repair path missing? Because branch selection UX was implemented in `Knowledge` only and never generalized into a reusable Console scope gate.
  3. Why does publish look like a total failure? Because publish commit and post-publish sync are collapsed into one request/result.
  4. Why does that cause repeated operator pain? Because owner cannot tell whether to retry sync, refresh the page, or publish again.
  5. Why is this a product blocker? Because both surfaces are trust surfaces for owners; ambiguous context and misleading failures directly undermine adoption.
- **Root cause statement:** the current system models branch context repair and knowledge publish as internal implementation details instead of explicit owner-facing states. That leaks Console internals into UX and produces false failure semantics.
- **Fix mechanism:** make branch repair explicit on the consultant verification page, and make publish/sync a truthful two-phase contract with durable sync status, visible safe-mode state, and retry-sync behavior.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing branch context storage/apply logic in `console-web/src/app/knowledge/page.tsx` and `console-web/src/lib/console-context-storage.ts`; existing consultant verification overview/session APIs; existing knowledge publish pipeline, audit events, and branch safe-mode fields.
- **External reuse:** RFC 9110 / MDN guidance for truthful accepted async work and explicit follow-up status instead of fake synchronous success/failure.
- **Why not build from scratch:** the current Knowledge/consultant-verification flows already have the right domain boundaries; the defect is in owner semantics and missing state exposure, not in the existence of the flows themselves.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted backend pass + `1` targeted Playwright pass after implementation.
- **Fail-fast / scenario lock:** stop after the targeted consultant-verification/knowledge publish lanes fail once without a new RCA.
- **Stop condition:** deterministic backend checks + targeted mocked E2E are green.
- **Escalation path:** Brain / Top Architect if a second rerun would be needed without new evidence.

## Invariant
- Do not change consultant verification runtime semantics (`FACT/COLLECT/HANDOFF`) or bypass branch scope.
- Do not allow `Publish` retry to create duplicate knowledge versions when only sync failed.
- Do not hide branch safe mode or sync failure details behind generic copy.
- Do not regress the knowledge-safety guards added in `a921` for structured policy preservation.

## Scope
- `Проверка консультанта` branch-context UX and overview contract.
- `Knowledge` publish/post-sync flow semantics, statuses, retry-sync path, and owner-facing copy.
- Shared Console context presentation for current branch/source-of-truth.
- Deterministic tests and E2E for both defect families.
- Canon docs/state/session updates for the new behavior.

## Out of scope
- New consultant runtime capabilities unrelated to branch selection or owner verification semantics.
- Full queue/job platform redesign beyond the bounded publish-sync contract for knowledge.
- Global Console navigation redesign outside the touched business/knowledge surfaces.

## Touch-list
- `console-web/src/app/business/consultant-verification/page.tsx`
- `console-web/src/app/business/consultant-verification/_components/*`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/lib/console-context-storage.ts`
- `console-web/src/lib/use-console-context-scope.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/console_consultant_verification.py`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/tests/test_console_consultant_verification_api.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_knowledge_validation.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-verification-branch-publish-flow-a3.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add a reusable owner-facing branch gate/apply path to `Проверка консультанта`, reusing the Console context storage flow already proven in `Knowledge`.
2. Extend consultant verification overview with explicit branch-context metadata so the page can render actionable UI instead of passive error copy.
3. Split knowledge publish semantics into `publish commit` and `sync status`, preserving current version commit while surfacing truthful owner-facing states.
4. Add a sync-only retry path and UI action; do not require a new publish version when only sync timed out.
5. Surface branch safe mode and sync health on `Knowledge` and `Проверка консультанта`.
6. Update OpenAPI/types/tests/E2E/docs, then sync `STATE.md` with evidence before merge.

## DoD
- `Проверка консультанта` lets owner/admin choose/apply branch inline when context is missing; no dead-end `Перейти` loop remains.
- Consultant verification page shows the currently applied client/branch/source status clearly enough that owner knows what is being tested.
- `Knowledge publish failed` no longer appears for the partial-success case where version commit succeeded but sync failed.
- Publish returns durable sync status and error details; sync failure is visible without guessing from audit logs.
- A sync timeout can be retried without creating a new knowledge version.
- Branch `knowledge_safe_mode` and sync status are visible in owner-facing UX.
- Targeted backend/frontend/E2E checks are green and `STATE.md` records the new FACT/evidence before merge.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/truffles-api && pytest -q tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py tests/test_knowledge_validation.py -k "consultant_verification or knowledge or publish"`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/truffles-api && ruff check app/routers/console.py app/schemas/console.py app/services/console_consultant_verification.py app/services/knowledge_registry_service.py tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py tests/test_knowledge_validation.py`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/console-web && npm run lint -- --file src/app/business/consultant-verification/page.tsx --file src/app/knowledge/page.tsx --file e2e/owner-admin-business.spec.ts --file src/lib/api-client.ts`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3/console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/owner-admin-business.spec.ts --project chromium --workers 1 --grep "consultant verification branch gate|knowledge publish sync failure"`
- `cd /home/zhan/worktrees/2026-03-15-consultant-verification-branch-publish-flow-a3 && SESSION_AGENT=a3 scripts/session_check.sh`

## Evidence
- Backend test output for branch-context overview and publish-sync split.
- Playwright proof for inline branch selection and truthful sync-failed UX.
- OpenAPI/type generation outputs.
- Runtime DB note for the reproduced `published + sync_failed` case.
- `STATE.md` entry updated before merge with commands/results and residual risk.

## Release safety (mandatory for non-doc changes)
- Strategy: no flag split if schema/API stays backward-compatible; otherwise fail-closed for old clients and guarded UI checks on new fields.
- Go/no-go signals:
  - no duplicate version creation on retry-sync tests,
  - no consultant verification dead-end when branch is missing,
  - publish partial-success case reports `published + sync_failed`, not generic failure.
- Rollback: revert the PR; existing published versions remain durable because no data backfill is required.
- Post-release monitoring window: first 48h after merge, watch `knowledge_publish_failed`, repeated `sync_status=failed`, and consultant-verification overview requests that still land in `branch_selection_required`.

## Rollback
- Revert the feature branch merge if owner flows regress.
- If sync-status fields were added, keep them unused or nullable; do not delete published knowledge rows.

## No-go
- No fake green states hiding `knowledge_safe_mode`.
- No new branch-specific hacks in consultant runtime logic.
- No repeat full publish just to recover a sync timeout.
- No generic `Something went wrong` copy where the system knows the exact partial-success state.

## Risks/Blockers
- Current API clients may assume publish is binary `success/error`; changing semantics must stay backward-compatible or be released with corresponding frontend in lockstep.
- Sync retry must be idempotent against existing published version artifacts and Qdrant/index side effects.
- If current branch context helpers are too page-specific, a small extraction will be needed before reusing them.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Publish sync likely still runs in-process; this block makes it truthful and retryable, but not yet a full job queue with out-of-band worker monitoring.
- Console scope management may still be duplicated across a few owner pages after we fix consultant verification.

### Why not in this block
- A full async job platform and a global Console scope framework are larger architectural blocks than the current owner-facing defect pair.

### Risk if deferred
- Very large sync workloads may still hit timeouts even if UX becomes truthful.
- Scope-gate duplication may continue to create minor UX drift on future owner pages.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-sync-jobs-and-retry-observability-a3` (follow-up, if in-process sync still breaches timeout budget)
- `TP-2026-03-15-console-scope-gate-unification-a3` (follow-up, if owner pages keep duplicating branch/client gates)

### Expiry/trigger to stop deferral
- If another `knowledge_publish_failed` timeout occurs after this fix, the sync-job follow-up becomes blocking.
- If any new owner surface reimplements branch/client gating again, scope-gate unification becomes blocking.

## Next-block contract (mandatory)
### Next block objective
- Move knowledge sync from request-bound execution to explicit async job orchestration with durable retry history, if timeout family persists after truthful UX fix.

### First deterministic check command
- `cd /home/zhan/truffles-main/truffles-api && pytest -q tests/test_console_owner_business.py -k "knowledge_publish_sync_retry"`

### Blocked-by conditions
- Must land the current truthful publish/sync split first.
- Must have at least one canary or runtime evidence point after merge showing whether timeout family persists.

### Owner role for closure
- Brain / Top Architect
