# TP-2026-03-06-console-e2e-auth-helper-rollout-a1

## Block identity
- `BLOCK_ID`: CONSOLE-E2E-AUTH-HELPER-ROLLOUT-A1
- `PARENT_BLOCK_ID`: CONSOLE-E2E-AUTH-HELPER-UNIFICATION-A1
- `DEPENDS_ON`: CONSOLE-E2E-AUTH-HELPER-UNIFICATION-A1
- `UNLOCKS`: CONSOLE-E2E-AUTH-HELPER-ROLLOUT-DONE-A1

## Название/цель
Распространить общий Keycloak auth helper на оставшиеся Playwright spec-файлы (`marketing`, `owner-admin-business`, `platform-admin`, `tenants-a11y`), чтобы убрать локальные `startKeycloakLogin/loginThroughKeycloak` дубли без изменения бизнес-поведения тестов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-03-06-console-e2e-auth-helper-unification-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/e2e/support/keycloak-auth.ts`
  - `console-web/e2e/marketing.spec.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`
  - `console-web/e2e/platform-admin.spec.ts`
  - `console-web/e2e/tenants-a11y.spec.ts`
- `Baseline findings`:
  - оставшиеся 4 spec-файла держат локальные копии `startKeycloakLogin/loginThroughKeycloak`;
  - `platform-admin` и `tenants-a11y` дополнительно имеют deterministic-auth ветку, которую нельзя повредить;
  - drift auth helper уже однажды потребовал отдельный hardening/unification блок.

## One web search (mandatory before implementation)
- **Query (exact):** `Playwright shared helper reuse across multiple spec files page object fixtures best practices`
- **Date/time (local):** `2026-03-06T06:11:25+05:00`
- **Sources opened (from this query):**
  - `https://playwright.dev/docs/auth`
  - `https://playwright.dev/docs/test-fixtures`
- **Ready solutions found:** Playwright рекомендует держать auth-flow в shared helpers/fixtures и не копировать его по spec-файлам, чтобы одинаково обслуживать login state и recovery logic.
- **Decision (`reuse/integrate/build`):** `integrate` — переиспользовать существующий `e2e/support/keycloak-auth.ts` и перевести оставшиеся spec-файлы на общий helper API.
- **Rejected options:**
  - оставлять локальные копии auth helper в каждом spec;
  - внедрять новый auth framework/fixture stack поверх уже принятого helper слоя.
- **Source quality:** high-signal source = официальная документация Playwright.

## Root cause (mandatory)
- **Symptom:** после merge unification-блока часть e2e-спеков продолжает жить на локальных auth helper-реализациях.
- **Minimal reproduction:**
  - `cd console-web && rg -n "async function (startKeycloakLogin|loginThroughKeycloak)" e2e/*.spec.ts`
- **Evidence:** локальные реализации найдены в `marketing`, `owner-admin-business`, `platform-admin`, `tenants-a11y`.
- **Five Whys:**
  1. Почему дубли остались? предыдущий блок сознательно ограничил blast radius `login/smoke/inspect_case`.
  2. Почему это проблема? любой auth-fix снова придется раскатывать вручную по нескольким файлам.
  3. Почему это ведет к drift? одинаковый flow уже расходится по timeout/recovery branches.
  4. Почему риск выше сейчас? `platform-admin`/`tenants-a11y` имеют отдельные auth branches и легко уйдут в частичную несовместимость.
  5. Почему нужно закрыть сейчас? иначе следующий live auth regression снова вернет разношерстный helper слой.
- **Root cause statement:** unification была выполнена частично, а после rollout вскрылось второе скрытое допущение helper-слоя: shared helper ждал любой URL на console host и строил повторный `/api/auth/signin` через внешний auth origin, из-за чего локальный auth flow уходил в `Invalid parameter: redirect_uri`, а owner/admin lane в ручных прогонах шумел manager-role fail вместо явного role-contract.
- **Fix mechanism:** подключить shared helper в оставшихся spec-файлах, сохранить только spec-specific `ensureLoggedIn`/selection logic, а в shared helper ужесточить ожидание только console-app URL (не `/api/auth`) и убрать повторный signin через auth origin; для owner/admin spec добавить явный skip при успешном логине не-owner/non-admin ролью.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse `console-web/e2e/support/keycloak-auth.ts`, существующие `consoleHostPattern/keycloakHostPattern/baseURL` контракты и текущие deterministic auth mocks.
- **External reuse:** follow shared helper / fixture guidance из официальной Playwright docs, без сторонних auth-библиотек.

## Invariant
- Не менять бизнес-assertions и тестовые intent в целевых spec-файлах.
- Не менять deterministic auth branches в `platform-admin` и `tenants-a11y`.
- Не добавлять route mocks в live auth lane и не ослаблять проверки до silent skip.

## Scope
- Удалить локальные `startKeycloakLogin/loginThroughKeycloak` из 4 spec-файлов.
- Подключить общий helper API и сохранить текущий `resolvedBaseURL`/selection gate behavior.
- Синхронизировать session/canon docs под новый rollout блок.

## Out of scope
- Изменения backend/Keycloak/runtime конфигурации.
- Переписывание spec-specific `resolveSelectionGate`, mock bundles или а11y/reporting flow.
- Новый auth abstraction сверх уже существующего helper модуля.

## Touch-list (files/tables)
- `console-web/e2e/support/keycloak-auth.ts`
- `console-web/e2e/marketing.spec.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/e2e/tenants-a11y.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-console-e2e-auth-helper-rollout-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Создать follow-up TP и обновить session/canon docs под rollout block.
2. Перевести `marketing` и `owner-admin-business` на общий helper, сохранив текущую selection-gate логику.
3. Перевести `platform-admin` и `tenants-a11y` на общий helper, не затронув deterministic-auth branches.
4. Прогнать `rg` anti-duplication check, lint и по одному целевому Playwright check на каждый spec.
5. Зафиксировать evidence в session docs и подготовить следующий PR.

## DoD
- В `marketing/owner-admin-business/platform-admin/tenants-a11y` нет локальных `startKeycloakLogin/loginThroughKeycloak`.
- Целевые Playwright checks проходят без изменения тестовых assertions; для `owner-admin-business` допустим явный `skip` с reason, если локальный/manual run не использует owner/admin роль.
- Session/canon docs указывают на новый rollout block и его evidence.

## Checks
- `cd console-web && rg -n "async function (startKeycloakLogin|loginThroughKeycloak)" e2e/marketing.spec.ts e2e/owner-admin-business.spec.ts e2e/platform-admin.spec.ts e2e/tenants-a11y.spec.ts`
- `cd console-web && npm run lint -- --file e2e/support/keycloak-auth.ts --file e2e/marketing.spec.ts --file e2e/owner-admin-business.spec.ts --file e2e/platform-admin.spec.ts --file e2e/tenants-a11y.spec.ts`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/marketing.spec.ts --project=chromium --reporter=line --grep "should open marketing page and render lifecycle blocks"`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --reporter=line --grep "should expose owner/admin control navigation and business summary"`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 E2E_DETERMINISTIC_AUTH=1 npx playwright test e2e/platform-admin.spec.ts --project=chromium --reporter=line --grep "should render full incident details, allow 30m hide, and navigate via CTA"`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 E2E_DETERMINISTIC_AUTH=1 npx playwright test e2e/tenants-a11y.spec.ts --project=chromium --reporter=line --grep "desktop snapshot"`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- `git diff` по touch-list.
- Output checks above.
- `rg` anti-duplication output after migration.

## Release safety (mandatory for non-doc changes)
- **Strategy:** e2e-only rollout через PR + targeted checks.
- **Go/no-go signals:** lint green, anti-duplication check clean, targeted Playwright lanes green.
- **Rollback:** `git revert --no-edit HEAD`.
- **Post-release monitoring window:** 24ч на auth-related e2e failures в PR/CI reruns.

## Rollback
- `git revert --no-edit HEAD`

## No-go
- Менять runtime-код продукта ради тестов.
- Включать silent skip вместо исправления auth-flow.
- Ломать deterministic auth fallback в `platform-admin`/`tenants-a11y`.

## Риски/блокеры
- Live Keycloak/console env может вернуть flaky auth gate и замедлить `marketing/owner-admin` прогоны.
- Локальный `localhost:3100` должен быть поднят для deterministic checks.
- Локальный real-auth lane по-прежнему зависит от внешней Keycloak redirect-uri policy и не является канонической acceptance lane для owner/admin.

## Token / run budget (mandatory for expensive suites)
- `Max full runs:` 2
- `Planned cadence:` docs -> code migration -> lint/rg -> 2 live auth checks -> 2 local deterministic checks.
- `Stop condition:` два подряд прогона без новой evidence => stop-the-line и RCA update.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: локальный `resolveAuthOrigin`/origin-discovery код еще остаётся в части spec-файлов, потому что текущий helper не экспортирует read-only origin resolver; кроме того, localhost real-auth зависит от внешней redirect-uri конфигурации Keycloak и не закрывается этим блоком.
- `Why not in this block`: блок ограничен rollout уже принятого helper API, без расширения helper surface и без изменений Keycloak/runtime конфигурации.
- `Risk if deferred`: следующий auth-change, связанный именно с origin discovery, снова потребует точечных правок в нескольких spec; локальный live-auth sanity останется менее надежным, чем канонический live CI lane.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-console-e2e-auth-origin-resolver-a1.md` (create only if next auth change touches origin discovery).
- `Expiry/trigger to stop deferral`: первый следующий auth fix, который снова меняет `buildSignInUrl` или origin selection.

## Next-block contract (mandatory)
- `Next block objective`: при следующем auth drift извлечь origin-discovery в shared helper и закрыть остаточный duplication слой.
- `First deterministic check command`: `cd console-web && rg -n "async function resolveAuthOrigin|buildSignInUrl\\(" e2e/*.spec.ts`
- `Blocked-by conditions`: нет.
- `Owner role for closure`: Brain / Top Architect.
