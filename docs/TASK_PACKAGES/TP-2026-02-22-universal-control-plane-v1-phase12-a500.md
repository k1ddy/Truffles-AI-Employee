# TP-2026-02-22-universal-control-plane-v1-phase12-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE12
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE11
- `UNLOCKS`: UCPV1-PHASE13

## Название/цель
Universal Control Plane v1 / Phase 12: Control Tower for Platform Admin, чтобы fleet управлялся через единый console-контур как default path (risk queue, readiness board, drift board, action center) с evidence-first решениями.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-master-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests (current state)`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_owner_admin.py`
  - `truffles-api/tests/test_console_fleet_attention.py`
  - `truffles-api/tests/test_console_owner_business.py`
  - `truffles-api/tests/test_console_ops_jobs.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
- `Baseline commands`:
  - `rg -n "UCPV1-PHASE12|phase12" docs/BLOCK_GRAPH.yaml docs/TASK_PACKAGES docs/REPORTS`
  - `ls -l docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
  - `rg -n "/admin/fleet/attention|/business/incidents|/ops/jobs|readiness|drift" truffles-api/app/routers/console.py`
  - `cd truffles-api && pytest -q tests/test_console_fleet_attention.py tests/test_console_owner_business.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py`
- `FACT findings`:
  - Runtime already has major control-tower primitives (`/admin/fleet/attention`, incidents, ops jobs, readiness/drift signals) but they are not packaged as canonical phase12 block artifacts.
  - Phase12 canonical files were missing (`docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md`, `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`) while `BLOCK_GRAPH` already referenced them.
  - There is deterministic test coverage around fleet attention, incidents, ops jobs, and onboarding state (`90 passed` baseline suite).

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google SRE Workbook error budget policy burn rate alerting`
- **Date/time (local):** `2026-03-02 08:37 (+0500)`
- **Why this query is precise:** нужен high-signal operational reference для архитектуры control tower, чтобы risk queue и action center базировались на error-budget governance, а не на ad-hoc manual triage.
- **Sources opened (from this query):**
  - Google SRE Book, Chapter 4 Service Level Objectives: `https://sre.google/sre-book/service-level-objectives/`
  - Google SRE Workbook, Alerting on SLOs: `https://sre.google/workbook/alerting-on-slos/`
  - Google SRE Workbook, Appendix B Example Error Budget Policy: `https://sre.google/workbook/error-budget-policy/`
- **Existing solutions found:**
  - objective control loops from SLO/SLI signals,
  - multi-window burn-rate alerting for queue prioritization,
  - explicit error-budget policy with pre-defined actions.
- **Decision:** `reuse/integrate` external SRE governance pattern into phase12 console contracts (risk priority, action catalog, evidence links), reusing existing Truffles endpoints instead of new control plane rewrite.
- **Rejected options:**
  - static risk prioritization by raw incident counters only,
  - CLI-first remediation path for platform operators.
- **Open questions:**
  - final fleet-level SLO thresholds per domain lane and escalation windows for strict go/no-go automation.

## Root cause (mandatory)
- **Symptom:** `UCPV1-PHASE12` remained `planned` even though runtime already contains substantial control-tower logic.
- **Minimal reproduction:**
  - `rg -n "UCPV1-PHASE12|phase12" docs/BLOCK_GRAPH.yaml docs/TASK_PACKAGES docs/REPORTS`
  - `ls -l docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- **Evidence to capture:**
  - missing canonical phase12 TP/report files,
  - existing runtime capabilities in `console.py`,
  - deterministic fleet/ops tests.
- **Five Whys (or equivalent):**
  1. Why phase12 was not progressing: block artifacts were absent.
  2. Why artifacts were absent: focus shifted to prior dependency closures (phase10/phase11).
  3. Why this is risky: runtime implementation outpaces canon tracking and weakens zero-context governance.
  4. Why governance weakens: next agents cannot apply one-block protocol without canonical TP/report.
  5. Why explicit phase12 analysis is required now: control-tower requires coordinated contract across risk/readiness/drift/action surfaces.
- **Root cause statement:**
  - отсутствие канонической phase12 block-обвязки (TP/report + status sync) привело к разрыву между фактической реализацией control-tower примитивов и управляемым delivery-контуром.
- **Fix mechanism:**
  - создать phase12 canonical artifacts, перевести блок в `in_progress`, зафиксировать FACT baseline и запустить phase12 slice-очередь через единый analysis gate.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `GET /console/v1/admin/fleet/attention`,
  - `GET /console/v1/business/incidents` and incident action models,
  - `GET|POST /console/v1/ops/jobs*`,
  - onboarding readiness kernel and drift signals in `console.py`.
- **External reuse:**
  - SRE error-budget and burn-rate governance pattern from official SRE book/workbook.
- **Why not reinvent the wheel:**
  - control-tower domain already partially implemented in runtime; required work is contract consolidation and deterministic alignment, not a new subsystem.

## Invariant
- Tenant isolation and hard-law boundaries remain fail-closed.
- Platform Admin governance remains server-authoritative.
- No semantic hardcode in policy-core runtime.
- Product outcome contract (`FACT/COLLECT/HANDOFF`) remains unchanged.

## Scope
- Create phase12 canonical TP/report artifacts.
- Move `UCPV1-PHASE12` from `planned` to `in_progress` in graph/master/state.
- Capture FACT baseline for control-tower primitives and deterministic test evidence.
- Define slice plan for risk queue, readiness board, drift board, action center consolidation.

## Out of scope
- Closing `UCPV1-PHASE12` to `passed` in this bootstrap slice.
- Starting `UCPV1-PHASE13` migration waves.
- Rewriting existing console runtime paths.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase12-a700.md`
- `STATE.md`

## Plan (1..N)
1. Create missing phase12 TP/report artifacts with mandatory gates and FACT baseline.
2. Run deterministic baseline checks for existing fleet/incident/ops/readiness surfaces.
3. Sync canon status (`BLOCK_GRAPH`, master report, STATE, session metadata) to phase12 `in_progress`.
4. Prepare next implementation slice contract for phase12 consolidation.

## DoD
- Phase12 canonical TP/report files exist and are linked in graph/master docs.
- `UCPV1-PHASE12` status is `in_progress` with evidence-backed analysis gate.
- Deterministic baseline checks for control-tower surfaces are green.
- Session metadata references phase12 TP and has no placeholders.

## Checks
- `SESSION_AGENT=a700 scripts/session_check.sh`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md --graph docs/BLOCK_GRAPH.yaml`
- `cd truffles-api && ruff check app/routers/console.py tests/test_console_fleet_attention.py tests/test_console_owner_business.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py`
- `cd truffles-api && pytest -q tests/test_console_fleet_attention.py tests/test_console_owner_business.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase12-a700.md`
- `STATE.md`
- `truffles-api/tests/test_console_fleet_attention.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_ops_jobs.py`
- `truffles-api/tests/test_console_onboarding_state.py`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` expensive realism runs in this bootstrap slice.
- **Fail-fast / scenario lock:** deterministic control-tower baseline only.
- **Stop condition:** if two consecutive iterations add no new evidence, stop and return to RCA/contract delta.
- **Escalation path:** Brain/Top Architect for scope expansion beyond analysis bootstrap.

## Release safety (mandatory for non-doc changes)
- **Strategy:** for future non-doc phase12 slices use phased rollout (`internal client -> pilot cohort -> selected production cohorts`).
- **Go/no-go signals:** fleet risk level stability, incident action success ratio, readiness hard-gate false-positive rate, drift backlog trend.
- **Rollback:** disable new phase12 action wiring by feature flag and keep existing fleet/incident read surfaces active.
- **Post-release monitoring window:** `24h` after each phase12 non-doc slice.

## Doc sync plan (after implementation)
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase12-a700.md`

## Rollback
- Revert phase12 bootstrap commit and set `UCPV1-PHASE12` back to `planned`.
- Remove phase12 references from session/state updates in the same revert commit.

## No-go
- Marking phase12 as `passed` without implementation slices and deterministic evidence.
- Introducing CLI-only control flows as default for platform operators.
- Mixing phase12 scope with unrelated runtime tracks.

## Risks/Blockers
- Existing control-tower logic is concentrated in `console.py`; decomposition risk for later slices.
- Fleet SLO threshold policy not yet finalized for strict automated go/no-go.
- Overlap between owner/admin and platform views can create contract ambiguity without explicit phase12 slice boundaries.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `Do not touch`: unrelated tracks outside phase12 docs/control-tower contract.
- `Open risks`: threshold policy finalization and console-router blast radius.
- `First command to verify`: `rg -n "UCPV1-PHASE12|in_progress|phase12-a500" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase12-a500.md`
