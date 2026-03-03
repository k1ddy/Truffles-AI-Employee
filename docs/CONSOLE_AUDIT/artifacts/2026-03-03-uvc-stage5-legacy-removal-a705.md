# UVC Stage 5 Legacy Removal Checklist (a705)

Date: `2026-03-03`
Parent TP: `TP-2026-03-03-uvc-ux-stage5-rollout-efficiency-a705.md`

## Scope
- `console-web/src/app/tenants/**`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/e2e/platform-admin.spec.ts`

## Inventory command
- Command: `rg -n "legacy|fallback|disabled|temporary|TODO" console-web/src/app/tenants console-web/src/app/integrations/page.tsx console-web/src/app/company-workspace/page.tsx console-web/src/components/OpsPage.tsx`
- Snapshot: `/tmp/uvc_stage5_legacy_scan_a705.txt`
- Raw hits: `49`

## Classification
- `disabled` hits: UI safety guards for scope/permissions/loading states; это не legacy-path и не дубли.
- `fallbackGuide` in Ops: internal incident helper name, не пользовательский термин и не alternate runtime path.
- `active_fallback_best_candidate` key: backend reason code contract (machine key); ключ сохранён как API-compatible.

## Removals/normalization completed
- Removed mixed-language user text (`fallback/live`) from primary UX labels:
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/tenants/tenants-page-helpers.ts`
- Resulting labels are business-readable and plain-language:
  - `сигналы активных филиалов`
  - `резервный выбор активного филиала`

## Duplicate/ownership checks
- `Integrations` remains fact/handoff layer only (no execute-level reconcile call in page runtime path).
- `Company Workspace` remains execute layer.
- `Tenants` remains provisioning/lifecycle layer.
- `Ops` remains incident/health/run center.
- Ownership contract enforced by `check:uvc-antidrift`.

## Regression guard result
- `npm --prefix console-web run check:uvc-antidrift` -> pass.
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm --prefix console-web run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"` -> `26 passed`.

## Open residuals
- Нет блокирующих legacy-path controls в primary UVC loop на текущем scope.
- Остаток: технический reason-code ключ `active_fallback_best_candidate` оставлен намеренно ради API compatibility; UX текст при этом нормализован.
