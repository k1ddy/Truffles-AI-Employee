# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave10-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE10-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: closure decision `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW5-A705 = Open`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW6-A705`

## Название/цель
Выполнить следующий bounded decomposition wave после closure-review5, чтобы дополнительно снизить blast-radius `UX-11/UX-12` без изменения продуктового поведения и без добавления новых вкладок.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review5-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes; optimize existing UVC surfaces only.
- `REQ-2` no shortcuts:
  - solution: structural extraction only, no behavior downgrade and no oracle weakening.
- `REQ-3` optimize existing tabs first:
  - solution: extract internal router/wizard orchestration slices from current monoliths.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`

## One web search (mandatory before implementation)
- **Query (exact):** `DORA metrics software delivery reliability change failure rate lead time for changes`
- **Date/time (local):** `2026-03-04 16:13 +0500`
- **Sources opened (from this query):**
  - `https://dora.dev/`
  - `https://dora.dev/guides/dora-metrics/`
- **Found reusable solution:** reduce change risk via bounded increments with explicit regression evidence and short feedback loop.
- **Decision:** continue `reuse -> integrate -> configure -> build` with deterministic regression lane.
- **Rejected options:** broad rewrite of `console.py` or `ProvisioningWizard.tsx` in one block.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave9.
- **Minimal reproduction:** merged-main baseline after wave9 still shows large parent files (`console.py=24493`, `ProvisioningWizard.tsx=4452`).
- **Evidence:** closure-review5 artifact and merged-main check outputs.
- **Five Whys:**
  1. why residual persists: previous waves extracted only bounded slices;
  2. why risk remains: core parent files still own multi-domain orchestration;
  3. why this hurts UX delivery: safe changes are slower in very large context files;
  4. why closure is blocked: fail-closed policy requires objective maintainability reduction;
  5. why wave10 now: closure-review5 kept residual open by contract.
- **Root cause statement:** orchestration concentration in router/wizard parent files remains above acceptable maintainability threshold.
- **Fix mechanism:** extract one backend normalization/orchestration slice and one frontend side-effect/action slice with parity-preserving contracts.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing extracted modules from wave1-9 and deterministic lanes.
- **External reuse:** DORA bounded-change guidance for low-risk iterative delivery.
- **Why not build from scratch:** bounded extraction minimizes regression risk and preserves UVC product contracts.

## Invariant
- No API contract drift for existing `/admin/*` endpoints.
- No new top-level tabs/routes and no ownership duplication across tabs.
- Behavioral parity for provisioning and control-plane action flows.

## Scope
- Backend: extract next branch/provisioning normalization slice from `console.py` into dedicated service module (target: reduce inline mutable validation logic around branch draft patch pipeline).
- Frontend: extract next wizard mutation side-effect/action orchestration slice from `ProvisioningWizard.tsx` into dedicated helper/hook module.
- Publish wave10 artifact and sync canon/session docs.

## Out of scope
- New user-facing features or additional product surfaces.
- Full monolith rewrite.
- Policy/LAW runtime behavior changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_branch_changes.py`
- `truffles-api/app/services/console_router_utils.py`
- `truffles-api/tests/test_console_branch_changes.py`
- `truffles-api/tests/test_console_router_utils.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-branch-actions.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave10-a705.md`
- canon/session docs touched by wave10 evidence

## Plan (1..N)
1. Capture closure-review5 merged-main baseline and pick minimal backend/frontend slices for wave10.
2. Implement backend extraction with deterministic parity tests.
3. Implement frontend extraction with targeted lint/build/e2e lane.
4. Publish wave10 artifact, sync canon/session docs, open PR.

## DoD
- Wave10 extraction committed with deterministic checks green.
- Ownership reduction is explicit in artifact (`before/after LOC + moved responsibilities`).
- Canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` passes.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Wave10 artifact with deterministic command outputs and moved-responsibility map.
- PR URL + CI run URL.
- `STATE.md`, `UX_BACKLOG`, master report sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- Max targeted rerun attempts for same hypothesis: `1`.
- Stop condition: any regression in deterministic lane -> stop and return to RCA before new edits.

## Release safety (mandatory)
- **Strategy:** bounded canary-by-PR merge with deterministic gate (`session-gate` + required CI jobs).
- **Go/no-go signals:** all required checks green; no drift in targeted UVC e2e lane.
- **Rollback:** revert wave10 merge commit.
- **Post-release monitoring window:** run closure-review6 on merged-main evidence before any wave11 work.

## Rollback
- `git revert MERGE_COMMIT_SHA` + rerun deterministic checks listed above.

## No-go
- Adding new tabs/routes as workaround.
- Direct runtime behavior changes unrelated to bounded decomposition slice.
- Weakening existing deterministic/e2e or anti-drift gates.

## Риски/блокеры
- CI volatility can mask true maintainability progress.
- Oversized extraction scope can reintroduce merge-red risk.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: parent files may remain above target maintainability threshold after wave10.
- `Why not in this block`: decomposition remains bounded to reduce regression blast radius.
- `Risk if deferred`: ongoing slow iteration and higher regression probability.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review6-a705.md` (to be created after wave10).
- `Expiry/trigger to stop deferral`: if closure-review6 still reports `Open`, next wave contract must be created in same block.

## Next-block contract (mandatory)
- `Next block objective`: closure-review6 fail-closed merged-main decision for `UX-11/UX-12`.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave10 PR not merged or required checks red.
- `Owner role for closure`: Brain + Top Architect.
