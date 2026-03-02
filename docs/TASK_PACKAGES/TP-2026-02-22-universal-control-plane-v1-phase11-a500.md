# TP-2026-02-22-universal-control-plane-v1-phase11-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE11
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE10
- `UNLOCKS`: UCPV1-PHASE12

## Название/цель
Universal Control Plane v1 / Phase 11: Compliance KZ Retention/Lifecycle, чтобы соблюдение KZ data boundary и lifecycle (`retention -> export -> destruction`) выполнялось автоматически, auditable и без ручных ad-hoc процедур.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `SPECS/ACTIVE_LEARNING.md`
- `STRATEGY/REQUIREMENTS.md`
- `STRATEGY/VISION.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests (current state)`:
  - `truffles-api/app/services/learning_service.py`
  - `truffles-api/app/models/learned_response.py`
  - `truffles-api/app/models/client_settings.py`
  - `truffles-api/app/routers/admin.py` (`/admin/media/cleanup`)
  - `truffles-api/app/routers/console.py` (client archive lifecycle)
  - `truffles-api/app/services/outbox_service.py` (`archive_pending_outbox`)
  - `truffles-api/tests/test_learning_service.py`
  - `truffles-api/tests/test_console_admin_provisioning.py`
- `Baseline commands`:
  - `rg -n "retention|retention_expires_at|anonymization|cleanup|archive_pending_outbox|deleted_at" truffles-api/app truffles-api/tests`
  - `rg -n "UCPV1-PHASE11|phase11" docs/BLOCK_GRAPH.yaml docs/REPORTS docs/TASK_PACKAGES`
  - `ls -1 truffles-api/migrations | tail -n 20`
- `FACT findings`:
  - Retention controls exist only as fragmented local mechanisms (`learning_retention_days`, media cleanup TTL, outbox archive), not as unified compliance lifecycle.
  - There is no central retention policy registry by data class with owner/TTL/legal_basis.
  - There is no platform-admin lifecycle endpoint for compliance export/destruction by tenant scope.
  - There is no deterministic compliance job suite proving automated `retention -> export -> destroy` with audit trail.

## One web search (mandatory before implementation)
- **Query (exact):** `Kazakhstan personal data law Article 12 storage in database located in the territory of the Republic of Kazakhstan Article 18 destruction`
- **Date/time (local):** `2026-03-02 06:18 (+0500)`
- **Why this query is precise:** нужен primary legal source для KZ localization + storage-term + destruction triggers до проектирования lifecycle contracts.
- **Sources opened (from this query):**
  - Law of the Republic of Kazakhstan `On Personal Data and their Protection` (Adilet, official legal information system): `https://adilet.zan.kz/eng/docs/Z1300000094`
- **Existing solutions found:**
  - Article 12: personal data must be stored in a database located in Kazakhstan; storage term is tied to processing purpose unless law states otherwise.
  - Article 18: mandatory destruction triggers include storage-term expiration and legal-relation termination.
- **Decision:**
  - `reuse/integrate`: build phase11 around explicit lifecycle contract with KZ-localization evidence, retention-term policy, and destruction job/audit events.
- **Rejected options:**
  - keeping only ad-hoc TTL knobs in isolated modules without central compliance registry.
- **Open questions:**
  - mapping of Truffles data classes to legal retention basis/source-of-truth per tenant contract.

## Root cause (mandatory)
- **Symptom:** B11 remains planned; no automated compliance lifecycle proving KZ-localized storage plus auditable retention/export/destruction across tenant data classes.
- **Minimal reproduction:**
  - `rg -n "retention_expires_at|learning_retention_days|media/cleanup|archive_pending_outbox" truffles-api/app`
  - verify absence of compliance registry tables and no `phase11` migration in `truffles-api/migrations`.
- **Evidence to capture:**
  - fragmented retention controls,
  - missing lifecycle registry/API,
  - missing deterministic tests for compliance jobs.
- **Five Whys (or equivalent):**
  1. Why B11 not delivered: lifecycle controls evolved as local maintenance features.
  2. Why local features are insufficient: no single compliance contract by data class/owner/legal basis.
  3. Why this is risky: retention/destruction cannot be proven consistently during audit.
  4. Why manual operations are unsafe: human-run cleanup is non-deterministic and weakly auditable.
  5. Why phase-level delivery required: needs schema, jobs, APIs, and evidence chain across runtime + console + ops.
- **Root cause statement:**
  - отсутствует единый compliance lifecycle layer (registry + scheduler + audit trail), который связывает legal requirements и фактические операции с данными.
- **Fix mechanism:**
  - introduce compliance data-class registry + retention policy + export/destruction jobs + immutable audit events and deterministic checks.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse existing job framework (`console_ops_jobs`) for scheduled/triggered compliance runs,
  - reuse lifecycle markers (`deleted_at`, archived statuses) where applicable,
  - reuse learning retention primitives (`retention_expires_at`) as one data-class signal.
- **External reuse:**
  - reuse primary legal structure from RK Law (`Article 12/18`) as contract anchors.
- **Why not reinvent the wheel:**
  - phase11 extends existing lifecycle primitives into one auditable compliance layer instead of rewriting storage/runtime subsystems.

## Invariant
- KZ data boundary remains strict (`Data in KZ` from product formula).
- Hard-law/safety boundaries are never weakened by operational convenience.
- Any lifecycle action is tenant-scoped and auditable.
- Product outcome contract (`FACT/COLLECT/HANDOFF`) remains unchanged.
- No semantic hardcode in policy-core runtime.

## Scope
- Define compliance data classes and retention policies (`owner`, `ttl`, `legal_basis`, `destruction_mode`).
- Add policy registry + lifecycle execution model for retention/export/destruction.
- Add platform-admin API for compliance lifecycle operations and evidence retrieval.
- Add deterministic jobs/tests and audit events for lifecycle outcomes.
- Sync canon docs (`BLOCK_GRAPH/master report/STATE/session evidence`).

## Out of scope
- Full migration waves across all historical tenants (`UCPV1-PHASE13`).
- Rewriting message pipeline or LLM policy-core behavior.
- Replacing existing SLA engine or onboarding/go-live logic.

## Touch-list (planned)
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `truffles-api/migrations/*` (phase11 compliance tables)
- `truffles-api/app/models/*` (compliance policy/run/audit entities)
- `truffles-api/app/services/*` (retention/export/destruction orchestration)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/*` (deterministic compliance lifecycle tests)
- `contracts/console_api/openapi.v1.yaml`

## Plan (1..N)
1. Analysis gate: define compliance data classes and legal mapping (Article 12/18 evidence).
2. Contract delta: design registry schema + API + RBAC + audit envelope.
3. Implement migration/models/services for lifecycle policy + run ledger.
4. Implement lifecycle operations (retention mark, export package metadata, destruction execution record).
5. Add deterministic tests for policy resolution, job execution, and audit chain.
6. Sync docs/state and set block status based on evidence (`in_progress` -> `passed` only after DoD).

## DoD
- Compliance registry exists with versioned policy per data class and tenant scope.
- Automated lifecycle jobs execute deterministically and emit audit records for each operation.
- Export/destruction operations are retrievable by platform-admin with traceable evidence.
- KZ-localization/legal basis fields are present in policy and run records.
- Deterministic tests prove positive/negative paths and fail-closed behavior.
- `docs/BLOCK_GRAPH.yaml` updated to `passed` only after evidence-backed completion.

## Checks
- Analysis stage (current block state):
  - `rg -n "retention|retention_expires_at|anonymization|media/cleanup|archive_pending_outbox|deleted_at" truffles-api/app truffles-api/tests`
  - `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md --graph docs/BLOCK_GRAPH.yaml`
- Implementation stage (future, mandatory):
  - `cd truffles-api && ruff check app tests`
  - `cd truffles-api && pytest -q tests/test_console_admin_provisioning.py tests/test_console_ops_jobs.py`
  - `cd truffles-api && pytest -q tests/test_learning_service.py tests/test_message_endpoint.py`
  - `cd truffles-api && python3 scripts/generate_openapi.py --check`

## Evidence
- Analysis evidence:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
  - legal source: `https://adilet.zan.kz/eng/docs/Z1300000094`
- Implementation evidence (future):
  - migration/model/service diffs,
  - deterministic tests,
  - compliance run/audit snapshots,
  - updated block/master/state docs.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` expensive realism runs in this bootstrap slice (analysis/doc sync only).
- **Fail-fast / scope lock:** only doc + deterministic governance checks (`zero_context_gate`, `session_check`).
- **Stop condition:** if two iterations in a row produce no new evidence, stop and return to RCA/contract delta.
- **Escalation path:** Brain/Top Architect for destructive-path policy decisions.

## Release safety (mandatory for non-doc changes)
- **Strategy:** canary by tenant scope (`internal demo tenant -> pilot client -> selected production clients`).
- **Go/no-go signals:** zero cross-tenant leakage, successful lifecycle run ratio, no unexpected delete/export failures, stable outbox/incident metrics.
- **Rollback:** disable phase11 jobs via feature flag + revert registry version + restore previous policy snapshot.
- **Post-release monitoring window:** minimum `24h` with audit counters and incident watch.

## Doc sync plan (after implementation)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase11-a700.md`

## Rollback
- Revert phase11 commits and disable compliance lifecycle jobs/flags.
- Restore previous policy snapshots and stop destructive operations.
- Document rollback evidence in phase11 report + STATE.

## No-go
- Нельзя удалять/экспортировать данные без audit record и tenant scope.
- Нельзя внедрять compliance как ручной runbook-only процесс.
- Нельзя закрывать блок без deterministic proof по lifecycle operations.

## Risks/Blockers
- Data-class inventory incompleteness can create false compliance confidence.
- Misconfigured destruction policy can cause irreversible data loss.
- Legacy sessions/process-hygiene noise must remain non-blocking for phase delivery.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes (analysis gate started).
- `Start from`: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `Do not touch`: unrelated tracks (quality-chain/firebreak/marketing).
- `Open risks`: data-class mapping completeness and safe destructive-path design.
- `First command to verify`: `rg -n "UCPV1-PHASE11|in_progress|phase11-a500" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
