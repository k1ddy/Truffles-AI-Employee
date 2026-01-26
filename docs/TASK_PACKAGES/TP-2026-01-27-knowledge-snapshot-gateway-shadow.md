# TP-2026-01-27 — Knowledge Snapshot Gateway (shadow)

## Goal
Add a gated knowledge snapshot endpoint that returns `knowledge_snapshot.v1` from published
Knowledge Studio data, without changing core runtime behavior.

## Invariant
- No behavior change for existing consult/booking/info flows.
- tenant_context required (client_id + branch_id) for snapshots.
- Snapshot content is derived from published `knowledge_versions` only.
- Core does not consume snapshots yet (shadow only).

## Scope
- Add snapshot builder service (packs + sha256 + optional signature/TTL).
- Add gated `/knowledge/snapshot` endpoint.
- Add Pydantic schema for snapshot request/response.
- Add unit tests for builder + endpoint gating.
- Update docs and register TP.

## Out of scope
- Replacing existing pack loaders in core.
- Qdrant snapshot delivery or cache distribution.
- Multi-region snapshot storage.
- Production cutover to snapshot-only behavior.

## Touch-list
- `truffles-api/app/routers/knowledge_gateway.py`
- `truffles-api/app/services/knowledge_snapshot_service.py`
- `truffles-api/app/schemas/knowledge_snapshot.py`
- `truffles-api/app/main.py`
- `truffles-api/app/routers/__init__.py`
- `truffles-api/tests/test_knowledge_snapshot_gateway.py`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-gateway-shadow.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Implement snapshot builder from published KnowledgeVersion + tenant_context.
2) Add gated endpoint that serves knowledge_snapshot.v1 payloads.
3) Add unit tests for builder and endpoint gating.
4) Update docs and register TP.

## DoD
- Snapshot builder returns valid `knowledge_snapshot.v1` with sha256 + tenant_context.
- Endpoint is gated by env and returns 404 when disabled.
- Tests cover builder happy path and missing version/tenant cases.
- Docs updated and TP registered.

## Checks
- `pytest -q truffles-api/tests/test_knowledge_snapshot_gateway.py`

## Evidence
- PR URL + CI run URL.

## Rollback
- Revert the PR introducing the knowledge snapshot gateway.

## No-go
- Missing tenant_context on snapshot responses.
- Endpoint enabled without env gate.
- Using draft/unpublished knowledge versions.

## Risks / blockers
- KnowledgeVersion payload structure may evolve; pack mapping must stay aligned with Knowledge Studio schema.
- Signature and TTL policy need follow-up decision for production use.

## Branch / Worktree
- Branch: `feat/knowledge-snapshot-gateway-2026-01-27`
- Worktree: `/home/zhan/worktrees/knowledge-snapshot-gateway-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
