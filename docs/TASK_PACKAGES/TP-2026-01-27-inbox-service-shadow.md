# TP-2026-01-27 — Inbox Service (shadow)

## Goal
Split inbox ingest into a dedicated service (shadow) that records durable `inbox_events`
without changing routing or production behavior.

## Canon refs
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-016)
- `STATE.md` (provider/inbox separation roadmap)
- `SPECS/ARCHITECTURE.md`
- `TECH.md`

## Invariant
- Hard-LAW/policy/pending remain pre-LLM and fail-closed.
- `tenant_context` is required for all inbound events.
- `/webhook` and decision pipeline behavior unchanged.
- Trace/meta/outbox flow remains intact.

## Scope
- New FastAPI entrypoint `app.inbox_service_app:app` with `/health`.
- `POST /inbox/event` accepts `provider_inbound.v1` payload and writes `inbox_events` via `record_inbox_event`.
- Env gate for inbound ingest (default off) + optional token header.
- Shadow container `truffles-inbox-service` (internal-only, port 8012) with restart script.
- Tests for `/health` and request path (DB write stubbed).
- Doc updates (TECH/STRUCTURE/STATE) + session log/index.

## Out of scope
- Provider Gateway calling Inbox Service (no routing/cutover).
- Decision Core reading from `inbox_events`.
- Rate limiting, DLQ, retries.

## Touch-list
- `truffles-api/app/inbox_service_app.py`
- `truffles-api/app/routers/inbox_service.py`
- `truffles-api/app/services/inbox_event_service.py` (if needed)
- `truffles-api/tests/test_inbox_service_app.py`
- `scripts/restart_inbox_service.sh`
- `TECH.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-27-inbox-service-shadow-arch.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Add `inbox_service_app` with `/health` and router.
2) Implement `/inbox/event` endpoint gated by env and token.
3) Add restart script (GHCR image, internal-net, port 8012).
4) Add tests for `/health` and handler return paths (mock DB write).
5) Update TECH/STRUCTURE/STATE.
6) Run container and capture health + inbox_event evidence.

## DoD
- `truffles-inbox-service` runs on port 8012 and returns `/health`.
- `/inbox/event` accepts valid `provider_inbound` and records `inbox_events`.
- Tests pass for the new app.
- Evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_inbox_service_app.py`

## Evidence
- `/tmp/inbox_service_health_YYYYMMDD_HHMMSS.json`
- `/tmp/inbox_event_canary_YYYYMMDD_HHMMSS.txt` (DB row)
- CI run URL

## Rollback
- Stop/remove the container and revert the PR.

## No-go
- Public ingress or traffic cutover.
- Missing `tenant_context`.
- Entry-point orchestration in `_legacy.py`.

## Risks / blockers
- `internal-net` must exist; GHCR image must be available.

## Branch / Worktree
- Branch: `feat/2026-01-27-inbox-service-shadow-arch`
- Worktree: `/home/zhan/worktrees/2026-01-27-inbox-service-shadow-arch`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
