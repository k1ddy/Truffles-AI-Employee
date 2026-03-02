# TP-2026-03-02-uvc-ux-convergence-a705

## Block identity
- `BLOCK_ID`: UVC-CONSOLE-UX-CONVERGENCE-A705
- `PARENT_BLOCK_ID`: none
- `DEPENDS_ON`: none
- `UNLOCKS`: UVC-CONSOLE-UX-CONVERGENCE-HARDENING-A705

## Название/цель
Свести UVC control-loop к уже существующим вкладкам (`Tenants`, `Integrations`, `Company Workspace`, `Ops`) без добавления новой продуктовой зоны по умолчанию, убрать дубли и сделать действия интуитивными по бизнес-логике.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/app/tenants/use-tenants-action-queue.ts`
  - `console-web/src/app/tenants/use-tenants-actions.ts`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/components/TenantsTopControls.tsx`
  - `console-web/src/app/tenants/tenants-page-view.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `rg -n "control-tower|ControlTower|control tower" console-web/src/lib/api-client.ts console-web/src/types/api.generated.ts`
  - `rg -n "controlTowerEnabled|tenants-control-tower|workspaceMode|actionQueue" console-web/src/app/tenants/page.tsx console-web/src/components/TenantsTopControls.tsx console-web/src/app/tenants/tenants-page-view.tsx`
  - `rg -n "provider-ops-queue|integrations-workspace-cta|integrations-row-open-workspace" console-web/src/app/integrations/page.tsx`
  - `rg -n "recommended-action|incident-guide|provider-actions|workspace-recommended-open-execute" console-web/src/app/company-workspace/page.tsx`
  - `rg -n "control-tower/(overview|readiness-board|drift-board|action-center|migration-program)" truffles-api/app/routers/console.py contracts/console_api/openapi.v1.yaml`
  - `rg -n "Integrations row to Company Workspace|integrations-workspace-cta|integrations-row-open-workspace" console-web/e2e/platform-admin.spec.ts`
- `FACT findings`:
  - Backend UVC phase12/13 endpoints are present and covered in OpenAPI, but frontend `adminApi` has no control-tower methods.
  - `Tenants` already contains control-loop primitives (modes, action queue, KPI drilldown), but queue semantics are local heuristics and not sourced from backend action-center/migration surfaces.
  - `Integrations` duplicates fleet-level queue/control concerns already represented in `Tenants`.
  - `Workspace` remains the real execute-layer, but linking relies on ad-hoc `localStorage` context markers.
  - Feature-flag UX debt remains (`NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER`, disabled/info banners).
- `Detected drift (docs vs code)`: report chain marks UCPV1 phase12/13 passed; frontend integration remains partial.

## One web search (mandatory before implementation)
- **Query (exact):** `enterprise dashboard progressive disclosure plain language UX guidelines`
- **Date/time (local):** `2026-03-02 16:34 (+05, Asia/Almaty)`
- **Why this query is precise:** нужно выбрать UX-паттерн для сложного control-loop без добавления новой вкладки, с упрощением терминов и без дублирующих действий.
- **Sources opened (from this query):**
  - NN/g, Progressive Disclosure: `https://www.nngroup.com/articles/progressive-disclosure/`
  - Interaction Design Foundation, Progressive Disclosure: `https://www.interaction-design.org/literature/topics/progressive-disclosure`
- **Existing solutions found:** progressive disclosure, single-path access to advanced actions, primary-vs-secondary information split, explicit guidance labels.
- **Decision:** `reuse/integrate` UX pattern progressive disclosure into existing tabs instead of building a new top-level page.
- **Rejected options:** new standalone Control Tower tab as default IA path (rejected due duplication risk and higher cognitive/maintenance cost).
- **Open questions:** none for this block; terminology simplification table will be implemented as code constants.

## Root cause (mandatory)
- **Symptom:** бизнес-оператор видит разрозненный UX: похожие очереди/CTA в нескольких вкладках и неполный UVC-контур на frontend.
- **Minimal reproduction:**
  - Открыть `Tenants` -> увидеть локальный action queue + workspace modes.
  - Открыть `Integrations` -> увидеть provider queue + CTA в `Workspace`.
  - Проверить `adminApi` -> отсутствуют методы `control-tower/*`.
- **Evidence to capture:** git diff, lint/type/e2e, селекторы и URL-переходы в smoke.
- **Five Whys (or equivalent):**
  1. Почему дубли есть? Потому что control-loop развивался по зонам (`Tenants`, `Integrations`, `Workspace`) отдельно.
  2. Почему зоны не сведены? Нет frontend action-source на backend `action-center`.
  3. Почему это не поймали на phase closure? Phase12/13 закрывались как backend-contract slices.
  4. Почему это опасно? Пользователь получает несколько competing entry points и неочевидный execute-path.
  5. Почему сейчас фикс? Пользователь явно требует UVC-consistent, intuitive, non-duplicated UX.
- **Root cause statement:** frontend orchestration не синхронизирована с UVC backend orchestration; управление осталось локально-эвристическим и фрагментированным.
- **Fix mechanism:** подключить `control-tower` контракты в существующий `Tenants` control-loop, убрать дубли из `Integrations`, сохранить `Workspace` единственным execute-layer.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `Tenants` control-loop primitives (`use-tenants-action-queue`, `use-tenants-actions`, KPI panels).
  - `Integrations -> Workspace` context bridge.
  - `Workspace` recommended action and provider-action modal.
  - Existing backend UVC endpoints (`overview/readiness/drift/action-center/migration/wave`).
- **External reuse:** progressive disclosure UX guidance (NN/g + IxDF) for primary/secondary information layering.
- **Why not reinvent the wheel:** existing tabs already map to required business layers; new page would duplicate responsibilities and increase drift risk.

## Invariant
- `Company Workspace` remains the only execute-layer for provider remediation.
- No cross-tenant/context regression in navigation/state transfer.
- No semantic hardcode in runtime core; changes are UI orchestration only.
- Existing role guards remain fail-closed.

## Scope
- Add missing control-tower methods/types in frontend API layer.
- Refactor `Tenants` queue source toward backend UVC action-center/migration data.
- Remove/trim duplicated fleet queue logic in `Integrations` while keeping branch diagnostics.
- Simplify labels/tooltips for business readability.
- Update e2e to enforce end-to-end control-loop linkage and prevent future drift.

## Out of scope
- Backend endpoint/schema changes.
- New top-level nav item/page for standalone Control Tower.
- Ops incident engine redesign.

## Touch-list
- `console-web/src/types/api.generated.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/app/tenants/use-tenants-action-queue.ts`
- `console-web/src/app/tenants/use-tenants-actions.ts`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/TenantsTopControls.tsx`
- `console-web/src/app/tenants/tenants-page-view.tsx`
- `console-web/e2e/platform-admin.spec.ts`

## Plan (1..N)
1. Sync API contract layer: regenerate `api.generated.ts`, add typed `adminApi` control-tower methods/params.
2. Build UVC read-model adapter in `Tenants` and map backend action items to existing action queue UI.
3. Refactor queue intent dispatcher to consume backend `kind/source/priority/href/params` with deterministic routing.
4. Remove duplicate fleet queue from `Integrations`; keep facts-only diagnostics and explicit execute CTA.
5. Replace temporary control-tower flag banners with stable business guidance copy and tooltip glossary.
6. Extend e2e smoke for `Tenants control-loop -> Workspace execute` and regression checks for duplicated queues.
7. Run checks, capture evidence, sync session/STATE docs.

## DoD
- `Tenants` is primary UVC control-loop surface using backend action-center/migration data.
- `Integrations` no longer exposes competing fleet action queue.
- `Workspace` remains sole execute path; deep-link from control-loop works deterministically.
- Complex terms replaced with user-readable business labels and inline hints.
- `api.generated.ts` and `adminApi` are in sync with OpenAPI control-tower endpoints.
- e2e covers control-loop linkage and fails on reintroduced drift.

## Checks
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`
- `cd console-web && npm run build`
- `cd console-web && npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Updated code diff for touched files.
- Lint/build/e2e command outputs.
- Selector-level evidence in e2e for control-loop to workspace transitions.
- Session log + index updates.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` full e2e targeted runs.
- **Fail-fast / scenario lock:** only `platform-admin.spec.ts` lanes relevant to tenants/integrations/workspace.
- **Stop condition:** two consecutive e2e failures with no new root-cause evidence -> stop and reopen RCA.
- **Escalation path:** Brain / Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout by existing environment flags, but UI path keeps backward-compatible workspace execute.
- **Go/no-go signals:** e2e pass for control-loop path, no console build/lint regressions, no RBAC regression.
- **Rollback:** revert commit restoring previous queue source and integrations panel sections.
- **Post-release monitoring window:** `24h` on platform-admin operations.

## Doc sync plan (after implementation)
- `docs/SESSIONS/SESSION-2026-03-02-uvc-ux-convergence-a705.md`
- `docs/SESSION_INDEX.md`
- `STATE.md` (NOW + evidence line)
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`
- `Drift closeout rule`: no block close without docs update or explicit GAP with owner.

## Rollback
- Revert block commit in branch; rerun lint/build/e2e smoke to confirm previous behavior.

## No-go
- Adding new standalone Control Tower page as default UX.
- Leaving duplicated fleet action queues in both `Tenants` and `Integrations`.
- Shipping without e2e linkage checks.

## Risks/Blockers
- Existing tests may assume old integrations queue section selectors.
- Large TS generated file diff can create merge friction.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `Tenants` page remains large and could benefit from further decomposition.
- `Why not in this block`: primary goal is behavior convergence and duplicate removal, not structural refactor.
- `Risk if deferred`: maintainability cost and slower future feature delivery.
- `Linked follow-up Task Package(s)`: `TP-2026-03-03-uvc-tenants-decomposition-a705` (to be created after closure).
- `Expiry/trigger to stop deferral`: if next control-loop feature requires touching >3 tenants modules.

## Next-block contract (mandatory)
- `Next block objective`: decompose `Tenants` control-loop into bounded modules after convergence is stable.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/app/tenants/page.tsx`
- `Blocked-by conditions`: this block merged with green e2e and no duplicate queue behavior.
- `Owner role for closure`: Brain / Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes (after this block merge).
- `Start from`: `console-web/src/app/tenants/use-tenants-action-queue.ts`
- `Do not touch`: backend runtime routers/schemas in this block.
- `Open risks`: selector drift in legacy e2e checks.
- `First command to verify`: `rg -n "control-tower|provider-ops-queue|workspace-recommended-open-execute" console-web/src/app/tenants console-web/src/app/integrations console-web/src/app/company-workspace`
