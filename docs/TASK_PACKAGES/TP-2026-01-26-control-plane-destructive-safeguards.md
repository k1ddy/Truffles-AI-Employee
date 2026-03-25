Title: Control Plane TP-C - destructive change safeguards
Owner: Top Architect
Date: 2026-01-26

Canon refs:
- SPECS/CONTROL_PLANE.md (roles, onboarding, governance)
- SPECS/MULTI_TENANT.md (tenant context, fail-closed)
- STRATEGY/REQUIREMENTS.md (safety and quality gates)
- docs/CONSOLE_GUIDE.md (console workflow)
- STATE.md (roadmap)

Dependencies:
- TP-A RBAC matrix enforcement (PR #383 merged)
- TP-B Onboarding state machine (PR #389 merged)

Invariant:
- Fail-closed tenant context and RBAC gates must remain.
- No silent destructive changes; every destructive action must be confirmed and audited.
- No changes to core pipeline (webhook/LLM routing).

Scope:
- Define destructive actions for Console (server-side list, branch/company/client scope).
- Add confirmation flow (two-step confirm + reason + TTL) for destructive actions.
- Enforce confirmation in API for destructive endpoints.
- Add audit events for confirmed and rejected attempts.
- Add UI confirmation flow (modal/inline) with reason and context.

Out of scope:
- New integrations/providers.
- Rewriting existing onboarding logic.
- Non-console admin operations and core pipeline changes.

Touch-list (files/tables):
- truffles-api/app/models/ (new confirmation model)
- truffles-api/migrations/0xx_add_console_confirmations.sql
- truffles-api/app/services/console_confirmations.py (confirmation logic)
- truffles-api/app/routers/console.py (guards for destructive endpoints)
- truffles-api/app/schemas/console.py (confirmation request/response)
- truffles-api/app/services/audit_service.py (audit entries)
- truffles-api/tests/test_console_confirmations.py
- contracts/console_api/openapi.v1.yaml
- contracts/console_api/errors.v1.json
- console-web/src/components/ (confirm modal + reason input)
- console-web/src/lib/api-client.ts
- docs/CONSOLE_GUIDE.md
- STATE.md, STRUCTURE.md

Plan:
1) Inventory destructive actions and define the list (owner/admin only).
2) Add confirmation model with TTL (confirmation_id, action, target, actor, reason, expires_at).
3) Add API:
   - POST /console/v1/confirmations (create)
   - Require confirmation_id + reason for destructive endpoints.
4) Enforce guards in destructive endpoints (409 CONFIRMATION_REQUIRED if missing/expired/mismatch).
5) Add audit events: confirmation_created, confirmation_used, confirmation_failed.
6) Update UI to request confirmation and show reason/target summary.
7) Add tests for confirmation flow and guard enforcement.
8) Update docs and STATE.

DoD:
- Destructive endpoints fail without valid confirmation (409 CONFIRMATION_REQUIRED).
- Confirmations are TTL-limited and audited.
- UI enforces confirmation + reason for destructive actions.
- Tests cover confirmation lifecycle and guard failures.

Checks:
- pytest -q truffles-api/tests/test_console_confirmations.py
- npm --prefix console-web run lint
- npm --prefix console-web run generate:api (if OpenAPI changed)

Evidence:
- CI run URL + test output
- STATE.md updated with PR/CI evidence

Rollback:
- Revert PR and rollback migration

No-go:
- Do not bypass confirmations for destructive actions
- Do not expand access for non-owner/admin roles
- Do not touch docs/CONSULTANT_CODEMAP.md

Branch/Worktree:
- Branch: feat/control-plane-destructive-safeguards
- Worktree: /home/zhan/worktrees/control-plane-destructive-safeguards
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch/worktree after merge
