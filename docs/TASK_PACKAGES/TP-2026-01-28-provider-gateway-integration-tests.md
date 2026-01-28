# TP-2026-01-28 — Provider Gateway Integration Tests

## Goal
Add integration tests for provider gateway flows (cross-tenant isolation, provider swap, status update)
with minimal, targeted safeguards and no runtime cutover.

## Canon refs
- `STATE.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`
- `contracts/events/provider_status.v1.jsonschema`
- `contracts/integrations/provider_outbound.v1.jsonschema`

## Invariant
- Tenant context required; cross-tenant updates must be rejected.
- Outbox idempotency/auto-heal unchanged.
- No orchestration added to entrypoints.

## Scope
- New integration test file covering:
  - provider status update with tenant match/mismatch
  - provider swap (payload provider/channel propagated to gateway adapter)
  - status update path updates outbox meta/status
- Minimal guard for tenant mismatch in provider status update if missing.

## Out of scope
- Provider Gateway outbound canary enablement.
- Live-checks / traffic cutover.
- Any changes to external provider behavior.

## Touch-list
- `truffles-api/app/services/provider_gateway_service.py`
- `truffles-api/app/routers/webhook/outbox.py` (if needed for provider swap assertion)
- `truffles-api/tests/test_provider_gateway_integration.py` (new)
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-28-provider-gateway-integration-tests-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Add integration test harness (mock DB/outbox row) for provider gateway flows.
2) Add/verify tenant mismatch guard on provider status update.
3) Add provider swap test (provider/channel in payload propagate to gateway adapter).
4) Add status update test (outbox meta/status updated).
5) Run pytest for new integration tests and capture evidence.
6) Update `STATE.md` + session log/index.

## DoD
- Integration tests cover cross-tenant mismatch, provider swap, status update.
- Tenant mismatch returns error and does not update outbox.
- Tests pass locally and evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_provider_gateway_integration.py`

## Evidence
- pytest output (attach in session log).
- CI run URL (if available).

## Rollback
- Revert the commit/PR.

## No-go
- Enabling outbound canary or changing provider routing.
- Skipping tenant_context guard when client_id mismatches.

## Risks / blockers
- Mocked DB chain must match SQLAlchemy call patterns; keep mocks minimal.

## Branch / Worktree
- Branch: `feat/2026-01-28-provider-gateway-integration-tests-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-provider-gateway-integration-tests-a1`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
