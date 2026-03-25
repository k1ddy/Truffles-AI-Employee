# TP-2026-01-28 — Decision Core (shadow)

## Goal
Create a shadow Decision Core service (separate app + router + restart script + tests) without changing
production routing or behavior.

## Canon refs
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-016)
- `STATE.md` (Inbox Service DONE; next step: Decision Core separation)
- `SPECS/ARCHITECTURE.md`
- `TECH.md`

## Invariant
- Hard-LAW/policy/pending remain pre-LLM and fail-closed.
- `/webhook` behavior unchanged; no traffic cutover.
- `_legacy.py` remains adapter-only (no orchestration in entrypoints).
- Trace/meta/outbox flow unchanged.

## Scope
- New FastAPI app `app.decision_core_app:app` with `/health`.
- `POST /decision/handle` accepts `WebhookRequest`, gated by env + token.
- Restart script for shadow container (port 8013, GHCR image).
- Tests for `/health` and disabled path (404).
- Update TECH/STRUCTURE/STATE + session log/index.

## Out of scope
- Provider Gateway cutover or inbound routing changes.
- Statelss core + pack snapshot enforcement (future).
- Any behavior change to `/webhook`.

## Touch-list
- `truffles-api/app/decision_core_app.py`
- `truffles-api/app/routers/decision_core.py`
- `truffles-api/app/routers/__init__.py`
- `truffles-api/tests/test_decision_core_app.py`
- `scripts/restart_decision_core.sh`
- `TECH.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-28-decision-core-shadow-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Add `decision_core_app` and router with env/token gates.
2) Add restart script (GHCR image, internal net, port 8013).
3) Add tests for `/health` and disabled path.
4) Update TECH/STRUCTURE/STATE and session log/index.
5) Local build + container health check evidence.

## DoD
- Decision Core app runs on port 8013 and returns `/health`.
- `/decision/handle` returns 404 when disabled.
- Tests pass.
- Evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_decision_core_app.py`
- `docker build -t truffles-decision-core:20260128 truffles-api`
- `IMAGE_NAME=truffles-decision-core:20260128 REQUIRE_GHCR=0 DECISION_CORE_ENABLED=1 scripts/restart_decision_core.sh`
- `curl -s http://127.0.0.1:8013/health`

## Evidence
- `/tmp/decision_core_health_YYYYMMDD_HHMMSS.json`
- CI run URL

## Rollback
- Stop/remove the container and revert the PR.

## No-go
- Cutover traffic to Decision Core.
- Running without `tenant_context` or bypassing Hard-LAW gates.

## Risks / blockers
- `truffles_internal-net` must exist; local build required before GHCR.

## Branch / Worktree
- Branch: `feat/2026-01-28-decision-core-shadow-a1`
- Worktree: `/home/zhan/worktrees/2026-01-28-decision-core-shadow-a1`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
