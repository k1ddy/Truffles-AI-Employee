# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave5-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE5-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705`
- `UNLOCKS`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW-A705`

## Название/цель
Выполнить следующий полноценный bounded decomposition шаг после final-close: сократить blast-radius `console.py` и `ProvisioningWizard.tsx` через extraction reusable validation/shell slices без изменения runtime-семантики.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-close-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: extract existing wizard shell panels as separate components without changing action map.
  - proof: same `data-testid` and event handlers retained.
- `REQ-2` no shortcut/costyl:
  - solution: extract deterministic query/limit/bool/uuid validation logic to shared backend utility module.
  - proof: router wrappers delegate to shared module + deterministic tests.
- `REQ-3` optimize existing surfaces before adding new tabs:
  - solution: no new routes/tabs; only internal decomposition of existing `ProvisioningWizard` and `console.py`.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_router_utils.py`
  - `truffles-api/tests/test_console_router_utils.py`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/components/provisioning-wizard-shell-panels.tsx` (new)
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `rg -n "_reject_unknown_query_params|_validate_limit|_parse_uuid_param|_parse_bool_param" truffles-api/app/routers/console.py`
  - `rg -n "provisioning-error-summary|onboarding-execution-hub|Режим онбординга" console-web/src/components/ProvisioningWizard.tsx`
- `FACT findings`:
  - baseline monolith sizes remain high (`console.py=24888`, `ProvisioningWizard.tsx=4742`).
  - repeated validation/shell rendering logic remains embedded in monolith entry files.

## One web search (mandatory before implementation)
- **Query (exact):** `react extract component keep state in parent`
- **Date/time (local):** `2026-03-04 12:36 +0500`
- **Sources opened (from this query):**
  - `https://react.dev/learn/sharing-state-between-components`
- **Found reusable solution:** keep mutation/state ownership in parent and extract presentational panels as controlled components via props.
- **Decision:** `integrate` (extract wizard shell panels to controlled components; keep state/actions in `ProvisioningWizard`).
- **Rejected options:** move stateful mutation logic into child components (higher coupling and regression risk).

## Root cause (mandatory)
- **Symptom:** `UX-11/UX-12` remained open after wave4; core monoliths still mix orchestration and presentational/validation layers.
- **Minimal reproduction:**
  1. inspect `console.py` section around `_reject_unknown_query_params/_validate_limit/_parse_*` helpers.
  2. inspect `ProvisioningWizard.tsx` top shell render blocks (error summary, mode switch, execution-hub) coupled into monolith.
  3. compare LOC snapshot (`24888/4742`) against closure threshold.
- **Evidence:** final-close artifact, LOC snapshot, wave4 merged PR `#891`.
- **Five Whys:**
  1. Why still open? Monoliths still include cross-cutting concerns.
  2. Why cross-cutting matters? It increases regression blast-radius for small edits.
  3. Why this slice now? It is low-risk and reusable across many endpoints/render states.
  4. Why not rewrite all at once? Big-bang rewrite violates bounded-wave contract.
  5. Why wave5? Final-close explicitly requires next bounded decomposition wave.
- **Root cause statement:** reusable validation and shell-panel concerns are still embedded in monolith entry files.
- **Fix mechanism:** extract backend validation helpers + frontend shell panels into reusable modules with deterministic checks.

## Reuse-first plan (mandatory)
- **Internal reuse:** extend existing `console_router_utils.py` module and existing wizard extracted-components pattern.
- **External reuse:** React official controlled-component guidance (`sharing state between components`).
- **Why not build from scratch:** current behavior is correct; objective is decomposition without semantic drift.

## Invariant
- No runtime/API behavior changes.
- No new top-level tabs/routes.
- Existing platform-admin contract lane semantics remain unchanged.

## Scope
- Backend: extract query/limit/bool/uuid validation logic into `console_router_utils.py` and delegate from `console.py` wrappers.
- Frontend: extract wizard shell panels (error summary, mode toggle, execution hub) into `provisioning-wizard-shell-panels.tsx`.
- Add deterministic tests for extracted backend helpers.

## Out of scope
- Full router/component rewrite.
- Policy-core, booking pipeline, or LLM behavior changes.
- UX text rewording beyond preserved extracted markup.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_router_utils.py`
- `truffles-api/tests/test_console_router_utils.py`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-shell-panels.tsx` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave5-a705.md` (new)
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Plan (1..N)
1. Extract backend validation helpers and add/extend deterministic tests.
2. Extract frontend shell panels to controlled components and rewire wizard render.
3. Re-run targeted deterministic checks (`py_compile`, pytest, lint/build, session check).
4. Publish wave5 artifact and sync canon docs.
5. Open PR.

## DoD
- `console.py` and `ProvisioningWizard.tsx` reduced via bounded extraction.
- extracted backend helper behavior covered by deterministic tests.
- targeted frontend lint/build/e2e lane green.
- canon docs reflect wave5 status and next-block contract.

## Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py truffles-api/tests/test_console_router_utils.py`
- `pytest -q truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-shell-panels.tsx --file src/components/provisioning-wizard-readiness-panel.tsx --file src/components/provisioning-wizard-derived.ts --file src/components/provisioning-wizard-utils.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff for extracted backend/frontend modules.
- Deterministic checks output.
- Updated canon docs + wave5 artifact.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` (`console-web build` + one targeted platform-admin e2e lane).
- E2E policy: one targeted acceptance rerun is allowed for safety after frontend extraction.
- Stop condition: any semantic behavior regression signal pauses wave and returns to RCA.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded behavior-preserving extraction only.
- **Go/no-go signals:** `py_compile` pass, pytest pass, frontend lint/build pass, session gate pass.
- **Rollback:** revert wave5 commit.
- **Post-release monitoring window:** required PR CI lanes (`session-gate`, `lint`, `unit-tests`, `deploy`) before merge.

## Rollback
- `git revert COMMIT_SHA` and rerun deterministic checks from this TP.

## No-go
- Big-bang rewrites.
- New runtime fallback branches.
- Introducing duplicate/unsynced UX controls across tabs.

## Risks/блокеры
- Hidden coupling in wizard render may require additional props wiring.
- Import ordering/typing gates can fail merge lane without behavioral issues.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: monolith residual remains until closure-review threshold is met.
- `Why not in this block`: wave5 intentionally bounded to one backend + one frontend slice.
- `Risk if deferred`: medium-high regression risk persists for unrelated edits.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705.md`.
- `Expiry/trigger to stop deferral`: if wave5 does not reduce measured blast-radius, escalate to architecture decision before next feature work.

## Next-block contract (mandatory)
- `Next block objective`: closure-review decision (`Fixed` vs `Open`) for `UX-11/UX-12` after wave5 evidence.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: wave5 checks red or canon sync incomplete.
- `Owner role for closure`: Brain + Top Architect.
