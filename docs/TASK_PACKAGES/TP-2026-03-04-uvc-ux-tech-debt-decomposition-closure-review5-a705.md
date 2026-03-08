# TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review5-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW5-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE9-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE10-A705` (only if residual remains)

## Название/цель
Выполнить closure-review после wave9 и принять fail-closed merged-main решение по `UX-11/UX-12`: `Fixed` или `Open + wave10`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave9-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: closure-review5 is evidence/governance only; runtime untouched.
- `REQ-2` no shortcuts:
  - solution: decision based on merged-main deterministic evidence, not wave count.
- `REQ-3` optimize existing tabs first:
  - solution: if residual remains, next block is internal wave10 decomposition only.

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
- **Found reusable solution:** closure decisions should be evidence-based and tied to reliability/maintainability guardrails, not subjective wave progress.
- **Decision:** keep fail-closed decision for `UX-11/UX-12` until objective maintainability risk is reduced.
- **Rejected options:** marking `Fixed` from merge count alone.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` may remain open after wave9 despite additional bounded extraction.
- **Minimal reproduction:** compare merged-main LOC + deterministic suite + residual hotspots in parent files.
- **Evidence:** wave9 artifact and merged-main check outputs.
- **Five Whys:**
  1. why uncertainty remains: wave9 extraction is intentionally bounded;
  2. why risk persists: parent files still host broad orchestration context;
  3. why closure-review is required: avoid false `Fixed` status;
  4. why fail-closed: protect maintainability and regression risk contract;
  5. why now: wave9 merge requires explicit merged-main decision before new wave.
- **Root cause statement:** structural debt remains concentrated in `console.py` and `ProvisioningWizard.tsx` after wave9.
- **Fix mechanism:** merged-main evidence review + explicit next-wave contract if residual stays open.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse wave1-9 artifacts, extracted modules, deterministic test lane, and canon sync workflow.
- **External reuse:** DORA guidance for evidence-first operational decisions.
- **Why not build from scratch:** closure-review5 is governance-only and should not touch runtime behavior.

## Invariant
- No runtime code changes.
- No new routes/tabs.
- Decision is evidence-first and fail-closed.

## Scope
- Revalidate merged-main wave9 baseline.
- Publish closure-review5 artifact with explicit `UX-11/UX-12` decision.
- Sync canon/session docs and set follow-up wave10 contract if residual remains.

## Out of scope
- Runtime wave10 implementation.

## Touch-list
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review5-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave10-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Capture merged-main wave9 deterministic baseline.
2. Publish closure-review5 artifact with `Fixed/Open` decision.
3. If open, lock follow-up TP for wave10 with explicit first checks.
4. Sync canon/session docs and run `session_check`.

## DoD
- closure-review5 artifact published.
- `UX-11/UX-12` status explicitly decided from merged-main evidence.
- follow-up wave10 TP created if status remains open.
- canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` green.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave9 merged PR URL + commit SHA.
- merged-main deterministic outputs.
- closure-review5 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- E2E policy: targeted lane only (`2 tests`) because runtime behavior is unchanged in this block.
- Stop condition: any red deterministic check -> no status promotion, keep residual `Open`.

## Release safety (mandatory for non-doc changes)
- **Strategy:** documentation/evidence-only closure decision.
- **Go/no-go signals:** deterministic checks green + session gate green.
- **Rollback:** revert closure-review5 commit.
- **Post-release monitoring window:** wave10 block reruns targeted acceptance lane.

## Rollback
- `git revert COMMIT_SHA` + rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- Marking `Fixed` without deterministic merged-main evidence.
- Mixing runtime refactor into closure-review5 docs block.

## Риски/блокеры
- Parallel `main` changes can skew LOC trend.
- Decision bias if deterministic checks are skipped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided from merged-main wave9 evidence.
- `Why not in this block`: closure-review5 is governance-only.
- `Risk if deferred`: repeated high-context edits in monoliths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave10-a705.md` (if needed).
- `Expiry/trigger to stop deferral`: if closure-review5 is `Open`, wave10 starts immediately as next block.

## Next-block contract (mandatory)
- `Next block objective`: either mark `UX-11/UX-12` as `Fixed` or execute wave10 bounded extraction.
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave9 not merged or merged-main checks red.
- `Owner role for closure`: Brain + Top Architect.
