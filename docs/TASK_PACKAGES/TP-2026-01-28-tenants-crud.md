# TP-2026-01-28 — Tenants CRUD (read-write)

- Title/goal: enable platform_admin to edit companies/clients/branches via Tenants, with confirmation safeguards and API+UI coverage.
- Canon refs: `STATE.md` (NOW: Tenants CRUD missing), `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`, `STRATEGY/TECH_ROADMAP.md`. CA_ID: n/a.
- Invariant: RBAC remains platform_admin-only for Tenants; selection gates stay fail-closed; destructive changes require confirmation; no DB schema changes.
- Scope: add PATCH endpoints for companies/clients, update console schemas + OpenAPI, regenerate API types, implement Tenants create/edit flows in console-web, add tests.
- Out of scope: delete endpoints; capabilities changes; onboarding logic changes; non-platform roles; DB migrations; Knowledge/Inbox UX.
- Touch-list:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `truffles-api/tests/test_console_admin_provisioning.py`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/types/api.generated.ts`
  - `docs/TASK_PACKAGES/TP-2026-01-28-tenants-crud.md`
  - `docs/SESSIONS/SESSION-2026-01-28-tenants-crud-a2.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- Plan:
  1) Add GAP to `STATE.md`: Tenants CRUD (read-write) missing for platform_admin.
  2) Backend: add PATCH `/admin/companies/{company_id}` + `/admin/clients/{client_id}` with validation + audit; update schemas + OpenAPI.
  3) Frontend: add `adminApi.patchCompany`/`patchClient`, implement edit actions in Tenants UI; use confirmations for branch deactivate.
  4) Regenerate API types and fix any compile issues.
  5) Add pytest coverage for new endpoints and RBAC.
  6) Run checks.
  7) Update `STATE.md` with evidence + session log/index; open PR and CI.
- DoD:
  - platform_admin can create/edit company/client/branch from Tenants.
  - branch deactivation or instance_id removal requires confirmation.
  - OpenAPI + generated types updated; tests pass; CI green.
  - `STATE.md` updated with evidence before merge.
- Checks:
  - `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint`
- Evidence: CI run URL + pytest output + lint output + optional UI screenshot; `STATE.md` updated pre-merge (Brain/Top Architect).
- Rollback: revert PR.
- No-go: RBAC expansion beyond platform_admin; bypassing selection gates; DB schema changes; destructive actions without confirmations; manual DB edits.
- Branch / Worktree:
  - Branch: `feat/2026-01-28-tenants-crud-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-tenants-crud-a2`
  - Base ref: `origin/main`
  - Merge policy: PR only (no rebase)
  - Cleanup: delete branch/worktree after merge
- Risks/Blockers: OpenAPI/typegen drift; ensure tests exist and pass.
