# TP-2026-03-15-knowledge-activation-observability-p2-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-OBSERVABILITY-P2-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-CORRECTION-P1-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-RELEASE-MODEL-CORRECTION-P1-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-TRANSPORT-P3-A30`

## Название/цель
Довести новый activation-job контракт до операционно наблюдаемого состояния: добавить heartbeat/stage metadata для knowledge activation и показать owner/admin на `Knowledge` честную картину `active live` vs `published candidate` без возврата к legacy sync-семантике.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-correction-p1-a30.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `CA_ID`: `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/models/knowledge_activation_job.py`
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `console-web/src/app/knowledge/_hooks/useKnowledgeStudioState.ts`
  - `console-web/src/app/knowledge/_components/KnowledgeBranchReadinessPanel.tsx`
  - `console-web/src/app/knowledge/_components/KnowledgeStudioFlow.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`
- `FACT findings`:
  - P1 already separated `active_version_id` from latest published candidate and introduced `knowledge_activation_jobs`.
  - `Knowledge` owner/admin UI still renders the branch state through legacy `sync_status` wording and does not surface `active live` vs `published candidate` clearly.
  - Activation jobs already have `heartbeat_at`, `started_at`, and `attempt_count`, but there is no persisted stage/progress metadata and no first-class owner/admin disclosure for the job lifecycle.

## One web search (mandatory before implementation)
- **Query (exact):** `Temporal activity heartbeat official docs retries`
- **Date/time (local):** `2026-03-15 16:21 +05`
- **Sources opened (from this query):** `https://docs.temporal.io/develop/python/failure-detection`
- **Found options:** official Temporal guidance keeps heartbeat/failure-detection metadata separate from business payload and treats heartbeat as an execution-lifecycle signal rather than artifact truth.
- **Decision:** `build` — keep Truffles on its current transport, but add explicit stage/heartbeat metadata to the activation job record and expose it separately from artifact/live-pointer state.
- **Rejected options:** introducing a new orchestration framework in this block; the bounded step here is to make the current job model observable and honest first.

## Root cause (mandatory)
- **Symptom:** after P1 the release model is correct in runtime, but `Knowledge` still shows activation mostly as legacy `sync` copy and cannot explain what the activation job is doing right now.
- **Minimal reproduction:** publish a new knowledge version, receive `activation_status=queued|running`, then open `Knowledge`; the page still communicates mostly in `sync` language and does not clearly show `active live version` vs `published candidate` nor the current activation stage.
- **Evidence:** `truffles-api/app/routers/console.py`, `truffles-api/app/schemas/console.py`, `console-web/src/app/knowledge/_hooks/useKnowledgeStudioState.ts`, `console-web/src/app/knowledge/_components/KnowledgeBranchReadinessPanel.tsx`, `console-web/src/app/knowledge/_components/KnowledgeStudioFlow.tsx`.
- **Five Whys (or equivalent):**
  1. Why is owner/admin observability still weak? Because the page still prefers legacy `sync_status` language.
  2. Why does it prefer legacy sync? Because the page was built before `active_version_id` and activation jobs existed.
  3. Why can't the job explain current progress? Because the job record has state timestamps but no persisted stage metadata.
  4. Why is that a problem now? Because `queued/running/failed` alone is not enough to separate transport lag, branch-doc sync, config application, and live-pointer switch.
  5. Why does this matter? Because after P1 the remaining debt is operational trust, not product semantics, and operators still need honest execution evidence.
- **Root cause statement:** the release model was corrected at the artifact/live-pointer layer, but the activation-job lifecycle is still under-modeled for disclosure: no persisted stage metadata and no owner/admin surface built around the new active-vs-candidate contract.
- **Fix mechanism:** persist activation stage metadata on the job record, update the activation lifecycle to heartbeat across stages, and switch the `Knowledge` owner/admin UI to explicit `active live` / `published candidate` / `activation job` terminology.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `knowledge_activation_jobs`, existing `activation_*` response fields, existing `knowledge/current` and `knowledge/history` endpoints, existing owner/admin `Knowledge` route.
- **External reuse:** Temporal heartbeat/failure-detection pattern as the reference for separating execution heartbeat from artifact truth.
- **Why not reinvent the wheel:** we do not need a new scheduler yet; we need better lifecycle disclosure on top of the current bounded transport.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `6`
- **Code dominance:** `backend + frontend + contract`
- **Override token:** `none`
- **Why this profile fits:** this block changes one job model, current/history API contracts, the `Knowledge` owner/admin surface, and one targeted E2E lane.

## Invariant
- Live runtime must stay pinned to `active_version_id`; no activation-observability work may reintroduce publish-switches-live behavior.
- Consultant verification preview remains available on pinned snapshot during pending/failed activation.
- Owner surface remains business-readable; detailed activation stage is secondary disclosure, not a new blocker.

## Scope
- Add persisted activation stage metadata and heartbeat exposure to `knowledge_activation_jobs`.
- Expose activation stage/heartbeat fields through existing `knowledge/current`, `knowledge/history`, `publish`, `retry-sync`, and `rollback` contracts.
- Update `Knowledge` owner/admin UI to show `active live` vs `published candidate` and the current activation job stage.
- Refresh deterministic tests and the targeted owner/admin E2E lane.

## Out of scope
- Replacing outbox transport with a dedicated worker queue.
- Alert routing or pager integration.
- Reworking consultant-verification IA again.

## Touch-list
- `truffles-api/app/models/knowledge_activation_job.py`
- `truffles-api/migrations/061_add_knowledge_activation_job_stage_fields.sql`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_knowledge_registry_sync_backfill.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/app/knowledge/_hooks/useKnowledgeStudioState.ts`
- `console-web/src/app/knowledge/_components/KnowledgeBranchReadinessPanel.tsx`
- `console-web/src/app/knowledge/_components/KnowledgeStudioFlow.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add activation-stage persistence and lifecycle helpers on `knowledge_activation_jobs`.
2. Expose `activation_stage`, `activation_stage_label`, and `activation_heartbeat_at` in existing Console knowledge contracts.
3. Update `Knowledge` page logic to prefer activation semantics over legacy sync wording and to show `active live` vs `published candidate` clearly.
4. Extend deterministic backend tests plus the targeted owner/admin E2E lane.
5. Sync canon/session docs after checks pass.

## DoD
- Activation jobs persist a meaningful current stage in addition to coarse state.
- `Knowledge` current/history responses expose heartbeat/stage metadata without breaking legacy sync consumers.
- `Knowledge` owner/admin UI shows `active live version`, `published candidate`, and current activation progress without claiming preview is blocked.
- Deterministic tests prove the new disclosure and one targeted Playwright lane stays green.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/models/knowledge_activation_job.py app/services/knowledge_registry_service.py app/routers/console.py app/schemas/console.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run lint -- --file src/app/knowledge/_hooks/useKnowledgeStudioState.ts --file src/app/knowledge/_components/KnowledgeBranchReadinessPanel.tsx --file src/app/knowledge/_components/KnowledgeStudioFlow.tsx --file src/lib/api-client.ts --file e2e/owner-admin-business.spec.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npx playwright test e2e/owner-admin-business.spec.ts -g "knowledge activation observability"`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** adding stage/heartbeat disclosure on top of the current activation job will make the `Knowledge` surface operationally truthful without changing the live-pointer contract.
- **Expected measurable effect:** current/history responses gain stage metadata and the targeted E2E lane shows `active live` vs `published candidate` with pending activation details.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one focused backend test suite, one frontend lint/build pass, and one targeted Playwright lane once the new observability contract is green.

## Evidence
- Migration + model diff for activation stage fields.
- Updated `knowledge/current` and `knowledge/history` responses with stage/heartbeat metadata.
- Knowledge owner/admin UI proof and targeted backend/E2E checks.

## Rollback
- Revert the stage-field migration and restore previous knowledge UI/API disclosure while keeping the P1 `active_version_id` contract intact.

## Release safety (mandatory for non-doc changes)
- **Strategy:** deploy backend migration first, then backend/frontend together; canary on one branch/client with a controlled publish and retry cycle.
- **Go/no-go signals:** live runtime still serves the previous `active_version_id` during pending activation; current/history responses expose stage metadata; owner/admin `Knowledge` page shows active/candidate split and activation details without regressing publish/retry actions.
- **Post-release monitoring window:** observe at least one `publish -> queued -> ready` cycle and one `failed -> retry -> queued` cycle on the canary branch before wider rollout.
- **Rollback:** revert deploy, keep P1 active-pointer code, and roll back only the stage-field migration/UI if the observability slice misbehaves.

## No-go
- Do not reintroduce preview blockers based on activation state.
- Do not collapse `active live` and `published candidate` back into one owner status.
- Do not add a second transport/orchestrator in this block.

## Risks/Blockers
- The `Knowledge` page still has dense state orchestration, so UI changes must stay local to the existing hook/components.
- Backward compatibility must hold for older job rows without stage metadata.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Transport is still generic outbox; this block only improves job observability, not the transport model itself.

### Why not in this block
- Replacing transport with a dedicated worker is a larger infra slice and should follow only after the current observability contract is proven useful.

### Risk if deferred
- Operators will still depend on outbox plumbing for root cause once stage-level observability is not enough.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-activation-transport-p3-a30.md` (create after P2 lands if dedicated worker/alerts remain necessary)

### Expiry/trigger to stop deferral
- If canary support still cannot distinguish queue lag vs runtime sync vs pointer-switch failure from the new job stage disclosure, the transport P3 block becomes mandatory.

## Next-block contract (mandatory)
### Next block objective
- Replace or isolate the generic outbox transport for knowledge activation while preserving the P1/P2 release and observability contracts.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'OUTBOX_EVENT_KNOWLEDGE_SYNC|process_knowledge_sync_event|knowledge_activation_jobs|activation_stage' truffles-api/app/services/knowledge_registry_service.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/console.py`

### Blocked-by conditions
- P2 must land first so the team can see whether stage/heartbeat disclosure is sufficient before changing the transport layer.

### Owner role for closure
- `Top Architect | Brain`
