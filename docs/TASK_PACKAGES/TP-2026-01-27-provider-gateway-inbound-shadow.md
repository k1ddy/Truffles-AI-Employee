# TP-2026-01-27 — Provider Gateway Inbound (shadow)

## Goal
Introduce a provider-agnostic inbound envelope adapter and shadow endpoint that validates
`provider_inbound.v1` and maps to the existing webhook pipeline without changing production behavior.

## Invariant
- Hard-LAW/policy/pending remain fail-closed and pre-LLM.
- No provider-specific logic in core decision pipeline.
- Existing `/webhook` and `/message` behavior unchanged.
- tenant_context required; no cross-tenant data access.
- Trace/meta preserved on early exits.

## Scope
- Add Pydantic schema for `provider_inbound` payloads.
- Translate provider inbound payload to `WebhookRequest` (text-first; reject unsupported media for now).
- Add a gated `POST /provider/inbound` endpoint that reuses existing webhook pipeline.
- Add unit tests for translator + endpoint guard.
- Update `docs/CONSULTANT_CODEMAP.md` to include the new ingress path.
- Register the Task Package in `STRUCTURE.md` and `STATE.md`.

## Out of scope
- Provider gateway outbound + status callbacks.
- Inbox durable storage (`inbox_event` table) or DLQ.
- Knowledge snapshot integration.
- Provider-specific adapters (ChatFlow/Instagram/CRM).
- Production traffic cutover.

## Touch-list
- `truffles-api/app/schemas/provider_gateway.py`
- `truffles-api/app/services/provider_gateway_service.py`
- `truffles-api/app/routers/provider_gateway.py`
- `truffles-api/app/main.py`
- `truffles-api/tests/test_provider_gateway_inbound.py`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-inbound-shadow.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Define Pydantic models for provider inbound and reuse tenant_context contract fields.
2) Implement translator to `WebhookRequest` with strict validation and text-only support.
3) Add `/provider/inbound` endpoint gated by env and wired into `_handle_webhook_payload`.
4) Add unit tests for translator validation and endpoint gating.
5) Update docs and register TP in `STRUCTURE.md`/`STATE.md`.

## DoD
- Translator rejects missing tenant_context/client_slug and unsupported media types.
- `/provider/inbound` accepts valid payloads and calls existing pipeline in shadow mode.
- Unit tests cover happy path + validation failures.
- Docs updated to reflect new ingress path.

## Checks
- `pytest -q truffles-api/tests/test_provider_gateway_inbound.py`

## Evidence
- PR URL + CI run URL.
- Test output in CI.

## Rollback
- Revert the PR that introduces the provider gateway inbound endpoint.

## No-go
- Endpoint enabled without env gate.
- Any provider-specific branching inside core decision pipeline.
- tenant_context missing or ignored.

## Risks / blockers
- Media payload mapping requires follow-up TP for full parity.
- Provider payloads may include fields that need `extensions` mapping.

## Branch / Worktree
- Branch: `feat/provider-gateway-inbound-2026-01-27`
- Worktree: `/home/zhan/worktrees/provider-gateway-inbound-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
