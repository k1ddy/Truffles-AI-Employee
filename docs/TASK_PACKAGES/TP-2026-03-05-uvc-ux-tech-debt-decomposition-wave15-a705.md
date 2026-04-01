# TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave15-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE15-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: closure decision `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW10-A705 = Open`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW11-A705`

## Название/цель
Выполнить следующий bounded decomposition wave после closure-review10, чтобы продолжить снижение оркестрационной концентрации в `console.py` и `ProvisioningWizard.tsx` без изменения продуктового поведения и без добавления новых вкладок.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review10-a705.md`
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
- **Query (exact):** `React docs thinking in React extract UI into components`
- **Date/time (local):** `2026-03-05 07:31 +0500`
- **Sources opened (from this query):**
  - `https://react.dev/learn/thinking-in-react`
- **Found reusable solution:** keep clear responsibility boundaries by splitting large UI into focused component/helper layers while preserving data flow contracts.
- **Decision:** continue bounded `reuse -> integrate -> configure -> build` decomposition for backend and frontend slices.
- **Rejected options:** one-shot rewrite of `console.py` / `ProvisioningWizard.tsx`.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after closure-review10.
- **Minimal reproduction:** merged-main baseline after wave14 is still `console.py=24358`, `ProvisioningWizard.tsx=4356`.
- **Evidence:** closure-review10 artifact and deterministic merged-main checks.
- **Five Whys:**
  1. why residual remains: previous waves extracted bounded slices only;
  2. why risk remains: parent files still combine multiple domains and mutation flows;
  3. why this hurts delivery: high merge-conflict and regression probability in Platform Admin flows;
  4. why closure is blocked: fail-closed threshold requires further ownership reduction;
  5. why wave15 now: closure-review10 explicitly kept backlog open by contract.
- **Root cause statement:** orchestration concentration in parent router/wizard files remains above maintainability threshold despite wave14 extraction.
- **Fix mechanism:** extract one backend orchestration slice and one frontend mutation/flow slice with parity-preserving tests.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing extracted modules (`console_branch_changes`, `provisioning-wizard-branch-actions`, `console_router_utils`) and deterministic test lanes.
- **External reuse:** React component decomposition guidance for stable ownership boundaries.
- **Why not build from scratch:** bounded extraction lowers regression blast radius and preserves UVC contracts.

## Invariant
- No API contract drift for existing `/admin/*` endpoints.
- No new top-level tabs/routes and no ownership duplication across existing tabs.
- Behavioral parity for provisioning and control-plane execution flows.

## Scope
- Backend: extract next branch-change/service orchestration slice from `console.py` into `console_branch_changes.py` via stable helper boundary.
- Frontend: extract next bounded mutation/orchestration slice from `ProvisioningWizard.tsx` into dedicated helper module(s).
- Publish wave15 artifact and sync canon/session docs.

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
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave15-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review11-a705.md`
- canon/session docs touched by wave15 evidence

## Plan (1..N)
1. Capture closure-review10 merged-main baseline and define minimal backend/frontend extraction slices.
2. Implement backend extraction with deterministic parity tests.
3. Implement frontend extraction with targeted lint/build/e2e checks.
4. Publish wave15 artifact, sync canon/session docs, open PR.

## DoD
- Wave15 extraction committed with deterministic checks green.
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
- Wave15 artifact with deterministic command outputs and moved-responsibility map.
- PR URL + CI run URL.
- `STATE.md`, `UX_BACKLOG`, master report sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- Max targeted rerun attempts for same hypothesis: `1`.
- Stop condition: any regression in deterministic lane -> stop and return to RCA before new edits.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded canary-by-PR merge with deterministic gate (`session-gate` + required CI jobs).
- **Go/no-go signals:** all required checks green; no drift in targeted UVC e2e lane.
- **Rollback:** revert wave15 merge commit.
- **Post-release monitoring window:** run closure-review11 on merged-main evidence before any wave16 work.

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
- `Current residuals accepted in this block`: parent files can remain above closure threshold after wave15.
- `Why not in this block`: decomposition remains bounded to preserve behavior guarantees.
- `Risk if deferred`: slow iteration and elevated regression probability in core admin paths.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review11-a705.md`.
- `Expiry/trigger to stop deferral`: if closure-review11 remains `Open`, next wave contract must be created in the same block.

## Next-block contract (mandatory)
- `Next block objective`: closure-review11 fail-closed merged-main decision for `UX-11/UX-12`.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave15 PR not merged or required checks red.
- `Owner role for closure`: Brain + Top Architect.
