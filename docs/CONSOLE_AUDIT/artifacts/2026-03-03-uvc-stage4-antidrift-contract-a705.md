# UVC Stage 4 Anti-Drift Contract (a705)

Date: `2026-03-03`
Parent TP: `TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705.md`

## Goal
Зафиксировать fail-closed quality контракт, который блокирует merge при дрейфе между OpenAPI, сгенерированными типами, frontend API bindings и UVC loop e2e контрактами.

## Contract Matrix

| Contract area | Gate type | Fail condition | Evidence source |
|---|---|---|---|
| OpenAPI schema validity | deterministic | `openapi.v1.yaml` невалиден | CI `console-contract-predeploy` |
| OpenAPI -> generated TS sync | deterministic | `src/types/api.generated.ts` отличается от `openapi-typescript` snapshot | `npm run check:uvc-antidrift` |
| Control Tower endpoint presence | deterministic | отсутствуют critical `/admin/control-tower/*` пути в OpenAPI/TS/api-client | `check-uvc-antidrift.mjs` |
| Stage 2/3 selector continuity | deterministic | отсутствует selector в UI или e2e | `check-uvc-antidrift.mjs` |
| Stage 3 loop suite coverage | deterministic | отсутствует named suite (`Navigation`, `Tenants`, `Integrations`) | `platform-admin.spec.ts` + anti-drift script |
| Ownership anti-dup guard | deterministic | execute action появляется в `Integrations` code path | `check-uvc-antidrift.mjs` |

## Required selectors
- `integrations-open-workspace-scope`
- `integrations-workspace-guidance`
- `workspace-next-step-ops`
- `workspace-empty-next-steps`
- `workspace-return-tenants`
- `workspace-return-integrations`
- `tenants-onboarding-loop-hint`
- `tenants-onboarding-open-ops`
- `ops-back-workspace`
- `ops-back-tenants`

## Required suites
- `Platform Admin Navigation`
- `Platform Admin Tenants`
- `Platform Admin Integrations`

## CI fail-closed wiring
- Job: `console-contract-predeploy`
- Mandatory steps:
  - `Validate console OpenAPI`
  - `npm --prefix console-web run check:uvc-antidrift`
- Result: PR cannot pass when anti-drift contract fails.

## Local commands
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run check:uvc-antidrift`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`

## Files in scope
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/scripts/check-uvc-antidrift.mjs`
- `.github/workflows/ci.yml`
