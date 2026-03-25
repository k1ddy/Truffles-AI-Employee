# Universal Control Plane v1 - Phase 5 Policy Governance Split (a500)

Date
- 2026-02-27

## Block identity
- `BLOCK_ID`: UCPV1-PHASE5
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE4
- `UNLOCKS`: UCPV1-PHASE6

## Input baseline (FACT)
- `UCPV1-PHASE4` closed as `passed`; `UCPV1-PHASE5` was `in_progress` with wave2 gap.
- Wave1 was already in place: capabilities operational override contract + runtime hard-law deny.
- Missing acceptance item before this session: versioned policy registry CRUD + rollback/pin contract.

## FACT pre-check evidence (before changes)
- `rg -n "@router\\.(get|post|patch|delete)\\(\"/admin/.+policy" truffles-api/app/routers/console.py` -> no policy registry endpoints.
- `rg -n "policy_overrides|_get_policy_pack|_resolve_hard_law_sections" truffles-api/app/schemas/capabilities.py truffles-api/app/routers/webhook/policy.py` -> wave1 boundary contract present, no versioned registry.
- `docs/BLOCK_GRAPH.yaml` -> `UCPV1-PHASE5: in_progress`.

## One web search evidence
- `Query (exact)` -> `policy as code versioning rollback best practices open policy agent`
- `Sources opened`:
  - https://www.openpolicyagent.org/docs/management
  - https://www.openpolicyagent.org/docs/deploy
- `Decision` -> keep reuse-first approach: extend existing runtime boundary and Console contracts; do not introduce new policy engine.

## Root cause validation
- `Root cause` -> no versioned operational policy lifecycle in Console/runtime path.
- `Closure mechanism`:
  - added `client_policy_versions` table + model + service (`publish/history/rollback`);
  - added platform-admin Console API for policy registry lifecycle;
  - connected runtime `_get_policy_pack` to effective policy registry overrides (branch first, client fallback), preserving hard-law deny.

## Reuse-first outcome
- `Internal reuse applied` -> yes; reused existing capability/runtime policy boundary and audit patterns from Console modules.
- `External reuse applied` -> yes; OPA governance patterns used as design reference without adding runtime dependencies.
- `If build-new` -> not applicable; no new policy engine introduced.

## Contract delta
- New versioned entity: `client_policy_versions` (`scope=client|branch`, `status=published|archived`, `version_number`, `source_version_id`).
- New Console API:
  - `GET /console/v1/admin/policy-registry`
  - `POST /console/v1/admin/policy-registry/publish`
  - `POST /console/v1/admin/policy-registry/rollback`
- Runtime policy merge order:
  - base policy pack
  - registry effective operational overrides
  - capability runtime operational overrides
  - hard-law sections remain non-overridable.

## Implemented changes
- `truffles-api/app/models/client_policy_version.py`
- `truffles-api/migrations/044_add_client_policy_versions.sql`
- `truffles-api/app/services/policy_registry_service.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_policy_registry_service.py`
- `truffles-api/tests/test_console_policy_registry.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `contracts/console_api/openapi.v1.yaml`

## Checks + outcomes
- `python3 -m py_compile truffles-api/app/models/client_policy_version.py truffles-api/app/services/policy_registry_service.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py` -> pass
- `pytest -q truffles-api/tests/test_policy_registry_service.py truffles-api/tests/test_console_policy_registry.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_console_onboarding_contract_api.py truffles-api/tests/test_console_domain_catalog.py` -> `36 passed in 3.45s`
- `pytest -q truffles-api/tests/test_apply_sql_migrations.py` -> `16 passed in 0.06s`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `1` (single implementation cycle, single validation cycle)
- `Stop condition respected` -> `yes`
- `If exceeded` -> n/a

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase5-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`

## Release safety decision
- `Strategy` -> tenant-scoped rollout through policy registry publish (client/branch).
- `Go/no-go` -> all deterministic checks green; openapi drift gate green; hard-law deny path covered.
- `Rollback` -> explicit `POST /admin/policy-registry/rollback` + commit revert fallback.

## Canon/doc sync updates
- Updated:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase5-a500.md`
  - `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase5-a500.md`
  - `docs/SESSION_INDEX.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift resolved`: `yes` for B05 acceptance scope.

## Residual GAP / Risks
- Operational override allow-list remains intentionally narrow (`payment_info`, `discounts`) pending future domain expansion review.
- `webhook/policy.py` remains high-coupling area; follow-up refactors require dedicated DEC if architecture changes.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (`UCPV1-PHASE6` unlocked)
- `Do not touch`: unrelated parallel tracks
- `First command to verify`: `pytest -q truffles-api/tests/test_policy_registry_service.py truffles-api/tests/test_console_policy_registry.py`

## Verdict
- `Passed`
