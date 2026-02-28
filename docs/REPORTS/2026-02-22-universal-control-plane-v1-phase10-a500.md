# Universal Control Plane v1 - Phase 10 SLA/SLO Engine (a500)

Date
- 2026-02-28

## Block identity
- `BLOCK_ID`: UCPV1-PHASE10
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE9
- `UNLOCKS`: UCPV1-PHASE11

## Input baseline (FACT)
- `UCPV1-PHASE9` remains `blocked` in `docs/BLOCK_GRAPH.yaml`, so phase10 implementation is dependency-locked.
- SLA/SLO logic exists as separate islands:
  - router in-memory SLA counters,
  - inbox case age SLA statuses,
  - onboarding SLA control loop,
  - provider lifecycle SLA deadline logic,
  - owner/admin ops KPI thresholds.
- Unified profile-driven multi-level SLA engine (`global -> domain -> client -> branch`) is not implemented.

## FACT pre-check evidence (before changes)
- `rg -n "_calculate_sla_status|_resolve_provider_ops_sla|_build_sla_control_loop|_update_router_sla" truffles-api/app` -> confirms fragmented SLA logic across modules.
- `truffles-api/app/routers/webhook/router_sla.py` -> in-memory counters + `fallback_rate_flag`, no profile storage/merge.
- `truffles-api/app/services/onboarding_state.py` -> branch-level SLA loop from `client_settings` (`reminder_timeout_1/2`, `auto_close_timeout`).
- `truffles-api/app/routers/console.py` -> fixed case SLA thresholds and provider ops deadline resolver.
- `truffles-api/app/schemas/console.py` -> SLA-related response fields exist, but no registry lifecycle contract.
- `ops/console_owner_admin_kpi_snapshot.py` -> external guard thresholds independent from runtime policy engine.

## One web search evidence
- `Query (exact)` -> `OpenSLO specification service level objectives alert policies`
- `Sources opened` -> `https://github.com/OpenSLO/OpenSLO`
- `Decision` -> `reuse/integrate` reference vocabulary for objective/policy structure in phase10 contracts.
- `What was reused` -> objective/policy decomposition approach (service/indicator/objective/alert policy) adapted to Truffles scope layering.

## Root cause validation
- `Symptom` -> B10 remains planned with no central SLA/SLO engine despite multiple SLA signals in runtime/console.
- `Minimal reproduction` -> inspect SLA helpers in `router_sla.py`, `onboarding_state.py`, and `console.py`; no shared profile registry or effective merge path exists.
- `Root cause statement` -> SLA logic evolved per feature area, but profile registry + hierarchy merge + runtime enforcement were never consolidated.
- `Proof after fix` -> analysis package now defines explicit contract delta/touch-list/migration plan for consolidated engine; implementation intentionally deferred until phase9 unblocks.

## Reuse-first outcome
- `Internal reuse applied` -> yes; existing onboarding/provider/KPI SLA producers are retained as signal sources.
- `External reuse applied` -> yes; OpenSLO reference vocabulary selected for profile contract structure.
- `If build-new` -> new code is limited to registry/merge/enforcement glue; no rewrite of existing telemetry producers.

## Contract delta
- Planned new contracts:
  - SLA profile versioning (`draft/published/rollback`) at scoped levels.
  - Effective merge contract for `global/domain/client/branch`.
  - Runtime trace/meta markers for `sla_profile_id/version` and applied violation action.
- Planned API additions:
  - `GET /admin/sla-profiles`
  - `POST /admin/sla-profiles/publish`
  - `POST /admin/sla-profiles/rollback`
  - `GET /admin/sla-profiles/history`
  - write operations restricted to `platform_admin`.

## Implemented changes
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Checks + outcomes
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md --graph docs/BLOCK_GRAPH.yaml` -> `zero_context_gate: OK`.
- `rg -n "UCPV1-PHASE10|phase10-a500" docs/TASK_PACKAGES docs/REPORTS docs/BLOCK_GRAPH.yaml` -> phase10 TP/report paths now present and linked from graph.

## Iteration budget outcomes
- `Planned max runs` -> 0 expensive runs (analysis-only step).
- `Actual runs` -> 0 expensive runs.
- `Stop condition respected` -> yes.
- `If exceeded` -> n/a.

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `truffles-api/app/routers/webhook/router_sla.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `ops/console_owner_admin_kpi_snapshot.py`
- `ops/owner_admin_control_loop.py`

## Release safety decision
- `Strategy used` -> n/a (analysis-only; no runtime changes shipped).
- `Go/no-go signals observed` -> dependency lock (`UCPV1-PHASE9` blocked) keeps phase10 code path closed.
- `Rollback readiness` -> not required for this doc-only step.

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase10-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Drift resolved`: `yes` (phase10 graph references are now backed by concrete TP/report docs).

## Residual GAP / Risks
- Phase10 implementation cannot start until phase9 semantic blocker is resolved.
- Migration risk remains high if SLA islands are partially migrated without unified merge contract.
- Violation-action misconfiguration can over-escalate if rollout lacks staged gates.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase10-a500.md`
- `Do not touch`: phase9 remediation branch scope and unrelated parallel tracks.
- `Open risks`: dependency lock + merge consistency across current SLA islands.
- `First command to verify`: `rg -n "UCPV1-PHASE9|UCPV1-PHASE10" docs/BLOCK_GRAPH.yaml STATE.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Verdict
- `Blocked`
