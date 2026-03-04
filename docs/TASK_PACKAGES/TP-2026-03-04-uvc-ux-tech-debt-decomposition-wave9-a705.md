# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave9-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE9-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW4-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW5-A705`

## Название/цель
Выполнить следующий bounded decomposition wave после closure-review4, чтобы дополнительно снизить blast-radius `UX-11/UX-12` без изменения продуктового поведения и без добавления новых вкладок.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review4-a705.md`
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
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/tests/test_console_onboarding_readiness.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`

## One web search (mandatory before implementation)
- **Query (exact):** `FastAPI bigger applications APIRouter service layer and React custom hooks extracting form orchestration`
- **Date/time (local):** `2026-03-04 16:35 +0500`
- **Sources opened (from this query):**
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
  - `https://react.dev/learn/reusing-logic-with-custom-hooks`
- **Found reusable solution:** split route/form orchestration into dedicated modules with stable input/output contracts and reuse existing components.
- **Decision:** continue `reuse -> integrate -> configure -> build` with deterministic regression lane.
- **Rejected options:** broad rewrite of `console.py` or `ProvisioningWizard.tsx` in one block.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave8 and closure-review4.
- **Minimal reproduction:** merged-main baseline after wave8 shows `console.py=24554` and `ProvisioningWizard.tsx=4552`.
- **Evidence:** `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review4-a705.md`.
- **Five Whys:**
  1. why residual persists: previous waves intentionally extracted bounded slices;
  2. why risk remains: parent files still own multi-domain orchestration;
  3. why this hurts UX delivery: safe changes are slower in large context files;
  4. why closure is blocked: fail-closed policy requires objective maintainability reduction;
  5. why wave9 now: closure-review4 explicitly kept residual open.
- **Root cause statement:** orchestration concentration in router/wizard parent files remains above acceptable maintainability threshold.
- **Fix mechanism:** extract one backend provisioning-orchestration slice and one frontend wizard-action slice with parity-preserving contracts.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing extracted services/modules from wave1-8 and retained deterministic suite.
- **External reuse:** FastAPI/React official decomposition guidance listed above.
- **Why not build from scratch:** bounded extraction minimizes regression risk and preserves UVC product contracts.

## Invariant
- No API contract drift for existing `/admin/*` endpoints.
- No new top-level tabs/routes and no ownership duplication across tabs.
- Behavioral parity for provisioning and control-plane action flows.

## Scope
- Backend: extract additional admin provisioning orchestration/payload-normalization slice from `console.py` into dedicated service module.
- Frontend: extract additional wizard mutation/action orchestration slice from `ProvisioningWizard.tsx` into dedicated helper/action module.
- Publish wave9 artifact and sync canon/session docs.

## Out of scope
- New user-facing features or additional product surfaces.
- Full monolith rewrite.
- Policy/LAW runtime behavior changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_onboarding_readiness.py`
- `truffles-api/app/services/console_router_utils.py`
- `truffles-api/app/services/console_fleet_state.py`
- `truffles-api/app/services/console_membership_state.py`
- `truffles-api/tests/test_console_onboarding_readiness.py`
- `truffles-api/tests/test_console_membership_state.py`
- `truffles-api/tests/test_console_fleet_state.py`
- `truffles-api/tests/test_console_router_utils.py`
- `truffles-api/tests/test_console_control_tower_program.py`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-state.ts`
- `console-web/src/components/provisioning-wizard-json-payloads.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave9-a705.md`
- canon/session docs touched by wave9 evidence

## Plan (1..N)
1. Capture merged-main wave8 baseline and pick minimal backend/frontend slices for wave9.
2. Implement backend extraction with deterministic parity tests.
3. Implement frontend extraction with targeted lint/build/e2e lane.
4. Publish wave9 artifact, sync canon/session docs, open PR.

## DoD
- Wave9 extraction committed with deterministic checks green.
- Ownership reduction is explicit in artifact (`before/after LOC + moved responsibilities`).
- Canon/session docs synced and `SESSION_AGENT=a705 scripts/session_check.sh` passes.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/tests/test_console_onboarding_readiness.py`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-state.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Wave9 artifact with deterministic command outputs and moved-responsibility map.
- PR URL + CI run URL.
- `STATE.md`, `UX_BACKLOG`, master report sync diff.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- E2E policy: one targeted platform-admin lane run after frontend extraction; rerun only with new RCA.
- Stop condition: two iterations without new evidence -> stop-the-line and revisit RCA.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded extraction behind existing contracts (no feature rollout).
- **Go/no-go signals:** all checks green, no OpenAPI drift, no e2e deep-link regression.
- **Rollback:** revert wave9 commit(s), rerun deterministic checks and `session_check`.
- **Post-release monitoring window:** closure-review5 must confirm merged-main evidence before next wave.

## Rollback
- `git revert COMMIT_SHA` + rerun `Checks` + `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- No behavior changes hidden as refactor.
- No new top-level tabs/routes.
- No weakening of deterministic gates or governance policy.

## Риски/блокеры
- Hidden coupling between router handlers and extracted helpers.
- Wizard mutation extraction can regress hydration/submit sequencing if not covered by e2e.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be reassessed after wave9 results.
- `Why not in this block`: full breakup is larger than bounded wave scope.
- `Risk if deferred`: high-context edits remain slow and regression-prone.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review5-a705.md` (create/lock at wave9 completion).
- `Expiry/trigger to stop deferral`: if closure-review5 stays `Open`, next bounded wave must start immediately.

## Next-block contract (mandatory)
- `Next block objective`: merged-main closure-review5 decision (`Fixed` or `Open + next wave`).
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave9 merge not completed or deterministic checks red.
- `Owner role for closure`: Brain + Top Architect.
