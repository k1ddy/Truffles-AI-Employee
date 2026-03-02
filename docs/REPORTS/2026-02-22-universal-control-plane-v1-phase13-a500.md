# Universal Control Plane v1 - Phase 13 Migration Program (a500)

Date
- 2026-03-02

## Block identity
- `BLOCK_ID`: UCPV1-PHASE13
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE12
- `UNLOCKS`: none

## Input baseline (FACT)
- `UCPV1-PHASE12` is `passed` and queue head moved to `UCPV1-PHASE13` planning track.
- Phase12 runtime/control-plane already exposes core migration signals:
  - `GET /console/v1/admin/control-tower/overview`,
  - `GET /console/v1/admin/control-tower/readiness-board`,
  - `GET /console/v1/admin/control-tower/drift-board`,
  - `GET /console/v1/admin/control-tower/action-center`.
- Dedicated phase13 artifacts and single migration-wave API contract were absent before this slice.

## FACT pre-check evidence (before changes)
- `rg -n "UCPV1-PHASE13|phase13" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md docs/TASK_PACKAGES docs/REPORTS` -> references existed in graph/master but no concrete phase13 artifacts.
- `ls -l docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md` -> `No such file or directory` before fix.
- `rg -n "/admin/control-tower/(overview|readiness-board|drift-board|action-center)" truffles-api/app/routers/console.py` -> phase12 control-tower primitives present.
- `rg -n "/admin/control-tower/migration-program" truffles-api/app/routers/console.py` -> migration-wave endpoint absent.

## One web search evidence
- `Query (exact)` -> `site:sre.google workbook canarying releases error budget policy`
- `Sources opened`:
  - `https://sre.google/workbook/canarying-releases/`
  - `https://sre.google/workbook/alerting-on-slos/`
  - `https://sre.google/workbook/error-budget-policy/`
- `Decision` -> reuse SRE canary/error-budget governance for phase13 wave gates (`canary -> cohort -> fleet`) and rollback triggers.

## Root cause validation
- `Symptom` -> phase13 remained planning-only despite being queue head after phase12 closure.
- `Minimal reproduction` -> phase13 TP/report missing + no unified migration-wave endpoint.
- `Root cause statement` -> governance and runtime orchestration drift: migration decisions depended on fragmented phase12 surfaces without a dedicated phase13 contract.
- `Fix mechanism` -> create phase13 canonical artifacts and deliver slice1 migration board endpoint that computes wave gates from existing control-tower signals.

## Reuse-first outcome
- `Internal reuse applied` -> yes (`readiness-board`, `drift-board`, `action-center` builders and schemas).
- `External reuse applied` -> yes (SRE workbook canary/error-budget patterns).
- `Build-new scope` -> only migration orchestration contract (read-only API + schema/tests).

## Contract delta
- Added canonical phase13 artifacts:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- Program status contract update:
  - `UCPV1-PHASE13`: `planned -> in_progress`.
- Slice1 runtime contract target:
  - `GET /console/v1/admin/control-tower/migration-program`.

## Implemented changes
- Created phase13 Task Package with mandatory gates and migration-wave slice1 contract.
- Created this phase13 Report as canonical execution artifact.
- Synced canon status/docs to start phase13 execution track:
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
  - `docs/SESSION_INDEX.md`
- Delivered phase13 slice1 runtime contract:
  - new platform-admin endpoint `GET /console/v1/admin/control-tower/migration-program`.
  - new migration schemas:
    - `ConsoleAdminControlTowerMigrationWave`,
    - `ConsoleAdminControlTowerMigrationProgramSummary`,
    - `ConsoleAdminControlTowerMigrationProgramResponse`.
  - new control-tower migration builder:
    - `_build_admin_control_tower_migration_program` with wave gates `canary/cohort/fleet`,
    - deterministic gate evaluation (`go|hold`) based on readiness/drift/action-center signals,
    - explicit rollback trigger reasons.
  - deterministic test coverage for endpoint RBAC, parameter pass-through, and wave aggregation contract.
  - OpenAPI contract synced with new endpoint.

## Slice 1 update (runtime integration)
- `GET /console/v1/admin/control-tower/migration-program` implemented and wired under platform-admin RBAC.
- Reuse path applied:
  - `_build_admin_control_tower_readiness_board`,
  - `_build_admin_control_tower_drift_board`,
  - `_build_admin_control_tower_action_center`.
- Wave contract:
  - `canary`: strict gate for P0/hard blockers and low soft-blocker budget.
  - `cohort`: medium soft-blocker budget with same hard-block protections.
- `fleet`: zero-budget promotion gate (hold when blockers remain).
- Rollback triggers are emitted as deterministic reason codes (`incident_p0_open`, `readiness_hard_gate_failed`, `provider_ops_p0_queue`, etc.).

## Slice 2 update (signals + promotion actions)
- Migration program response extended with rollout signals:
  - `ready_branches` (`pass/fail`, threshold `>=1`),
  - `hard_blockers` (`pass/fail`, threshold `==0`),
  - `soft_blockers` (`pass/warn/fail`, threshold `<=3`),
  - `blocked_branches` (`pass/fail`, threshold `==0`).
- Empty scope response now explicitly emits fail signal `active_clients` with threshold `1` to keep fail-closed behavior transparent in UI/API.
- Added deterministic promotion action projection:
  - action-center items map to migration wave by priority (`p0 -> canary`, `p1 -> cohort`, `p2 -> fleet`),
  - each projected action carries current wave gate (`go|hold`) for operator-facing promotion queue.
- Contract and schema deltas:
  - `ConsoleAdminControlTowerMigrationSignal`,
  - `ConsoleAdminControlTowerPromotionAction`,
  - `signals` and `promotion_actions` added to migration program response.
- Deterministic test coverage extended:
  - validates signal statuses and thresholds in aggregated response,
  - validates action-to-wave mapping and gate propagation,
  - validates explicit empty-scope fail signal behavior.

## Slice 2 checks + outcomes
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py tests/test_console_owner_business.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k \"migration_program or control_tower\"` -> `15 passed, 41 deselected`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py tests/test_console_fleet_attention.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py` -> `105 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> contract check passed after syncing `contracts/console_api/openapi.v1.yaml` from generated spec.
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md --graph docs/BLOCK_GRAPH.yaml` -> `zero_context_gate: OK`.
- `SESSION_AGENT=a702 scripts/session_check.sh` -> `Session OK`.

## Slice 3 update (wave detail execution view)
- Added per-wave operational endpoint:
  - `GET /console/v1/admin/control-tower/migration-program/{wave}` for `wave in {canary, cohort, fleet}`.
- New wave-detail contract returns deterministic operator decision:
  - `decision`: `promote|hold`,
  - `reason`: current wave reason,
  - `promotion_actions`: only actions for selected wave,
  - `promotion_actions_total`: full action count for selected wave before limit.
- Reuse path preserved:
  - wave detail endpoint reuses existing migration program builder output (no duplicated control-tower aggregation queries).
- Contract/schema deltas:
  - `ConsoleAdminControlTowerMigrationWaveDetailResponse` added to console schemas.
- Deterministic test coverage extended:
  - RBAC deny for non-platform role on wave-detail endpoint,
  - endpoint parameter pass-through + per-wave action filtering,
  - helper-level action-count/limit behavior for selected wave.

## Slice 3 checks + outcomes
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py tests/test_console_owner_business.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k \"migration_program or migration_wave_detail or control_tower\"` -> `18 passed, 41 deselected`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py tests/test_console_fleet_attention.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py` -> `108 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> initial drift found (`GET /console/v1/admin/control-tower/migration-program/{wave}` missing in contract), then synced `contracts/console_api/openapi.v1.yaml` from generated spec and recheck passed.
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md --graph docs/BLOCK_GRAPH.yaml` -> `zero_context_gate: OK`.
- `SESSION_AGENT=a703 scripts/session_check.sh` -> `Session OK`.

## Checks + outcomes
- `cd truffles-api && ruff check app/routers/console.py app/schemas/console.py tests/test_console_owner_business.py` -> `All checks passed`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py -k \"migration_program or control_tower\"` -> `14 passed, 41 deselected`.
- `cd truffles-api && pytest -q tests/test_console_owner_business.py tests/test_console_fleet_attention.py tests/test_console_ops_jobs.py tests/test_console_onboarding_state.py` -> `104 passed`.
- `cd truffles-api && python3 scripts/generate_openapi.py --check` -> initial drift found (`GET /console/v1/admin/control-tower/migration-program` missing in contract), then synced `contracts/console_api/openapi.v1.yaml` from generated spec and recheck passed.
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md --graph docs/BLOCK_GRAPH.yaml` -> `zero_context_gate: OK`.
- `SESSION_AGENT=a701 scripts/session_check.sh` -> `Session OK`.

## Iteration budget outcomes
- `Planned max runs` -> 0 expensive realism runs.
- `Actual runs` -> 0 expensive realism runs (current slice).
- `Stop condition respected` -> yes.

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
- `docs/SESSION_INDEX.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-slice2-a702.md`
- `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-slice3-a703.md`

## Release safety decision
- `Strategy used` -> read-only platform-admin API contract expansion.
- `Go/no-go signals` -> migration wave gates derived from existing control-tower risk/readiness/drift/action data.
- `Rollback readiness` -> single commit revert restores pre-phase13 behavior.

## Canon/doc sync updates
- `Updated docs`:
  - `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `docs/SESSIONS/SESSION-2026-03-02-ucpv1-phase13-a701.md`
  - `docs/SESSION_INDEX.md`

## Residual GAP / Risks
- Threshold values for fully automatic promotion remain product calibration task.
- Control-tower logic concentration in `console.py` remains technical debt for later decomposition.

## Handoff (for zero-context next agent)
- `Ready for next agent`: after current slice checks pass.
- `Start from`: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase13-a500.md`.
- `Do not touch`: unrelated tracks outside phase13 migration contract.
- `Open risks`: threshold calibration and router blast radius.
- `First command to verify`: `rg -n "UCPV1-PHASE13|migration-program|migration-program/\\{wave\\}|in_progress" docs/BLOCK_GRAPH.yaml docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md truffles-api/app/routers/console.py`.

## Verdict
- `In progress`
