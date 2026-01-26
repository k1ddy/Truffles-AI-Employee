# TP-2026-01-27 — Inbox Event (provider gateway shadow)

## Goal
Introduce a durable inbox event store for provider gateway inbound traffic (shadow mode), with strict
tenant_context capture and dedupe, without changing default webhook behavior.

## Invariant
- No behavior change for existing `/webhook` pipeline.
- tenant_context required on inbox events (client_id mandatory).
- Dedupe on provider_message_id avoids duplicate processing.
- Trace/meta still recorded for existing gates; inbox failure does not break legacy flow unless explicitly required.

## Scope
- Add `inbox_events` table + model.
- Add service to record provider inbound events with dedupe and tenant checks.
- Wire provider gateway inbound to record inbox events (env-gated).
- Add tests for inbox recording + dedupe.
- Update docs and register TP.

## Out of scope
- Full Inbox Service extraction.
- Event routing / queue fan-out.
- Backfilling existing webhook traffic.
- Provider-specific adapters beyond gateway.

## Touch-list
- `truffles-api/migrations/015_add_inbox_events.sql`
- `truffles-api/app/models/inbox_event.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/app/services/inbox_event_service.py`
- `truffles-api/app/routers/provider_gateway.py`
- `truffles-api/tests/test_inbox_event_service.py`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-inbox-event.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Add inbox_events table + SQLAlchemy model with tenant keys and dedupe constraint.
2) Implement record_inbox_event service (validate tenant_context, dedupe on provider_message_id).
3) Wire provider gateway inbound to record inbox events when enabled (env gates).
4) Add unit tests for record/dedupe and gateway gating.
5) Update docs and register TP.

## DoD
- `inbox_events` table + model exist with dedupe constraint.
- record_inbox_event captures tenant_context + raw payload.
- Provider gateway inbound records inbox events when enabled (gated).
- Unit tests cover happy path + duplicate detection.
- Docs updated and TP registered.

## Checks
- `pytest -q truffles-api/tests/test_inbox_event_service.py`

## Evidence
- PR URL + CI run URL.

## Rollback
- Revert the PR introducing inbox events.

## No-go
- Missing tenant_context on inbox events.
- Changing legacy `/webhook` behavior.
- Dedupe disabled or removed.

## Risks / blockers
- Requires DB migration in prod before enabling gate.
- Needs clear policy on what happens if inbox write fails (shadow vs required).

## Branch / Worktree
- Branch: `feat/provider-gateway-inbox-event-2026-01-27`
- Worktree: `/home/zhan/worktrees/provider-gateway-inbox-event-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
