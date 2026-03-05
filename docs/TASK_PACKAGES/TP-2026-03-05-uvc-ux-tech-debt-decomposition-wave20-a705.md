# TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave20-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE20-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW15-A705 = Open`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW16-A705`

## Название/цель
Закрыть failed criterion `C1` из closure-review15: опустить `console.py` до порога `<=24396` через bounded extraction без изменения продуктового поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review15-a705.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes; extraction only inside existing router/wizard flow.
- `REQ-2` no shortcuts:
  - solution: no gate weakening, no behavior hardcodes.
- `REQ-3` optimize existing tabs first:
  - solution: reduce orchestration concentration in existing files.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`

## One web search (mandatory before implementation)
- **Query (exact):** `Martin Fowler refactoring Extract Function Composing Methods`
- **Date/time (local):** `2026-03-05 17:58 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/extractFunction.html`
- **Found reusable solution:** shrink high-context methods by delegating cohesive orchestration blocks behind explicit helper boundaries.
- **Decision:** bounded `reuse -> integrate -> configure -> build` wave focused on `console.py` extraction to meet criterion `C1`.
- **Rejected options:** one-shot router rewrite and threshold override.

## Root cause (mandatory)
- **Symptom:** closure-review15 binary DoD failed (`C1/LOC threshold`).
- **Minimal reproduction:** `wc -l` on merged-main: `console.py=24469`, threshold is `<=24396`.
- **Evidence:** closure-review15 artifact.
- **Five Whys:**
  1. `console.py` still exceeds threshold because cross-domain orchestration blocks remain in router.
  2. Those blocks stay because previous waves prioritized safer, smaller slices.
  3. Remaining concentration increases merge risk and maintenance cost.
  4. Binary DoD blocks `Fixed` until threshold is met.
  5. Therefore wave20 must target the remaining high-context orchestration slice directly.
- **Root cause statement:** residual orchestration concentration in router keeps LOC above closure threshold despite prior waves.
- **Fix mechanism:** extract one additional cohesive orchestration slice from `console.py` to service helper(s) and preserve deterministic parity.

## Reuse-first plan (mandatory)
- **Internal reuse:** `console_control_tower_program.py`, `console_control_tower_utils.py`, existing control-tower deterministic tests.
- **External reuse:** Extract Function refactoring catalog pattern.
- **Why not build from scratch:** bounded extraction minimizes regression blast radius.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `3`
- **Code dominance:** `required`
- **Override token:** `UVC_SCOPE_OVERRIDE_A705`
- **Why this profile fits:** wave20 is runtime extraction with minimal docs.

## Invariant
- No API contract drift on existing `/admin/*` routes.
- No new top-level tabs/routes.
- Deterministic lane remains green.

## Scope
- Backend extraction in `console.py` targeting criterion `C1`.
- Minimal frontend touch only if required to keep parity.
- Closure-review16 contract preparation.

## Out of scope
- New product features.
- Full router rewrite.
- Policy/LAW changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_control_tower_program.py`
- `truffles-api/tests/test_console_control_tower_program.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/components/ProvisioningWizard.tsx` (only if parity needs)
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave20-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705.md`

## Plan (1..N)
1. Identify the highest-LOC cohesive orchestration slice in `console.py` tied to control-tower board assembly.
2. Extract to service helper boundary and rewire router calls.
3. Extend deterministic tests for extracted behavior.
4. Run full deterministic lane and verify `C1` threshold.
5. Publish wave20 artifact and lock closure-review16 TP.

## DoD
- `console.py <= 24396` and `ProvisioningWizard.tsx <= 4296`.
- Deterministic lane green.
- Extracted helper contracts are explicitly covered in tests.
- session/canon sync complete.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `pytest -q truffles-api/tests/test_console_owner_business.py -k "control_tower and (drift_board or readiness_board)"`
- `SESSION_TP_SCOPE_OVERRIDE=UVC_SCOPE_OVERRIDE_A705 SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Wave20 artifact with before/after LOC and failed-criteria closure.
- PR URL + CI URL.
- Canon diff (`UX_BACKLOG`, master report, session docs).

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- Max targeted rerun attempts for same hypothesis: `1`.
- Stop condition: deterministic regression or no LOC improvement -> stop and return to RCA.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded canary-by-PR merge with required CI checks.
- **Go/no-go signals:** deterministic lane green + `C1` threshold met.
- **Rollback:** revert wave20 merge commit.
- **Post-release monitoring window:** closure-review16 on merged-main evidence.

## Rollback
- `git revert MERGE_COMMIT_SHA` + rerun deterministic lane.

## No-go
- Threshold override without owner-approved contract update.
- Runtime behavior change unrelated to extraction target.

## Риски/блокеры
- Parallel merges can increase router LOC during wave20.
- Oversized extraction can create merge-red risk.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: possible residual in wizard file if backend-only wave closes `C1` first.
- `Why not in this block`: prioritizing failed criterion from closure-review15.
- `Risk if deferred`: lingering cross-domain complexity in parent files.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705.md`.
- `Expiry/trigger to stop deferral`: if closure-review16 still fails binary matrix, next wave must start immediately with failed-criteria map.

## Next-block contract (mandatory)
- `Next block objective`: closure-review16 fail-closed decision on merged-main wave20 evidence.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave20 PR not merged or deterministic lane red.
- `Owner role for closure`: Brain + Top Architect.
