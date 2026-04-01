# TP-2026-03-03-uvc-ux-stage5-rollout-efficiency-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STAGE5-A705
- `PARENT_BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `DEPENDS_ON`: merge of Stage 4 block (`UVC-UX-STAGE4-A705`) into `main`
- `UNLOCKS`: UVC-UX-PROGRAM-CLOSEOUT-A705

## Название/цель
Полностью закрыть Stage 5 программы UVC UX: провести безопасный rollout, доказать практическую эффективность улучшений на бизнес-метриках, удалить legacy UX-paths и зафиксировать финальный closeout без UX/логических костылей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705.md`

## Requirement traceability (mandatory)
- `REQ-1` prove effectiveness in practice:
  - solution: pre-defined UX/business metric baseline vs post-rollout comparison.
  - proof: artifacted metric report with go/no-go interpretation.
- `REQ-2` remove legacy and duplicates:
  - solution: explicit legacy-path inventory and removal checklist.
  - proof: no legacy selectors/flags in primary flow.
- `REQ-3` no user discomfort after changes:
  - solution: staged rollout with monitoring and rollback drills.
  - proof: stable metrics and no critical regression events.
- `REQ-4` keep architecture clean:
  - solution: finalize canonical ownership by tabs and remove temporary bypasses.
  - proof: closeout audit artifact and passed checklist.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/app/tenants/**`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/e2e/platform-admin.spec.ts`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-rollout-report-a705.md`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-legacy-removal-a705.md`
- `Baseline commands`:
  - `rg -n "legacy|fallback|disabled|temporary|TODO" console-web/src/app/tenants console-web/src/app/integrations/page.tsx console-web/src/app/company-workspace/page.tsx console-web/src/components/OpsPage.tsx`
  - `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`
  - `SESSION_AGENT=a705 scripts/session_check.sh`
- `FACT findings`:
  - Stage 5 cannot start before Stage 4 anti-drift stability is green.
  - current program has no dedicated rollout efficiency closeout TP despite master-plan requirement.
- `Detected drift (docs vs code)`:
  - master plan includes Stage 5 but implementation TP was missing.

## One web search (mandatory before implementation)
- **Query (exact):** `site:sre.google workbook canary releases error budget monitoring`
- **Date/time (local):** `2026-03-03 12:10 +05`
- **Why this query is precise:** нужен high-signal reference для управляемого rollout и решения go/no-go на метриках и error budget.
- **Sources opened (from this query):**
  - Google SRE Workbook, Canarying Releases: `https://sre.google/workbook/canarying-releases/`
  - Google SRE Workbook, Error Budget Policy: `https://sre.google/workbook/error-budget-policy/`
- **Existing solutions found:** staged rollout, explicit success/failure signals, rollback thresholds, decision policy tied to reliability budget.
- **Decision:** `integrate` — применить staged rollout + measured go/no-go policy к UX-программе.
- **Rejected options:** one-shot rollout without measured decision gates.
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** даже после хорошей реализации UX-блоков программа может формально считаться “готовой” без доказанной бизнес-эффективности и без удаления legacy путей.
- **Minimal reproduction:**
  1. Закрыть Stage 1..4 только тестами.
  2. Не сделать baseline/post-rollout metrics and legacy sweep.
  3. Получить скрытые UX friction и технический хвост.
- **Evidence to capture:** baseline vs after metrics, legacy removal checklist, rollback drill output.
- **Five Whys (or equivalent):**
  1. Почему нужен отдельный Stage 5? Технические тесты не равны бизнес-эффективности.
  2. Почему legacy остаётся? Временные пути часто не удаляются автоматически.
  3. Почему это риск? Возвращаются дубли и непредсказуемое поведение.
  4. Почему не закрыть внутри Stage 4? Stage 4 про drift contract, не про rollout outcomes.
  5. Почему сейчас? Это финальный блок master-плана 1–5.
- **Root cause statement:** отсутствует обязательный closeout-блок, связывающий техническую готовность с реальной UX/business эффективностью и очисткой legacy.
- **Fix mechanism:** staged rollout + metrics proof + mandatory legacy removal audit.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing e2e loop suite from Stage 4.
  - existing session/state evidence protocol.
  - existing UVC tab ownership matrix from Stage 1 and glossary from Stage 2.
- **External reuse:** Google SRE rollout/error-budget principles.
- **Why not reinvent the wheel:** rollout governance уже описана в SRE и частично в проектных gates; требуется адаптация к UVC UX-контексту.

## Invariant
- Rollout без go/no-go signals запрещён.
- Legacy primary-path controls после Stage 5 запрещены.
- Эффективность должна быть доказана метриками, не только “tests green”.

## Scope
- **Wave 1:** rollout plan execution (`canary -> cohort -> fleet`) с проверяемым rollback drill.
- **Wave 2:** metrics proof pack (baseline vs post) для UX/business KPI.
- **Wave 3:** legacy-path removal and final closeout audit.

## Out of scope
- New feature development.
- Backend domain redesign.
- Non-UVC product areas.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage5-rollout-efficiency-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-rollout-report-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-legacy-removal-a705.md`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/app/tenants/**`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/components/OpsPage.tsx`
- `STATE.md`

## Plan (1..N)
1. Зафиксировать rollout matrix и go/no-go thresholds с owner decision points.
2. Прогнать canary/cross-tab monitoring window и сохранить baseline/post artifacts.
3. Зафиксировать KPI comparison report и принять decision.
4. Удалить legacy/fallback пути из primary UX path по checklist.
5. Провести final acceptance run + program closeout запись в `STATE.md`.

## DoD
- Rollout проведен с documented go/no-go decisions.
- KPI report показывает улучшение/неухудшение по целевым метрикам.
- Legacy removal checklist закрыт для primary paths.
- Program 1–5 закрыт как `FACT` с evidence в `STATE.md`.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`
- `SESSION_AGENT=a705 scripts/session_check.sh`
- `scripts/quality_artifact_report.py --hours 24 --show-commands` (если применимо)

## Evidence
- rollout report artifact
- KPI comparison artifact (baseline/post)
- legacy removal artifact
- final `STATE.md` closeout record

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` full targeted acceptance runs + `1` final confirmation run.
- **Fail-fast / scenario lock:** only UVC-critical lanes.
- **Stop condition:** KPI degradation or repeated critical regressions.
- **Escalation path:** Brain + Top Architect + Owner.

## Release safety (mandatory for non-doc changes)
- **Strategy:** controlled staged rollout with rollback drill.
- **Go/no-go signals:** no critical loop break, stable anti-drift suite, KPI trend acceptable.
- **Rollback:** stage rollback using last stable release commit + regression re-check.
- **Post-release monitoring window:** `7d` final observation.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-rollout-report-a705.md`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage5-legacy-removal-a705.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-*.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - Stage 5 cannot close without metrics proof and legacy removal evidence.

## Rollback
- `git revert HEAD` (or release rollback commit), rerun Stage 4 anti-drift suite and targeted e2e.

## No-go
- Закрывать программу без KPI proof pack.
- Оставлять temporary fallback routes в primary path.
- Декларировать success без documented go/no-go decisions.

## Risks/Blockers
- Если Stage 4 suite нестабилен, Stage 5 rollout блокируется.
- KPI baseline может быть недостаточно чистым без строгой фиксации окна измерения.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: часть non-critical UX microcopy может остаться вне финальной программы.
- `Why not in this block`: Stage 5 фокусируется на эффективности и legacy primary paths.
- `Risk if deferred`: minor UX inconsistency without core flow impact.
- `Linked follow-up Task Package(s)`: отдельный maintenance TP по микрокопи (если будет нужен).
- `Expiry/trigger to stop deferral`: если microcopy drift влияет на conversion/loop completion, defer запрещён.

## Next-block contract (mandatory)
- `Next block objective`: UVC UX program closeout acceptance and handoff to steady-state maintenance.
- `First deterministic check command`: `rg -n "UVC-UX-STAGE[1-5]-A705|UVC Stage" docs/TASK_PACKAGES docs/CONSOLE_AUDIT/artifacts STATE.md`
- `Blocked-by conditions`: Stage 5 rollout/metrics/legacy criteria not met.
- `Owner role for closure`: Brain + Top Architect + Owner.
