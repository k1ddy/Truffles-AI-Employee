Title: Org-level tenancy (Company -> Client -> Branch) + RBAC
Owner: Brain (handoff to Top Architect for DEC alignment)
Date: 2026-01-22

Canon refs:
- docs/IMPERIUM_DECISIONS.yaml (DEC-011)
- SPECS/MULTI_TENANT.md (scope and target model)
- STATE.md (NOW/GAP entry to be updated by Brain)

Invariant:
- No cross-tenant access (company/client/branch data isolation).
- Existing single-client users continue to work without regression.
- Core webhook/decision pipeline is untouched.

Scope:
- Add membership/RBAC model for Company/Client/Branch.
- Extend console auth context to include company/client/branch.
- Require explicit tenant_context on console mutations and audit events.
- Update Console API contracts and UI to select client/branch when needed.
- Tenant-scoping tests (unit + contract).

Out of scope:
- CRM/Calendar integrations.
- Changes to core decision logic or packs.
- Provider/channel migrations.

Touch-list (files/tables):
- truffles-api/app/models/* (new membership tables)
- truffles-api/migrations/*.sql (new schema)
- truffles-api/app/services/console_auth.py
- truffles-api/app/routers/console.py
- truffles-api/app/schemas/console.py
- contracts/console_api/openapi.v1.yaml
- contracts/console_api/errors.v1.json
- console-web/src/app/*
- console-web/src/components/*
- console-web/src/lib/*
- docs/CONSOLE_GUIDE.md
- SPECS/MULTI_TENANT.md
- STRATEGY/TECH_ROADMAP.md

Plan:
1) Data model + migration (company_memberships, roles, branch_scopes).
2) Auth context: resolve memberships, enforce tenant_context.
3) API changes: /me includes memberships; mutations require tenant_context.
4) UI: selection flow for company/client/branch; persist selection.
5) Contracts + docs updates.
6) Tests: tenant-scoping unit tests + console contract + e2e smoke.

DoD:
- Owner can see multiple clients/branches via /me.
- Branch-scoped users cannot access other branches (403).
- Console contract updated; CI green.
- Evidence recorded in STATE.md by Brain/Top Architect.

Checks:
- console-e2e (Playwright smoke)
- console-contract (Schemathesis GET-only)
- unit tests for tenant scoping (new)

Evidence:
- CI run URL + logs.
- SQL or trace evidence if required.
- STATE.md updated by Brain/Top Architect.

Rollback:
- Revert migration + code changes.
- Restore prior /me contract and auth logic.

No-go:
- Hardcoded tenant IDs.
- Silent changes to core pipeline.
- Bypassing auth/tenant checks in console API.

Risks/Blockers:
- Existing OIDC sub mapping to agents without membership rows.
- Migration of legacy admins to new membership tables.
- Data backfill timing vs UI rollout.

Branch/Worktree:
- Branch: feature/org-level-tenancy
- Worktree: /home/zhan/worktrees/org-level-tenancy
- Base: main
- Merge policy: PR only, no rebase
