# TP-2026-02-22-universal-control-plane-v1-phase13-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE13
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE12
- `UNLOCKS`: none

## Название/цель
Universal Control Plane v1 / Phase 13: Migration Program (`current -> target`) без stop-the-world, чтобы rollout шел по волнам `canary -> cohort -> fleet` с явными pass/fail gates и rollback triggers, а не через ad-hoc ручные решения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests (current state)`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Baseline commands`:
  - `rg -n "UCPV1-PHASE13|phase13" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md docs/TASK_PACKAGES docs/REPORTS`
  - `ls -l docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
  - `rg -n "/admin/control-tower/(overview|readiness-board|drift-board|action-center)" truffles-api/app/routers/console.py`
  - `rg -n "/admin/control-tower/migration-program" truffles-api/app/routers/console.py`
- `FACT findings`:
  - `BLOCK_GRAPH`/master-report already reference phase13 TP/report paths, but files were absent.
  - Phase12 control-tower contract is implemented and passed (`overview`, `readiness-board`, `drift-board`, `action-center`).
  - Dedicated migration-wave contract (`canary -> cohort -> fleet`) is not materialized in API/schema/tests; migration decisions are currently distributed across separate control-tower surfaces.

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google workbook canarying releases error budget policy`
- **Date/time (local):** `2026-03-02 09:53 (+0500)`
- **Why this query is precise:** нужен high-signal reference для волнового rollout/gate контракта (`go/no-go`, rollback criteria), чтобы phase13 не стал ad-hoc orchestration.
- **Sources opened (from this query):**
  - `https://sre.google/workbook/canarying-releases/`
  - `https://sre.google/workbook/alerting-on-slos/`
  - `https://sre.google/workbook/error-budget-policy/`
- **Existing solutions found:**
  - phased canary rollout with explicit promotion/rollback criteria,
  - SLO burn-rate signal as go/no-go gate,
  - error-budget policy mapped to deterministic actions.
- **Decision:** `reuse/integrate` SRE wave-governance pattern into existing control-tower runtime contracts; avoid building separate migration subsystem.
- **Rejected options:**
  - manual checklist-only rollout without runtime gate signals,
  - fleet-wide promotion without canary/cohort evidence ladder.
- **Open questions:**
  - final threshold values for automatic promotion from `cohort` to `fleet` per domain lane.

## Root cause (mandatory)
- **Symptom:** `UCPV1-PHASE13` is queue head in master program, but migration contract is still operationally fragmented.
- **Minimal reproduction:**
  - `rg -n "UCPV1-PHASE13|phase13" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md` -> references exist.
  - `ls -l docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md` -> files absent.
  - `rg -n "/admin/control-tower/migration-program" truffles-api/app/routers/console.py` -> no migration endpoint.
- **Evidence:**
  - phase13 artifact gap in docs,
  - absence of single migration-wave API surface,
  - existing phase12 control-tower primitives in runtime.
- **Five Whys (or equivalent):**
  1. Why phase13 is not executable: no canonical TP/report existed.
  2. Why delivery is fragmented: migration gates are distributed across separate endpoints.
  3. Why this is risky: promotion/rollback decisions are harder to audit and automate.
  4. Why automation is weakened: no single contract for wave summary and blockers.
  5. Why fix now: phase13 is queue head after phase12 passed; delays keep migration governance as manual process debt.
- **Root cause statement:**
  - после закрытия phase12 отсутствовал выделенный phase13 delivery-контур (canonical artifacts + unified wave-gate API), поэтому migration orchestration осталась разрозненной и неаудируемой как один контракт.
- **Fix mechanism:**
  - materialize phase13 artifacts and deliver slice1 migration board endpoint that reuses existing control-tower signals to compute deterministic wave gates and rollback triggers.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_build_admin_control_tower_readiness_board`
  - `_build_admin_control_tower_drift_board`
  - `_build_admin_control_tower_action_center`
  - existing control-tower schemas and platform-admin RBAC path in `console.py`.
- **External reuse:**
  - Google SRE workbook patterns for canary promotions and error-budget gates.
- **Why not reinvent the wheel:**
  - runtime already calculates required risk/readiness/drift/action signals; phase13 needs orchestration contract, not a new analytics engine.

## Invariant
- Platform-admin authorization remains mandatory and fail-closed.
- Tenant isolation and hard-law boundaries remain unchanged.
- Product outcome contract (`FACT/COLLECT/HANDOFF`) unchanged.
- No semantic hardcode in policy-core runtime.

## Scope
- Create canonical phase13 TP/report artifacts.
- Move `UCPV1-PHASE13` from `planned` to `in_progress` in graph/master/state/session sync.
- Deliver phase13 slice1 backend contract:
  - `GET /console/v1/admin/control-tower/migration-program`.
- Add migration program schemas and deterministic tests.
- Sync OpenAPI after contract delta.

## Out of scope
- Closing phase13 to `passed` in this slice.
- Executing production wave promotions/mutations.
- New background workers or cross-service scheduler introduction.
- Refactor/decomposition of entire `console.py`.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`

## Plan (1..N)
1. Create phase13 TP/report and sync canon status to `in_progress`.
2. Implement migration board builder + endpoint by reusing phase12 control-tower builders.
3. Add schemas for migration waves/summary/gates/rollback triggers.
4. Add deterministic tests for RBAC, empty scope, and wave aggregation path.
5. Run lint/tests/openapi/session gates and update report/state evidence.

## DoD
- Phase13 TP/report exist and are linked from block graph/master report.
- `UCPV1-PHASE13` status is `in_progress` with evidence-backed analysis gate.
- New endpoint `GET /console/v1/admin/control-tower/migration-program` is implemented and covered by deterministic tests.
- OpenAPI drift gate is green.
- Session artifacts (`SESSION` + `SESSION_INDEX`) point to phase13 TP.

## Checks
- `SESSION_AGENT=a701 scripts/session_check.sh`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md --graph docs/BLOCK_GRAPH.yaml`
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py tests/test_console_owner_business.py`
- `cd truffles-api && pytest -q tests/test_console_owner_business.py tests/test_console_fleet_attention.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` expensive realism runs for this slice.
- **Fail-fast / scenario lock:** deterministic control-tower suites only.
- **Stop condition:** if two consecutive iterations add no new evidence, stop and return to RCA.
- **Escalation path:** Brain/Top Architect for scope growth beyond slice1.

## Release safety (mandatory for non-doc changes)
- **Strategy:** read-only migration board rollout behind platform-admin RBAC.
- **Go/no-go signals:** wave `canary/cohort/fleet` gate states computed from readiness/drift/action-center summaries.
- **Rollback:** revert migration endpoint/schema commit; phase12 endpoints remain source of truth.
- **Post-release monitoring window:** `24h` for API error rate and contract usage sanity.

## Doc sync plan (after implementation)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
- `docs/SESSION_INDEX.md`

## Rollback
- Revert phase13 slice1 commit and set `UCPV1-PHASE13` back to `planned` if contract is not fit.
- Remove phase13 session/report references in the same rollback commit.

## No-go
- Marking phase13 as `passed` in slice1.
- Writing promotion mutations without explicit rollout gate contract.
- Replacing wave governance with static/manual-only checklist.

## Risks/Blockers
- Phase13 logic still sits in `console.py` and may need later decomposition.
- Threshold policy values for strict auto-promotion are still pending owner calibration.
- Existing stale active sessions in global index remain process noise (non-blocking for this block).

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes (after slice1 checks green).
- `Start from`: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`.
- `Do not touch`: unrelated tracks outside phase13/control-tower migration contract.
- `Open risks`: threshold calibration and console router blast radius.
- `First command to verify`: `rg -n "UCPV1-PHASE13|migration-program|in_progress" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md truffles-api/app/routers/console.py`.
