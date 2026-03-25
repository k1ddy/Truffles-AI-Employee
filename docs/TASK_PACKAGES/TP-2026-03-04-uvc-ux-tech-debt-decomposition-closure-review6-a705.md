# TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review6-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW6-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE10-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE11-A705` (only if residual remains)

## Название/цель
Выполнить closure-review после wave10 и принять fail-closed merged-main решение по `UX-11/UX-12`: `Fixed` или `Open + wave11`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave10-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review6 is evidence/governance only; runtime untouched.
- `REQ-2` no shortcuts:
  - solution: decision based on merged-main deterministic evidence, not wave count.
- `REQ-3` optimize existing tabs first:
  - solution: if residual remains, next block is internal wave11 decomposition only.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`

## One web search (mandatory before implementation)
- **Query (exact):** `DORA metrics software delivery reliability change failure rate lead time for changes`
- **Date/time (local):** `2026-03-04 16:13 +0500`
- **Sources opened (from this query):**
  - `https://dora.dev/`
  - `https://dora.dev/guides/dora-metrics/`
- **Found reusable solution:** closure decisions should remain evidence-based and mapped to reliability guardrails.
- **Decision:** preserve fail-closed closure policy on merged-main evidence.
- **Rejected options:** marking `Fixed` solely from number of completed waves.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` may remain open after wave10.
- **Minimal reproduction:** compare merged-main LOC + deterministic suite + residual hotspots in parent files.
- **Evidence:** wave10 artifact and merged-main check outputs.
- **Five Whys:**
  1. why uncertainty remains: wave10 extraction is intentionally bounded;
  2. why risk persists: broad parent files may still carry orchestration concentration;
  3. why closure-review is required: avoid false `Fixed` status;
  4. why fail-closed: protect maintainability contract;
  5. why now: wave10 completion requires explicit merged-main decision.
- **Root cause statement:** structural debt may still remain after wave10 and must be judged by objective evidence.
- **Fix mechanism:** evidence-based closure decision with immediate next-wave contract if open.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse wave1-10 artifacts, extracted modules, deterministic test lane, and canon sync pattern.
- **External reuse:** DORA reliability/maintainability guidance for objective closure criteria.
- **Why not build from scratch:** closure-review6 is governance-only, not runtime implementation.

## Invariant
- No runtime code changes.
- No new routes/tabs.
- Decision is evidence-first and fail-closed.

## Scope
- Revalidate merged-main wave10 baseline.
- Publish closure-review6 artifact with explicit `UX-11/UX-12` decision.
- Sync canon/session docs.

## Out of scope
- Runtime wave11 implementation.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review6-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `STRUCTURE.md`
- session docs/index

## Plan (1..N)
1. Capture merged-main wave10 deterministic baseline.
2. Publish closure-review6 artifact with `Fixed/Open` decision.
3. Sync canon/session docs and run `session_check`.
4. Open PR.

## DoD
- closure-review6 artifact published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave10 merged PR URL + commit SHA.
- merged-main deterministic outputs.
- closure-review6 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (docs/evidence decision block).
- E2E policy: reuse wave10 green acceptance evidence because runtime unchanged.
- Stop condition: if runtime edits are required, stop and switch to wave11 implementation block.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review6 commit.
- **Post-release monitoring window:** wave11 block reruns targeted acceptance lane if opened.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `Fixed` without deterministic merged-main evidence.
- Mixing runtime refactor into closure-review6 docs block.

## Риски/блокеры
- Parallel `main` changes can skew LOC trend.
- Decision bias if deterministic checks are skipped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided from merged-main wave10 evidence.
- `Why not in this block`: closure-review6 is governance-only.
- `Risk if deferred`: repeated high-context edits in monoliths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave11-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if closure-review6 is `Open`, wave11 starts immediately as next block.

## Next-block contract (mandatory)
- `Next block objective`: either mark `UX-11/UX-12` as `Fixed` or execute wave11 bounded extraction.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave10 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
