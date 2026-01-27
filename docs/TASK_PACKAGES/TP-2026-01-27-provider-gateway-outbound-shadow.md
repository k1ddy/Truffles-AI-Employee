# TP-2026-01-27 — Provider Gateway Outbound + Status (shadow)

## Goal
Add a gated provider-gateway outbound adapter and status callback handling, wired into the existing
outbox worker without changing default behavior.

## Invariant
- Outbox idempotency and retry behavior remain intact.
- No provider-specific logic in core decision pipeline.
- Existing ChatFlow outbound path stays the default when gateway is disabled.
- tenant_context is preserved on outbound payloads and status callbacks.
- Trace/meta still recorded on failures.

## Scope
- Add provider gateway outbound adapter (HTTP) and payload builder for `provider_outbound.v1`.
- Support media payloads (`media_send.v1`) with signed URL + TTL (no behavior change when disabled).
- Add optional status callback endpoint to update outbox status + meta.
- Add env gates for outbound + status endpoints.
- Update docs to reflect the new outbound shadow path.
- Add unit tests for payload builder + status endpoint.
- Register TP in `STRUCTURE.md` and `STATE.md`.

## Out of scope
- Provider gateway inbound (already done).
- Inbox durable storage (`inbox_event`) or DLQ.
- Knowledge snapshot integration.
- Production cutover to provider gateway.

## Touch-list
- `truffles-api/app/adapters/provider_gateway.py`
- `truffles-api/app/services/provider_gateway_service.py`
- `truffles-api/app/routers/provider_gateway.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/ports/messaging.py` (no changes expected)
- `truffles-api/tests/test_provider_gateway_outbound.py`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-outbound-shadow.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Add outbound adapter + payload builder for `provider_outbound` (text-only), gated by env.
2) Wire outbox worker to use provider gateway adapter when enabled; preserve default ChatFlow path.
3) Add provider status callback endpoint to update outbox status + meta (gated).
4) Add unit tests for payload builder and status handling.
5) Update docs and register TP.

## DoD
- Outbound payload builder produces valid provider_outbound for text and media messages.
- When gateway disabled, outbound behavior remains unchanged.
- Status callback updates outbox status/meta when outbox_id is provided.
- Unit tests cover builder + status endpoint.
- Docs updated and TP registered.

## Checks
- `pytest -q truffles-api/tests/test_provider_gateway_outbound.py`

## Evidence
- PR URL + CI run URL.

## Rollback
- Revert the PR introducing provider gateway outbound/status.

## No-go
- Gateway enabled without explicit env gates.
- Provider-specific branching inside decision pipeline.
- tenant_context missing on outbound payloads.

## Risks / blockers
- Provider gateway response contract may evolve (store in outbox meta via `extensions`).
- Media support requires follow-up TP (signed URL + async send).

## Branch / Worktree
- Branch: `feat/provider-gateway-outbound-2026-01-27`
- Worktree: `/home/zhan/worktrees/provider-gateway-outbound-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
