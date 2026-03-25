# TP-2026-03-05-console-e2e-live-auth-hardening-a1

## Block identity
- `BLOCK_ID`: CONSOLE-E2E-LIVE-AUTH-HARDENING-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1
- `UNLOCKS`: CONSOLE-E2E-LIVE-AUTH-HARDENING-DONE-A1

## Название/цель
Стабилизировать live no-mocks e2e контур для `inspect_case` после merge: убрать skip из-за зафиксированных фильтров/fixture-only fallback и обеспечить предсказуемое поведение с real auth (`storageState + Keycloak`) без ослабления контракта.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md`
- `docs/runbooks/INBOX_CALENDAR_WAVE4_RELEASE.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `STATE.md`
- `Baseline findings`:
  - `login.spec` live auth path (`E2E_USE_STORAGE_STATE=1`, `E2E_DETERMINISTIC_AUTH=0`) проходит стабильно (`3 passed`).
  - `inspect_case` live no-mocks остается `skip` при `cases-empty` и невозможности открыть fixture `LIVE_CASE_ID`.
  - в UI заявок фильтры и last case сохраняются на 24ч (`console:inbox:case-list:v1:*`), что может уводить тест в пустую очередь.

## One web search (mandatory before implementation)
- **Query (exact):** `Playwright authentication storageState global setup best practices`
- **Date/time (local):** `2026-03-05T18:10:47+05:00`
- **Sources opened:**
  - `https://playwright.dev/docs/auth`
  - `https://playwright.dev/docs/test-global-setup-teardown`
- **Ready solutions found:** Playwright рекомендует переиспользовать аутентифицированное `storageState` и держать setup отдельным/детерминированным; flaky e2e снижается при исключении зависимостей от mutable UI-state между прогонами.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse текущего global setup + storageState, добавить очистку inbox workspace state и data-aware fallback (через live API case-id), без нового auth framework.
- **Rejected options:** расширять deterministic-auth mocks для live lane (нарушает цель no-mocks).
- **Source quality:** high-signal source = официальная документация Playwright.

## Root cause (mandatory)
- **Symptom:** `inspect_case` в live no-mocks периодически `skip`, хотя auth уже валиден.
- **Minimal reproduction:**
  - `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=list`
- **Evidence:** в логе `No cases in queue` -> `Live mode: queue is empty, trying direct case fallback.` -> `1 skipped`.
- **Five Whys:**
  1. Почему skip? Очередь пуста и fallback идет только на fixture case id.
  2. Почему очередь пуста? Сохраняемые на 24ч фильтры/контекст могут не совпадать с доступными live кейсами.
  3. Почему fallback не спасает? `LIVE_CASE_ID` по умолчанию fixture `555...`, не гарантирован в live.
  4. Почему это проблема? Live lane становится data-fragile и не отражает реальную стабильность auth/навигации.
  5. Почему это критично? Release safety требует интерпретируемый live signal без случайных skip.
- **Root cause statement:** live no-mocks сценарий зависит от mutable UI storage state и fixture-only fallback вместо data-aware поиска доступного кейса.
- **Fix mechanism:** перед live no-mocks очистить inbox workspace keys и добавить fallback: получить доступный case id через `/api/proxy/cases` и открыть его напрямую.

## Reuse-first plan (mandatory)
- **Reuse:** текущий `global-setup` (`storageState`), `ensureLoggedIn`, существующие selectors/assertions в `inspect_case`.
- **Integrate:** добавить deterministic cleanup localStorage + API-backed case fallback.
- **Build only if needed:** новые сервисы/эндпоинты не требуются.

## Invariant
- Не ослаблять assertions для mocked lane.
- Не переводить live lane на route mocks.
- Не менять runtime бизнес-логику `Заявки/Записи`.

## Scope
- Усилить `inspect_case` live no-mocks path против пустой/зафильтрованной очереди.
- Сохранить прозрачные reason-codes в skip/fail.

## Out of scope
- Изменения backend API.
- Полный рефакторинг всех e2e auth хелперов в проекте.

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `STATE.md`

## Plan (1..N)
1. Добавить в `inspect_case` очистку inbox workspace keys в live no-mocks перед загрузкой очереди.
2. Добавить API-backed fallback для case id (`/api/proxy/cases`) при пустой очереди.
3. Прогнать login live + inspect_case mocked/live + session gate.
4. Обновить session/state evidence.

## DoD
- `inspect_case` live no-mocks дает `pass` на доступных данных и не зависит от fixture-only case id.
- При отсутствии кейсов причина фиксируется детерминированно (не немой skip).
- Обязательные проверки зелёные.

## Checks
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/login.spec.ts --project=chromium-login --reporter=line`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Output checks above.
- Скриншоты `case_inspection.png`/`calendar_case_context.png` при live проходе.

## Release safety (mandatory)
- **Rollout:** e2e-only change, прямой deploy не требуется; используем CI gate + live lane.
- **Go/no-go:** `inspect_case` live no-mocks не падает по auth/data-fragile path.
- **Rollback:** `git revert` данного PR-коммита.

## Rollback
- `git revert --no-edit HEAD`

## No-go
- Добавлять в live lane route mocks.
- Убирать reason-codes и молча пропускать ошибки.

## Риски/блокеры
- Внешний live контур может реально не иметь доступных кейсов для роли/филиала.
- Деградация Keycloak/NextAuth вне scope этого блока.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: auth хелперы e2e дублируются в нескольких spec-файлах.
- `Why not in this block`: цель узкая, стабилизация live lane без широкого рефакторинга.
- `Risk if deferred`: дальнейшие auth-fixes будут дороже из-за дублирования.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-console-e2e-auth-helper-unification-a1.md` (create if repeated auth edits continue).
- `Expiry/trigger to stop deferral`: `>=2` новых правок auth-flow в разных spec за один релизный цикл.

## Next-block contract (mandatory)
- `Next block objective`: унифицировать live auth helper слой для `login/smoke/inspect_case`.
- `First deterministic check command`: `cd console-web && rg -n \"startKeycloakLogin|loginThroughKeycloak\" e2e/*.spec.ts e2e/global-setup.ts`
- `Blocked-by conditions`: нет.
- `Owner role for closure`: Brain / Top Architect.
