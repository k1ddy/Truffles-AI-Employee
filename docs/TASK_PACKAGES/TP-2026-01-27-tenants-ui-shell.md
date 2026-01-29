# TP-2026-01-27 — Tenants UI shell (platform_admin)

- **Title/goal:** add a Tenants section in console-web for `platform_admin` by reusing the existing Provisioning Wizard; no backend changes.
- **Canon refs:** `STATE.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/CONSOLE_GUIDE.md`.
- **Invariant:** no backend/DB changes; no permission expansion for non-platform roles; provisioning flow behavior stays the same.
- **Scope:** console-web only — add Tenants nav item, new `/tenants` page, extract Provisioning Wizard to a component and reuse it.
- **Out of scope:** admin list endpoints, tenant search, data migrations, knowledge UX, trace/explain changes, provisioning logic changes.
- **Touch-list:**
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx` (new)
  - `console-web/src/app/settings/page.tsx`
  - `console-web/src/app/tenants/page.tsx` (new)
  - `STATE.md`, `docs/SESSIONS/SESSION-2026-01-27-tenants-ui-shell-a2.md`, `docs/SESSION_INDEX.md`
- **Plan:**
  1) Add GAP to `STATE.md`: Tenants UI missing for `platform_admin` (evidence: no `/tenants` route in console-web).
  2) Add `tenants` to `ConsoleSection` + RBAC (platform_admin only).
  3) Extract `ProvisioningWizard` to `console-web/src/components/ProvisioningWizard.tsx`; keep behavior unchanged.
  4) Update Settings page to use the extracted component.
  5) Create `/tenants` page with AccessDenied gating for non-platform roles.
  6) Update ConsoleShell nav to include Tenants for `platform_admin`.
  7) Run `npm --prefix console-web run lint`.
  8) Update `STATE.md` to DONE with evidence (CI run URL + lint output).
  9) Update session log + `docs/SESSION_INDEX.md`, commit, PR, CI.
- **DoD:**
  - `/tenants` visible only to `platform_admin` and renders the Provisioning Wizard.
  - Settings still works (no behavior change).
  - Lint clean; CI green; `STATE.md` updated with evidence before merge.
- **Checks:** `npm --prefix console-web run lint`
- **Evidence:** CI run URL + lint output; `STATE.md` update in PR.
- **Rollback:** revert PR.
- **No-go:** backend/DB changes; provisioning logic changes; RBAC expansion for non-platform roles.
- **Branch / Worktree:**
  - Branch: `feat/2026-01-27-tenants-ui-shell-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-27-tenants-ui-shell-a2`
  - Base ref: `origin/main`
  - Merge policy: PR (no rebase)
  - Cleanup: delete branch/worktree after merge
- **Risks/Blockers:** extraction could change wizard behavior; mitigate by minimal refactor + lint check.
