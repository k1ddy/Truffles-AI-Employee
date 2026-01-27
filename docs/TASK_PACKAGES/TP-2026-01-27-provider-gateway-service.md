# TP-2026-01-27 — Provider Gateway Service (shadow)

## Goal
Split Provider Gateway into its own container (shadow), without switching production traffic, and capture
health evidence for the new service boundary.

## Canon refs
- `docs/IMPERIUM_DECISIONS.yaml` (DEC-016)
- `STATE.md` (Provider Gateway roadmap)
- `SPECS/ARCHITECTURE.md`

## Invariant
- Hard-LAW/policy/pending stay pre-LLM and fail-closed.
- tenant_context required on all provider payloads.
- Outbox idempotency and trace/meta remain intact.
- No changes to decision pipeline or routing behavior.

## Scope
- New FastAPI entrypoint `app.provider_gateway_app:app` with `/health`.
- Shadow container `truffles-provider-gateway` (internal-only, no external ingress).
- `scripts/restart_provider_gateway.sh` for GHCR image run (port 8011, internal-net).
- Docs updates (TECH/ARCH/STRUCTURE/STATE) and session log/index.

## Out of scope
- Public ingress/Traefik routing.
- Production cutover to Provider Gateway.
- New provider integrations or behavior changes in core.

## Touch-list
- `truffles-api/app/provider_gateway_app.py`
- `truffles-api/tests/test_provider_gateway_app.py`
- `scripts/restart_provider_gateway.sh`
- `TECH.md`
- `SPECS/ARCHITECTURE.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-27-provider-gateway-service-arch.md`
- `docs/SESSION_INDEX.md`

## Plan
1) Add `provider_gateway_app` with `/health` and include `provider_gateway` router.
2) Add `restart_provider_gateway.sh` (GHCR image, internal-net, port 8011, OTEL service name).
3) Add `/health` test for the new app.
4) Update TECH/ARCH/STRUCTURE/STATE.
5) Run container and capture `/health` evidence.
6) Commit doc-only updates with session log/index.

## DoD
- Container `truffles-provider-gateway` runs on port 8011.
- `/health` returns `{status: "ok", service: "provider_gateway"}`.
- Tests pass for the new app.
- Evidence recorded in `STATE.md`.

## Checks
- `pytest -q truffles-api/tests/test_provider_gateway_app.py`

## Evidence
- CI run URL.
- `/tmp/provider_gateway_health_20260127_151028.json`.
- `docker inspect truffles-provider-gateway --format '{{.Config.Image}}'`.
- Entry in `STATE.md`.

## Rollback
- Remove the container and revert the PR.

## No-go
- Enable public routing or global cutover.
- Add orchestration logic to entrypoints.
- Ship without tenant_context enforcement.

## Risks / blockers
- GHCR image must be available and internal-net must exist.
- Provider gateway env gates remain off by default; verify only `/health` in shadow mode.

## Branch / Worktree
- Branch: `feat/2026-01-27-provider-gateway-service-arch`
- Worktree: `/home/zhan/worktrees/2026-01-27-provider-gateway-service-arch`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain / Top Architect after merge
