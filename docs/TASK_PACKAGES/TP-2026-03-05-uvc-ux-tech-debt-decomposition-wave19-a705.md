# TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave19-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE19-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: closure decision `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW14-A705 = Open`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW15-A705`

## Название/цель
Выполнить следующий bounded decomposition wave после closure-review14, чтобы продолжить снижение оркестрационной концентрации в `console.py` и `ProvisioningWizard.tsx` без изменения продуктового поведения и без добавления новых вкладок.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review14-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes; reuse existing UVC surfaces only.
- `REQ-2` no shortcuts:
  - solution: bounded extraction only, no oracle weakening and no behavior downgrade.
- `REQ-3` optimize existing tabs first:
  - solution: reduce complexity inside existing router/wizard files by delegating internal orchestration.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`

## One web search (mandatory before implementation)
- **Query (exact):** `Refactoring catalog Extract Function Martin Fowler`
- **Date/time (local):** `2026-03-05 16:40 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/extractFunction.html`
- **Found reusable solution:** continue incremental ownership transfer by extracting cohesive orchestration blocks behind stable helper boundaries with parity checks.
- **Decision:** continue bounded `reuse -> integrate -> configure -> build` decomposition for backend and frontend slices.
- **Rejected options:** one-shot rewrite of `console.py` / `ProvisioningWizard.tsx`.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after closure-review14.
- **Minimal reproduction:** merged-main baseline after wave18 is still `console.py=24390`, `ProvisioningWizard.tsx=4323`.
- **Evidence:** closure-review14 artifact and deterministic merged-main checks.
- **Five Whys:**
  1. why residual remains: previous waves extracted bounded slices only;
  2. why risk remains: parent files still combine multiple domains and mutation flows;
  3. why this hurts delivery: high merge-conflict and regression probability in Platform Admin flows;
  4. why closure is blocked: fail-closed threshold requires further ownership reduction;
  5. why wave19 now: closure-review14 explicitly kept backlog open by contract.
- **Root cause statement:** orchestration concentration in parent router/wizard files remains above maintainability threshold despite wave18 extraction.
- **Fix mechanism:** extract one backend orchestration slice and one frontend mutation/flow slice with parity-preserving tests.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing extracted modules (`console_branch_changes`, `provisioning-wizard-branch-actions`, `console_router_utils`) and deterministic test lanes.
- **External reuse:** extraction pattern from Refactoring catalog (`Extract Function`) to keep cohesive responsibilities isolated.
- **Why not build from scratch:** bounded extraction lowers regression blast radius and preserves UVC contracts.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `3`
- **Code dominance:** `required`
- **Override token:** `UVC_SCOPE_OVERRIDE_A705`
- **Why this profile fits:** wave19 is runtime extraction block; docs are limited to contract/template updates while code changes must dominate.

## Invariant
- No API contract drift for existing `/admin/*` endpoints.
- No new top-level tabs/routes and no ownership duplication across existing tabs.
- Behavioral parity for provisioning and control-plane execution flows.

## Scope
- Backend: extract next branch-change/service orchestration slice from `console.py` into `console_branch_changes.py` via stable helper boundary.
- Frontend: extract next bounded mutation/orchestration slice from `ProvisioningWizard.tsx` into dedicated helper module(s).
- Publish wave19 artifact and sync canon/session docs.

## Out of scope
- New product features.
- Full monolith rewrite.
- Policy/LAW runtime behavior changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_branch_changes.py`
- `truffles-api/tests/test_console_branch_changes.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-branch-actions.ts`
- `console-web/src/components/provisioning-wizard-state.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave19-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review15-a705.md`
- canon/session docs touched by wave19 evidence

## Plan (1..N)
1. Capture closure-review14 merged-main baseline and define minimal backend/frontend extraction slices.
2. Implement backend extraction with deterministic parity tests.
3. Implement frontend extraction with targeted lint/build/e2e checks.
4. Publish wave19 artifact, sync canon/session docs, open PR.

## DoD
- Wave19 extraction committed with deterministic checks green.
- Ownership reduction is explicit in artifact (`before/after LOC + moved responsibilities`).
- Canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` passes.

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
- Wave19 artifact with deterministic command outputs and moved-responsibility map.
- PR URL + CI run URL.
- `STATE.md`, `UX_BACKLOG`, master report sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- Max targeted rerun attempts for same hypothesis: `1`.
- Stop condition: any regression in deterministic lane -> stop and return to RCA before new edits.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded canary-by-PR merge with deterministic gate (`session-gate` + required CI jobs).
- **Go/no-go signals:** all required checks green; no drift in targeted UVC e2e lane.
- **Rollback:** revert wave19 merge commit.
- **Post-release monitoring window:** run closure-review15 on merged-main evidence before any wave20 work.

## Rollback
- `git revert MERGE_COMMIT_SHA` + rerun deterministic checks listed above.

## No-go
- Adding new tabs/routes as workaround.
- Runtime behavior changes unrelated to bounded decomposition slice.
- Weakening deterministic/e2e or anti-drift gates.

## Риски/блокеры
- CI volatility can hide true maintainability trend.
- Oversized extraction scope can repeat merge-red failures.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: parent files can remain above closure threshold after wave19.
- `Why not in this block`: decomposition remains bounded to preserve behavior guarantees.
- `Risk if deferred`: slow iteration and elevated regression probability in core admin paths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review15-a705.md`.
- `Expiry/trigger to stop deferral`: if wave19 closes neither `UX-11` nor `UX-12`, closure-review15 must open next bounded wave immediately.

## Next-block contract (mandatory)
- `Next block objective`: closure-review15 fail-closed merged-main decision for `UX-11/UX-12`.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave19 PR not merged or required checks red.
- `Owner role for closure`: Brain + Top Architect.
