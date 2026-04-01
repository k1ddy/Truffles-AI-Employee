# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave3-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE3-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#888` (`fd848ada`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSEOUT-A705

## Название/цель
Закрыть третий полноценный этап structural-debt по `UX-11` и `UX-12` без изменения бизнес-поведения: вынести orchestration-сборку `control-tower` из `console.py` в отдельный feature-slice модуль и вынести derived-state слой `ProvisioningWizard.tsx` в отдельный модуль, сохранив текущие UX-loop и API контракты.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave2-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes/CTA branches; only internal decomposition and import rewiring.
  - proof: platform-admin e2e lane remains green.
- `REQ-2` no shortcut/costyl in runtime path:
  - solution: pure extraction of orchestration/derived builders, no semantic hardcode/fallback branch changes.
  - proof: deterministic tests + unchanged contract/e2e behavior.
- `REQ-3` optimize existing surfaces first:
  - solution: decomposition inside existing `console.py` and `ProvisioningWizard.tsx` before any new feature work.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_control_tower_program.py` (new)
  - `truffles-api/tests/test_console_control_tower_program.py` (new)
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/components/provisioning-wizard-derived.ts` (new)
  - `console-web/e2e/platform-admin.spec.ts`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `rg -n "^def _build_admin_control_tower_action_center|^def _build_admin_control_tower_migration_program" truffles-api/app/routers/console.py`
  - `rg -n "const stepStateById = useMemo|const stepStatus = useMemo|const onboardingTimeline = useMemo|const readinessItems = useMemo" console-web/src/components/ProvisioningWizard.tsx`
- `FACT findings`:
  - `console.py` remains overgrown (`25143` LOC snapshot).
  - `ProvisioningWizard.tsx` remains overgrown (`4911` LOC snapshot).

## One web search (mandatory before implementation)
- **Query (exact):** `site:react.dev extract logic custom hook useMemo`
- **Date/time (local):** `2026-03-04 10:51 +0500`
- **Sources opened (from this query):**
  - `https://react.dev/learn/you-might-not-need-an-effect`
- **Found reusable solution:** keep rendering component focused on UI/event orchestration and move derivation/transform logic to pure helpers, while preserving single source of truth in component state.
- **Decision:** `reuse/integrate` (extract existing derived/orchestration logic into dedicated modules, preserve contracts).
- **Rejected options:** full rewrite of wizard/router flows.

## Root cause (mandatory)
- **Symptom:** after wave2, functional behavior is stable, but edit blast radius stays high because orchestration blocks still live inside monolith files.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/console.py` and inspect `control-tower` action-center/migration-program orchestration block.
  2. Open `console-web/src/components/ProvisioningWizard.tsx` and inspect dense `useMemo` derived-state layer.
  3. Compare touch-surface for small changes inside these blocks.
- **Evidence:** `UX-11/UX-12` remain `Open` (mitigated wave2), high LOC monolith files, multi-concern diff surface.
- **Five Whys:**
  1. Why risk remains? Orchestration and derived-state logic are still embedded in large files.
  2. Why that matters? Small behavior-safe changes still require broad context and large diffs.
  3. Why broad diffs are bad? Review and regression confidence drop.
  4. Why wave2 wasn’t enough? Wave2 extracted helper/lexicon layers, but not orchestration/derived layers.
  5. Why wave3 now? This is the next deterministic block in residual-debt contract.
- **Root cause statement:** unresolved orchestration/derived-state coupling keeps `UX-11/UX-12` in mitigated-but-open state.
- **Fix mechanism:** extract bounded orchestration and derived-state modules with deterministic regression checks and no contract changes.

## Reuse-first plan (mandatory)
- **Internal reuse:** preserve existing logic; move to dedicated modules and rewire imports only.
- **External reuse:** React official guidance for extracting non-render logic from component body.
- **Why not build from scratch:** behavior already validated by merged UVC stages; rewrite would add regression risk.

## Invariant
- Не менять runtime business semantics и backend/frontend API contracts.
- Не добавлять новые top-level tabs/routes.
- Не ослаблять anti-drift/CI/session gates.

## Scope
- Backend (`UX-11`): extract control-tower action-center/migration-program composition logic from `console.py` to `console_control_tower_program.py` with deterministic tests.
- Frontend (`UX-12`): extract `ProvisioningWizard` derived-state selectors/formatters (`step status`, `timeline`, `readiness` collections) to `provisioning-wizard-derived.ts`.
- Keep targeted platform-admin lane as regression guard.
- Sync session/state/structure/master docs for current block.

## Out of scope
- Full feature-router split for all `console.py`.
- Full multi-component visual split of Provisioning Wizard steps.
- Any onboarding policy/runtime semantic change.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave3-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_control_tower_program.py` (new)
- `truffles-api/tests/test_console_control_tower_program.py` (new)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-derived.ts` (new)
- `console-web/e2e/platform-admin.spec.ts` (only if selector/contracts need update)

## Plan (1..N)
1. Register Wave3 TP in active session metadata and canon map.
2. Extract backend control-tower orchestration layer into dedicated module and rewire router imports.
3. Add deterministic tests for new backend module.
4. Extract frontend wizard derived-state helpers into dedicated module and rewire component usage.
5. Run targeted lint/pytest/e2e/session-check and capture evidence.
6. Update `STATE`/master/backlog/session docs, commit, push, open PR.

## DoD
- `console.py` uses extracted orchestration module for action-center/migration-program composition.
- `ProvisioningWizard.tsx` uses extracted derived-state module for wave3 target useMemo logic.
- New backend tests for extracted module are green.
- Targeted platform-admin e2e lane remains green.
- Canon docs synced with evidence and next-block contract.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py truffles-api/tests/test_console_control_tower_program.py`
- `pytest -q truffles-api/tests/test_console_control_tower_program.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-derived.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff of extracted backend/frontend modules and rewiring.
- Targeted pytest/lint/e2e outputs.
- Updated `STATE.md` NOW entry + master report status line + backlog wave status.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` targeted platform-admin runs.
- Fail-fast lock: only platform-admin grep lane.
- Stop condition: repeated e2e failure without new RCA evidence.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** behavior-preserving extraction + deterministic regression checks.
- **Go/no-go signals:** py_compile green, pytest green, lint green, targeted e2e green.
- **Rollback:** revert Wave3 commit and re-run checks.
- **Post-release monitoring window:** PR CI (`console-e2e`, `console-contract-predeploy`).

## Rollback
- `git revert COMMIT_SHA` and rerun commands from `Checks`.

## No-go
- API/schema contract edits in this block.
- New UX entry points/tabs/routes.
- Hidden fallback branches that bypass ownership matrix.

## Risks/Blockers
- Hidden dependencies while extracting orchestration helpers can trigger runtime import errors.
- E2E flakes outside targeted lane may still appear.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: full router domain split and full wizard step-component split remain after Wave3.
- `Why not in this block`: bounded deterministic scope to keep regression surface controllable.
- `Risk if deferred`: medium (future changes still touch monolith entry files).
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSEOUT-A705`.
- `Expiry/trigger to stop deferral`: if next change still requires edits across >3 unrelated concerns in either monolith.

## Next-block contract (mandatory)
- `Next block objective`: finalize closeout decision (`UX-11/UX-12` open->fixed or explicit residual) with post-wave metrics and evidence sync.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: Wave3 checks not green or PR not merged.
- `Owner role for closure`: Brain + Top Architect.
