# Universal Control Plane v1 — Phase 2 Slice 2 Implementation Wave 2 (a500)

Date
- 2026-02-27

## Block identity
- `BLOCK_ID`: UCPV1-PHASE2-SLICE2-IMPL2
- `PARENT_BLOCK_ID`: UCPV1-PHASE2
- `DEPENDS_ON`: UCPV1-GATES-SANITARY
- `UNLOCKS`: UCPV1-PHASE3

## Input baseline (FACT)
- `UCPV1-PHASE2-SLICE2-IMPL1` закрыл platform-admin boundary для `onboarding-blueprints` и `reference-packs`.
- В `console.py` остались onboarding governance handlers, которые используют generic provisioning permission и не имеют explicit platform-admin gate:
  - `/admin/onboarding-contract`
  - `/admin/webhook-secret`
  - `/admin/onboarding/autopilot`

## FACT pre-check evidence (before changes)
- `rg -n '"/admin/(onboarding-contract|webhook-secret|onboarding/autopilot)"|require_console_permission\\(|_require_platform_admin\\(' truffles-api/app/routers/console.py` -> target handlers confirmed on generic `require_console_permission`.
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py` -> `9 passed in 5.16s`.
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "run_onboarding_autopilot or webhook_secret"` -> `6 passed, 38 deselected in 5.26s`.

## One web search evidence
- `Query (exact)` -> `OWASP ASVS access control deny by default least privilege`
- `Sources opened`:
  - https://owasp-aasvs4.readthedocs.io/en/latest/V4.1.html
  - https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/
  - https://top10proactive.owasp.org/the-top-10/c1-accesscontrol/
- `Decision` -> `reuse + integrate` existing `_require_platform_admin` guard for onboarding governance handlers.
- `What was reused` -> existing console auth boundary primitives and current deterministic test patterns.

## Root cause validation
- `Symptom` -> governance endpoints are broader than Platform Admin First contract.
- `Minimal reproduction` -> inspect target handlers in `console.py`; verify no explicit `_require_platform_admin`.
- `Root cause statement` -> partial migration from generic provisioning guard to explicit governance hard-gates.
- `Proof after fix` -> explicit `_require_platform_admin` added on all four target handlers and deny tests for non-platform roles added/passing.

## Reuse-first outcome
- `Internal reuse applied` -> yes (`_require_platform_admin`, existing endpoint/test structure).
- `External reuse applied` -> not required.
- `If build-new` -> n/a.

## Contract delta
- Onboarding governance endpoints moved from generic provisioning boundary to explicit platform-admin hard-gate:
  - `GET|PATCH /admin/onboarding-contract`
  - `GET /admin/webhook-secret`
  - `POST /admin/onboarding/autopilot`

## Implemented changes
- `truffles-api/app/routers/console.py`
  - Added `_require_platform_admin(context)` in:
    - `get_onboarding_contract`
    - `patch_onboarding_contract`
    - `get_webhook_secret`
    - `run_onboarding_autopilot`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
  - Added:
    - `test_patch_onboarding_contract_requires_platform_admin`
    - `test_get_onboarding_contract_requires_platform_admin`
    - `test_get_webhook_secret_requires_platform_admin`
    - `test_run_onboarding_autopilot_requires_platform_admin`
  - Updated happy-path role context for governance tests to `platform_admin` where required by new contract.
- `SPECS/CONTROL_PLANE.md`
  - Synced canon: onboarding governance/control endpoints are platform-admin-only.

## Checks + outcomes
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_contract_api.py truffles-api/tests/test_console_access_admin_pr2.py`
  - pass
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
  - pass (`13 passed`)
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "run_onboarding_autopilot or webhook_secret or onboarding_contract"`
  - pass (`6 passed, 38 deselected`)
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "platform_admin or onboarding"`
  - pass (`5 passed, 17 deselected`)

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `3`
- `Stop condition respected` -> `yes`
- `If exceeded` -> n/a

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `SPECS/CONTROL_PLANE.md`

## Release safety decision
- `Strategy used` -> phased rollout (platform-admin canary tenant first).
- `Go/no-go signals observed` -> deterministic deny/allow contract confirmed in targeted tests; no regressions in touched provisioning suites.
- `Rollback readiness` -> verified via single-commit revert path (router + tests + spec sync).

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`
  - `SPECS/CONTROL_PLANE.md`
- `Drift resolved`: `yes`
- `If no`: n/a

## Residual GAP / Risks
- Owner/admin operational dependency on these governance endpoints now intentionally fail-closed by contract; rollout communication is required.
- Remaining Phase 2 boundary topics outside this block (`branch-changes`, memberships lifecycle semantics) move to later phases.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (mark block status and unlock next)
- `Do not touch`: unrelated `/admin/branch-changes*` and identity/membership flows in this block
- `Open risks`: onboarding governance behavior shift for non-platform roles
- `First command to verify`: `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`

## Verdict
- `Passed`
