# TP-2026-02-22-universal-control-plane-v1-phase7-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE7
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE6
- `UNLOCKS`: UCPV1-PHASE8

## Название/цель
Universal Control Plane v1 / Phase 7: внедрить Provider/Channel Control (WA-first), чтобы состояние каналов и провайдеров было управляемо через Console на уровне branch и деградировало детерминированно при проблемах провайдера.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/ESCALATION.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase6-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/provider_registry_service.py` (or equivalent provider/channel services)
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/app/services/outbox_service.py`
  - `truffles-api/tests/test_console_admin_provisioning.py`
  - `truffles-api/tests/*provider*`
- `Baseline commands`:
  - `rg -n "provider|channel|chatflow|telegram|binding|instance" truffles-api/app`
  - `rg -n "safe_mode|collect_only|degrade|handoff" truffles-api/app`
  - `rg -n "provider|channel" truffles-api/tests`
- `FACT findings`:
  - `GET /admin/provider-lifecycle`, `GET /admin/integrations`, `POST /admin/integrations/{branch_id}/reconcile` already implemented with `_require_platform_admin` and tenant access guards.
  - Branch-level integration payload already exposes provider binding lifecycle (`provider_binding_*`, `integration_state`, `drift_issues`) via `_build_branch_integration_status`.
  - Deterministic degrade/control path already present through provider ops queue + `integration_reconcile` workflow and corresponding tests.
- `Detected drift (docs vs code)`: B07 remained `planned` in program docs although required implementation and deterministic tests were already present in codebase.

## One web search (mandatory before implementation)
- **Query (exact):** `messaging provider lifecycle health checks branch binding fail closed degradation patterns`
- **Date/time (local):** `2026-02-27 19:36 (+05)`
- **Why this query is precise:** фокус на lifecycle+health+binding и fail-closed degrade для multi-tenant channel governance.
- **Sources opened (from this query):**
  - AWS Well-Architected Framework: Operational Excellence (monitor workload resources) — https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_mission_organization_monitor_resources.html
- **Existing solutions found:** explicit service-health states, operational alarms, and deterministic remediation workflows mapped to incident classes.
- **Decision:** reuse existing internal lifecycle/reconcile mechanisms (`provider lifecycle map`, `integration_state`, `provider ops queue`) and complete block by evidence + doc sync, without introducing new orchestration subsystem.
- **Rejected options:** introducing separate provider orchestration service in this block (out of scope and unnecessary for current DoD).
- **Open questions:** none for B07 closure; next deltas move to B08.

## Root cause (mandatory)
- **Symptom:** provider/channel lifecycle и явный branch-level status/degrade пока не зафиксированы как завершенный контракт в B07.
- **Minimal reproduction:** run `pytest -q truffles-api/tests/test_console_integrations_registry.py tests/test_console_ops_jobs.py` and inspect existing provider lifecycle endpoints/handlers in `truffles-api/app/routers/console.py`.
- **Evidence to capture:** tests + traces + outbox/provider state evidence
- **Five Whys (or equivalent):**
  1. Why block looked unfinished? B07 status in docs/graph was still `planned`.
  2. Why status lagged behind code? Earlier phases delivered integration primitives without explicit B07 closure pass.
  3. Why closure was missed? No dedicated B07 evidence pass with synchronized TP/Report/Graph updates.
  4. Why this matters? Zero-context agents rely on docs first; stale status causes repeated re-analysis and drift.
  5. Why could drift persist? Program-level status checks were not executed for B07 as a separate closure session.
- **Root cause statement:** documentation/state drift, not missing runtime functionality.
- **Fix mechanism:** execute dedicated B07 FACT verification, run target checks, and synchronize TP/Report/BLOCK_GRAPH/master report/STATE with evidence.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing provider adapters, outbox pipeline, console RBAC/audit flows.
- **External reuse:** provider lifecycle/health best practices (to be documented in one web search section).
- **Why not reinvent the wheel:** Phase7 should extend existing provider/channel contracts, not introduce a new orchestration fabric.

## Invariant
- Any inbound still resolves to `FACT/COLLECT/HANDOFF`.
- Hard-law/safety/tenant guards remain fail-closed.
- Provider degradation never causes silent message loss; deterministic fallback path is visible in trace/meta.

## Scope
- Provider/channel lifecycle registry controls (WA-first, Telegram notify fallback).
- Branch-level explicit channel status and provider binding truth.
- Deterministic degrade path (`collect_only`/safe-mode contract as approved).
- Console read/write controls for platform-admin governance.

## Out of scope
- Rewriting core LLM policy engine.
- New external provider integrations beyond approved B07 scope.
- Cross-block refactor outside provider/channel lifecycle.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase7-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase7-a500.md`
- `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase7-a520.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `truffles-api/app/**` (phase7-relevant provider/channel modules only)
- `truffles-api/tests/**` (phase7-relevant tests only)
- `contracts/console_api/openapi.v1.yaml` (if API changes)

## Plan (1..N)
1. Start dedicated phase7 session/worktree and run FACT pre-check.
2. Finalize analysis gate (contract delta, risks, migration, rollback).
3. Implement provider/channel lifecycle + branch binding controls in scope.
4. Add deterministic degrade behavior + observability signals.
5. Add/update tests and openapi contract.
6. Sync docs/evidence and close block.

## DoD
- Branch-level channel/provider status is explicit and auditable.
- Provider degradation triggers deterministic fallback path with reason codes.
- Console governance endpoints enforce platform-admin RBAC and tenant context.
- Tests and evidence prove no silent provider failure path.
- `docs/BLOCK_GRAPH.yaml`: `UCPV1-PHASE7 -> passed`, `UCPV1-PHASE8` unlocked.

## Checks
- `cd truffles-api && ruff check app tests`
- `pytest -q truffles-api/tests -k "provider or channel or outbox"`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase7-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase7-a500.md --graph docs/BLOCK_GRAPH.yaml`

## Evidence
- Console API/DB/runtime diffs for provider lifecycle.
- Deterministic tests + trace/meta snippets for degrade flow.
- Phase7 report with verdict and residual risks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** targeted provider/channel suites first.
- **Stop condition:** 2 runs without new evidence -> stop and refresh RCA.
- **Escalation path:** Brain/Top Architect for expanded run budget.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout by branch/provider bindings.
- **Go/no-go signals:** channel health, outbox delivery status, degrade reason codes.
- **Rollback:** revert phase7 changes and restore previous provider bindings/state.
- **Post-release monitoring window:** 24h with provider/channel dashboards and trace checks.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase7-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - no pass without code/tests/report/graph sync in same block.

## Rollback
- Revert phase7 commit(s).
- Restore previous provider bindings/status profile.
- Re-run targeted provider/channel tests.

## No-go
- No broad refactor outside provider/channel scope.
- No semantic hardcode in core routing.
- No weakening of fail-closed gates for provider failures.

## Risks/Blockers
- Provider-specific edge cases can cause hidden fallback drift if observability is incomplete.
- Existing adapter variance may require explicit compatibility handling.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` then this TP
- `Do not touch`: unrelated parallel tracks and unrelated UCP blocks
- `Open risks`: provider adapter variance, degrade observability completeness
- `First command to verify`: `rg -n "provider|channel|degrade|safe_mode" truffles-api/app`
