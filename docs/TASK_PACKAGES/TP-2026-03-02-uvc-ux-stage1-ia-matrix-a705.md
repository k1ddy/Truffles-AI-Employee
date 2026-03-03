# TP-2026-03-02-uvc-ux-stage1-ia-matrix-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STAGE1-A705
- `PARENT_BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `DEPENDS_ON`: merged PR `#872` (`610ab8f3`) on `main`
- `UNLOCKS`: UVC-UX-STAGE2-A705

## Название/цель
Закрыть Stage 1 программы UVC UX: зафиксировать матрицу ответственности вкладок и убрать оставшиеся дубли/скрытые состояния в навигации действий, чтобы у каждого бизнес-действия был один понятный entry point.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-convergence-a705.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/app/tenants/**`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-02-uvc-stage1-ia-matrix-a705.md`
- `Baseline commands`:
  - `git merge-base --is-ancestor 610ab8f3 origin/main`
  - `rg -n "provider-ops-queue" console-web/src/app/integrations/page.tsx`
  - `rg -n "console:workspace_recommended_action|readWorkspaceRecommendedActionContext" console-web/src/app/company-workspace/page.tsx`
  - `rg -n "tenants-action-queue|integrations-row-open-workspace|workspace-recommended-open-execute" console-web/e2e/platform-admin.spec.ts`
- `FACT findings`:
  - Convergence baseline merged in `main` and active.
  - Primary duplicate queue in `Integrations` is removed, but `Workspace` still had legacy hidden state fallback for recommended action.
  - Deep-link path is query-driven; fallback storage path is redundant and increases ambiguity in execution source.
- `Detected drift (docs vs code)`: no backend drift; Stage 1 UX ownership matrix was not yet codified as artifact.

## One web search (mandatory before implementation)
- **Query (exact):** `site:design-system.service.gov.uk complex tasks service pages`
- **Date/time (local):** `2026-03-02 18:01, Asia/Almaty`
- **Why this query is precise:** нужен high-signal reference для сложных операционных интерфейсов с одним понятным пользовательским маршрутом и без competing entry points.
- **Sources opened (from this query):**
  - GOV.UK Design System, Task list pages: `https://design-system.service.gov.uk/patterns/task-list-pages/`
  - GOV.UK Design System, Complete multiple tasks: `https://design-system.service.gov.uk/patterns/complete-multiple-tasks/`
- **Existing solutions found:** decomposition of complex flows into explicit task paths, clear progress cues, one primary next action per context.
- **Decision:** `integrate` — применить task-path IA для распределения обязанностей между существующими вкладками и убрать скрытые альтернативные источники состояния.
- **Rejected options:** keep dual-source action context (`query + storage`) because it hides real action origin and complicates operator understanding.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** у части действий остаются размытые источники запуска и маршрутизации, что снижает предсказуемость UX.
- **Minimal reproduction:**
  1. Открыть `Company Workspace` через deep-link из `Tenants`/`Integrations`.
  2. Сравнить источник подсказки действия по URL и скрытому локальному state.
  3. Убедиться, что действие может зависеть от неочевидного fallback.
- **Evidence to capture:** git diff, e2e deep-link assertions, IA matrix artifact with canonical entry points.
- **Five Whys (or equivalent):**
  1. Почему есть ambiguity? Исторически были параллельные механизмы передачи контекста.
  2. Почему это осталось после convergence? Cleanup был частичным для совместимости.
  3. Почему это плохо для UX? Оператор не видит явный источник подсказки.
  4. Почему это риск для поддержки? Сложнее воспроизводить переходы и расследовать инциденты.
  5. Почему нужно закрыть в Stage 1? Это базовый IA-инвариант до language/hints и full anti-drift.
- **Root cause statement:** отсутствовал зафиксированный Stage-уровневый IA контракт "one action source per flow", что оставило legacy dual-source behavior.
- **Fix mechanism:** оформить IA matrix artifact + удалить legacy fallback, оставив URL как единственный прозрачный источник контекста.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `Tenants` action queue and `Integrations -> Workspace` deep-link contracts.
  - Existing e2e selectors for cross-tab transitions.
  - Existing UVC endpoint contracts; backend changes не требуются.
- **External reuse:** GOV.UK Design System patterns for task-path clarity in complex services.
- **Why not reinvent the wheel:** основной UX-контур уже построен, требуется только закрепление ответственности и удаление residual ambiguity.

## Invariant
- Один бизнес-action должен иметь один канонический entry point.
- `Company Workspace` остается единственным execute-слоем.
- Переходы между вкладками должны быть объяснимы через URL/query, не через скрытое состояние.

## Scope
- Stage 1 wave1: зафиксировать IA matrix (`keep|move|remove`) по ключевым UVC зонам.
- Stage 1 wave2: удалить legacy dual-source state в `Company Workspace`.
- Stage 1 wave3: зафиксировать anti-drift checks для entry points.

## Out of scope
- Массовый copy refresh и словарь терминов (Stage 2).
- Полное расширение кросс-вкладочных циклов (`Inbox/Marketing/Knowledge`) (Stage 3).
- Новые backend endpoints.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage1-ia-matrix-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-02-uvc-stage1-ia-matrix-a705.md`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/e2e/platform-admin.spec.ts`

## Plan (1..N)
1. Create IA matrix artifact with explicit `keep|move|remove` decisions for top actions.
2. Remove hidden storage fallback for Workspace recommended action.
3. Keep query-based context as single source of truth and preserve clear action reset.
4. Extend or adapt e2e checks to lock this behavior.
5. Run deterministic checks and record evidence.

## DoD
- IA matrix artifact exists and covers all primary actions in `Tenants/Integrations/Workspace/Ops`.
- `Company Workspace` no longer reads/writes `console:workspace_recommended_action`.
- Deep-link from `Tenants`/`Integrations` still opens recommended action in `Workspace`.
- Targeted lint/build/e2e checks are green.

## Checks
- `git merge-base --is-ancestor 610ab8f3 origin/main`
- `cd console-web && npm run lint -- --file src/app/company-workspace/page.tsx`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Tenants|Platform Admin Integrations"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- Code diff for `company-workspace/page.tsx`.
- New IA matrix artifact document.
- e2e assertions for deep-link -> execute CTA visibility.
- Session + state records after Stage 1 close.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1` targeted e2e pass for Stage 1.
- **Fail-fast / scenario lock:** run only platform-admin tenants/integrations flows.
- **Stop condition:** two consecutive failures without new RCA evidence.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** low-risk UI behavior cleanup without backend schema changes.
- **Go/no-go signals:** no regression in deep-link e2e flows; build/lint green.
- **Rollback:** revert Stage 1 commit restoring prior workspace fallback.
- **Post-release monitoring window:** `24h` for workspace action-open flows.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_AUDIT/pages/tenants.md`
  - `docs/CONSOLE_AUDIT/pages/integrations.md`
  - `docs/CONSOLE_AUDIT/pages/company-workspace.md`
  - `STATE.md`
- `Drift closeout rule`:
  - Stage 1 cannot close without IA matrix artifact and linked code evidence.

## Rollback
- `git revert HEAD` and rerun Stage 1 checks.

## No-go
- Возвращать dual-source action context (`query + storage`).
- Добавлять новые competing entry points для execute.
- Ослаблять e2e coverage ради скорости.

## Risks/Blockers
- e2e may rely on previous fallback behavior in edge environments.
- Selector updates may be needed if UI blocks are regrouped.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: massive terminology simplification is deferred.
- `Why not in this block`: Stage 1 focuses on IA ownership and deterministic action source.
- `Risk if deferred`: mixed terminology may still increase onboarding time for new operators.
- `Linked follow-up Task Package(s)`: `UVC-UX-STAGE2-A705`.
- `Expiry/trigger to stop deferral`: Stage 2 must start immediately after Stage 1 pass.

## Next-block contract (mandatory)
- `Next block objective`: execute Stage 2 plain-language glossary and contextual hints rollout.
- `First deterministic check command`: `rg -n "Playbook|Следующее рекомендуемое действие|Портфель|Онбординг|Изменения" console-web/src/app/tenants console-web/src/app/company-workspace`
- `Blocked-by conditions`: Stage 1 checks are not green.
- `Owner role for closure`: Brain + Top Architect.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes.
- `Start from`: `docs/CONSOLE_AUDIT/artifacts/2026-03-02-uvc-stage1-ia-matrix-a705.md`.
- `Do not touch`: backend UVC contracts.
- `Open risks`: e2e assumptions tied to old fallback.
- `First command to verify`: `rg -n "console:workspace_recommended_action|readWorkspaceRecommendedActionContext" console-web/src/app/company-workspace/page.tsx`
