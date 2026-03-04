# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave4-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE4-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of closeout PR for `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSEOUT-A705`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705

## Название/цель
Выполнить следующий полноценный этап decomposition после closeout: дополнительно снизить blast-radius `console.py` и `ProvisioningWizard.tsx` через feature-slice extraction без изменения runtime-семантики.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closeout-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## One web search (mandatory before implementation)
- **Query (exact):** `FastAPI bigger applications multiple files APIRouter best practices`
- **Date/time (local):** `2026-03-04 06:49:25 UTC`
- **Sources opened (from this query):**
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- **Decision:** `integrate` (reuse FastAPI modular router pattern for bounded extraction; no rewrite).
- **Rejected options:**
  - `build`: full rewrite from scratch was rejected due contract-risk and blast-radius.
  - `no-op`: keeping extraction deferred was rejected because it would not reduce `UX-11/UX-12` maintainability debt.

## Root cause (mandatory)
- **Symptom:** `UX-11`/`UX-12` remained `Open (Mitigated wave3)` even after previous decomposition waves; merge-red also confirmed coupling risk in provisioning status types.
- **Minimal reproduction:** inspect monolith hotspots (`console.py`, `ProvisioningWizard.tsx`) and run production build; pre-wave4 baseline still had large concentrated readiness/go-no-go logic inside both files.
- **Evidence:** `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` (`24920`, `4819`) before wave4; merge-red type failure in `ProvisioningWizard.tsx:3660`.
- **Five Whys:**
  1. Why still open? Readiness-specific logic remained embedded in router/component monoliths.
  2. Why embedded? Prior waves targeted other slices (helpers/domain/derived/orchestration), not readiness rendering + hard-gate helpers.
  3. Why problematic? Any change in readiness semantics or UI contract required touching large files with mixed concerns.
  4. Why high risk? Mixed concerns increase accidental regressions and make type-contract mismatches harder to isolate.
  5. Why now? Wave4 is the next explicit residual-debt contract after closeout and is required before final-close decision.
- **Root cause statement:** unresolved readiness-specific coupling in backend/router and frontend/wizard monoliths keeps `UX-11/UX-12` above closure threshold.
- **Fix mechanism:** extract readiness hard-gate helper slice to backend service module and readiness timeline/scorecard UI slice to frontend component module, then revalidate contracts.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse existing extracted modules (`console_control_tower_utils`, `console_control_tower_program`, `provisioning-wizard-domain`, `provisioning-wizard-derived`, `provisioning-wizard-utils`) and keep existing route/component contracts.
- **External reuse:** reuse official FastAPI modularization guidance (`bigger-applications`) as extraction pattern; no new third-party libs.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` full frontend e2e lane (`26` tests) for acceptance in this wave.
- **Max replay/rerun policy:** allow one targeted rerun only if failure is infra/flaky and not deterministic regression.
- **Stop condition:** if two consecutive runs fail without new evidence, stop and return to RCA before additional runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded behavior-preserving extraction only; no API shape changes and no new top-level UX routes.
- **Go/no-go signals:** `py_compile` pass, targeted backend pytest pass, `console-web` lint/build pass, targeted platform-admin e2e pass (`26 passed`), `SESSION_AGENT=a705 scripts/session_check.sh` pass.
- **Rollback:** `git revert 9f0efc02`.
- **Rollback procedure:** `git revert 9f0efc02` and rerun deterministic checks from this TP before reattempt.
- **Post-release monitoring window:** monitor required PR CI lanes (`session-gate`, `lint`, `unit-tests`, `console-e2e`, `deploy`) until green before merge and capture run URL in evidence.

## Invariant
- No runtime behavior changes.
- No new top-level tabs/routes.
- Existing platform-admin contract tests stay green.

## Scope
- Backend: extract next bounded control-tower/onboarding feature-slice from `console.py` into dedicated module(s).
- Frontend: extract next bounded `ProvisioningWizard` view/action slice into dedicated component/hook module(s).
- Add deterministic tests for newly extracted units.

## Out of scope
- Full router rewrite.
- Full provisioning wizard rewrite.
- Any policy-core/booking semantic changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/*` (new extracted modules)
- `truffles-api/tests/*` (targeted deterministic tests)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/*` (new extracted modules)
- `console-web/e2e/platform-admin.spec.ts` (only if selector contract needs update)

## Plan (1..N)
1. FACT pre-check and one mandatory web-search for wave4 extraction strategy.
2. Backend wave4 extraction + deterministic tests.
3. Frontend wave4 extraction + deterministic tests/lint.
4. Re-run targeted platform-admin lane.
5. Canon sync and PR.

## DoD
- `console.py` and `ProvisioningWizard.tsx` are further reduced by bounded extraction.
- New extraction modules are covered by deterministic tests.
- Targeted e2e lane remains green.
- Canon docs synced with updated residual/final-close contract.

## Checks
- `python3 -m py_compile ...`
- `pytest -q ...`
- `cd console-web && npm run lint -- --file ...`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff of extracted modules and rewiring.
- Test/lint/e2e outputs.
- Updated closeout progression in `STATE/master/backlog`.

## Rollback
- `git revert COMMIT_SHA` and rerun deterministic checks.

## No-go
- Big-bang rewrites.
- New runtime fallback branches.
- Contract changes hidden as refactor.

## Risks/блокеры
- Hidden coupling in monolith files can expand extraction scope.
- E2E flakes can mask true regressions if not triaged deterministically.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: residual remains until final-close criteria are met.
- `Why not in this block`: wave4 is bounded; final closure may require one more bounded block.
- `Risk if deferred`: medium.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705`.
- `Expiry/trigger to stop deferral`: if two consecutive blocks do not reduce blast-radius metrics.

## Next-block contract (mandatory)
- `Next block objective`: final-close decision for `UX-11/UX-12` with closure criteria.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave4 checks red or PR not merged.
- `Owner role for closure`: Brain + Top Architect.
