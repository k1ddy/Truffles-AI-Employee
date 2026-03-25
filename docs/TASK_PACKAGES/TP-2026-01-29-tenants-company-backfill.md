Title: Tenants: company backfill + require company_id for new clients

Invariant
- All clients must belong to a company; no new clients can be created without company_id.
- Global admin visibility across tenants remains intact.
- No changes to core messaging pipeline behavior.

Scope
- Create Company "Truffles Corp" and backfill existing clients (demo_salon, truffles, demo_salon_script_test).
- Enforce company_id required in client creation (API + UI).
- Update Console API contract + generated types.

Out of scope
- DB constraint (NOT NULL) on clients.company_id (deferred).
- Trace/Explain v2.
- Tenants CRUD delete flows.
- Full Tenants list API with pagination (separate TP).

Touch-list
- truffles-api/app/routers/console.py
- truffles-api/app/schemas/console.py
- contracts/console_api/openapi.v1.yaml
- console-web/src/components/ProvisioningWizard.tsx
- console-web/src/lib/api-client.ts
- console-web/src/types/api.generated.ts
- truffles-api/tests/test_console_admin_provisioning.py
- docs/SESSIONS/SESSION-2026-01-29-tenants-company-backfill-a2.md
- docs/SESSION_INDEX.md
- STATE.md

Plan
1) Create Company "Truffles Corp" in DB and backfill client.company_id for demo_salon, truffles, demo_salon_script_test.
2) Require company_id in ConsoleClientCreateRequest + server validation.
3) Update UI to require company selection before client creation.
4) Regenerate OpenAPI types.
5) Add/adjust tests for create_client validation.
6) Verify via SQL and Tenants UI snapshot.

DoD
- demo_salon/truffles/demo_salon_script_test have company_id set to Truffles Corp.
- New client creation fails without company_id (API+UI).
- Lint/test checks pass.

Checks
- docker exec truffles_postgres_1 psql -U n8n -d chatbot -c "select ..." (evidence)
- pytest -q truffles-api/tests/test_console_admin_provisioning.py
- npm --prefix console-web run lint

Evidence
- SQL output before/after backfill.
- Test output.
- Screenshot of Tenants showing demo_salon/truffles under Truffles Corp.
- STATE.md updated with evidence.

Rollback
- Update clients.company_id back to NULL for affected slugs and delete Truffles Corp if needed.

No-go
- Any failed checks.
- Unexpected files in diff.
- Inability to identify affected clients safely.

Branch + Worktree
- Branch: feat/2026-01-29-tenants-company-backfill-a2
- Worktree: /home/zhan/worktrees/2026-01-29-tenants-company-backfill-a2
- Base ref: origin/main
- Merge policy: PR -> main (no rebase)
- Cleanup: remove worktree + branch after merge

Risks/Blockers
- Existing clients without company_id beyond known slugs.
- UI may still rely on /me filtering; after backfill, visibility should improve.
