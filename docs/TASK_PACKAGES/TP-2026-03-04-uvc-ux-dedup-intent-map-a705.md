# TP-2026-03-04-uvc-ux-dedup-intent-map-a705

## Block identity
- `BLOCK_ID`: UVC-UX-DEDUP-INTENT-MAP-A705
- `PARENT_BLOCK_ID`: UVC-UX-TECH-DEBT-DECOMPOSITION-A705
- `DEPENDS_ON`: merge of PR `#885` into `main` (`b7717be9`)
- `UNLOCKS`: UVC-UX-DEDUP-INTENT-MAP-A705-WAVE2 (cross-tab copy + telemetry-driven UX cleanup)

## Название/цель
Устранить дубли и неоднозначные CTA в существующих вкладках `Tenants/Integrations/Company Workspace/Ops`, и закрепить единый понятный intent-map (где факт, где действие, где проверка) без добавления новых top-level вкладок.

## Canon refs
- `AGENTS.md`
- `STATE.md` (`NOW`: UVC wave1 merged, next UX optimization requires no new tabs)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705.md`

## Requirement traceability (mandatory)
- `REQ-1` UX actions must be connected and business-clear:
  - solution: remove duplicate entry actions and keep one primary action path per tab context.
  - proof: updated e2e asserts for action path and copy.
- `REQ-2` optimize existing tabs first:
  - solution: changes only in current tabs, no new nav tabs/routes.
  - proof: touch-list contains only existing pages/components/e2e.
- `REQ-3` simplify terminology and add hints:
  - solution: unified intent-map hints with plain language (`Факт -> Действие -> Проверка`).
  - proof: visible intent-map blocks in Tenants/Integrations/Workspace/Ops.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/tenants/tenants-page-view.tsx`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
- `Baseline commands`:
  - `rg -n "integrations-open-workspace-scope|integrations-workspace-guidance|workspace-next-step-ops|ops-back-workspace|tenants-onboarding-open-ops" console-web/src console-web/e2e/platform-admin.spec.ts`
  - `rg -n "Открыть Workspace|Перейти в Ops|Открыть OPS" console-web/src/app/tenants console-web/src/app/integrations console-web/src/app/company-workspace console-web/src/components/OpsPage.tsx`
- `FACT findings`:
  - `Integrations` has duplicated global action entry points (header CTA + dedicated workspace-cta + row-level CTA), which creates competing entry paths.
  - Cross-tab intent semantics exist but are fragmented in copy and placement; operator needs one explicit mental model per tab.

## One web search (mandatory before implementation)
- **Query (exact):** `site:w3.org WCAG 2.2 3.2.3 consistent navigation`
- **Date/time (local):** `2026-03-04 09:17 UTC`
- **Sources opened (from this query):**
  - `https://www.w3.org/TR/WCAG22/#consistent-navigation`
- **Found reusable solution:** keep navigation mechanisms consistent and predictable across pages to reduce cognitive load.
- **Decision:** `reuse/integrate` this principle into existing tabs by normalizing one primary action path and consistent intent-map hints.
- **Rejected options:** adding a new Control Tower top-level tab for this block (violates optimize-existing-tabs constraint).

## Root cause (mandatory)
- **Symptom:** users see overlapping action affordances and uneven hinting between tabs, which weakens action continuity.
- **Minimal reproduction:**
  1. Open `/integrations` and compare header CTA, workspace guidance block, and row CTA.
  2. Continue to `/company-workspace` and `/ops`; observe hint logic is present but not uniformly structured as one intent model.
- **Evidence:** current UI copy/CTA locations in files from touch-list + existing e2e contracts.
- **Five Whys:**
  1. Why confusion? Multiple entry points present the same action intent.
  2. Why duplicated? Features were added by waves for safety, but not consolidated post-merge.
  3. Why not auto-resolved? Anti-drift gates validate contracts/selectors, not CTA uniqueness semantics.
  4. Why business impact? Operators spend extra clicks and context switching on routine remediation flow.
  5. Why now? Wave1 merged; this is the right point for UX consolidation without new architecture churn.
- **Root cause statement:** action semantics across existing tabs are functionally correct but not normalized into a single predictable operator path.
- **Fix mechanism:** consolidate duplicate CTA placements and standardize intent-map copy in current tabs with deterministic e2e checks.

## Reuse-first plan (mandatory)
- **Strategy:** `reuse -> integrate -> configure -> build`
- **Internal reuse:** existing cross-tab flow, existing testids, existing e2e suite (`platform-admin.spec.ts`).
- **External reuse:** WCAG consistent navigation guidance (predictable repeated navigation patterns).
- **Why no rewrite:** behavior is already working; we only normalize UX semantics and CTA placement.

## Invariant
- No new top-level tabs/routes.
- No backend contract changes.
- No runtime semantic hardcode; only UI structure/copy alignment in existing surfaces.

## Scope
- De-duplicate top-level/competing CTA placement in `Integrations`.
- Normalize intent-map hints (`Факт -> Действие -> Проверка`) in `Tenants/Integrations/Workspace/Ops`.
- Keep action continuity and existing deep-link contracts intact.
- Update Playwright smoke expectations where UX contract changed.

## Out of scope
- Full redesign of these pages.
- Backend API/schema changes.
- New business modules/routes.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-dedup-intent-map-a705.md` (new)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-stage1-pr-a705.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`
- `console-web/src/app/tenants/tenants-page-view.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/e2e/platform-admin.spec.ts`

## Plan (1..N)
1. Align session metadata + start this TP block.
2. Apply de-dup in `Integrations` CTA placement and simplify top action row.
3. Add unified intent-map hints in `Tenants/Integrations/Workspace/Ops` with plain language.
4. Update e2e assertions for adjusted UX contract.
5. Run lint + targeted Playwright + session checks and capture evidence.

## DoD
- Duplicate top-level CTA path in `Integrations` removed; one clear primary action entry remains.
- All four target tabs display consistent intent-map guidance (`Факт/Действие/Проверка`) in business language.
- Targeted e2e lane is green and reflects new UX contract.
- Session/STATE/STRUCTURE metadata synced.

## Checks
- `cd console-web && npm run lint -- --file src/app/tenants/tenants-page-view.tsx --file src/app/integrations/page.tsx --file src/app/company-workspace/page.tsx --file src/components/OpsPage.tsx --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Diff with de-dup + intent-map changes on target pages.
- Green lint + targeted e2e output.
- Updated session log + `STATE.md` FACT entry + `STRUCTURE.md` active TP list.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `2` targeted Playwright passes.
- Fail-fast: focused grep only, no full suite.
- Stop condition: two consecutive e2e failures with no new RCA.
- Escalation: Brain/Top Architect.

## Release safety (mandatory for non-doc changes)
- **Rollout strategy:** PR-only canary via existing `console-e2e` + targeted local proof.
- **Go/no-go signals:** lint pass + targeted e2e pass + no selector contract regressions.
- **Rollback:** revert commit and rerun `Checks`.
- **Post-release monitoring window:** first two CI runs after merge (`console-e2e` + `console-contract-predeploy`).
- **Verification after rollback:** ensure previous UX/e2e contract restored.

## Rollback
- `git revert 7541fe0b`
- rerun commands from `Checks`.

## No-go
- Add new top-level tab as shortcut.
- Introduce technical jargon back into primary operator copy.
- Keep duplicate primary CTA paths in same context.

## Risks/Blockers
- Existing e2e selectors tied to old CTA location may need updates.
- Copy normalization can drift if not covered in smoke assertions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `UX-11` (`console.py`) and `UX-12` (`ProvisioningWizard.tsx`) remain open after wave1 mitigation.
- `Why not in this block`: this block is UX-flow normalization, not deeper module decomposition.
- `Risk if deferred`: continued high code-edit blast radius in backend/frontend monolith files.
- `Linked follow-up Task Package(s)`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE2-A705`.
- `Expiry/trigger to stop deferral`: next change requiring >3 unrelated edits in either monolith.

## Next-block contract (mandatory)
- `Next block objective`: execute wave2 structural decomposition (`UX-11/UX-12`) after UX dedup contract is merged.
- `First deterministic check command`: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`
- `Blocked-by conditions`: current dedup/intent-map block not merged green.
- `Owner role for closure`: Brain + Top Architect.

## Branch / worktree / merge policy
- `Branch`: `feat/2026-03-02-uvc-ux-stage1-pr-a705`
- `Worktree path`: `/home/zhan/worktrees/2026-03-02-uvc-ux-stage1-pr-a705`
- `Base ref`: `origin/main`
- `Merge policy`: merge only, no rebase
- `Cleanup`: Brain/Top Architect after merge
