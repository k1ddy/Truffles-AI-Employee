# TP-2026-01-27 — Knowledge Snapshot Consult Cutover (fallback → strict)

## Goal
Switch consult answers to snapshot-sourced packs with a controlled cutover.
Target: strict snapshot mode per-tenant, with an explicit fallback mode for rollout safety.

## Invariant
- Hard-LAW/policy/pending remain fail-closed and pre-LLM.
- Consult replies only from tenant packs; no domain dictionaries in core.
- Tenant isolation (tenant_context required for snapshot access).
- decision_trace/meta exists for every inbound and consult decision.
- Outbox idempotency unchanged.

## Scope
- Add snapshot consult mode flags (shadow/fallback/strict) and a per-tenant allowlist.
- Wire consult pack loading to snapshot data when mode is fallback/strict.
- Define fallback behavior: if snapshot missing/invalid, either fallback to legacy pack (fallback mode) or
  clarify/escalate (strict mode).
- Add consult trace/meta fields for snapshot source and playbook presence.
- Add tests for strict/fallback behavior + snapshot validation failures.
- Add live-check evidence on demo_salon (canary).

## Out of scope
- Provider Gateway cutover for inbound/outbound.
- Knowledge Studio publish pipeline changes.
- Non-consult flows (booking/info/manager).

## Touch-list
- `truffles-api/app/services/knowledge_snapshot_consumer.py`
- `truffles-api/app/services/consult_pack_service.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/services/knowledge_service.py` (if resolver needs snapshot packs)
- `truffles-api/tests/test_consult_pack_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `TECH.md` (env flags)
- `docs/CONSULTANT_CODEMAP.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-consult-cutover.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1) Define config:
   - `KNOWLEDGE_SNAPSHOT_CONSULT_MODE=shadow|fallback|strict` (default shadow).
   - `KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST` (client_slug list for canary).
2) Update consult pack resolver:
   - If mode in fallback/strict and client in allowlist, load packs from snapshot consumer.
   - If snapshot missing/invalid: fallback to legacy pack in fallback mode; clarify/escalate in strict mode.
3) Keep trace/meta:
   - Add `consult_snapshot_*` meta fields for source/version/sha256/playbook status.
   - Ensure consult decision trace includes snapshot stage.
4) Tests:
   - Strict mode rejects missing snapshot with clarify/escalate.
   - Fallback mode uses legacy pack when snapshot missing.
   - Snapshot present uses snapshot playbook (topic selection unchanged).
5) Live-check:
   - demo_salon canary: capture trace bundle with snapshot source + consult decision.
6) Docs + STATE evidence update.

## DoD
- Snapshot-backed consult works in fallback/strict modes with explicit flags.
- Missing snapshot does not leak knowledge (strict mode clarifies/escalates).
- Tests cover strict/fallback behavior and snapshot validation errors.
- Live-check trace bundle captured with consult_snapshot meta and consult decision.
- Docs updated (TECH + CONSULTANT_CODEMAP) and STATE evidence recorded.

## Checks
- `pytest -q truffles-api/tests/test_consult_pack_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k consult_snapshot`

## Evidence
- CI run URL for the PR.
- Live-check trace bundle (demo_salon canary).
- decision_meta + outbox status from trace bundle.

## Rollback
- Disable `KNOWLEDGE_SNAPSHOT_CONSULT_MODE` (set to shadow) or remove allowlist.
- Revert the PR if needed.

## No-go
- Enabling strict mode for tenants without a published snapshot.
- Using snapshot packs without tenant_context validation.
- Adding domain dictionaries back into core.

## Risks / blockers
- Snapshot availability gaps for existing tenants.
- Latency from snapshot fetch/validation.
- Need to coordinate allowlist + live-check windows.

## Branch / Worktree
- Branch: `tp/knowledge-snapshot-consult-cutover-2026-01-27`
- Worktree: `/home/zhan/worktrees/knowledge-snapshot-consult-cutover-2026-01-27`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
