# TP-2026-03-15-knowledge-activation-admin-observability-p4-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-ADMIN-OBS-P4-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-TRANSPORT-P3-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-ACTIVATION-TRANSPORT-P3-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-CANARY-P5-A30`

## Название/цель
Сделать dedicated activation transport наблюдаемым для platform admin/operator: показать health summary и job queue в Console Ops, добавить bounded retry path поверх `knowledge_activation_jobs`, и включить alert/metric signals так, чтобы оператору не приходилось читать raw логи или generic outbox plumbing.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-transport-p3-a30.md`
- `CA_ID`: `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/health_service.py`
  - `truffles-api/app/logging_config.py`
  - `truffles-api/app/main.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_admin_health.py`
  - `truffles-api/tests/test_console_outbox_ops.py`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
- `FACT findings`:
  - P3 removed generic outbox as the default activation carrier; new work now lives directly in `knowledge_activation_jobs`.
  - Platform Admin still sees only generic system health and outbox queues in `Ops`; there is no first-class activation queue/retry surface.
  - Sentinel/health alerting knows about outbox pressure but not activation backlog/stuck worker signals, so activation regressions remain log-driven.

## One web search (mandatory before implementation)
- **Query (exact):** `prometheus client_python Gauge labels official documentation`
- **Date/time (local):** `2026-03-15 18:05 +05`
- **Sources opened (from this query):** `https://prometheus.github.io/client_python/instrumenting/labels/`, `https://prometheus.github.io/client_python/instrumenting/gauge/`
- **Found options:** official client_python docs confirm labeled gauges are the right primitive for grouped queue-health metrics and recommend explicit label initialization through `.labels()`.
- **Decision:** `reuse/integrate` — extend the existing Prometheus/logging metrics layer with bounded activation gauges instead of inventing custom metric plumbing or storing monitoring-only state in the database.
- **Rejected options:** bespoke metrics exporter; no metrics at all with health visible only through `/console/v1/ops/*`.

## Root cause (mandatory)
- **Symptom:** after P3, execution ownership is correct, but operators still cannot answer “is activation healthy / stuck / retryable?” from productized surfaces.
- **Minimal reproduction:** publish a version, let activation queue or fail, then open Console Ops; outbox health is visible, but there is no activation queue, no activation retry action, and no activation-specific alert summary.
- **Evidence:** `truffles-api/app/services/health_service.py`, `truffles-api/app/routers/console.py` (`/health`, `/ops/outbox` only), `console-web/src/components/OpsPage.tsx`.
- **Five Whys (or equivalent):**
  1. Why is operator visibility incomplete? Because Ops still surfaces only generic health and outbox queues.
  2. Why is that wrong after P3? Because the execution owner is now `knowledge_activation_jobs`, not outbox.
  3. Why does that matter? Because retry, stuck, and backlog signals must attach to the real execution owner to be actionable.
  4. Why isn’t current health enough? Because DB/Redis/outbox can be healthy while activation jobs are queued, stale, or repeatedly failing.
  5. Why is this a product problem, not only infra? Because platform admin/operator needs a bounded action loop, not raw log inspection, to keep live knowledge updates reliable.
- **Root cause statement:** admin/operator observability still points at the old generic queue and system-level health, so the new activation execution owner lacks first-class health, retry, and alert surfaces.
- **Fix mechanism:** add activation-specific health/metric snapshots, expose activation jobs/retry through Console Ops, and wire alerting to activation backlog/stuck/failure thresholds.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `knowledge_activation_jobs`, P3 transport helpers, existing `OpsPage` queue/retry patterns, existing `ConsoleHealthResponse`, existing sentinel `check_and_alert_health`, existing Prometheus helpers in `logging_config.py`.
- **External reuse:** official `client_python` Gauge/labels docs.
- **Why not reinvent the wheel:** the repo already has queue-health patterns, Ops action loops, and Prometheus integration; P4 only needs to attach them to activation jobs.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `backend + frontend`
- **Override token:** `none`
- **Why this profile fits:** this block changes health contracts, ops APIs, one admin UI surface, and canon docs, but stays within the existing release model.

## Invariant
- Preview/live release semantics from P0/P1/P2/P3 must not change.
- Live pointer remains gated by successful activation only.
- Retry must create/queue bounded activation attempts without mutating the knowledge artifact.
- Admin observability must reflect the real activation owner (`knowledge_activation_jobs`), not generic outbox state.

## Scope
- Add activation health snapshot + alerting + metrics.
- Extend `/console/v1/health` with activation summary.
- Add Console Ops list/retry endpoints for activation jobs.
- Show activation health/queue in `OpsPage`.

## Out of scope
- PagerDuty/Telegram escalation routing changes.
- Owner-facing `Knowledge` redesign.
- Canary/release automation.

## Touch-list
- `truffles-api/app/services/health_service.py`
- `truffles-api/app/logging_config.py`
- `truffles-api/app/main.py`
- `truffles-api/app/services/knowledge_registry_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_admin_health.py`
- `truffles-api/tests/test_console_outbox_ops.py`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`

## Plan
1. Add activation health snapshot + thresholds + alert hook in `health_service.py`.
2. Extend health schemas/API and add activation ops list/retry endpoints in `console.py`.
3. Add activation gauges to `/metrics`.
4. Add admin Ops UI for activation health + queue/retry.
5. Cover backend contracts with deterministic tests and regenerate API types.
6. Sync canon/session docs after checks pass.

## DoD
- Platform Admin can see activation health in `/console/v1/health` and `OpsPage`.
- Platform Admin can inspect queued/running/failed/stuck activation jobs and retry failed/stuck ones from Console Ops.
- Sentinel/admin health alerting includes activation backlog/stuck/failure thresholds.
- Prometheus `/metrics` exports activation queue gauges.
- Existing owner/live contracts remain unchanged.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_admin_health.py tests/test_console_outbox_ops.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check app/services/health_service.py app/logging_config.py app/main.py app/services/knowledge_registry_service.py app/routers/console.py app/schemas/console.py tests/test_admin_health.py tests/test_console_outbox_ops.py tests/test_knowledge_registry_sync_backfill.py tests/test_console_owner_business.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && python3 scripts/generate_openapi.py --check`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run generate:api`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run lint -- --file src/components/OpsPage.tsx --file src/lib/api-client.ts`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** adding activation-specific admin health/retry surfaces will make the new transport operationally observable without changing release semantics.
- **Expected measurable effect:** `/health` and `OpsPage` show activation backlog/stuck counts, failed/stuck jobs can be retried from Ops, and alerting includes activation degradation signals.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one green backend suite, one green frontend lint/build pass, one OpenAPI/types regeneration, and one green session gate.

## Evidence
- Health/ops API contract diff with activation summary and retry surface.
- Deterministic tests for activation health/retry.
- Updated Ops UI showing activation queue/health.

## Rollback
- Remove activation-specific health/ops UI/API additions and keep P3 transport intact; operators can fall back to logs/DB inspection without affecting live activation correctness.

## Release safety (mandatory for non-doc changes)
- **Strategy:** ship as additive admin/operator observability only; no change to owner publish/live path.
- **Go/no-go signals:** `/console/v1/health` still works for existing consumers, activation summary matches DB state, retry creates new queued activation jobs only for failed/stuck rows, and Ops UI renders both old outbox and new activation sections.
- **Post-release monitoring window:** verify one failed activation and one stuck activation are visible and retryable through Ops.
- **Rollback:** revert the additive admin health/ops changes; keep P3 worker/service transport untouched.

## No-go
- Do not reintroduce generic outbox as activation owner.
- Do not mutate existing activation jobs back to queued in place.
- Do not change owner-facing `Knowledge` semantics in this block.

## Risks/Blockers
- OpsPage is already large; changes must stay localized and avoid cross-page refactors.
- Health response is consumed in multiple places; additive fields only.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- No canary/release automation yet for the dedicated activation worker/service.

### Why not in this block
- This block is about observability and bounded operator action loops, not rollout orchestration.

### Risk if deferred
- Activation is observable and retryable, but release promotion still depends on manual canary discipline.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-activation-canary-p5-a30.md`

### Expiry/trigger to stop deferral
- If production rollout of the dedicated activation worker/service starts without a documented canary/go-no-go path, P5 becomes mandatory.

## Next-block contract (mandatory)
### Next block objective
- Add canary/release verification for the dedicated activation worker/service.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'knowledge_activation|activation_status|ops/knowledge-activation|health_check_knowledge_activation' truffles-api/app console-web/src`

### Blocked-by conditions
- P4 admin observability must land first so canary decisions have productized health and retry signals.

### Owner role for closure
- `Top Architect | Brain`
