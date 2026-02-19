# 2026-02-19 Onboarding Blueprint v1 (a131)

## Scope

- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-blueprint-v1-a131.md`
- Branch: `feat/2026-02-19-onboarding-blueprint-v1-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-blueprint-v1-a131`

## Delivery

- Added backend blueprint registry: `truffles-api/app/services/onboarding_blueprints.py`.
  - Canonical templates for `beauty`, `clinic`, `legal`, `ecom`.
  - Domain payload presets, go-live blocker profiles, question templates.
- Added admin API endpoint `GET /console/v1/admin/onboarding-blueprints`.
  - Supports optional `domain_slug` filter.
  - Returns typed blueprint payload including `question_templates` and `go_live_blockers_profile`.
- Extended intake question queue with domain-aware templates.
  - `build_intake_question_queue(..., domain_slug=...)` now resolves question text through blueprint templates first.
- Switched Provisioning Wizard to backend-driven templates.
  - UI now fetches blueprints from API and applies selected preset.
  - Fallback presets remain only for temporary backend unavailability.
- Updated OpenAPI contract with new onboarding-blueprints endpoint and response schemas.

## Checks (fact)

- `python3 -m py_compile truffles-api/app/services/onboarding_blueprints.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py`
  - result: pass
- `ruff check truffles-api/app/services/onboarding_blueprints.py truffles-api/app/services/onboarding_intake_service.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_onboarding_intake_service.py`
  - result: pass
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_blueprints"`
  - result: `3 passed`
- `pytest -q truffles-api/tests/test_onboarding_intake_service.py`
  - result: `16 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check`
  - result: pass (path/method drift not detected)
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/lib/api-client.ts`
  - result: pass
- `npm --prefix console-web run build`
  - result: pass

## Behavior Contract

- Source-of-truth for onboarding domain templates moved to backend service, not UI constant list.
- Provisioning template application remains backward-compatible for payload semantics.
- Intake auto-questions become domain-scoped without changing required-field contract logic.
