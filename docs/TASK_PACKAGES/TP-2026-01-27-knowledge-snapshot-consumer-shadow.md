# TP-2026-01-27 — Knowledge Snapshot Consumer (shadow)

## Goal
Add a gated shadow consumer path that builds/validates consult playbooks from knowledge snapshots
and records trace/meta, without changing runtime decisions.

## Invariant
- No behavior change in consult/info/booking when the shadow flag is off.
- Snapshot data is derived only from published KnowledgeVersion payloads.
- tenant_context isolation is enforced (client_id + branch_id).
- decision_trace/decision_meta remain intact on all paths.

## Scope
- Add snapshot consumer helper (build snapshot + validate consult_playbook).
- Gate by env flag and record consult snapshot trace/meta.
- Keep file-based consult pack as the source of truth (shadow only).
- Add tests for gating, snapshot errors, and trace/meta.
- Update docs and register TP.

## Out of scope
- Cutover to snapshot-based responses.
- Knowledge snapshot cache/storage or Qdrant distribution.
- Provider gateway changes.

## Touch-list
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/services/consult_pack_service.py`
- `truffles-api/app/services/knowledge_snapshot_service.py` (reuse helper)
- `truffles-api/app/services/knowledge_snapshot_consumer.py` (new)
- `truffles-api/tests/test_message_endpoint.py`
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-consumer-shadow.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Implement snapshot consumer helper (build snapshot + consult_playbook validator).
2) Wire into consult flow with env gate and shadow trace/meta; keep decisions unchanged.
3) Add tests for enabled/disabled behavior and snapshot error reporting.
4) Update docs and register TP.

## DoD
- With env flag off, no snapshot trace entries and no behavior changes.
- With env flag on and tenant_context present, trace includes consult snapshot stage with ok/error.
- Existing consult behavior unchanged; new tests pass.
- Docs updated and TP registered.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k consult_snapshot`
- `pytest -q truffles-api/tests/test_consult_pack_service.py`

## Evidence
- PR URL + CI run URL.
- Trace entry in tests (consult snapshot stage recorded).

## Rollback
- Revert the PR introducing the shadow consumer.

## No-go
- Snapshot path affects response selection without explicit cutover decision.
- Snapshot enabled but no trace/meta emitted on consult path.
- Cross-tenant snapshot usage.

## Risks / blockers
- Some flows may lack branch_id; snapshot will be skipped with a recorded error.
- Snapshot schema drift requires validator alignment.

## Branch / Worktree
- Branch: `feat/knowledge-snapshot-consumer-2026-01-27`
- Worktree: `/home/zhan/worktrees/knowledge-snapshot-consumer-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Top Architect after merge
