# TP-2026-03-15-knowledge-release-model-correction-p1-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-CORRECTION-P1-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-STOPLOSS-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-STOPLOSS-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-OBSERVABILITY-P2-A30`

## Название/цель
Довести knowledge release model до корректного архитектурного контракта: publish создаёт immutable artifact и preview-кандидата, а live traffic переключается только через `active_version_id` после завершённой activation job с отдельным lifecycle и observability.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-owner-knowledge-stabilization-reset-a4.md`
- `CA_ID`: `UX-48`, `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/knowledge_runtime.py`
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/models/knowledge_version.py`
  - `truffles-api/app/models/branch.py`
  - `truffles-api/app/services/console_consultant_verification.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `truffles-api/tests/test_console_consultant_verification_api.py`
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/business/consultant-verification/page.tsx`
- `FACT findings`:
  - P0 stop-loss corrected owner preview and session integrity, but live runtime still resolves `get_current_published()` directly.
  - `sync_status` still models activation execution on `KnowledgeVersion`, not on a retryable job record.
  - `knowledge.sync` still rides generic outbox semantics without job-level `queued/running/stuck/heartbeat/retries`.

## One web search (mandatory before implementation)
- **Query (exact):** `SQLAlchemy relationship multiple foreign keys same table foreign_keys official docs`
- **Date/time (local):** `2026-03-15 15:45 +05`
- **Sources opened (from this query):** `https://docs.sqlalchemy.org/en/20/orm/join_conditions.html#handling-multiple-join-paths`
- **Found options:** official SQLAlchemy guidance for disambiguating multiple foreign-key paths with `foreign_keys`, plus related `primaryjoin`/`remote_side` guidance for explicit joins.
- **Decision:** `integrate` — keep the new `branches.active_knowledge_version_id -> knowledge_versions.id` pointer simple, avoid ambiguous ORM relationships for now, and stay with explicit query-based resolution instead of adding fragile mapper relationships in this block.
- **Rejected options:** adding new ORM relationships between `Branch` and `KnowledgeVersion` for active-version traversal; not needed for the current read/write paths and would expand mapper risk without product value.

## Root cause (mandatory)
- **Symptom:** live traffic can still switch semantic truth before activation is truly ready, and activation remains operationally opaque.
- **Minimal reproduction:** publish a new version, observe `sync_status=pending`, and confirm that live runtime still resolves the newly published version while activation is incomplete.
- **Evidence:** `truffles-api/app/services/knowledge_runtime.py`, `truffles-api/app/services/knowledge_registry_service.py`, `truffles-api/app/routers/console.py`, P0 RCA in `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-stoploss-a30.md`.
- **Five Whys (or equivalent):**
  1. Why can live switch too early? Because live runtime reads `current published` directly.
  2. Why does publish move live truth? Because `published` currently doubles as both artifact existence and live-active pointer.
  3. Why is activation opaque? Because activation uses generic outbox dispatch, not a dedicated job lifecycle.
  4. Why is retry/state modeling weak? Because execution state is stored on `KnowledgeVersion`.
  5. Why is this hard to expose honestly? Because product/UI semantics still depend on overloaded infrastructure state.
- **Root cause statement:** knowledge lifecycle still lacks distinct persistence and runtime contracts for `artifact`, `preview candidate`, and `live active` version plus a dedicated activation execution model.
- **Fix mechanism:** add `active_version_id`, move activation execution into dedicated job records/lifecycle, and keep publish/preview/live activation as explicitly separate states in API/runtime/UI.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing knowledge version records, existing outbox transport as temporary dispatch mechanism, current consultant-verification preview model, current branch-scoped publish/retry endpoints.
- **External reuse:** rollout-state separation pattern from Argo Rollouts (`preview service` vs `active service`).
- **Why not reinvent the wheel:** the missing piece is lifecycle separation and observability, not a new owner-facing feature surface.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `backend + contract + targeted frontend`
- **Override token:** `none`
- **Why this profile fits:** the block changes persistence, runtime selection, Console contracts, generated OpenAPI, and the owner consultant-verification surface in one bounded release-model correction.

## Invariant
- Preview sessions remain immutable and reproducible.
- Live traffic must not switch to a new knowledge version before activation is `ready`.
- Activation retries/ops detail must be observable without leaking raw internals into the owner primary path.

## Scope
- Introduce `branches.active_knowledge_version_id` (or equivalent active pointer).
- Introduce dedicated activation job record/lifecycle for knowledge activation.
- Update live runtime selection to read the active pointer, not `current published`.
- Expose explicit activation job status in owner/admin-facing read models.

## Out of scope
- Reworking consultant-verification session pinning again.
- Reversing the P0 preview availability correction.
- General owner/admin IA redesign beyond activation observability.

## Touch-list
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/models/knowledge_version.py`
- `truffles-api/app/models/branch.py`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/consultant-verification/page.tsx`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Define persistence split: immutable knowledge artifact, active live pointer, and activation job row.
2. Update publish/activation flow so publish creates candidate artifact and activation moves the active pointer only on success.
3. Update runtime and API contracts to read/write the new active pointer and job state.
4. Add deterministic proof for `publish pending != live switched`.
5. Update owner/admin docs and runbooks with preview-vs-live-vs-activation semantics.

## DoD
- Live runtime no longer reads newly published versions before activation success.
- Activation has a job record with explicit state transitions and retry/error fields.
- Owner/admin overview returns separate preview and live activation signals without hiding preview.
- Deterministic tests prove `pending activation` keeps the previous live version active.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_knowledge_runtime.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_consultant_verification_api.py tests/test_console_owner_business.py tests/test_admin_health.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/services/knowledge_registry_service.py app/services/console_consultant_verification.py app/routers/console.py app/services/knowledge_runtime.py app/services/knowledge_snapshot_service.py app/services/health_service.py app/routers/webhook/decision.py app/models/branch.py app/models/knowledge_activation_job.py app/schemas/console.py tests/test_knowledge_runtime.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py tests/test_console_consultant_verification_api.py tests/test_admin_health.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run lint -- --file src/lib/api-client.ts --file src/app/business/consultant-verification/page.tsx --file src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx --file src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts --file src/app/business/consultant-verification/_lib/presentation.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npx playwright test e2e/owner-admin-business.spec.ts -g "should keep consultant verification preview available while client update is pending"`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** P1 should keep preview available while pending activation, but live runtime must stay pinned to the previous active version until activation succeeds.
- **Expected measurable effect:** backend tests prove active-pointer gating; frontend build and one targeted Playwright lane prove the owner surface now distinguishes `live` vs `published candidate`.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one focused backend suite, one lint/build pass, and one targeted Playwright lane once the active-pointer contract is proven; no repeated exploratory reruns without new evidence.

## Evidence
- Migration + model diff for active pointer / activation jobs: `truffles-api/app/models/branch.py`, `truffles-api/app/models/knowledge_activation_job.py`, `truffles-api/migrations/060_add_knowledge_release_activation_jobs.sql`.
- Runtime + Console contract proof: `truffles-api/app/services/knowledge_registry_service.py`, `truffles-api/app/services/knowledge_runtime.py`, `truffles-api/app/services/console_consultant_verification.py`, `truffles-api/app/routers/console.py`, `truffles-api/app/schemas/console.py`, `contracts/console_api/openapi.v1.yaml`.
- Deterministic tests proving `publish pending != live switched`: `truffles-api/tests/test_knowledge_runtime.py`, `truffles-api/tests/test_knowledge_registry_sync_backfill.py`, `truffles-api/tests/test_console_owner_business.py`, `truffles-api/tests/test_console_consultant_verification_api.py`, `truffles-api/tests/test_admin_health.py`.
- Updated owner/admin UI proof: `console-web/src/lib/api-client.ts`, `console-web/src/types/api.generated.ts`, `console-web/src/app/business/consultant-verification/page.tsx`, `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx`, `console-web/src/app/business/consultant-verification/_lib/presentation.ts`, `console-web/e2e/owner-admin-business.spec.ts`.

## Rollback
- Revert the active-pointer / activation-job migration and restore previous publish/runtime flow.

## Release safety (mandatory for non-doc changes)
- **Strategy:** ship migration first, then deploy backend/frontend together; canary on one branch/client that already uses consultant verification before wider rollout.
- **Go/no-go signals:** `publish` returns queued activation without switching `active_version_id`; live runtime still serves previous active knowledge during pending activation; consultant verification shows `published` preview while live update is pending; targeted backend/frontend checks stay green.
- **Post-release monitoring window:** watch the canary branch/client through at least one `publish -> queued activation -> ready` cycle and one `retry activation` cycle before broadening rollout.
- **Rollback:** revert the deploy, restore pre-P1 code, and if required roll back migration `060_add_knowledge_release_activation_jobs.sql`; verify `GET /console/v1/knowledge/current` and live runtime return to the prior contract.

## No-go
- Do not reintroduce sync as preview blocker.
- Do not hide activation failure by silently switching live pointer anyway.
- Do not keep job lifecycle only inside outbox events without a first-class record.

## Risks/Blockers
- Branch/runtime migration will touch persistence and potentially live rollout tooling.
- Backward compatibility is needed for existing published rows and retry endpoints.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Owner/admin IA for activation observability may still need a later P2 disclosure cleanup after the runtime model is corrected.

### Why not in this block
- This follow-up is already the architecture-correction block; any remaining owner/admin disclosure refinement is secondary.

### Risk if deferred
- Activation could become technically correct but still operationally hard to diagnose for admins.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-activation-observability-p2-a30.md` (future, create only if P1 lands and admin disclosure still needs dedicated work)

### Expiry/trigger to stop deferral
- If P1 lands and admin/support still cannot distinguish queued/running/stuck activation from one read model, the P2 observability block becomes mandatory.

## Next-block contract (mandatory)
### Next block objective
- Implement `active_version_id` and activation-job lifecycle without regressing the P0 preview/session contract.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'get_current_published\\(|sync_status|knowledge_safe_mode|published' truffles-api/app/services/knowledge_runtime.py truffles-api/app/services/knowledge_registry_service.py truffles-api/app/routers/console.py`

### Blocked-by conditions
- Requires the P0 stop-loss branch to stay green and accepted as the current preview contract baseline.

### Owner role for closure
- `Top Architect | Brain`
