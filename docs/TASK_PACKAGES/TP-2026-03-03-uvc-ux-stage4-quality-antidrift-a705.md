# TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705

## Block identity
- `BLOCK_ID`: UVC-UX-STAGE4-A705
- `PARENT_BLOCK_ID`: UVC-UX-PLAN-1-5-MASTER-A705
- `DEPENDS_ON`: merge of Stage 3 block (`UVC-UX-STAGE3-A705`) into `main`
- `UNLOCKS`: UVC-UX-STAGE5-A705

## Название/цель
Полностью закрыть Stage 4 программы UVC UX: построить обязательный anti-drift quality контракт, который не допускает повторного расхождения UI, бизнес-логики и backend-контрактов UVC.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-uvc-ux-plan-1-5-master-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage3-cross-tab-flows-a705.md`

## Requirement traceability (mandatory)
- `REQ-1` no regressions between tabs after fixes:
  - solution: contract suite for loop continuity + language contract + role guard.
  - proof: deterministic e2e gates in CI and local.
- `REQ-2` no hidden drift between OpenAPI and frontend usage:
  - solution: explicit contract smoke for critical endpoints in `api-client` usage.
  - proof: check scripts + failing tests on missing/renamed fields.
- `REQ-3` no reintroduction of duplicates:
  - solution: selector-level anti-dup assertions + matrix conformance checks.
  - proof: drift-check list with stable test ids.
- `REQ-4` no “temporary bypass” in production path:
  - solution: fail-closed gates in acceptance lane.
  - proof: stage cannot pass when anti-drift checks are skipped/failing.

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/e2e/platform-admin.spec.ts`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
  - `contracts/console_api/openapi.v1.yaml`
  - `.github/workflows/*` (if CI gate updates are required)
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage4-antidrift-contract-a705.md`
- `Baseline commands`:
  - `cd truffles-api && python3 scripts/generate_openapi.py --check`
  - `cd console-web && npm run generate:api`
  - `rg -n "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations" console-web/e2e/platform-admin.spec.ts`
  - `rg -n "openapi.v1.yaml|api.generated.ts" docs/CONSOLE_AUDIT docs/TASK_PACKAGES`
- `FACT findings`:
  - contract smoke exists partially, but no single acceptance block that protects all UVC critical loops and glossary anti-drift together.
  - Stage 3 output is dependency for stable selector and loop contracts.
- `Detected drift (docs vs code)`:
  - master plan requires Stage 4, but dedicated implementation TP was missing.

## One web search (mandatory before implementation)
- **Query (exact):** `site:playwright.dev/docs best practices testing your app`
- **Date/time (local):** `2026-03-03 12:09 +05`
- **Why this query is precise:** нужен primary-source стандарт для устойчивых e2e контрактов с минимальным флейком и корректной изоляцией тестов.
- **Sources opened (from this query):**
  - Playwright Docs, Best Practices: `https://playwright.dev/docs/best-practices`
  - Playwright Docs, Test Isolation: `https://playwright.dev/docs/test-isolation`
- **Existing solutions found:** isolate tests, avoid implementation-detail asserts, keep deterministic mocks/contracts, fail fast on unstable selectors.
- **Decision:** `integrate` — зафиксировать Stage 4 как deterministic anti-drift contract suite c loop-aware assertions.
- **Rejected options:** broad non-deterministic smoke only (недостаточно для дрейф-защиты).
- **Open questions:** none.

## Root cause (mandatory)
- **Symptom:** после локальных UX улучшений возможен возврат старых терминов/дублирующих кнопок и расхождение frontend-backend контрактов.
- **Minimal reproduction:**
  1. Изменить label/route в одной вкладке.
  2. Не обновить связанный e2e assert/contract usage.
  3. Получить silent drift без немедленного fail.
- **Evidence to capture:** anti-drift suite output, contract check logs, selector matrix.
- **Five Whys (or equivalent):**
  1. Почему drift возвращается? Нет единого fail-closed quality suite на UX-контракт.
  2. Почему частичные тесты не спасают? Они не покрывают полный контур причинно-следственных переходов.
  3. Почему критично для бизнеса? Растут misroute и операторские ошибки.
  4. Почему не закрыто раньше? Сначала требовались IA и language стабилизация.
  5. Почему именно теперь? Stage 4 логически следует за Stage 3 loops.
- **Root cause statement:** отсутствует централизованный acceptance-контракт на дрейф UI/loops/contracts.
- **Fix mechanism:** обязательный anti-drift suite с детерминированными проверками на контракты, loop continuity и glossary.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `platform-admin.spec.ts` test bed.
  - existing OpenAPI generation/check path (`scripts/generate_openapi.py`, `npm run generate:api`).
  - existing stage1/2 selectors and flow asserts.
- **External reuse:** Playwright official best practices (источники выше).
- **Why not reinvent the wheel:** текущий e2e каркас уже подходит, требуется расширение и fail-closed дисциплина.

## Invariant
- Любой UVC-critical flow must be contract-tested.
- Любой glossary-critical label drift must fail checks.
- Любой contract drift between OpenAPI and frontend usage must be detected before merge.

## Scope
- **Wave 1:** contract smoke for UVC frontend API layer vs OpenAPI critical paths.
- **Wave 2:** deterministic e2e anti-drift suite for Stage 3 loops + Stage 2 language contract.
- **Wave 3:** no-dup/no-hidden-entry assertions and CI gate hardening.

## Out of scope
- Feature redesign beyond Stage 3 loops.
- LLM runtime behavior changes.
- Product KPI target tuning (Stage 5 scope).

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-stage4-quality-antidrift-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage4-antidrift-contract-a705.md`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `contracts/console_api/openapi.v1.yaml`
- `STATE.md`

## Plan (1..N)
1. Зафиксировать anti-drift contract matrix artifact (loops + labels + API bindings).
2. Расширить e2e deterministic checks по Stage 2+3 контрактам.
3. Добавить frontend contract smoke against OpenAPI-generated types for critical endpoints.
4. Включить fail-closed gating в acceptance checks для Stage 4 scope.
5. Подготовить evidence bundle и handoff в Stage 5.

## DoD
- Есть Stage 4 anti-drift artifact с полным контрактным покрытием критичных UVC flow/labels/contracts.
- Targeted deterministic e2e suite green и покрывает Stage 2+3 контракты.
- OpenAPI/frontend critical contract smoke green.
- Stage 4 checks обязательны и fail-closed в acceptance lane.

## Checks
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file e2e/platform-admin.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations"`
- `SESSION_AGENT=a705 scripts/session_check.sh`

## Evidence
- anti-drift matrix artifact
- e2e outputs with named anti-drift checks
- OpenAPI/frontend contract smoke outputs
- `STATE.md` fact entry with commands/results

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `2` targeted full-loop runs.
- **Fail-fast / scenario lock:** only platform-admin UVC lanes.
- **Stop condition:** 2 failures without new RCA evidence.
- **Escalation path:** Brain + Top Architect.

## Release safety (mandatory for non-doc changes)
- **Strategy:** gated rollout of stricter checks before code-freeze of Stage 5.
- **Go/no-go signals:** no flaky regressions above threshold, all anti-drift contracts stable.
- **Rollback:** revert Stage 4 check changes and restore last stable gate snapshot.
- **Post-release monitoring window:** `72h` for drift signals.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-stage4-antidrift-contract-a705.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-*.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - Stage 4 cannot close without reproducible anti-drift evidence.

## Rollback
- `git revert HEAD` + rerun Stage 4 checks.

## No-go
- Оставлять optional anti-drift checks для Stage 4 acceptance.
- Разрешать bypass на failing drift asserts.
- Добавлять brittle text-only asserts без contract-level checks.

## Risks/Blockers
- Flaky selectors can delay closure if not normalized in Stage 3.
- Contract generation drift may expose pre-existing type gaps.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: часть non-critical secondary pages может не войти в Stage 4 strict suite.
- `Why not in this block`: приоритет — UVC critical loops and contracts.
- `Risk if deferred`: локальные secondary drifts без немедленного влияния на core loops.
- `Linked follow-up Task Package(s)`: `TP-2026-03-03-uvc-ux-stage5-rollout-efficiency-a705.md`.
- `Expiry/trigger to stop deferral`: если secondary drift затрагивает primary CTA, defer запрещён.

## Next-block contract (mandatory)
- `Next block objective`: Stage 5 rollout + efficiency proof + legacy path removal.
- `First deterministic check command`: `rg -n "UVC Stage 2 Language Glossary|UVC Stage 1 IA Matrix|anti-drift" docs/CONSOLE_AUDIT/artifacts`
- `Blocked-by conditions`: Stage 4 anti-drift gates are not stable/green.
- `Owner role for closure`: Brain + Top Architect.
