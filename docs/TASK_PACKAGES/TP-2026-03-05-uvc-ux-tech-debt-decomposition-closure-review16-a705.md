# TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW16-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE20-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE21-A705` (only if residual remains)

## Название/цель
Выполнить closure-review после wave20 и принять fail-closed merged-main решение по `UX-11/UX-12`: `Fixed` или `Open + wave21`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave20-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave20-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review16 is governance-only; runtime unchanged.
- `REQ-2` no shortcuts:
  - solution: decision only from merged-main deterministic evidence.
- `REQ-3` optimize existing tabs first:
  - solution: if residual remains, next block is internal wave21 decomposition only.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`

## One web search (mandatory before implementation)
- **Query (exact):** `DORA metrics evidence based quality gates software delivery`
- **Date/time (local):** `2026-03-05 18:15 +0500`
- **Sources opened (from this query):**
  - `https://dora.dev/guides/dora-metrics/`
- **Found reusable solution:** closure decisions must stay objective and evidence-first.
- **Decision:** keep fail-closed binary DoD matrix for closure-review16.
- **Rejected options:** closing by wave count without deterministic merged-main checks.

## Root cause (mandatory)
- **Symptom:** even after wave20, `UX-11/UX-12` closure status can be ambiguous without merged-main validation.
- **Minimal reproduction:** branch evidence can diverge from merged-main after concurrent merges.
- **Evidence:** wave20 artifact + merged-main deterministic outputs.
- **Five Whys:**
  1. why ambiguity remains: wave completion does not guarantee final closure state;
  2. why this matters: objective thresholds can regress after merges;
  3. why closure-review is mandatory: prevent false `Fixed` decision;
  4. why fail-closed: protect maintainability contract;
  5. why now: wave20 completion must be converted into merged-main decision.
- **Root cause statement:** structural-debt closure cannot be inferred from implementation completion alone; merged-main objective evidence is mandatory.
- **Fix mechanism:** execute binary DoD matrix and close only when every criterion passes.

## Reuse-first plan (mandatory)
- **Internal reuse:** wave20 artifact, deterministic lane, session/canon sync pattern.
- **External reuse:** DORA reliability guidance for evidence-first decisions.
- **Why not build from scratch:** closure-review16 is governance/evidence-only.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `closure_review`
- **Doc touch budget (files):** `8`
- **Code dominance:** `n/a`
- **Override token:** `none`
- **Why this profile fits:** closure-review16 is a decision block; runtime edits are explicitly forbidden.

## Invariant
- No runtime code changes.
- No new routes/tabs.
- Decision is evidence-first and fail-closed.

## Scope
- Revalidate merged-main wave20 baseline.
- Publish closure-review16 artifact with explicit `UX-11/UX-12` decision.
- Sync canon/session docs.

## Out of scope
- Runtime wave21 implementation.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review16-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `STRUCTURE.md`
- session docs/index

## Plan (1..N)
1. Capture merged-main wave20 deterministic baseline.
2. Publish closure-review16 artifact with `Fixed/Open` decision.
3. Sync canon/session docs and run `session_check`.
4. Open PR.

## DoD
- closure-review16 artifact published.
- `UX-11/UX-12` decision taken by binary matrix (no narrative-only decision allowed):
  - mark `Fixed` only if **all** of the following are true on merged-main:
    - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` gives `console.py <= 24396` and `ProvisioningWizard.tsx <= 4296`;
    - deterministic lane remains green (`35 passed` core lane + `branch_change` lane green);
    - wave20 delegation contract is present and used:
      - `build_admin_control_tower_drift_board_response` and `build_admin_control_tower_readiness_board_response` exist in `console_control_tower_program.py`;
      - `_build_admin_control_tower_drift_board` and `_build_admin_control_tower_readiness_board` in router delegate to those helpers.
  - otherwise status must be `Open` and wave21 TP must list exact failed criteria.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `rg -n "def build_admin_control_tower_drift_board_response|def build_admin_control_tower_readiness_board_response" truffles-api/app/services/console_control_tower_program.py`
- `rg -n "_build_admin_control_tower_drift_board_response|_build_admin_control_tower_readiness_board_response|def _build_admin_control_tower_drift_board|def _build_admin_control_tower_readiness_board" truffles-api/app/routers/console.py`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave20 merged PR URL + commit SHA.
- merged-main deterministic outputs.
- closure-review16 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (docs/evidence decision block).
- E2E policy: reuse wave20 acceptance evidence because runtime unchanged.
- Stop condition: if runtime edits are required, stop and switch to wave21 implementation block.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review16 commit.
- **Post-release monitoring window:** wave21 block reruns targeted acceptance lane if opened.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `Fixed` without deterministic merged-main evidence.
- Mixing runtime refactor into closure-review16 docs block.
- Re-opening wave21 without explicit failed binary criteria from closure-review16 matrix.

## Риски/блокеры
- Parallel `main` changes can skew LOC trend.
- Decision bias if deterministic checks are skipped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided from merged-main wave20 evidence.
- `Why not in this block`: closure-review16 is governance-only.
- `Risk if deferred`: repeated high-context edits in monoliths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave21-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if closure-review16 is `Open`, wave21 starts immediately as next block.

## Next-block contract (mandatory)
- `Next block objective`: either close `UX-11/UX-12` as `Fixed` by binary matrix pass or execute wave21 with failed-criteria map.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave20 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
