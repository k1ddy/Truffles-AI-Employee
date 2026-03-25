# 2026-02-20 Tenants A11y Evidence (a201)

## Scope
- Page: `https://console.truffles.kz/tenants`
- Role lane: `platform_admin`
- Devices: desktop + mobile viewport
- Method: Playwright e2e + Axe scan with saved artifacts

## Commands
```bash
cd console-web
npx playwright install chromium
PLAYWRIGHT_WEB_SERVER=0 \
PLAYWRIGHT_BASE_URL=https://console.truffles.kz \
E2E_USE_STORAGE_STATE=1 \
E2E_USERNAME=admin \
E2E_PASSWORD=admin \
npx playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=list
```

## Run Result
- Status: `PASS` (2/2 tests)
- Duration: `~47s`
- Note: threshold gate (`critical=0`, `serious=0`) collected as metrics; hard-fail mode is available via `A11Y_FAIL_ON_THRESHOLDS=1`.

## Strict Threshold Recheck
```bash
cd console-web
PLAYWRIGHT_WEB_SERVER=0 \
PLAYWRIGHT_BASE_URL=https://console.truffles.kz \
E2E_USE_STORAGE_STATE=1 \
E2E_USERNAME=admin \
E2E_PASSWORD=admin \
A11Y_FAIL_ON_THRESHOLDS=1 \
npx playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=list
```

- Status: `FAIL` (expected for live recheck before deploy)
- Failure reason: live `console.truffles.kz` still returns `critical=2`, `serious=1`; branch code fixes are not deployed yet.

## Artifacts
- Desktop screenshot: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop.png`
- Mobile screenshot: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile.png`
- Desktop axe JSON: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop-axe.json`
- Mobile axe JSON: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile-axe.json`

## Axe Summary
- Desktop: `critical=2`, `serious=1`, `moderate=0`, `minor=0`
- Mobile: `critical=2`, `serious=1`, `moderate=0`, `minor=0`

## Top Violations (both desktop/mobile)
1. `select-name` (`critical`)
- Patterns: tenants filters and onboarding/provisioning selects under Tenants workspace.
- Evidence selectors: `.justify-end > select:nth-child(2)`, `select:nth-child(3)`, `select:nth-child(4)`, `.md\\:grid-cols-2 > select`, `.grid-cols-1.md\\:grid-cols-3.grid > select:nth-child(2)`, `select:nth-child(7)`.

2. `label` (`critical`)
- Patterns: date inputs in provider binding/autopilot blocks.
- Evidence selectors: `.w-full[type="date"][value=""]:nth-child(3|5|6)`.

3. `color-contrast` (`serious`)
- Patterns: guide/help muted texts and context hint lines.
- Evidence selectors include `div[data-testid="tenants-workspace-guide"]` text rows and several muted small-text rows.

## Correlation to Current Code
- Recent fixes reduced part of missing names, but live page still exposes unnamed `select`/`date` in the rendered DOM. The remaining issues likely come from additional controls outside the already patched subset in:
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
- Contrast findings align with muted helper text clusters in Tenants and context header.
