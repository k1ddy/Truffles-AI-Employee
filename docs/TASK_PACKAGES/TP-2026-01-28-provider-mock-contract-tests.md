# TP-2026-01-28 — Provider Mock + Contract Tests

## Goal
Add a mock provider harness and contract tests for provider inbound/outbound/status/media payloads
to prevent adapter or schema drift without changing runtime behavior.

## Canon refs
- `STATE.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`
- `contracts/integrations/provider_inbound.v1.jsonschema`
- `contracts/integrations/provider_outbound.v1.jsonschema`
- `contracts/integrations/media_send.v1.jsonschema`
- `contracts/events/provider_status.v1.jsonschema`

## Invariant
- Provider gateway/outbox runtime behavior unchanged (tests only).
- Trace/meta/outbox flow unchanged.
- No new env gates or traffic cutover.

## Scope
- Contract tests for provider inbound/outbound/status/media payloads.
- Mock provider harness to validate outbound adapter payloads.
- Ensure provider outbound payload serialization matches JSON schema (UUID -> string).
- Test-only dependency for JSON schema validation (if needed).

## Out of scope
- Provider Gateway outbound canary enablement.
- Integration tests for cross-tenant/provider swap/status update (separate TP).
- Changes to gateway/outbox logic or HTTP handlers.

## Touch-list
- `truffles-api/app/services/provider_gateway_service.py`
- `truffles-api/tests/test_provider_gateway_inbound.py`
- `truffles-api/tests/test_provider_gateway_outbound.py`
- `truffles-api/requirements.txt`
- `docs/SESSIONS/SESSION-2026-01-28-provider-mock-contract-tests-a1.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`

## Plan
1) Add JSON schema validation helper in tests.
2) Ensure outbound payload serialization is JSON-compatible.
3) Validate inbound payloads against provider_inbound contract.
4) Validate outbound payloads (text + media) against provider_outbound contract.
5) Validate provider_status and media_send contracts.
6) Add mock provider harness for outbound adapter tests.
7) Run pytest for provider gateway tests and record evidence.

## DoD
- Contract tests cover inbound/outbound/status/media payloads.
- ProviderGatewayAdapter outbound payloads validated by mock provider.
- Outbound payload JSON serialization matches contract (UUID as string).
- `pytest` passes for updated tests.
- Evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_provider_gateway_inbound.py`
- `pytest -q truffles-api/tests/test_provider_gateway_outbound.py`

## Evidence
- pytest output logs (attach in session log).
- CI run URL (if available).

## Rollback
- Revert the commit/PR.

## No-go
- Modify runtime logic or enable outbound canary.
- Skip contract validation for media TTL.

## Risks / blockers
- JSON schema validator dependency must be available in CI.

## Branch / Worktree
- Branch: `feat/2026-01-28-provider-mock-contract-tests-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-provider-mock-contract-tests-a1`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
