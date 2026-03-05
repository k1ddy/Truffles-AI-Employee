# Web Console Audit (implemented UI)

Scope
- Implementation-backed inventory of the Web Console (UI + API + data flows).
- Only implemented behavior is documented; canon/plan items are excluded.

Sources (code-backed)
- UI shell + nav: `console-web/src/components/ConsoleShell.tsx`
- Pages: `console-web/src/app/*/page.tsx`, `console-web/src/components/*`
- Console API: `truffles-api/app/routers/console.py`
- Calendar API: `truffles-api/app/routers/calendar.py`
- Auth/RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
- Proxy/auth: `console-web/src/app/api/proxy/[...path]/route.ts`, `console-web/src/lib/auth.ts`

How to use
- Start with Roles to see navigation and access per role.
- Use Pages for UI element-level behavior and endpoints.
- Use System notes for cross-component flows (WhatsApp/Telegram/outbox/knowledge).
- Use Canon vs Implemented for gap tracking against Control Plane canon.

Comparison
- `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`

Reports
- `docs/REPORTS/2026-02-01-console-web-fact-audit.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v1.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`
- `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave1-implementation-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave2-data-trust-team-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave3-simple-settings-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave4-action-loop-v1.md`

Artifacts
- `docs/CONSOLE_AUDIT/artifacts/2026-03-02-uvc-stage1-ia-matrix-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage2-language-glossary-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage3-flow-matrix-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage4-antidrift-contract-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-rollout-report-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-legacy-removal-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-program-closeout-steady-loop-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-steady-state-operations-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-operations-governance-closeout-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-tech-debt-decomposition-wave1-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave2-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave3-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closeout-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave4-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-close-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave5-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave6-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review2-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave7-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-review3-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave8-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review4-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave9-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review5-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave10-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review6-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave11-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review7-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave12-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review8-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave13-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review9-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave14-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review10-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave15-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review11-a705.md`

Backlog
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

Roles
- `docs/CONSOLE_AUDIT/roles/platform_admin.md`
- `docs/CONSOLE_AUDIT/roles/owner.md`
- `docs/CONSOLE_AUDIT/roles/admin.md`
- `docs/CONSOLE_AUDIT/roles/manager.md`
- `docs/CONSOLE_AUDIT/roles/support.md`

Pages
- `docs/CONSOLE_AUDIT/pages/global-shell.md`
- `docs/CONSOLE_AUDIT/pages/inbox.md`
- `docs/CONSOLE_AUDIT/pages/case-detail.md`
- `docs/CONSOLE_AUDIT/pages/calendar.md`
- `docs/CONSOLE_AUDIT/pages/knowledge.md`
- `docs/CONSOLE_AUDIT/pages/team.md`
- `docs/CONSOLE_AUDIT/pages/settings.md`
- `docs/CONSOLE_AUDIT/pages/audit.md`
- `docs/CONSOLE_AUDIT/pages/ops.md`
- `docs/CONSOLE_AUDIT/pages/insights.md`
- `docs/CONSOLE_AUDIT/pages/business.md`
- `docs/CONSOLE_AUDIT/pages/business-data-trust.md`
- `docs/CONSOLE_AUDIT/pages/business-team-performance.md`
- `docs/CONSOLE_AUDIT/pages/subscription.md`
- `docs/CONSOLE_AUDIT/pages/marketing.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`

System
- `docs/CONSOLE_AUDIT/system/auth-and-proxy.md`
- `docs/CONSOLE_AUDIT/system/integrations-and-data.md`

Maintenance
- Update the relevant role/page doc when UI text, actions, or endpoints change.
- Add new pages to the Pages list and link to code in the new doc.
