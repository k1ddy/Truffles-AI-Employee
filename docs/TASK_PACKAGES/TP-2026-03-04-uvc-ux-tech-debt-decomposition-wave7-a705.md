# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave7-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE7-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW2-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-REVIEW3-A705`

## Название/цель
Выполнить следующий bounded decomposition wave для `UX-11/UX-12` в уже существующих поверхностях (без новых вкладок/роутов): вынести stateful backend/frontend orchestration из монолитных файлов в отдельные модули с детерминированными тестами.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review2-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new routes/tabs; reuse existing `Tenants/Integrations/Workspace/Ops/Settings` entrypoints.
  - proof: runtime nav map unchanged; only internal extraction.
- `REQ-2` intuitive business logic + plain operator hints:
  - solution: behavior/text contract preserved; only internals moved.
  - proof: targeted platform-admin e2e lane remains green.
- `REQ-3` reuse-first optimization of existing tabs:
  - solution: continue decomposition in `console.py` and `ProvisioningWizard.tsx` without product-surface expansion.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> expected baseline from closure-review2: `24743`, `4617`.
- `pytest -q truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py` -> expected baseline: `24 passed`.
- `rg -n "_ensure_role_not_deprecated_for_assignment|_extend_missing_memberships" truffles-api/app/routers/console.py` -> confirms remaining stateful membership logic in router.
- `rg -n "const \[.*set[A-Z]" console-web/src/components/ProvisioningWizard.tsx | wc -l` -> confirms high state concentration in wizard shell.

## One web search (mandatory before implementation)
- **Query (exact):** `FastAPI bigger applications multiple files APIRouter dependencies best practices`
- **Date/time (local):** `2026-03-04 13:36 +0500`
- **Sources opened (from this query):**
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- **Found reusable solution:** split route-level logic into dedicated modules and include shared dependencies/helpers to avoid duplication and giant router files.
- **Decision:** `reuse/integrate` this modularization pattern for next extraction wave.
- **Rejected options:** keep adding helpers inside `console.py` without extracting stateful slices.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave6; core files still act as orchestration monoliths.
- **Minimal reproduction:**
  1. read `console.py` and observe remaining stateful membership/assignment orchestration in router scope;
  2. read `ProvisioningWizard.tsx` and observe dense local state lifecycle/update/reset orchestration;
  3. verify LOC blast-radius remains high (`24743`, `4617`).
- **Evidence:** closure-review2 artifact + deterministic checks from merged main.
- **Five Whys:**
  1. Why still open? extracted slices are partial; orchestration concentration remains.
  2. Why concentration remains? previous waves prioritized lower-risk helper extraction.
  3. Why this matters? routine edits still require high-context file changes.
  4. Why risk persists? review/test blast radius is still large per change.
  5. Why wave7? next bounded split can remove another stateful cluster without behavior change.
- **Root cause statement:** remaining stateful orchestration in `console.py` and `ProvisioningWizard.tsx` keeps maintainability risk above closure threshold.
- **Fix mechanism:** extract one backend and one frontend stateful cluster into dedicated modules/hooks with deterministic contract tests.

## Reuse-first plan (mandatory)
- **Internal reuse:** continue current pattern (`console_*` service modules + `provisioning-wizard-*` modules).
- **External reuse:** FastAPI official modular-router guidance (`APIRouter` + shared dependencies).
- **Why not rewrite:** wave7 is bounded risk-reduction; full rewrite would break no-shortcut/no-big-bang constraints.

## Invariant
- No runtime behavior changes for operator workflows.
- No new top-level tabs/routes.
- Existing e2e selector contract remains stable.

## Scope
- Backend (`UX-11`): extract role/membership assignment orchestration helpers from `console.py` into a dedicated service module and keep router as composition layer.
- Frontend (`UX-12`): extract wizard local state lifecycle orchestration (bootstrap/reset/sync) into dedicated module/hook and keep JSX shell focused on rendering/actions.
- Add/extend deterministic tests for extracted backend module and keep existing quality lanes green.

## Out of scope
- New features, new endpoints, or UX redesign.
- Cross-domain architecture changes outside `UX-11/UX-12` decomposition.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_membership_state.py` (new)
- `truffles-api/tests/test_console_membership_state.py` (new)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-state.ts` (new)
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave7-a705.md` (new)
- Canon/session sync docs

## Plan (1..N)
1. Capture deterministic baseline and locate exact extraction seams.
2. Implement backend stateful slice extraction + deterministic unit tests.
3. Implement frontend state lifecycle extraction and rewire wizard.
4. Run deterministic backend checks + frontend lint/build + targeted e2e.
5. Publish wave7 artifact and sync canon/session docs.

## DoD
- Backend and frontend wave7 slices extracted with unchanged runtime behavior.
- Deterministic backend tests added and passing.
- `platform-admin` targeted e2e lane remains green.
- Canon/session docs synced with explicit residual decision contract.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-state.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- PR URL + commit SHA.
- Pre/post LOC snapshot.
- Deterministic check outputs (`py_compile`, `pytest`, `lint`, `build`, targeted e2e, `session_check`).
- Wave7 artifact + canon sync diff.

## Token / run budget (mandatory for expensive suites)
- Keep e2e lane to targeted platform-admin contract only.
- Max full runs: `1` per change iteration (run full lane once after local deterministic green).
- Stop condition: if deterministic checks fail twice without new RCA evidence, block and return to root cause.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded extraction with no feature toggles and no endpoint contract change.
- **Go/no-go signals:** backend tests + frontend lint/build + targeted e2e all green.
- **Rollback:** revert wave7 commit; rerun deterministic checks.
- **Post-release monitoring window:** next closure review validates residual risk using merged-main baseline.

## Rollback
- `git revert COMMIT_SHA` and rerun `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- No semantic/UX behavior rewrites in this block.
- No new top-level nav/tabs/routes.
- No disabling/relaxing deterministic gates to force pass.

## Риски/блокеры
- Hidden coupling between router and extracted membership state functions.
- Wizard state extraction can regress form synchronization if not covered by focused checks.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: to be decided after wave7 evidence.
- `Why not in this block`: wave7 remains bounded to avoid big-bang rewrite.
- `Risk if deferred`: continued high-context edits in monolith files.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-review3-a705.md`.
- `Expiry/trigger to stop deferral`: if post-wave7 closure review still shows high blast-radius, lock wave8 with explicit owner approval.

## Next-block contract (mandatory)
- `Next block objective`: closure decision after wave7 (`Fixed` vs `Open + wave8`).
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave7 checks red or missing artifact/canon sync.
- `Owner role for closure`: Brain + Top Architect.
