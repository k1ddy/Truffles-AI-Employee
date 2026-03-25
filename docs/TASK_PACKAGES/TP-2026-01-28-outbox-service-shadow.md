# TP-2026-01-28 — Outbox Service (shadow)

## Goal
Split outbox processing into a dedicated shadow service (separate app/router + restart script + tests)
without changing production routing or behavior.

## Canon refs
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-016)
- `STATE.md` (service separation roadmap)
- `SPECS/ARCHITECTURE.md`
- `TECH.md`

## Invariant
- Outbox idempotency + auto-heal unchanged.
- `/webhook` behavior unchanged; no traffic cutover.
- Trace/meta/outbox flow unchanged; no orchestration in entrypoints.

## Scope
- New FastAPI app `app.outbox_service_app:app` with `/health`.
- `POST /outbox/process` gated by env + token, mirrors admin outbox processing.
- Restart script for shadow container (port 8014, GHCR image).
- Tests for `/health` + disabled/token paths + enabled path (mocked).
- Docs updates (TECH/STRUCTURE/STATE) + session log/index.

## Out of scope
- Switching cron/worker to the new service.
- Any changes to outbox processing logic, retry rules, or payloads.
- Public ingress/Traefik routing.

## Touch-list
- `truffles-api/app/outbox_service_app.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/__init__.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `scripts/restart_outbox_service.sh`
- `TECH.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-28-outbox-service-shadow-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Add outbox service app + router with env/token gates.
2) Add restart script (GHCR image, internal-net, port 8014).
3) Add tests for `/health` and process endpoint (mocked).
4) Update TECH/STRUCTURE/STATE + session log/index.
5) Run container and capture `/health` evidence.

## DoD
- `truffles-outbox-service` runs on port 8014 and returns `/health`.
- `/outbox/process` returns 404 when disabled and 401 when token required.
- Tests pass for the new app.
- Evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_outbox_service_app.py`

## Evidence
- `/tmp/outbox_service_health_YYYYMMDD_HHMMSS.json`
- CI run URL

## Rollback
- Stop/remove the container and revert the PR.

## No-go
- Cutover traffic or replace worker/cron.
- Skip token enforcement when `OUTBOX_SERVICE_TOKEN` is set.
- Modify outbox processing logic.

## Risks / blockers
- `truffles_internal-net` must exist; GHCR image must be available.

## Branch / Worktree
- Branch: `feat/2026-01-28-outbox-service-shadow-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-outbox-service-shadow-a1`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
