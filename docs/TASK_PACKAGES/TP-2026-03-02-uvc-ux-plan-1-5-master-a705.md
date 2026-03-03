# TP-2026-03-02-uvc-ux-plan-1-5-master-a705

## Block identity
- `BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `PARENT_BLOCK_ID`: UVC-CONSOLE-UX-CONVERGENCE-A705
- `DEPENDS_ON`: merge of PR `#872` (`610ab8f3`) into `main`
- `UNLOCKS`: UVC-UX-STAGE1-A705, UVC-UX-STAGE2-A705, UVC-UX-STAGE3-A705, UVC-UX-STAGE4-A705, UVC-UX-STAGE5-A705

## Название/цель
Закрыть оставшиеся дефекты и UX-разрывы UVC через оптимизацию уже существующих вкладок (`Tenants`, `Integrations`, `Company Workspace`, `Ops`, `Settings`, `Knowledge`, `Marketing`, `Inbox`) без добавления новой верхнеуровневой вкладки по умолчанию; получить интуитивный бизнес-поток, понятные подсказки и отсутствие дублирующих действий.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase12-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase13-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-convergence-a705.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/tenants/**`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
  - `console-web/e2e/platform-admin.spec.ts`
  - `contracts/console_api/openapi.v1.yaml`
- `Baseline commands`:
  - `git log --oneline feat/2026-03-02-uvc-ux-convergence-a705 -n 1`
  - `git log --oneline origin/main -n 20`
  - `rg -n "controlTowerEnabled|control tower disabled|NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER" console-web/src/app/tenants console-web/src/components`
  - `rg -n "provider-ops-queue|recommended_action" console-web/src/app/integrations/page.tsx`
  - `rg -n "workspace-recommended-open-execute|console:workspace_recommended_action" console-web/src/app/company-workspace/page.tsx console-web/src/app/integrations/page.tsx`
  - `rg -n "control-tower/(overview|readiness-board|drift-board|action-center|migration-program)" console-web/src/lib/api-client.ts contracts/console_api/openapi.v1.yaml truffles-api/app/routers/console.py`
  - `rg -n "integrations-row-open-workspace|workspace-recommended-open-execute|control-tower" console-web/e2e/platform-admin.spec.ts`
- `FACT findings`:
  - Backend UVC phase12/13 contract surfaces are present and stable in `truffles-api` and OpenAPI.
  - UX convergence implementation exists in branch `feat/2026-03-02-uvc-ux-convergence-a705` and PR `#872`, but is not yet part of `origin/main`.
  - In current `main`, feature-flag debt and duplicated queue semantics are still observable in `Tenants`/`Integrations`.
  - Deep-link e2e coverage exists partially; complete anti-drift suite for cross-tab business loops is still missing.
- `Detected drift (docs vs code)`: UVC backend phase closure is `passed`; frontend convergence is branch-level until PR `#872` merge.

## One web search (mandatory before implementation)
- **Query (exact):** `plain language progressive disclosure complex dashboard UX`
- **Date/time (local):** `2026-03-02 17:53, Asia/Almaty`
- **Why this query is precise:** нужно выбрать UX-правила для сложной операционной панели без новой вкладки и без перегрузки терминологией.
- **Sources opened (from this query):**
  - Interaction Design Foundation, Progressive Disclosure: `https://www.interaction-design.org/literature/topics/progressive-disclosure`
  - Interaction Design Foundation, Cognition in UX/UI Design: `https://www.interaction-design.org/literature/topics/cognition`
- **Existing solutions found:** progressive disclosure, reduction of cognitive load, staged reveal of advanced actions, plain-language hints near decision points.
- **Decision:** `integrate` — применить progressive disclosure + plain-language guidance в уже существующих вкладках вместо добавления отдельной зоны.
- **Rejected options:** new standalone default Control Tower tab (дублирует ответственность и повышает когнитивную сложность).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** пользователи видят фрагментированную бизнес-логику в Console (часть действий дублируется или названа по-разному между вкладками), а сложные термины не всегда расшифрованы по месту.
- **Minimal reproduction:**
  1. Открыть `Tenants` и `Integrations`.
  2. Сравнить action/queue секции и формулировки действий.
  3. Проверить переходы в `Company Workspace` и наличие одинаковых смыслов под разными названиями.
- **Evidence to capture:** diff UI/IA matrix, e2e flows, UX copy glossary coverage, regression checks, support-feedback deltas.
- **Five Whys (or equivalent):**
  1. Почему UX выглядит фрагментированным? Потому что контрольный цикл развивался по вкладкам отдельно.
  2. Почему дубли остались? Потому что responsibilities matrix не была зафиксирована как контракт.
  3. Почему сложные термины мешают? Потому что нет обязательного plain-language словаря в UI.
  4. Почему риск регрессии высокий? Потому что e2e покрывает только часть deep-link и не защищает весь кросс-вкладочный контур.
  5. Почему это не закрыть одним коммитом? Потому что нужен полный цикл: IA cleanup -> copy simplification -> flow hardening -> anti-drift -> rollout evidence.
- **Root cause statement:** отсутствует единый, контрактно закрепленный UX orchestration layer для бизнес-смыслов между вкладками, плюс нет обязательной системы понятных формулировок и полноты проверки сквозных сценариев.
- **Fix mechanism:** реализовать программу 1..5 с четкой ownership-матрицей вкладок, plain-language словарем, сквозными сценариями, anti-drift проверками и поэтапным rollout с измеримой эффективностью.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing UVC backend contracts `/admin/control-tower/*`.
  - existing tabs and flows (`Tenants` control loop, `Integrations` fact layer, `Company Workspace` execute layer, `Ops` incidents).
  - existing e2e framework in `console-web/e2e/platform-admin.spec.ts`.
- **External reuse:** progressive disclosure and cognitive-load reduction guidance from opened UX sources.
- **Why not reinvent the wheel:** архитектура вкладок и backend-API уже реализованы; оптимальный путь — убрать дубли и стандартизировать UX semantics поверх существующего контура.

## Invariant
- Не добавлять новую верхнеуровневую вкладку по умолчанию; сначала максимальная оптимизация текущих вкладок.
- `Company Workspace` остается единственным execute-слоем для remediation/provider actions.
- `Integrations` остается факт-слоем (диагностика/матрица/состояния), а не competing action-center.
- `Tenants` остается главным orchestration-слоем для lifecycle/provisioning/control-loop.
- Любой ключевой action должен иметь понятный plain-language label и contextual hint.

## Scope
- Полная реализация программы 1..5 (через этапы и волны ниже) для UX/IA/flow/quality hardening UVC.
- Удаление дублирующих кнопок/секций/маршрутов.
- Упрощение терминов, подсказки и унификация бизнес-лексики.
- Обязательное доказательство эффективности на практике (checks + UX/business metrics).

## Out of scope
- Изменение LLM policy-core и runtime semantic routing.
- Backend migration redesign beyond existing UVC contracts.
- Введение нового top-level product area без отдельного owner-решения и evidence.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage1-ia-matrix-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage2-language-hints-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage3-cross-tab-flows-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage4-quality-antidrift-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage5-rollout-efficiency-a705.md`
- `console-web/src/app/tenants/**`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/e2e/platform-admin.spec.ts`

## Plan (1..N)
1. **Stage 1 (Plan item 1): Responsibility Matrix + IA Cleanup (full).**
   - **Objective:** убрать все UX-дубли и закрепить единую матрицу ответственности вкладок.
   - **Wave 1:** inventory and mapping of actions/buttons/queues by tab with `keep|move|remove` decision per item.
   - **Wave 2:** implement cleanup in `Tenants/Integrations/Workspace/Ops` with deterministic deep-links only.
   - **Wave 3:** lock IA contract in docs + e2e selectors to prevent reintroduction.
   - **Closure criteria:** 0 duplicated primary actions across tabs; every action has one canonical entry point.
2. **Stage 2 (Plan item 2): Plain Language + Contextual Hints (full).**
   - **Objective:** сделать все ключевые бизнес-действия интуитивно понятными без внутренних терминов.
   - **Wave 1:** create canonical glossary (`term -> plain label -> hint -> where used`).
   - **Wave 2:** apply labels/hints across existing tabs and action cards.
   - **Wave 3:** UX consistency audit for wording collisions and unresolved technical jargon.
   - **Closure criteria:** 100% primary CTA and status labels mapped in glossary; no unexplained complex terms in critical flows.
3. **Stage 3 (Plan item 3): Cross-Tab Business Flows Hardening (full).**
   - **Objective:** сделать сквозные пользовательские пути цельными и предсказуемыми.
   - **Wave 1:** `Tenants action-center -> Workspace execute -> Ops confirmation` full loop.
   - **Wave 2:** `Integrations diagnostics -> Workspace remediation -> Tenants lifecycle refresh` full loop.
   - **Wave 3:** `Inbox/Marketing/Knowledge` handoff links into core control loop with clear return paths.
   - **Closure criteria:** каждый критичный business loop завершается без dead-end и с понятным next action.
4. **Stage 4 (Plan item 4): Quality + Anti-Drift Contract Suite (full).**
   - **Objective:** сделать “UI снова отстал от backend” технически невозможным без падения проверок.
   - **Wave 1:** contract smoke for control-tower endpoints consumption in frontend API layer.
   - **Wave 2:** e2e deep-link and role-guard suite for all Stage 3 loops.
   - **Wave 3:** regression gate for duplicated-action selectors and glossary coverage checks.
   - **Closure criteria:** green deterministic suite with explicit anti-drift checks on each critical loop.
5. **Stage 5 (Plan item 5): Rollout, Efficiency Proof, and Legacy Removal (full).**
   - **Objective:** закрыть программу практической эффективностью и удалить временные/костыльные пути.
   - **Wave 1:** phased rollout with go/no-go signals and rollback drill.
   - **Wave 2:** measure operational UX outcomes (time-to-action, misroute rate, repeated-click rate, unresolved handoff rate).
   - **Wave 3:** remove legacy fallbacks/flags and finalize docs/state as passed program.
   - **Closure criteria:** целевые метрики достигнуты, legacy paths удалены, user-facing friction materially reduced.

## DoD
- PR `#872` merged into `main`; baseline convergence becomes canonical.
- All five stages closed with separate TP/Report artifacts and green checks.
- No duplicate primary actions across `Tenants/Integrations/Workspace/Ops`.
- Plain-language glossary covers all critical business actions and statuses.
- End-to-end flows pass deterministic e2e and remain stable after release window.
- Program effectiveness proven by predefined UX/business metrics (not only “tests green”).

## Checks
- `git merge-base --is-ancestor 610ab8f3 origin/main`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- PR links and merged commits for each stage.
- e2e artifacts for deep-link and role-guard flows.
- before/after IA matrix and glossary diff.
- quantitative UX metrics over rollout window (defined in Stage 5 TP).
- `STATE.md` entries with facts and evidence per stage.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` full e2e runs per stage (`10` total for 5 stages).
- **Fail-fast / scenario lock:** run only impacted suites by stage; full suite only at stage closure.
- **Stop condition:** two consecutive runs without new evidence -> stop-the-line and reopen RCA.
- **Escalation path:** Brain + Top Architect approval for additional loops.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout by stage (`canary -> cohort -> fleet`) with feature-level toggles only during rollout.
- **Go/no-go signals:** no critical e2e regressions, stable action completion rate, no increase in wrong-route transitions.
- **Rollback:** stage-level revert with deterministic re-check of previous stable baseline.
- **Post-release monitoring window:** `72h` per major stage and `7d` for final Stage 5 closure.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `docs/CONSOLE_AUDIT/pages/tenants.md`
  - `docs/CONSOLE_AUDIT/pages/integrations.md`
  - `docs/CONSOLE_AUDIT/pages/company-workspace.md`
  - `STATE.md`
  - `docs/SESSIONS/*`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - stage cannot be closed without matching code + docs + evidence; otherwise explicit `GAP` with owner and next TP.

## Rollback
- Revert the stage commit(s) and rerun deterministic checks before reattempt.

## No-go
- Добавлять новую top-level вкладку до закрытия Stages 1..3 и without explicit owner approval + evidence.
- Оставлять дублирующие action entry points между `Tenants` и `Integrations`.
- Оставлять технические термины в primary CTA без plain-language hint.
- Ослаблять acceptance gates ради скорости.

## Risks/Blockers
- PR `#872` may remain unmerged and block start.
- Selector churn can break e2e if not versioned with IA updates.
- Over-aggressive cleanup may hide necessary secondary actions; mitigation is progressive disclosure, not deletion by default.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: large `Tenants` page surface and legacy localStorage fallback semantics.
- `Why not in this block`: this is a master planning TP; debt removal is distributed across Stages 1, 3, and 5.
- `Risk if deferred`: recurrent UX drift and repeated duplication in future changes.
- `Linked follow-up Task Package(s)`: UVC-UX-STAGE1-A705 .. UVC-UX-STAGE5-A705.
- `Expiry/trigger to stop deferral`: if any new UX feature requests another cross-tab shortcut before Stage 3 closure, stop and prioritize debt closure first.

## Next-block contract (mandatory)
- `Next block objective`: create and execute `UVC-UX-STAGE1-A705` with full `keep|move|remove` IA matrix and duplicate-removal implementation.
- `First deterministic check command`: `git merge-base --is-ancestor 610ab8f3 origin/main`
- `Blocked-by conditions`: PR `#872` not merged into `main`.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`.
- `Do not touch`: runtime policy-core/LLM semantics; scope is console UX orchestration.
- `Open risks`: merge timing of PR `#872`, e2e selector drift.
- `First command to verify`: `git merge-base --is-ancestor 610ab8f3 origin/main && echo "convergence merged" || echo "blocked: convergence not merged"`
