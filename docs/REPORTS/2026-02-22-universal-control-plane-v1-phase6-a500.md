# Universal Control Plane v1 - Phase 6 Tool Registry Certification (a500)

Date
- 2026-02-27

## Block identity
- `BLOCK_ID`: UCPV1-PHASE6
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE5
- `UNLOCKS`: UCPV1-PHASE7

## Input baseline (FACT)
- `UCPV1-PHASE5` closed as `passed` and unlocked phase6.
- Runtime had capability allow/deny gate only; no DB-backed tool certification/health/scope contract.
- Console had no platform-admin API for tool registry governance.

## FACT pre-check evidence (before changes)
- `rg -n "resolve_tool_protocol_decision|tool_action_disabled|capability_blocked" truffles-api/app/services/tool_registry_service.py` -> token gate exists.
- `rg -n "tool registry|certif|tool_registry" truffles-api/app/models truffles-api/migrations` -> no tool certification table/model.
- `rg -n "admin/capabilities" truffles-api/app/routers/console.py` -> patch endpoint existed without certification validation.

## One web search evidence
- `Query (exact)` -> `software supply chain policy enforcement certified artifacts allowlist health checks best practices`
- `Sources opened` ->
  - https://cloud.google.com/binary-authorization/docs/overview
  - https://cloud.google.com/binary-authorization/docs/key-concepts
- `Decision` -> reuse existing tool protocol gate and add DB-backed certification/health/scope admission before capabilities activation and runtime tool execution.
- `What was reused` -> existing capability token gate, console RBAC/audit patterns, runtime tool execution contract.

## Root cause validation
- `Symptom` -> uncertified tools were not governed by dedicated registry and could be active via capability token policies.
- `Minimal reproduction` -> inspect runtime+console paths and verify absence of tool registry persistence/validation hooks.
- `Root cause statement` -> missing canonical tool registry entity and missing fail-closed coupling across capabilities and runtime.
- `Proof after fix` -> capabilities patch now rejects blocked tool allow tokens; runtime blocks uncertified/down/scope-mismatched tools with deterministic reason in trace/meta.

## Reuse-first outcome
- `Internal reuse applied` -> yes; existing tool protocol + capabilities + console permission/audit primitives extended.
- `External reuse applied` -> yes; policy admission patterns referenced from Binary Authorization docs.
- `If build-new` -> only missing contract pieces added (model+migration+service+endpoints).

## Contract delta
- Added persistence contract `tool_registry_entries` with certification/health/scope/status metadata.
- Added Console API:
  - `GET /console/v1/admin/tool-registry`
  - `PUT /console/v1/admin/tool-registry/{tool_action}`
- Added capabilities governance contract:
  - `PATCH /console/v1/admin/capabilities` now validates `tools.allow` tokens against certification/health/scope.
- Added runtime contract:
  - `execute_tool_action` enforces tool certification decision before executing action.

## Implemented changes
- `truffles-api/app/models/tool_registry_entry.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/migrations/045_add_tool_registry_entries.sql`
- `truffles-api/app/services/tool_certification_service.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_tool_certification_service.py`
- `truffles-api/tests/test_console_tool_registry.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `contracts/console_api/openapi.v1.yaml`

## Checks + outcomes
- `python3 -m py_compile truffles-api/app/models/tool_registry_entry.py truffles-api/app/services/tool_certification_service.py truffles-api/app/services/tool_registry_service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_console_tool_registry.py truffles-api/tests/test_booking_appointments.py truffles-api/tests/test_console_admin_provisioning.py` -> pass
- `cd truffles-api && ruff check app tests` -> `All checks passed`
- `pytest -q truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_console_tool_registry.py` -> `9 passed`
- `pytest -q truffles-api/tests/test_booking_appointments.py -k "tool_registry"` -> `34 passed, 26 deselected`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "capabilities"` -> `3 passed, 20 deselected`
- `pytest -q truffles-api/tests/test_apply_sql_migrations.py` -> `16 passed`
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> pass (after syncing generated spec into `contracts/console_api/openapi.v1.yaml`)
- `scripts/session_check.sh` -> `zero_context_gate: OK`

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `2` (initial test run found mock-registry fallback defect, second run green)
- `Stop condition respected` -> `yes`
- `If exceeded` -> n/a

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase6-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase6-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `contracts/console_api/openapi.v1.yaml`

## Release safety decision
- `Strategy used` -> phased rollout via platform-admin tool registry updates (tenant-controlled behavior change).
- `Go/no-go signals observed` -> all deterministic checks green and openapi drift resolved.
- `Rollback readiness` -> revert phase6 commit(s) and restore registry entries to `certified/healthy/active`.

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase6-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase6-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift resolved`: `yes` for B06 scope.

## Residual GAP / Risks
- Future additions in static tool catalog must remain synchronized with registry seed/default map.
- Runtime tool registry service remains dense; further decomposition requires dedicated DEC if behavior boundaries change.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (`UCPV1-PHASE7` now unlocked)
- `Do not touch`: unrelated parallel tracks
- `Open risks`: tool catalog/registry sync discipline
- `First command to verify`: `pytest -q truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_console_tool_registry.py`

## Verdict
- `Passed`
