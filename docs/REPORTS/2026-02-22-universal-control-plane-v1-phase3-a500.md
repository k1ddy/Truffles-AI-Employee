# Universal Control Plane v1 — Phase 3 Domain Catalog + Capabilities v2 (a500)

Date
- 2026-02-27

## Block identity
- `BLOCK_ID`: UCPV1-PHASE3
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE2-SLICE2-IMPL2
- `UNLOCKS`: UCPV1-PHASE4

## Input baseline (FACT)
- `UCPV1-PHASE2-SLICE2-IMPL2` passed and unlocked Phase3.
- Current implementation has:
  - client/branch capabilities storage and API,
  - reference pack upsert/list,
  - onboarding blueprint list (static service).
- Missing for B03 DoD:
  - DB-managed domain registry CRUD,
  - domain capability templates in Console governance flow,
  - effective merge layer `global -> domain -> client -> branch`.

## FACT pre-check evidence (before changes)
- `rg -n 'onboarding-blueprints|reference-packs|/admin/capabilities|domain_slug' truffles-api/app/routers/console.py` -> confirms existing endpoints and absence of domain registry CRUD.
- `rg -n 'CapabilitiesPayload|merge_capabilities|domain_slug' truffles-api/app/services/capabilities_service.py truffles-api/app/schemas/capabilities.py` -> confirms merge currently base/override only.

## One web search evidence
- `Query (exact)` -> `schema-driven feature flags configuration hierarchy override precedence`
- `Sources opened`:
  - https://martinfowler.com/articles/feature-toggles.html
  - https://12factor.net/config
  - https://owasp-aasvs4.readthedocs.io/en/latest/V4.1.html
- `Decision` -> reuse existing schema/merge/authorization primitives and add missing domain layer + registry model.
- `What was reused` -> `CapabilitiesPayload`, `merge_capabilities`, `_require_platform_admin`, existing console audit patterns.

## Root cause validation
- `Symptom` -> no domain registry CRUD and no domain-layer in effective capabilities.
- `Minimal reproduction` -> inspect `/admin/capabilities` merge path + search for `/admin/domain-*` registry endpoints.
- `Root cause statement` -> partial governance implementation: client/branch layers exist, domain governance layer missing.
- `Proof after fix` -> domain registry CRUD endpoints added and effective merge now resolves `global -> domain -> client -> branch` with deterministic precedence.

## Reuse-first outcome
- `Internal reuse applied` -> yes (`CapabilitiesPayload`, `merge_capabilities` extension, existing console permission/audit helpers).
- `External reuse applied` -> not required.
- `If build-new` -> n/a.

## Contract delta
- Added domain registry contract:
  - `GET /admin/domain-catalog`
  - `PUT /admin/domain-catalog/{domain_slug}`
  - `DELETE /admin/domain-catalog/{domain_slug}`
- Added domain capability template layer in effective merge path for `/admin/capabilities` and onboarding capability mismatch computation.

## Implemented changes
- `truffles-api/migrations/043_add_domain_capability_templates.sql`
  - new DB table for domain capability templates.
- `truffles-api/app/models/domain_capability_template.py`
  - ORM model for domain registry entries.
- `truffles-api/app/models/__init__.py`
  - model export wiring.
- `truffles-api/app/schemas/console.py`
  - new schemas: `ConsoleDomainCatalogItem/ListResponse/UpsertRequest`.
- `truffles-api/app/services/capabilities_service.py`
  - new helper `merge_capabilities_layers(...)`.
- `truffles-api/app/routers/console.py`
  - domain template read/serialize helpers.
  - new domain catalog CRUD endpoints (platform-admin only).
  - effective capabilities merge switched to domain-aware layering.
- `truffles-api/tests/test_console_domain_catalog.py`
  - deterministic tests for access control, upsert validation, merge precedence.
- `SPECS/CONTROL_PLANE.md`
  - canon sync for domain catalog API boundary.

## Checks + outcomes
- `python3 -m py_compile truffles-api/app/models/domain_capability_template.py truffles-api/app/services/capabilities_service.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_domain_catalog.py`
  - pass
- `pytest -q truffles-api/tests/test_console_domain_catalog.py`
  - pass (`4 passed`)
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "capabilities or platform_admin"`
  - pass (`5 passed, 17 deselected`)
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py -k "capability or onboarding"`
  - pass (`13 passed`)

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `3`
- `Stop condition respected` -> `yes`
- `If exceeded` -> n/a

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase3-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase3-a500.md`
- `truffles-api/migrations/043_add_domain_capability_templates.sql`
- `truffles-api/app/models/domain_capability_template.py`
- `truffles-api/app/services/capabilities_service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_domain_catalog.py`
- `SPECS/CONTROL_PLANE.md`

## Release safety decision
- `Strategy used` -> phased rollout (platform-admin canary first).
- `Go/no-go signals observed` -> access control and merge precedence validated by deterministic suites; no regressions in touched provisioning/onboarding tests.
- `Rollback readiness` -> single-commit revert path verified.

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase3-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase3-a500.md`
  - `SPECS/CONTROL_PLANE.md`
  - `docs/BLOCK_GRAPH.yaml`
- `Drift resolved`: `yes`
- `If no`: n/a

## Residual GAP / Risks
- Existing tenants without `domain_slug` fallback to pre-existing behavior (domain layer not applied), which is intentional compatibility mode.
- Lifecycle migration for historical domains into `domain_capability_templates` can be extended in later phases if needed.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (`UCPV1-PHASE4` is next unlocked block)
- `Do not touch`: unrelated marketing/branch-change flows
- `Open risks`: backward compatibility for empty-domain tenants
- `First command to verify`: `pytest -q truffles-api/tests/test_console_domain_catalog.py`

## Verdict
- `Passed`
