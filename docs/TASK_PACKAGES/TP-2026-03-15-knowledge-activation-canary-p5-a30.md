# TP-2026-03-15-knowledge-activation-canary-p5-a30

## Block identity
- `BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-CANARY-P5-A30`
- `PARENT_BLOCK_ID`: `CONSOLE-KNOWLEDGE-ACTIVATION-ADMIN-OBS-P4-A30`
- `DEPENDS_ON`: `CONSOLE-KNOWLEDGE-ACTIVATION-ADMIN-OBS-P4-A30`
- `UNLOCKS`: `CONSOLE-KNOWLEDGE-ACTIVATION-CLOSEOUT-P6-A30`

## Название/цель
Закрыть rollout gap для dedicated knowledge activation worker/service: включить service в canonical release flow, добавить machine-readable canary/go-no-go guard и зафиксировать rollback SOP так, чтобы deploy не оставлял activation service на старом image и не зависел от ручного чтения health/logs.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-admin-observability-p4-a30.md`
- `CA_ID`: `UX-50`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `scripts/restart_release.sh`
  - `scripts/restart_knowledge_activation_service.sh`
  - `truffles-api/scripts/knowledge_activation_release_guard.py`
  - `truffles-api/tests/test_knowledge_activation_release_guard.py`
  - `truffles-api/tests/test_restart_release_scripts.py`
  - `TECH.md`
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`
- `FACT findings`:
  - P3 introduced a dedicated activation worker/service, but `scripts/restart_release.sh` still restarts only API + workers and does not include `truffles-knowledge-activation-service` in release parity.
  - P4 added admin health/metrics/ops disclosure, but there is still no single canary command that proves activation service health, process endpoint reachability, metrics exposure, and admin health signals after deploy.
  - Current rollout still depends on manual operator discipline instead of a machine-readable go/no-go artifact.

## One web search (mandatory before implementation)
- **Query (exact):** `Google SRE Workbook canarying releases go no-go signals`
- **Date/time (local):** `2026-03-15 18:45 +05`
- **Sources opened (from this query):** `https://sre.google/workbook/canarying-releases/`
- **Found options:** explicit canary stages, attributable go/no-go signals, and cheap rollback are mandatory; rollout decisions should be based on measured service health rather than intuition.
- **Decision:** `reuse/integrate` — add a bounded release guard artifact and explicit go/no-go checks to the existing deploy scripts instead of inventing a second deployment path.
- **Rejected options:** manual checklist only; hidden ad-hoc curls without artifact output.

## Root cause (mandatory)
- **Symptom:** activation transport is implemented and observable, but release promotion can still leave the dedicated service on an old image or proceed without a deterministic go/no-go result.
- **Minimal reproduction:** deploy through `scripts/restart_release.sh`; API + workers are restarted and parity-checked, but `truffles-knowledge-activation-service` is untouched, and there is no machine-readable canary artifact proving `/health`, `/knowledge-activation/process`, admin health, and metrics after rollout.
- **Evidence:** `scripts/restart_release.sh`, `scripts/restart_knowledge_activation_service.sh`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`.
- **Five Whys (or equivalent):**
  1. Why can deploy drift activation service? Because release parity checks cover API + workers only.
  2. Why is that a problem now? Because activation service became part of the dedicated transport ownership in P3.
  3. Why isn't P4 observability enough? Because visibility after deploy still requires manual multi-step interpretation.
  4. Why is manual interpretation risky? Because canary decisions become inconsistent and rollback gets delayed.
  5. Why is this architectural, not only ops polish? Because deploy correctness is part of the runtime contract for the new activation model.
- **Root cause statement:** the canonical release flow was never updated to treat the dedicated activation service as a first-class release target, and rollout still lacks a deterministic canary artifact built from activation-specific health signals.
- **Fix mechanism:** extend canonical release flow to restart/verify the activation service, add a single release-guard command that emits go/no-go JSON from health/process/metrics signals, and document rollback using the same path.

## Reuse-first plan (mandatory)
- **Internal reuse:** `scripts/restart_release.sh`, `scripts/restart_knowledge_activation_service.sh`, P4 `health_service.py` + `/admin/health/check`, P3 `/knowledge-activation/process`, existing release parity pattern in `restart_api.sh` / `restart_workers.sh`.
- **External reuse:** Google SRE Workbook canarying guidance.
- **Why not reinvent the wheel:** deploy/restart/parity primitives already exist; this block only needs to wire the activation service into them and add one bounded guard artifact.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `12`
- **Code dominance:** `ops/release automation`
- **Override token:** `none`
- **Why this profile fits:** this block is mainly release scripts, one verification script, deterministic script tests, and runbook/canon sync.

## Invariant
- P0/P1/P2/P3/P4 runtime semantics must not change.
- Release guard must not mutate knowledge artifacts or activation jobs beyond calling the existing safe process endpoint.
- Rollout/rollback must use the same canonical deploy path; no second hidden deployment flow.

## Scope
- Extend canonical release flow to include knowledge activation service restart/parity.
- Add machine-readable activation release guard (health/process/admin-health/metrics).
- Document canary/go-no-go/rollback SOP.

## Out of scope
- New product UI.
- PagerDuty/alert routing changes.
- Automatic tenant-specific publish scenarios in production.

## Touch-list
- `scripts/restart_release.sh`
- `scripts/restart_knowledge_activation_service.sh`
- `truffles-api/scripts/knowledge_activation_release_guard.py`
- `truffles-api/tests/test_knowledge_activation_release_guard.py`
- `truffles-api/tests/test_restart_release_scripts.py`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md`

## Plan
1. Extend release scripts so activation service can be restarted and parity-checked in the canonical deploy path.
2. Add a release-guard CLI that checks activation service `/health`, `/knowledge-activation/process`, admin health `checks.knowledge_activation`, and metrics exposure, then writes a go/no-go artifact.
3. Add deterministic tests for the guard CLI and release-script orchestration.
4. Write the rollout/canary/rollback runbook and sync canon/session docs.

## DoD
- `restart_release.sh` can include `truffles-knowledge-activation-service` in the same release/parity contract as API/workers.
- A single guard command emits JSON with decision `go|no_go`, reasons, and activation evidence.
- Runbook documents exact deploy/canary/rollback commands and go/no-go signals.
- Deterministic tests cover both the guard logic and release-script orchestration.

## Checks
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && pytest -q tests/test_knowledge_activation_release_guard.py tests/test_restart_release_scripts.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30/truffles-api && ruff check scripts/knowledge_activation_release_guard.py tests/test_knowledge_activation_release_guard.py tests/test_restart_release_scripts.py`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && bash -n scripts/restart_release.sh scripts/restart_knowledge_activation_service.sh`
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && SESSION_AGENT=a30 bash scripts/session_check.sh`

## Token / run budget (mandatory for expensive suites)
- **Hypothesis:** wiring the activation service into the release path plus a single release-guard artifact will make canary/go-no-go deterministic and rollback cheap.
- **Expected measurable effect:** one command path restarts API/workers/activation service together, and one guard artifact proves post-deploy activation health without manual interpretation.
- **Max full runs:** `1`
- **Max targeted reruns per failure family:** `2`
- **Stop condition:** stop after one green script/CLI test pass, one green shell syntax pass, and one green session gate.

## Evidence
- Diff showing activation service included in release flow.
- Release-guard artifact schema/CLI.
- Deterministic test output for guard + release orchestration.
- Runbook commands with explicit rollback.

## Rollback
- Revert P5 scripts/runbook changes and keep P4 observability intact; deploys can still use the older API+workers path while the activation service is managed manually.

## Release safety (mandatory for non-doc changes)
- **Strategy:** additive rollout automation only; runtime activation logic remains unchanged.
- **Go/no-go signals:** activation service health returns `ok`, process endpoint returns 200, admin health exposes non-error `checks.knowledge_activation`, metrics export activation gauges, and image parity includes the activation service container.
- **Post-release monitoring window:** first 30 minutes after deploy with one captured guard artifact and one repeated health snapshot.
- **Rollback:** redeploy previous image digest through the same `restart_release.sh` path with activation service restart enabled, then rerun the release guard.

## No-go
- Do not introduce a second deployment path.
- Do not auto-mutate knowledge versions/jobs just to manufacture canary evidence.
- Do not weaken health gates to hide activation warnings/criticals.

## Risks/Blockers
- Production rollout depends on env/token availability for internal service/process checks.
- Shell-script tests must stay hermetic and not call real docker.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- No tenant-specific synthetic publish/retry canary yet; P5 verifies service/control-plane health, not end-to-end customer publish scenarios.

### Why not in this block
- This block closes deploy correctness first; branch-specific synthetic activation would need staged tenant data and stronger prod choreography.

### Risk if deferred
- Deploy safety is controlled, but final closeout still lacks a reusable tenant-level synthetic activation scenario.

### Linked follow-up Task Package(s)
- `TP-2026-03-15-knowledge-activation-closeout-p6-a30.md`

### Expiry/trigger to stop deferral
- If activation regressions still require tenant-specific publish rehearsal after P5 rollout, P6 becomes mandatory before declaring the program closed.

## Next-block contract (mandatory)
### Next block objective
- Close the program with final rollout evidence or tenant-level synthetic activation proof if still needed.

### First deterministic check command
- `cd /home/zhan/worktrees/2026-03-15-knowledge-release-model-stoploss-a30 && rg -n 'RESTART_KNOWLEDGE_ACTIVATION_SERVICE|RUN_KNOWLEDGE_ACTIVATION_CANARY|knowledge_activation_release_guard' scripts truffles-api/scripts docs/runbooks`

### Blocked-by conditions
- P5 release path and guard artifact must land first.

### Owner role for closure
- `Top Architect | Brain`
