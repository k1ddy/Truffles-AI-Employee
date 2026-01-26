# TP-2026-01-26 — Provider Gateway + Knowledge Gateway Architecture

## Goal
Define the target architecture and execution plan for provider-agnostic channels, strict tenant data isolation,
guaranteed inbox/outbox delivery, and pack-only consultant behavior. Document decisions, boundaries, and safety
gates before any implementation.

## Invariant
- Hard-LAW/policy/pending remain fail-closed and pre-LLM.
- No cross-tenant data access (tenant_context required everywhere).
- Consultant answers only from tenant packs/snapshots; no provider/demo-specific logic in core.
- Inbox/outbox remain idempotent and trace/meta must exist for every inbound.

## Scope
- Record DEC-016 for provider gateway + knowledge snapshot architecture.
- Update architecture/specs to define new services and boundaries.
- Define contracts for provider ingress/egress, message status, media, and knowledge snapshots.
- Define capability model for channels/features (WhatsApp/Instagram/CRM/Calendar).
- Define reliability/security/observability requirements (retries, DLQ, audit, monitoring).
- Provide migration/rollback and test strategy.

## Out of scope
- Implementing new providers or migrating production traffic.
- Rewriting current webhook pipeline without a follow-up TP.
- Changes to business policy rules or pricing logic.

## Touch-list
- `docs/IMPERIUM_DECISIONS.yaml`
- `SPECS/ARCHITECTURE.md`
- `SPECS/INFRASTRUCTURE.md`
- `SPECS/MULTI_TENANT.md`
- `SPECS/SYSTEM_REFERENCE.md` (SOP updates if needed)
- `contracts/integrations/*` (new provider contracts)
- `contracts/events/*` (inbox/outbox envelopes, status events)
- `docs/runbooks/*` (monitoring/incident/outbox guidance)
- `docs/TASK_PACKAGES/TP-2026-01-26-provider-gateway-architecture.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Add DEC-016 with the chosen provider gateway + knowledge snapshot architecture.
2) Extend `SPECS/ARCHITECTURE.md` with:
   - Provider Gateway (ingress/egress) + Channel Adapters.
   - Inbox Service (durable ingest + idempotency + dedupe).
   - Outbox Service (retries + DLQ + status mapping).
   - Knowledge Gateway (signed, versioned per-tenant snapshot).
3) Define security and isolation rules in `SPECS/INFRASTRUCTURE.md` / `SPECS/MULTI_TENANT.md`:
   - tenant_context required on every read/write.
   - per-tenant knowledge isolation (DB, Qdrant, cache).
   - signed snapshot validation (hash + version pinning).
4) Draft contracts under `contracts/integrations/` and `contracts/events/`:
   - `provider_inbound.v1`, `provider_outbound.v1`,
   - `provider_status.v1`, `media_send.v1`,
   - `knowledge_snapshot.v1`, `inbox_event.v1`.
5) Define capability registry requirements (channel + feature flags) and mapping to providers.
6) Define monitoring/alerts/runbooks:
   - inbox lag, outbox retry rate, provider error rate,
   - per-tenant SLA dashboards,
   - incident response steps + rollback.
7) Provide staged rollout plan:
   - shadow mode → partial tenants → full cutover,
   - contract tests + provider swap checklist.

## DoD
- DEC-016 recorded in `docs/IMPERIUM_DECISIONS.yaml`.
- Architecture/specs updated with clear service boundaries and safety gates.
- Contracts defined for provider I/O and knowledge snapshot.
- Security/isolation requirements documented and enforced in specs.
- Monitoring + rollback plan documented.
- No production behavior change without a follow-up implementation TP.

## Checks
- Docs-only (no runtime checks required).

## Evidence
- PR URL with DEC/spec updates.
- CI run URL (docs-only changes).

## Rollback
- Revert DEC/spec/contract changes in the PR.

## No-go
- Any implementation that bypasses tenant_context.
- Provider-specific logic in core decision pipeline.
- Inbox/outbox without idempotency and DLQ.
- LLM responses not constrained to pack/snapshot data.

## Risks / blockers
- Contract ownership needs alignment (provider teams).
- Per-tenant isolation in Qdrant may require operational changes.
- Migration path must avoid downtime and avoid duplicate sends.

## Branch / Worktree
- Branch: `dec/provider-architecture-2026-01-26`
- Worktree: `/home/zhan/worktrees/dec-provider-gateway-2026-01-26`
- Base ref: `origin/main`
- Merge policy: PR + CI green
- Cleanup: Brain or Top Architect after merge
