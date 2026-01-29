# TP-2026-01-29-tenants-list-api

Title/Goal
- Add Tenants list API with pagination so platform_admin can see all tenants without context selection, and wire Tenants UI to it.

Invariant
- RBAC remains strict; list endpoints are platform_admin-only.
- No core pipeline changes (trace/meta/outbox/routing).
- No DB migrations or prod data changes.

Scope
- Add GET /console/v1/admin/companies, /admin/clients, /admin/branches with cursor/limit/q and filters (company_id/client_id).
- Return paginated list responses (items/cursor/has_more).
- Update OpenAPI and regenerate TS types.
- Update Tenants UI to use list API with pagination.
- Add unit tests for list filtering/validation logic.

Out of scope
- Tenants CRUD write changes beyond existing endpoints.
- UX hiding technical fields (Advanced view).
- Trace/Explain v2.
- DB constraints/migrations.

Touch-list
- truffles-api/app/routers/console.py
- truffles-api/app/schemas/console.py
- truffles-api/tests/test_console_tenants_list.py
- contracts/console_api/openapi.v1.yaml
- console-web/src/lib/api-client.ts
- console-web/src/app/tenants/page.tsx
- console-web/src/types/api.generated.ts
- docs/SESSIONS/*
- docs/SESSION_INDEX.md
- STATE.md (evidence)

Plan
1) Add list response schemas (companies/clients/branches).
2) Implement list endpoints with RBAC and query validation.
3) Update OpenAPI and regenerate types.
4) Wire Tenants UI to list API + pagination.
5) Add unit test(s).
6) Run checks.
7) Capture evidence; update STATE.md.

DoD
- platform_admin can list all companies/clients/branches without context headers.
- list endpoints support cursor/limit/q and filters.
- Tenants UI uses list API and paginates.
- Tests and lint pass (or waiver noted in TP if blocked).

Checks
- pytest -q truffles-api/tests/test_console_tenants_list.py
- npm --prefix console-web run lint

Evidence
- Test outputs (stdout or log files).
- Screenshot of Tenants list with >1 company/client (path recorded).
- Update STATE.md with evidence pointers.

Rollback
- git revert HEAD

No-go
- CI red, unexpected diff, missing evidence, or API returns mixed-tenant data.

Branch
- feat/2026-01-29-tenants-list-api-a2

Worktree path
- /home/zhan/worktrees/2026-01-29-tenants-list-api-a2

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Must ignore selection headers for list endpoints to show all tenants to platform_admin.
- Cursor collisions on identical created_at values (accept for now; monitor).
