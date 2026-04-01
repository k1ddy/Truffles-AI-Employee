# TP-2026-01-30-console-ui-unblock

- Title/goal: Unblock Console UI clicks after admin/admin login in Chrome (selection gate visible but unclickable).
- Canon refs: `AGENTS.md`, `STATE.md` (add GAP entry), `SPECS/CONTROL_PLANE.md`, `TECH.md`.
- Invariant: RBAC + selection gating logic stays unchanged; no auth/Keycloak changes.
- Scope: Console UI CSS/overlay behavior only.
- Out of scope: Console API, Keycloak, DB, RBAC policy changes.
- Touch-list (files/tables): `console-web/src/app/globals.css` (primary), `console-web/src/components/ConsoleShell.tsx` (only if required).
- Plan:
  1) Reproduce symptom in Chrome and confirm click-blocking layer via CSS/DOM inspection.
  2) Move noise overlay behind app content (no pointer blocking).
  3) Verify selection gate is clickable after login.
  4) Run Playwright login smoke for evidence.
  5) Record GAP resolution in `STATE.md` with evidence.
- DoD:
  - admin/admin can interact with selection gate in Chrome.
  - No regression in navigation and RBAC gating.
  - Playwright login smoke passes against prod.
- Checks:
  - `PLAYWRIGHT_BASE_URL=https://console.truffles.kz PLAYWRIGHT_WEB_SERVER=0 E2E_USERNAME=admin E2E_PASSWORD=admin npx playwright test login.spec.ts --project=chromium-login --reporter=line`
- Evidence:
  - Playwright output + (if needed) screenshot; `STATE.md` entry updated by Top Architect.
- Rollback:
  - Revert CSS change and redeploy console-web.
- No-go:
  - No changes to API auth, RBAC matrices, or Keycloak config.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-01-30-console-ui-unblock-a1`
  - Worktree: `/home/zhan/worktrees/2026-01-30-console-ui-unblock-a1`
  - Base ref: `origin/main`
  - Merge policy: PR to `main` (no rebase)
  - Cleanup: remove worktree/branch after merge
- Risks/Blockers:
  - If issue is caused by browser extension/CSS injection, code change may not fully resolve.
