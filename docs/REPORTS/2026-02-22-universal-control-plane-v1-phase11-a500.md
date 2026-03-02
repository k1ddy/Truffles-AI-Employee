# Universal Control Plane v1 - Phase 11 Compliance KZ Retention/Lifecycle (a500)

Date
- 2026-03-02

## Block identity
- `BLOCK_ID`: UCPV1-PHASE11
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE10
- `UNLOCKS`: UCPV1-PHASE12

## Input baseline (FACT)
- `UCPV1-PHASE10` is `passed`, so dependency lock for phase11 is removed.
- Current platform has partial retention-related controls:
  - learning retention (`learning_retention_days`, `retention_expires_at`),
  - media cleanup endpoint (`/admin/media/cleanup`),
  - archive mechanisms for selected operational tables.
- Unified compliance lifecycle (`retention -> export -> destruction`) with centralized policy and audit chain is not implemented.

## FACT pre-check evidence (before changes)
- `rg -n "retention|retention_expires_at|anonymization|media/cleanup|archive_pending_outbox|deleted_at" truffles-api/app truffles-api/tests` -> confirms fragmented controls in isolated modules.
- `ls -1 truffles-api/migrations | tail -n 20` -> latest migration is phase10 (`046_add_sla_profile_versions.sql`), no phase11 compliance schema yet.
- `rg -n "UCPV1-PHASE11|phase11" docs/BLOCK_GRAPH.yaml docs/REPORTS docs/TASK_PACKAGES` -> graph references phase11 paths, but implementation artifacts were absent before this bootstrap.

## One web search evidence
- `Query (exact)` -> `Kazakhstan personal data law Article 12 storage in database located in the territory of the Republic of Kazakhstan Article 18 destruction`
- `Sources opened` -> `https://adilet.zan.kz/eng/docs/Z1300000094`
- `Key extracted norms`:
  - Article 12: personal data shall be stored in a database located in the territory of RK; storage term ties to purpose unless law states otherwise.
  - Article 18: destruction required on storage-term expiry, legal-relation termination, and other legal triggers.
- `Decision` -> phase11 contracts must include localization evidence + retention-term policy + destruction triggers + auditable execution ledger.

## Root cause validation
- `Symptom` -> B11 planned but not delivered as deterministic compliance lifecycle.
- `Minimal reproduction` -> inspect retention-related code paths (`learning_service`, `admin media cleanup`, `archive_pending_outbox`); no central compliance registry or lifecycle run ledger.
- `Root cause statement` -> compliance controls were introduced as local operational utilities, not as unified legal-governed lifecycle layer.
- `Fix mechanism` -> implement phase11 registry + lifecycle jobs + export/destruction evidence chain under platform-admin governance.

## Reuse-first outcome
- `Internal reuse applied` -> yes (`console_ops_jobs`, lifecycle/archive patterns, learning retention fields).
- `External reuse applied` -> yes (RK law primary source via Adilet for legal anchors).
- `Build-new scope` -> only compliance orchestration layer (registry + audit + deterministic checks), no rewrite of existing runtime semantics.

## Contract delta (analysis scope)
- Planned phase11 contracts:
  - compliance data-class registry (`data_class`, `owner`, `legal_basis`, `ttl`, `destruction_mode`),
  - lifecycle run ledger (`run_id`, `scope`, `policy_version`, `result`, `evidence_ref`),
  - export/destruction operation records with tenant isolation and immutable audit events.
- Planned API additions (platform-admin only):
  - compliance policy read/write,
  - lifecycle run trigger/preview,
  - export/destruction evidence retrieval.

## Implemented changes
- Added phase11 block artifacts:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
- Canon sync for phase11 execution start:
  - `docs/BLOCK_GRAPH.yaml` (`UCPV1-PHASE11: in_progress`)
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md` (B11 status/queue update)
  - `STATE.md` (NOW evidence for phase11 analysis start)
- Slice 1 delivery (`compliance policy registry`):
  - migration: `truffles-api/migrations/047_add_compliance_policy_versions.sql`
  - model: `truffles-api/app/models/compliance_policy_version.py`
  - schema: `truffles-api/app/schemas/compliance_policy.py`
  - service: `truffles-api/app/services/compliance_policy_registry_service.py`
  - console API:
    - `GET /console/v1/admin/compliance-policy-registry`
    - `POST /console/v1/admin/compliance-policy-registry/publish`
    - `POST /console/v1/admin/compliance-policy-registry/rollback`
  - router/schema wiring:
    - `truffles-api/app/routers/console.py`
    - `truffles-api/app/schemas/console.py`
  - deterministic tests:
    - `truffles-api/tests/test_compliance_policy_registry_service.py`
    - `truffles-api/tests/test_console_compliance_policy_registry.py`
  - OpenAPI canon sync:
    - `contracts/console_api/openapi.v1.yaml`
- Slice 2 delivery (`compliance lifecycle ledger + preview records`):
  - migration:
    - `truffles-api/migrations/048_add_compliance_lifecycle_runs.sql`
  - models:
    - `truffles-api/app/models/compliance_lifecycle_run.py`
    - `truffles-api/app/models/compliance_lifecycle_record.py`
  - service:
    - `truffles-api/app/services/compliance_lifecycle_service.py`
  - console API:
    - `POST /console/v1/admin/compliance-lifecycle/runs`
    - `GET /console/v1/admin/compliance-lifecycle/runs`
    - `GET /console/v1/admin/compliance-lifecycle/runs/{run_id}`
  - deterministic behavior:
    - tenant-scoped preview for `learned_responses` due by `retention_expires_at`,
    - lifecycle run summary + per-entity candidate records,
    - fail-closed on unsupported `data_class`/invalid params.
  - tests:
    - `truffles-api/tests/test_compliance_lifecycle_service.py`
    - `truffles-api/tests/test_console_compliance_lifecycle.py`
- Slice 3 delivery (`ops orchestration for lifecycle lane`):
  - `console_ops_jobs` catalog extended with `compliance_lifecycle`.
  - `run_ops_job` supports `compliance_lifecycle` trigger path in `dry_run/execute` modes.
  - Ops runner bridges to lifecycle ledger execution with deterministic failure mapping (`ConsoleAPIError` -> failed job payload + audit metadata).
  - deterministic tests:
    - `truffles-api/tests/test_console_ops_jobs.py` (success/failure/audit payload for compliance job type)
    - `truffles-api/tests/test_console_compliance_lifecycle.py` (`_run_compliance_lifecycle_job` scope validation + run-mode mapping)
- Slice 4 delivery (`automation cadence/profile guardrails`):
  - Added lifecycle lane contract (`manual|auto`) with deterministic validation.
  - Added profile presets (`retention_hourly|export_daily|destruction_daily`) for operation/max-items/cadence defaults.
  - Added auto-lane cadence gate: if matching successful run is not due, job returns explicit `skipped=true` payload with `last_run_at` and `next_due_at`.
  - Cadence gate is execute-only (`dry_run` always remains available for diagnostics).
  - Added fail-closed checks:
    - invalid profile rejected,
    - profile/operation mismatch rejected.
  - deterministic tests:
    - `truffles-api/tests/test_console_compliance_lifecycle.py` (auto skip path, due path, invalid profile, mismatch rejection)
- Slice 5 foundation (`execution-action mapping envelope`):
  - Added deterministic `execution_action` mapping in lifecycle service:
    - retention: `retention_scan`,
    - export: `export_preview` (preview) / `export_package` (manual),
    - destruction: `destruction_preview` (preview) and mode-specific manual actions (`deactivate_record|anonymize_record|archive_record`).
  - Lifecycle summary now includes `run_mode` and `execution_action`.
  - Each lifecycle record payload now includes `execution_action` for audit consistency.
  - deterministic tests:
    - `truffles-api/tests/test_compliance_lifecycle_service.py` (preview + manual action mapping coverage).
- Slice 5 implementation (`safe apply-actions path`):
  - Added explicit `apply_actions` gate in ops lifecycle runner:
    - allowed only for `mode=execute`,
    - allowed only for `lane=manual`,
    - requires explicit `reason`.
  - Added rollout controls for mutation lane:
    - `approval_token` is mandatory when `apply_actions=true`,
    - canary cap enforced: `max_items <= 50` for apply-actions.
  - Added apply-action execution outcomes in lifecycle service:
    - summary fields: `apply_actions`, `applied_count`, `skipped_count`, `error_count`,
    - per-record payload fields: `apply_actions`, `applied`, `action_status`, `apply_error` (on failure).
  - Added immutable evidence envelope in lifecycle summary:
    - `evidence_record_count` (number of entity outcomes),
    - `evidence_digest` (SHA-256 over deterministic per-entity outcome tokens).
  - For `learned_responses` manual destruction mode:
    - `delete` -> deactivate record,
    - `anonymize` -> redact question/response + deactivate,
    - `archive` -> mark archived state (`rejected`) + deactivate.
  - deterministic tests:
    - `truffles-api/tests/test_console_compliance_lifecycle.py` (apply-actions guardrails + pass-through),
    - `truffles-api/tests/test_compliance_lifecycle_service.py` (manual apply behavior and counters).
- Slice 6 implementation (`external evidence artifact publication + read API`):
  - Added immutable artifact persistence layer:
    - migration: `truffles-api/migrations/049_add_compliance_lifecycle_artifacts.sql`,
    - model: `truffles-api/app/models/compliance_lifecycle_artifact.py`,
    - service: `truffles-api/app/services/compliance_lifecycle_artifact_service.py`.
  - Artifact publication is executed on every lifecycle run completion (ops + direct endpoint path), with `artifact_id`/`artifact_digest` mirrored into run summary.
  - Added read API:
    - `GET /console/v1/admin/compliance-lifecycle/runs/{run_id}/artifact`.
  - On-demand backfill behavior for legacy runs:
    - if artifact row is missing, endpoint publishes artifact from existing run+records and commits deterministic snapshot.
  - Ops lifecycle result payload now includes `evidence_artifact` reference (`artifact_id`, `artifact_type`, `artifact_digest`, `api_path`).
  - deterministic tests:
    - `truffles-api/tests/test_compliance_lifecycle_artifact_service.py`,
    - `truffles-api/tests/test_console_compliance_lifecycle.py` (artifact endpoint + ops payload assertion).

## Checks + outcomes
- `SESSION_AGENT=a700 scripts/session_check.sh` -> `Session OK`.
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md --graph docs/BLOCK_GRAPH.yaml` -> `zero_context_gate: OK`.
- `cd truffles-api && ruff check app/models/__init__.py app/models/compliance_policy_version.py app/schemas/__init__.py app/schemas/compliance_policy.py app/schemas/console.py app/services/compliance_policy_registry_service.py app/routers/console.py tests/test_compliance_policy_registry_service.py tests/test_console_compliance_policy_registry.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_compliance_policy_registry_service.py tests/test_console_compliance_policy_registry.py tests/test_policy_registry_service.py tests/test_console_policy_registry.py tests/test_sla_profile_registry_service.py tests/test_console_sla_profile_registry.py` -> `25 passed`.
- `cd truffles-api && pytest -q tests/test_compliance_lifecycle_service.py tests/test_console_compliance_lifecycle.py tests/test_compliance_policy_registry_service.py tests/test_console_compliance_policy_registry.py tests/test_policy_registry_service.py tests/test_console_policy_registry.py tests/test_sla_profile_registry_service.py tests/test_console_sla_profile_registry.py` -> `34 passed`.
- `cd truffles-api && pytest -q tests/test_console_ops_jobs.py tests/test_console_compliance_lifecycle.py tests/test_compliance_lifecycle_service.py tests/test_compliance_policy_registry_service.py tests/test_console_compliance_policy_registry.py` -> `32 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass after contract sync (`openapi.v1.yaml` updated).
- `SESSION_AGENT=a700 scripts/session_check.sh` -> `Session OK` (after Slice 4).
- `cd truffles-api && ruff check app/routers/console.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_console_compliance_policy_registry.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `28 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass (no OpenAPI drift after Slice 4).
- `cd truffles-api && ruff check app/services/compliance_lifecycle_service.py tests/test_compliance_lifecycle_service.py app/routers/console.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_compliance_lifecycle_service.py tests/test_console_compliance_policy_registry.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `33 passed`.
- `cd truffles-api && ruff check app/services/compliance_lifecycle_service.py app/routers/console.py tests/test_compliance_lifecycle_service.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `All checks passed` (after apply-actions slice).
- `cd truffles-api && pytest -q tests/test_compliance_lifecycle_service.py tests/test_console_compliance_policy_registry.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `39 passed`.
- `cd truffles-api && ruff check app/models/compliance_lifecycle_artifact.py app/services/compliance_lifecycle_artifact_service.py app/services/compliance_lifecycle_service.py app/routers/console.py app/schemas/console.py tests/test_compliance_lifecycle_artifact_service.py tests/test_compliance_lifecycle_service.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_compliance_lifecycle_artifact_service.py tests/test_compliance_lifecycle_service.py tests/test_console_compliance_policy_registry.py tests/test_console_compliance_lifecycle.py tests/test_console_ops_jobs.py` -> `44 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass after adding lifecycle artifact endpoint to contract.

## Iteration budget outcomes
- `Planned max runs` -> 0 expensive realism runs (analysis/doc sync only).
- `Actual runs` -> 0 expensive realism runs.
- `Stop condition respected` -> yes.
- `If exceeded` -> n/a.

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `https://adilet.zan.kz/eng/docs/Z1300000094`
- `truffles-api/migrations/047_add_compliance_policy_versions.sql`
- `truffles-api/app/services/compliance_policy_registry_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_compliance_policy_registry_service.py`
- `truffles-api/tests/test_console_compliance_policy_registry.py`
- `truffles-api/migrations/048_add_compliance_lifecycle_runs.sql`
- `truffles-api/migrations/049_add_compliance_lifecycle_artifacts.sql`
- `truffles-api/app/models/compliance_lifecycle_artifact.py`
- `truffles-api/app/services/compliance_lifecycle_artifact_service.py`
- `truffles-api/app/services/compliance_lifecycle_service.py`
- `truffles-api/tests/test_compliance_lifecycle_artifact_service.py`
- `truffles-api/tests/test_compliance_lifecycle_service.py`
- `truffles-api/tests/test_console_compliance_lifecycle.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/app/schemas/console.py`
- `contracts/console_api/openapi.v1.yaml`

## Release safety decision
- `Strategy used` -> guarded mutation lane with explicit operator intent (`reason`, `approval_token`, `lane=manual`, `max_items<=50`) plus immutable evidence publication per run.
- `Go/no-go signals observed` -> deterministic tests green + API contract synced + artifact digest/read path available for audit.
- `Rollback readiness` -> revert Slice 4/5/6 commits and disable apply-actions path while keeping preview evidence lane active; keep B11 status `in_progress` until closure checklist is complete.

## Canon/doc sync updates
- `Updated docs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase11-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`

## Residual GAP / Risks
- Data-class coverage risk: incomplete inventory can produce false-positive compliance status.
- Destructive-path risk: policy mistakes can trigger irreversible deletions.
- Process hygiene debt remains non-blocking and must not stall phase11 delivery.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`
- `Do not touch`: unrelated tracks.
- `Open risks`: data-class mapping completeness and destruction safety.
- `First command to verify`: `rg -n "UCPV1-PHASE11|in_progress|phase11-a500" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase11-a500.md`

## Verdict
- `In Progress`
