# TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review15-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW15-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE19-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE20-A705` (only if residual remains)

## Название/цель
Выполнить closure-review после wave19 и принять fail-closed merged-main решение по `UX-11/UX-12`: `Fixed` или `Open + wave20`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave19-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave19-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review15 is governance-only; runtime unchanged.
- `REQ-2` no shortcuts:
  - solution: decision only from merged-main deterministic evidence.
- `REQ-3` optimize existing tabs first:
  - solution: if residual remains, next block is internal wave20 decomposition only.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`

## One web search (mandatory before implementation)
- **Query (exact):** `DORA metrics software delivery reliability change failure rate lead time`
- **Date/time (local):** `2026-03-05 17:55 +0500`
- **Sources opened (from this query):**
  - `https://dora.dev/guides/dora-metrics/`
- **Found reusable solution:** closure decisions must stay evidence-first with deterministic reliability checks.
- **Decision:** keep fail-closed closure policy on merged-main evidence.
- **Rejected options:** marking `Fixed` by wave count only.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` can remain open after wave19.
- **Minimal reproduction:** wave19 can still leave parent files above closure threshold despite bounded extraction.
- **Evidence:** wave19 artifact + merged-main deterministic outputs.
- **Five Whys:**
  1. why uncertainty remains: wave19 extraction is bounded by contract;
  2. why residual risk can persist: parent files can still carry multi-domain orchestration;
  3. why closure-review is mandatory: prevent false `Fixed` status;
  4. why fail-closed: protect maintainability contract;
  5. why now: wave19 completion requires explicit merged-main decision.
- **Root cause statement:** structural debt closure cannot be inferred from wave completion; objective merged-main evidence is required.
- **Fix mechanism:** fail-closed decision block with immediate follow-up contract if residual remains.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse wave19 artifact, extracted modules, deterministic test lane, and canon sync pattern.
- **External reuse:** DORA reliability guidance for objective closure criteria.
- **Why not build from scratch:** closure-review15 is decision/evidence only.

## Invariant
- No runtime code changes.
- No new routes/tabs.
- Decision is evidence-first and fail-closed.

## Scope
- Revalidate merged-main wave19 baseline.
- Publish closure-review15 artifact with explicit `UX-11/UX-12` decision.
- Sync canon/session docs.

## Out of scope
- Runtime wave20 implementation.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review15-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `STRUCTURE.md`
- session docs/index

## Plan (1..N)
1. Capture merged-main wave19 deterministic baseline.
2. Publish closure-review15 artifact with `Fixed/Open` decision.
3. Sync canon/session docs and run `session_check`.
4. Open PR.

## DoD
- closure-review15 artifact published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave19 merged PR URL + commit SHA.
- merged-main deterministic outputs.
- closure-review15 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` (docs/evidence decision block).
- E2E policy: reuse wave19 acceptance evidence because runtime unchanged.
- Stop condition: if runtime edits are required, stop and switch to wave20 implementation block.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review15 commit.
- **Post-release monitoring window:** wave20 block reruns targeted acceptance lane if opened.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `Fixed` without deterministic merged-main evidence.
- Mixing runtime refactor into closure-review15 docs block.

## Риски/блокеры
- Parallel `main` changes can skew LOC trend.
- Decision bias if deterministic checks are skipped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided from merged-main wave19 evidence.
- `Why not in this block`: closure-review15 is governance-only.
- `Risk if deferred`: repeated high-context edits in monoliths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave20-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if closure-review15 is `Open`, wave20 starts immediately as next block.

## Next-block contract (mandatory)
- `Next block objective`: either mark `UX-11/UX-12` as `Fixed` or execute wave20 bounded extraction.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave19 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
