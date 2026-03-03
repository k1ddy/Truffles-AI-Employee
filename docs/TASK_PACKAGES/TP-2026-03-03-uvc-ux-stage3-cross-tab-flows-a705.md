# TP-2026-03-03-uvc-ux-stage3-cross-tab-flows-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STAGE3-A705
- `PARENT_BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `DEPENDS_ON`: merge of PR `#875` (Stage 2) into `main`
- `UNLOCKS`: UVC-UX-STAGE4-A705

## Название/цель
Полностью закрыть Stage 3 программы UVC UX: сделать сквозные бизнес-циклы между существующими вкладками цельными, без dead-end и без дублирующих действий, чтобы оператор всегда видел один следующий шаг по бизнес-логике.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-stage2-language-hints-a705.md`

## Requirement traceability (mandatory)
- `REQ-1` no disconnected logic/buttons:
  - solution: fixed canonical loops with one owner per loop segment.
  - proof: deterministic e2e for each loop and explicit no-dead-end asserts.
- `REQ-2` no duplicate functions across tabs:
  - solution: `Integrations` fact-only, `Workspace` execute-only, `Tenants` orchestration-only, `Ops` verify-only.
  - proof: `keep|move|remove` matrix + selector-level anti-dup checks.
- `REQ-3` intuitive business flow:
  - solution: progressive next-step hints and explicit return paths in each loop.
  - proof: e2e checks for transition intent + URL context + visible next CTA.
- `REQ-4` optimize existing tabs before adding new:
  - solution: no new top-level navigation in this block.
  - proof: nav structure unchanged; only in-tab flow hardening.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/tenants/tenants-page-view.tsx`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/app/marketing/page.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage3-flow-matrix-a705.md`
- `Baseline commands`:
  - `git merge-base --is-ancestor 8ed79348 origin/main`
  - `rg -n "workspace-recommended-open-execute|integrations-row-open-workspace|ops-incident-state|tenants-action-queue" console-web/e2e/platform-admin.spec.ts`
  - `rg -n "recommended_action|action_source|action_reasons" console-web/src/app/tenants console-web/src/app/integrations/page.tsx console-web/src/app/company-workspace/page.tsx`
- `FACT findings`:
  - Stage 1/2 artifacts and checks exist in branch; Stage 2 PR is open and is a hard dependency for Stage 3 start on `main`.
  - Core deep-link chain exists, but full loop contracts (`Tenants -> Workspace -> Ops` and `Integrations -> Workspace -> Tenants`) are not yet closed as one acceptance block.
- `Detected drift (docs vs code)`:
  - master plan defines Stage 3 as full loop hardening, but dedicated implementation TP for Stage 3 was missing.

## One web search (mandatory before implementation)
- **Query (exact):** `site:gov.uk service manual map user journey service blueprint`
- **Date/time (local):** `2026-03-03 12:07 +05`
- **Why this query is precise:** нужен high-signal reference для проектирования сквозных операционных пользовательских путей без разрывов между системными зонами.
- **Sources opened (from this query):**
  - GOV.UK Service Manual, Creating an experience map: `https://www.gov.uk/service-manual/design/creating-an-experience-map`
  - GOV.UK Service Manual, Map and understand the whole problem: `https://www.gov.uk/service-manual/design/mapping-the-whole-problem`
- **Existing solutions found:** end-to-end journey mapping with explicit step ownership, transition intent, and visible next action at each handoff point.
- **Decision:** `integrate` — формализовать loop-маршруты как детерминированные контракты между вкладками.
- **Rejected options:** ad-hoc fixes per page without common loop contract (приводит к повторному дрейфу).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** пользователь проходит часть пути и застревает на вкладке без очевидного следующего шага или попадает в competing action entry.
- **Minimal reproduction:**
  1. Начать с `Tenants` action queue.
  2. Перейти в `Workspace` и выполнить действие.
  3. Попробовать завершить цикл в `Ops` и вернуться к источнику без потери контекста.
- **Evidence to capture:** flow matrix, URL context continuity, e2e traces with transition asserts.
- **Five Whys (or equivalent):**
  1. Почему появляются dead-end? Переходы были покрыты частично, а не как полный loop.
  2. Почему это сохраняется? Нет общего acceptance-контракта loop-level.
  3. Почему это критично? Оператор тратит время и увеличивает риск ошибочных действий.
  4. Почему нельзя решить точечно? Точечные фиксы не защищают межвкладочные handoff.
  5. Почему делать сейчас? Stage 3 блокирует Stage 4 anti-drift governance.
- **Root cause statement:** отсутствует целостный loop-level контракт с owner-логикой и проверками переходов между вкладками.
- **Fix mechanism:** построить и закрепить полные loop contracts + e2e assertions для переходов и возвратов.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - существующие deep-link параметры (`branch_id`, `recommended_action`, `action_source`, `action_reasons`).
  - текущие action cards в `Tenants` и `Integrations`.
  - текущие `Ops` incident/job panels для post-action verify.
- **External reuse:** GOV.UK service journey mapping guidance (источники выше).
- **Why not reinvent the wheel:** необходимые вкладки и API уже есть; нужен связующий UX-контракт, а не новая архитектура.

## Invariant
- Без новых top-level tabs.
- `Workspace` остается единственным execute-слоем.
- `Integrations` не получает competing execute controls.
- Каждый loop завершается явным next action или явным done-state.

## Scope
- **Wave 1:** `Tenants -> Workspace -> Ops` полный loop с подтверждением результата.
- **Wave 2:** `Integrations -> Workspace -> Tenants` полный loop с возвратом и видимым обновлением контекста.
- **Wave 3:** `Knowledge/Marketing/Inbox` handoff-link compatibility с core loop без дублирования execute.

## Out of scope
- Backend schema migrations.
- Новые бизнес-фичи вне loop stabilization.
- Полный language audit (уже Stage 2).

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage3-cross-tab-flows-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage3-flow-matrix-a705.md`
- `console-web/src/app/tenants/tenants-page-view.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/marketing/page.tsx`
- `console-web/e2e/platform-admin.spec.ts`
- `STATE.md`

## Plan (1..N)
1. Сформировать flow matrix артефакт с canonical transition map и owner по каждому шагу.
2. Удалить/перенести оставшиеся competing entry points по матрице.
3. Внедрить единые return-path и next-step подсказки в loop завершениях.
4. Добавить e2e deterministic asserts по continuity (`source -> execute -> verify -> return`).
5. Прогнать проверки, зафиксировать evidence и подготовить handoff в Stage 4.

## DoD
- Полностью закрыт `Tenants -> Workspace -> Ops` loop без dead-end.
- Полностью закрыт `Integrations -> Workspace -> Tenants` loop без competing action ambiguity.
- Есть flow matrix artifact и e2e anti-regression checks.
- Проверки (lint + targeted e2e + session_check) зелёные.

## Checks
- `git merge-base --is-ancestor 8ed79348 origin/main`
- `cd console-web && npm run lint -- --file src/app/tenants/tenants-page-view.tsx --file src/app/integrations/page.tsx --file src/app/company-workspace/page.tsx --file src/components/OpsPage.tsx --file src/app/knowledge/page.tsx --file src/app/marketing/page.tsx --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- flow-matrix artifact
- code diff for loop continuity
- e2e run output with loop assertions
- `STATE.md` fact entry with command evidence

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` targeted e2e runs for this stage.
- **Fail-fast / scenario lock:** `Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations`.
- **Stop condition:** 2 прогона подряд без новой RCA evidence.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased enablement of loop changes in existing tabs.
- **Go/no-go signals:** no deep-link regressions, no increase in unresolved loop exits.
- **Rollback:** `git revert HEAD` + rerun deterministic checks.
- **Post-release monitoring window:** `48h` on cross-tab transitions.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_AUDIT/pages/tenants.md`
  - `docs/CONSOLE_AUDIT/pages/integrations.md`
  - `docs/CONSOLE_AUDIT/pages/company-workspace.md`
  - `docs/CONSOLE_AUDIT/pages/ops.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-*.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - Stage 3 cannot close without flow matrix + e2e continuity evidence.

## Rollback
- `git revert HEAD` and rerun Stage 3 check suite.

## No-go
- Добавлять второй execute-owner вне `Workspace`.
- Закрывать stage без loop-level e2e continuity checks.
- Делать hidden fallback transitions, не видимые оператору.

## Risks/Blockers
- Stage 2 merge delay blocks Stage 3 start on `main`.
- Existing selectors may require update after loop CTA consolidation.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: secondary links from non-core tabs (`Knowledge`, `Marketing`) могут остаться без полного loop visual guidance.
- `Why not in this block`: приоритет — core operational loops first.
- `Risk if deferred`: edge-path onboarding for new operators будет медленнее.
- `Linked follow-up Task Package(s)`: `TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705.md`.
- `Expiry/trigger to stop deferral`: если edge-path loops дают >5% unresolved exits, defer запрещён.

## Next-block contract (mandatory)
- `Next block objective`: Stage 4 anti-drift quality suite for cross-tab loops + glossary contract.
- `First deterministic check command`: `rg -n "should keep Settings labels plain-language|should keep Ops labels plain-language|deep-link from Tenants action queue|Integrations and Workspace labels plain-language" console-web/e2e/platform-admin.spec.ts`
- `Blocked-by conditions`: Stage 3 loops not green in targeted e2e.
- `Owner role for closure`: Brain + Top Architect.
