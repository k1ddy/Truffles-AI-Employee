# TP-2026-01-26 — Provider Gateway Contracts v1

## Goal
Define provider-agnostic contract schemas for inbound/outbound messaging, status callbacks, inbox events,
media payloads, and knowledge snapshots to support DEC-016 without changing runtime behavior.

## Invariant
- tenant_context required for every inbound/outbound event.
- No provider-specific logic in core decision pipeline.
- No runtime behavior change (docs/contracts only).

## Scope
- Add JSON schemas for provider gateway envelopes and inbox/outbox events.
- Align contract names with DEC-016 and `SPECS/ARCHITECTURE.md`.
- Register new Task Package and contract paths in `STRUCTURE.md`.
- Record plan in `STATE.md` (PLAN only, no evidence claim).

## Out of scope
- Implementing Provider Gateway / Knowledge Gateway services.
- Modifying webhook pipeline or outbox logic.
- Adding new providers (Instagram/CRM) beyond contracts.

## Touch-list
- `contracts/integrations/provider_inbound.v1.jsonschema`
- `contracts/integrations/provider_outbound.v1.jsonschema`
- `contracts/integrations/media_send.v1.jsonschema`
- `contracts/integrations/knowledge_snapshot.v1.jsonschema`
- `contracts/events/inbox_event.v1.jsonschema`
- `contracts/events/provider_status.v1.jsonschema`
- `docs/TASK_PACKAGES/TP-2026-01-26-provider-contracts-v1.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Create contract schemas with strict required fields and tenant_context references.
2) Ensure contract naming matches DEC-016 and architecture spec list.
3) Update STRUCTURE/STATE with references to the new Task Package and contract files.
4) Validate JSON syntax locally with `python3 -m json.tool`.

## DoD
- All six contract files exist and validate as JSON.
- Every contract includes `tenant_context` or derives it from parent.
- Contract names match DEC-016 list in `SPECS/ARCHITECTURE.md`.
- STRUCTURE/STATE updated to reflect new contracts/TP.

## Checks
- `python3 -m json.tool contracts/integrations/provider_inbound.v1.jsonschema`
- `python3 -m json.tool contracts/integrations/provider_outbound.v1.jsonschema`
- `python3 -m json.tool contracts/integrations/media_send.v1.jsonschema`
- `python3 -m json.tool contracts/integrations/knowledge_snapshot.v1.jsonschema`
- `python3 -m json.tool contracts/events/inbox_event.v1.jsonschema`
- `python3 -m json.tool contracts/events/provider_status.v1.jsonschema`

## Evidence
- PR URL + CI run URL.

## Rollback
- Revert the PR that adds the contracts.

## No-go
- Missing tenant_context in any schema.
- Runtime code changes or provider-specific logic added to core.
- Contracts that allow silent cross-tenant data mixing.

## Risks / blockers
- Contract ownership alignment across provider teams.
- Future provider-specific fields require `extensions` blocks to avoid breaking changes.

## Branch / Worktree
- Branch: `feat/provider-contracts-v1-2026-01-26`
- Worktree: `/home/zhan/worktrees/provider-contracts-v1-2026-01-26`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
