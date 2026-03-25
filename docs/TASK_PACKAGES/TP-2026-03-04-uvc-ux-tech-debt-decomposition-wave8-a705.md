# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave8-a705

## Block identity
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE8-A705`
- `PARENT_BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- `DEPENDS_ON`: `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-REVIEW3-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW4-A705`

## Название/цель
Выполнить следующий bounded decomposition wave после final-review3, чтобы дополнительно снизить blast-radius `UX-11/UX-12` без изменения продуктового поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-review3-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes; keep action ownership in existing UVC surfaces.
- `REQ-2` no shortcuts:
  - solution: extraction only; no semantic bypass or contract weakening.
- `REQ-3` optimize existing tabs first:
  - solution: split only existing backend/frontend monolith slices with deterministic guards.

## FACT pre-check (before implementation)
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`

## One web search (mandatory before implementation)
- **Query (exact):** `FastAPI bigger applications APIRouter split files and React custom hooks extraction without behavior changes`
- **Date/time (local):** `2026-03-04 15:30 +0500`
- **Sources opened (from this query):**
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
  - `https://react.dev/learn/reusing-logic-with-custom-hooks`
- **Found reusable solution:** extract route logic into dedicated modules/services and extract UI stateful logic into dedicated reusable units while preserving inputs/outputs.
- **Decision:** continue bounded reuse-first extraction (`reuse -> integrate -> configure -> build`) with deterministic regression checks.
- **Rejected options:** broad rewrite of `console.py` / `ProvisioningWizard.tsx` in one block.

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remain open after wave7 because parent files are still high-context.
- **Minimal reproduction:** merged-main baseline shows `console.py=24606`, `ProvisioningWizard.tsx=4544` with residual orchestration concentration.
- **Evidence:** `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-review3-a705.md`.
- **Five Whys:**
  1. why residual persists: previous waves extracted helper slices first;
  2. why risk remains: orchestration/state mutation still concentrated;
  3. why quality risk remains: routine edits still touch large parent files;
  4. why fail-closed continues: fixed-status cannot be claimed without lower blast-radius;
  5. why wave8 now: final-review3 explicitly requires immediate continuation.
- **Root cause statement:** remaining orchestration/state slices in parent files keep maintainability risk above closure threshold.
- **Fix mechanism:** extract one backend orchestration slice + one frontend state/action slice with unchanged runtime contracts.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse existing extracted modules (`console_router_utils`, `console_control_tower_program`, `console_onboarding_readiness`, `console_fleet_state`, `console_membership_state`, provisioning helper/domain/derived/readiness/shell/json/state modules).
- **External reuse:** FastAPI APIRouter and React custom-hooks refactor guidance from primary docs.
- **Why not build from scratch:** bounded extraction must preserve contracts and minimize regression risk.

## Invariant
- No API contract drift in existing `/admin/*` and UVC flows.
- No new top-level tabs or route ownership changes.
- Behavior parity preserved; only structural decomposition.

## Scope
- Backend: extract one additional orchestration/state slice from `console.py` into dedicated service module.
- Frontend: extract one additional state/action orchestration slice from `ProvisioningWizard.tsx` into dedicated module/hook.
- Publish wave8 artifact and sync canon docs.

## Out of scope
- Feature expansion in UVC UX.
- New tenancy policy model changes.
- Full rewrite of `console.py` or `ProvisioningWizard.tsx`.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_membership_state.py`
- `truffles-api/app/services/console_onboarding_readiness.py`
- `truffles-api/app/services/console_router_utils.py`
- `truffles-api/tests/test_console_membership_state.py`
- `truffles-api/tests/test_console_onboarding_readiness.py`
- `truffles-api/tests/test_console_router_utils.py`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-state.ts`
- `console-web/src/components/provisioning-wizard-derived.ts`
- `console-web/src/components/provisioning-wizard-shell-panels.tsx`
- `console-web/e2e/platform-admin.spec.ts`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave8-a705.md`
- canon/session docs impacted by wave8 evidence

## Plan (1..N)
1. Capture merged-main baseline and select minimal backend/frontend target slices.
2. Extract backend slice with parity-preserving wrappers and deterministic tests.
3. Extract frontend slice with parity-preserving wiring and targeted lint/build/e2e checks.
4. Publish wave8 artifact and sync canon/session docs.

## DoD
- Wave8 extraction merged in branch with deterministic checks green.
- LOC trend and module ownership improved vs final-review3 baseline.
- Canon/session docs synced with explicit residual decision for next closure-review block.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-state.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- wave8 artifact report with before/after metrics and deterministic output.
- PR URL + CI run URL.
- updated `STATE.md` + `UX_BACKLOG` status line.

## Rollback
- `git revert COMMIT_SHA` + rerun deterministic checks + `SESSION_AGENT=a705 scripts/session_check.sh`.

## No-go
- No behavior changes masked as refactor.
- No new UVC top-level tab or duplicated action ownership.
- No skipping deterministic suite for merge readiness.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `1`.
- E2E policy: one targeted platform-admin lane run after frontend extraction; rerun only if deterministic check fails with a new hypothesis.
- Stop condition: two repeated failures without new RCA evidence -> stop-the-line and return to root-cause section.

## Release safety (mandatory for non-doc changes)
- Strategy: `canary` at code-review level via targeted deterministic suite and existing platform-admin e2e lane before merge.
- Go/no-go signals: all checks in `Checks` section green; no API type drift; no e2e deep-link regressions.
- Rollback: immediate revert of wave8 commits with deterministic rerun.
- Post-release monitoring window: closure-review4 must revalidate merged-main baseline before any next-wave promotion.

## Риски/блокеры
- Large-file extraction can create hidden import coupling.
- Frontend state extraction can regress hydration timing if not covered by e2e path.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: will be reassessed after wave8 results.
- `Why not in this block`: full monolith breakup exceeds bounded wave scope.
- `Risk if deferred`: high-context edits continue to slow safe delivery.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review4-a705.md`.
- `Expiry/trigger to stop deferral`: if wave8 closes neither `UX-11` nor `UX-12`, closure-review4 must open next bounded wave immediately.

## Next-block contract (mandatory)
- `Next block objective`: closure-review4 fail-closed decision (`Fixed` or `Open + next wave`).
- `First deterministic check command`: `rg -n "UX-11|UX-12" docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `Blocked-by conditions`: wave8 checks red or artifact absent.
- `Owner role for closure`: Brain + Top Architect.
