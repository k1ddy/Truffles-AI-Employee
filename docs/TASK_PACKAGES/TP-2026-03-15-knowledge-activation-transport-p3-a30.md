# TP-2026-03-15-knowledge-activation-transport-p3-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-TRANSPORT-P3-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-OBSERVABILITY-P2-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-ACTIVATION-OBSERVABILITY-P2-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-ADMIN-OBS-P4-A30`

## Название/цель
Убрать knowledge activation из generic outbox transport path и перевести её на dedicated activation worker/service, который claims jobs напрямую из `knowledge_activation_jobs`, выполняет activation по job record, детектит stuck-running jobs и оставляет owner/admin контракт P1/P2 неизменным.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-correction-p1-a30.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-observability-p2-a30.md`
- `CA_ID`: `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/workers/outbox.py`
  - `truffles-api/app/outbox_service_app.py`
  - `truffles-api/app/routers/outbox_service.py`
  - `scripts/restart_workers.sh`
  - `truffles-api/docker-compose.yml`
  - `truffles-api/tests/test_knowledge_registry_sync_backfill.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `truffles-api/tests/test_outbox_service_app.py`
- `FACT findings`:
  - P1 fixed the product contract: live runtime now stays pinned to `branches.active_knowledge_version_id` until activation succeeds.
  - P2 fixed disclosure: activation jobs now persist stage/heartbeat metadata and the `Knowledge` surface shows `Live версия` vs `Published candidate` honestly.
  - The transport is still generic outbox: `publish/retry/rollback` enqueue `knowledge.sync`, and the actual activation work still executes inside `app/routers/webhook/outbox.py` / `app/workers/outbox.py`.
  - That means job ownership is still split between `knowledge_activation_jobs` and `outbox_messages`, so queue lag vs worker failure vs retry ownership is still transport-shaped instead of job-shaped.

## One web search (mandatory before implementation)
- **Query (exact):** `PostgreSQL FOR UPDATE SKIP LOCKED official documentation SELECT job queue`
- **Date/time (local):** `2026-03-15 16:48 +05`
- **Sources opened (from this query):** `https://www.postgresql.org/docs/current/sql-select.html`
- **Found options:** PostgreSQL primary docs explicitly support `FOR UPDATE ... SKIP LOCKED` for non-blocking concurrent row claiming, which matches the existing outbox claim pattern and is sufficient for a dedicated DB-backed activation worker.
- **Decision:** `reuse/build` — reuse the existing DB-backed worker pattern and move knowledge activation to direct job claiming from `knowledge_activation_jobs` with `SKIP LOCKED`, instead of inventing a new queue or orchestration framework.
- **Rejected options:** keeping activation on generic outbox as the default runtime path; introducing an external orchestrator in this block.

## Root cause (mandatory)
- **Symptom:** after P2, owners can see activation state honestly, but the actual transport still depends on generic outbox delivery semantics.
- **Minimal reproduction:** publish a knowledge version, get a queued activation job, then inspect runtime ownership; job truth lives in `knowledge_activation_jobs`, but actual execution still depends on `knowledge.sync` rows being claimed and processed by the generic outbox worker.
- **Evidence:** `truffles-api/app/services/knowledge_registry_service.py`, `truffles-api/app/routers/webhook/outbox.py`, `truffles-api/app/workers/outbox.py`, `truffles-api/app/routers/console.py`.
- **Five Whys (or equivalent):**
  1. Why is activation still transport-shaped? Because queueing still emits generic outbox rows.
  2. Why is that bad? Because execution ownership is split between the job table and a separate transport table.
  3. Why does split ownership matter? Because queued/running/stuck/retry semantics become harder to attribute and operate.
  4. Why is that still a problem after P2? Because P2 improved disclosure, not execution ownership.
  5. Why does execution ownership matter now? Because the next failure family is no longer product semantics; it is transport/worker operability.
- **Root cause statement:** knowledge activation still executes through a generic message-delivery subsystem, so the system has a correct release model but still lacks a first-class execution owner for activation transport.
- **Fix mechanism:** claim and execute `knowledge_activation_jobs` directly through a dedicated activation worker/service, keep legacy outbox handling only as compatibility fallback, and let stuck detection/retry semantics live on the job record itself.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `knowledge_activation_jobs`, existing activation stage/state helpers, existing outbox `SKIP LOCKED` claim pattern, existing worker/service-app shadow pattern.
- **External reuse:** PostgreSQL `FOR UPDATE SKIP LOCKED` concurrency pattern from the official docs.
- **Why not reinvent the wheel:** the needed primitive already exists in the current repo and database; we only need to move execution ownership from `outbox_messages` to `knowledge_activation_jobs`.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `backend + worker/runtime`
- **Override token:** `none`
- **Why this profile fits:** this block changes transport/runtime ownership, worker/service entrypoints, a bounded set of contracts/tests, and canon docs.

## Invariant
- Live runtime must remain pinned to `active_version_id` until activation succeeds.
- Preview availability must stay independent from live activation state.
- `knowledge_activation_jobs` remains the source of truth for activation execution state; outbox must not become the primary owner again.

## Scope
- Add dedicated knowledge activation claim/process functions on `knowledge_activation_jobs`.
- Add dedicated activation worker/service entrypoints.
- Switch publish/retry/rollback queueing off generic outbox transport.
- Keep legacy outbox `knowledge.sync` handling only as compatibility fallback for already-enqueued rows.
- Add stuck detection for running activation jobs in the dedicated path.

## Out of scope
- Pager/notification routing.
- UI redesign beyond preserving the existing P2 contract.
- Multi-worker scaling proof beyond deterministic worker-claim behavior.

## Touch-list
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/workers/knowledge_activation.py`
- `truffles-api/app/knowledge_activation_service_app.py`
- `truffles-api/app/routers/knowledge_activation_service.py`
- `truffles-api/app/models/__init__.py` if needed
- `truffles-api/docker-compose.yml`
- `scripts/restart_workers.sh`
- `scripts/restart_knowledge_activation_service.sh`
- `truffles-api/tests/test_knowledge_registry_sync_backfill.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_knowledge_activation_service_app.py`
- `truffles-api/tests/test_outbox_service_app.py` if compatibility expectations change
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`

## Plan
1. Add direct job-claim / stuck-detection / process-by-job-id helpers in `knowledge_registry_service.py`.
2. Add dedicated activation worker and service-app entrypoints using the existing shadow-service pattern.
3. Switch queueing in `console.py` to create job records without emitting generic outbox rows.
4. Keep outbox `knowledge.sync` processing as legacy compatibility path for already-enqueued rows.
5. Add deterministic tests for direct claims, service processing, and publish/retry contract continuity.
6. Sync docs/session canon after checks pass.

## DoD
- New knowledge activation work is no longer queued through generic outbox by default.
- Dedicated worker/service can claim queued activation jobs directly from `knowledge_activation_jobs` and process them safely.
- Running jobs can be marked `stuck` from heartbeat timeout without relying on outbox failure semantics.
- Existing owner/admin `Knowledge` and consultant-verification contracts remain unchanged from P1/P2.
- Deterministic tests prove the new dedicated transport path and compatibility fallback.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py tests/test_knowledge_activation_service_app.py tests/test_outbox_service_app.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/services/knowledge_registry_service.py app/routers/console.py app/routers/webhook/outbox.py app/routers/knowledge_activation_service.py app/knowledge_activation_service_app.py app/workers/knowledge_activation.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py tests/test_knowledge_activation_service_app.py tests/test_outbox_service_app.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** moving activation transport to direct job claiming will preserve P1/P2 semantics while making execution ownership match the job record.
- **Expected measurable effect:** publish/retry no longer depend on `knowledge.sync` outbox rows; dedicated activation process endpoints/worker can claim queued jobs directly; deterministic tests cover queueing, claim/process, and stuck detection.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one focused backend test suite, one lint pass, one OpenAPI check, and a green session gate once the dedicated transport path is stable.

## Evidence
- New worker/service files and queueing diff proving direct job transport.
- Deterministic tests for claim/process/stuck handling.
- Canon/session updates documenting the P3 transport correction.

## Rollback
- Revert dedicated activation worker/service files and restore queueing through `enqueue_knowledge_sync_event`, while keeping P1/P2 live-pointer and observability contracts intact.

## Release safety (mandatory for non-doc changes)
- **Strategy:** shadow-enable dedicated activation service/worker first, verify one branch/client publish cycle, then flip default queueing to the dedicated path.
- **Go/no-go signals:** publish/retry still return queued activation job metadata; live pointer does not move before activation success; queued jobs are claimed by the dedicated worker without creating new `knowledge.sync` rows; compatibility outbox handler still processes pre-existing rows.
- **Post-release monitoring window:** observe one `publish -> queued -> ready` cycle and one forced `running -> stuck -> retry` cycle on canary.
- **Rollback:** disable the dedicated worker/service env toggle, restore outbox queueing, and leave the job table/state model untouched.

## No-go
- Do not move live pointer during publish.
- Do not reintroduce preview blocking.
- Do not delete legacy outbox compatibility before the dedicated path is proven.

## Risks/Blockers
- Existing tests assume `enqueue_knowledge_sync_event`; they need bounded updates, not broad rewrites.
- Worker/service patterns exist, but deployment scripts and STRUCTURE/session canon must stay in sync.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Admin/operator UI for worker health, retry policy tuning, and alert routing still remains limited after transport correction.

### Why not in this block
- This block is about execution ownership first. Broader admin control-plane surfacing should follow only after the dedicated path is stable.

### Risk if deferred
- Operators will still rely on logs or DB inspection for higher-order recovery decisions, even though the worker ownership is fixed.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-activation-admin-observability-p4-a30.md`

### Expiry/trigger to stop deferral
- If canary support cannot answer “is the worker healthy / retrying / stuck” from productized surfaces after P3, P4 becomes mandatory.

## Next-block contract (mandatory)
### Next block objective
- Add admin-facing worker-health/retry/alert visibility on top of the dedicated activation transport.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'knowledge_activation_service|claim_queued_knowledge_activation_jobs|mark_stale_knowledge_activation_jobs_stuck|KNOWLEDGE_ACTIVATION_WORKER_ENABLED' truffles-api/app scripts truffles-api/tests`

### Blocked-by conditions
- P3 dedicated transport must land first so admin surfaces attach to the real execution owner instead of the legacy outbox path.

### Owner role for closure
- `Top Architect | Brain`
