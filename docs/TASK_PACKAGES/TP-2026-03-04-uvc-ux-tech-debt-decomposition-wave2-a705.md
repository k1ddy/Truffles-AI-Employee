# TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave2-a705

## Block identity
- `BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE2-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#886` (`dbd810d0`) into `main`
- `UNLOCKS`: UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE3-A705

## Название/цель
Закрыть второй полноценный этап structural-debt по `UX-11` и `UX-12` без изменения бизнес-поведения: вынести доменные helper-блоки `control-tower` из `console.py` и вынести крупный domain-lexicon слой из `ProvisioningWizard.tsx` в отдельные модули, сохранив текущие UX-loop и API контракты.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-11`, `UX-12`)

## Requirement traceability (mandatory)
- `REQ-1` no disconnected/duplicate UX actions:
  - solution: no new tabs/routes/CTA branches; only internal decomposition and import rewiring.
  - proof: existing platform-admin e2e lane remains green.
- `REQ-2` no shortcut/costyl in runtime path:
  - solution: pure extraction of deterministic helpers/config maps, no semantic hardcode/fallback branch changes.
  - proof: router/component behavior snapshots unchanged by tests.
- `REQ-3` optimize existing surfaces first:
  - solution: targeted decomposition inside existing `console.py` and `ProvisioningWizard.tsx`.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/console_control_tower_utils.py` (new)
  - `truffles-api/tests/test_console_control_tower_utils.py` (new)
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/components/provisioning-wizard-domain.ts` (new)
  - `console-web/e2e/platform-admin.spec.ts`
- `Baseline commands`:
  - `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
  - `rg -n "^def _build_control_tower_issue_counts|^def _build_admin_control_tower_migration_wave_detail|^def _build_migration_signals" truffles-api/app/routers/console.py`
  - `rg -n "^const MISSING_LABELS|^const AUTOPILOT_FIELD_GUIDE|^const MANUAL_STEP_FIELD_GUIDE|^function formatMissingRequirement" console-web/src/components/ProvisioningWizard.tsx`
- `FACT findings`:
  - `console.py` remains overgrown (`25370` LOC snapshot).
  - `ProvisioningWizard.tsx` remains overgrown (`5332` LOC snapshot).

## One web search (mandatory before implementation)
- **Query (exact):** `site:react.dev extract component`
- **Date/time (local):** `2026-03-04 09:55 +0500`
- **Sources opened (from this query):**
  - `https://react.dev/learn/importing-and-exporting-components`
- **Found reusable solution:** isolate large UI files by extracting stable component/domain units with explicit exports/imports while preserving data flow.
- **Decision:** `reuse/integrate` (extract existing constants/formatters/helpers into dedicated modules and rewire imports).
- **Rejected options:** full rewrite of onboarding flow or routing contracts.

## Root cause (mandatory)
- **Symptom:** UVC UX loops are functionally stable, but future edits remain high-risk because `console.py` and `ProvisioningWizard.tsx` still mix too many responsibilities.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/console.py` and inspect mixed control-tower helper block with router handlers.
  2. Open `console-web/src/components/ProvisioningWizard.tsx` and inspect embedded domain dictionaries/field-guides/formatters inside main component file.
  3. Measure LOC and touch-surface (`wc -l`, `rg`) before change.
- **Evidence:** backlog `UX-11/UX-12`, current LOC snapshot, wave1 extraction already done but insufficient for full maintainability.
- **Five Whys:**
  1. Why future UX/API changes are risky? Large files couple unrelated concerns.
  2. Why coupling persists? Domain helper layers still live in monolith files.
  3. Why this slows delivery? Any small change forces broad diff + broad review surface.
  4. Why wave1 was not enough? Wave1 only extracted generic utility helpers and merge-red fix.
  5. Why Wave2 now? It is next deterministic block in residual-debt contract.
- **Root cause statement:** structural coupling remains in control-tower and provisioning domain helper layers, keeping blast radius high despite stable runtime behavior.
- **Fix mechanism:** extract bounded domain helper modules (backend + frontend), keep contracts unchanged, and assert continuity with deterministic checks.

## Reuse-first plan (mandatory)
- **Internal reuse:** keep existing logic as-is, move into dedicated modules with explicit imports.
- **External reuse:** React official component extraction guidance.
- **Why not build from scratch:** existing behavior already validated by merged UVC stages; rewrite would increase regression risk.

## Invariant
- Не менять runtime business semantics и backend/frontend API contracts.
- Не добавлять новые top-level tabs/routes.
- Не ослаблять anti-drift/CI/session gates.

## Scope
- Backend (`UX-11`): extract pure/mapping migration/control-tower helper functions from `console.py` into `console_control_tower_utils.py`.
- Frontend (`UX-12`): extract provisioning domain dictionaries/field guides/formatters from `ProvisioningWizard.tsx` into `provisioning-wizard-domain.ts`.
- Add deterministic tests for extracted backend helper module.
- Keep targeted platform-admin e2e lane as regression guard.
- Sync session/state/structure/master docs for current block.

## Out of scope
- Full router split by feature files.
- Full component architecture rewrite of Provisioning Wizard.
- Any onboarding policy/contract semantic change.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave2-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_control_tower_utils.py` (new)
- `truffles-api/tests/test_console_control_tower_utils.py` (new)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/provisioning-wizard-domain.ts` (new)
- `console-web/e2e/platform-admin.spec.ts` (only if selector/contracts need update)

## Plan (1..N)
1. Register Wave2 TP in active session metadata and canon map.
2. Extract backend control-tower helper layer to dedicated service module and rewire imports in router.
3. Extract frontend provisioning domain lexicon/formatters to dedicated domain module and rewire component imports.
4. Add/update deterministic tests for backend extracted helpers.
5. Run targeted lint/pytest/e2e/session-check and capture evidence.
6. Update STATE/master/structure, commit, push, open PR.

## DoD
- `console.py` uses extracted control-tower helper module for Wave2 target functions.
- `ProvisioningWizard.tsx` uses extracted provisioning domain module for Wave2 target constants/formatters.
- New backend unit tests for extracted helper module are green.
- Targeted platform-admin e2e lane remains green.
- Canon docs synced with evidence and next-block contract.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_utils.py truffles-api/tests/test_console_control_tower_utils.py`
- `pytest -q truffles-api/tests/test_console_control_tower_utils.py`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-domain.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff of extracted backend/frontend modules and rewiring.
- Targeted pytest/lint/e2e outputs.
- Updated `STATE.md` NOW entry + master report status line.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` targeted platform-admin runs.
- Fail-fast lock: only platform-admin grep lane.
- Stop condition: repeated e2e failure without new RCA evidence.
- Escalation path: Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** behavior-preserving extraction + deterministic regression checks.
- **Go/no-go signals:** py_compile green, pytest green, lint green, targeted e2e green.
- **Rollback:** revert Wave2 commit and re-run checks.
- **Post-release monitoring window:** PR CI (`console-e2e`, `console-contract-predeploy`).

## Rollback
- `git revert COMMIT_SHA` and rerun commands from `Checks`.

## No-go
- API/schema contract edits under the same block.
- New UX entry points/tabs/routes.
- Hidden fallback branches that bypass ownership matrix.

## Risks/Blockers
- Hidden imports/dependencies from extracted helpers can cause runtime name errors if not fully rewired.
- E2E flakes outside targeted lane may still appear.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: deep feature-router split (`console.py`) and full multi-file view-state decomposition (`ProvisioningWizard.tsx`) remain after Wave2.
- `Why not in this block`: preserve bounded scope and deterministic verification.
- `Risk if deferred`: medium (large diff surface for future cross-domain edits).
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE3-A705`.
- `Expiry/trigger to stop deferral`: if any next change needs edits across >3 unrelated concerns in either monolith.

## Next-block contract (mandatory)
- `Next block objective`: finish Wave3 with feature-slice modules for onboarding/control-tower handlers and reduce direct monolith ownership.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: Wave2 checks not green or PR not merged.
- `Owner role for closure`: Brain + Top Architect.
