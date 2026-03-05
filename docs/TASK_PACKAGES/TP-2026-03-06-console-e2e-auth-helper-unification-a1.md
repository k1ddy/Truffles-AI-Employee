# TP-2026-03-06-console-e2e-auth-helper-unification-a1

## Block identity
- `BLOCK_ID`: CONSOLE-E2E-AUTH-HELPER-UNIFICATION-A1
- `PARENT_BLOCK_ID`: CONSOLE-E2E-LIVE-AUTH-HARDENING-A1
- `DEPENDS_ON`: CONSOLE-E2E-LIVE-AUTH-HARDENING-A1
- `UNLOCKS`: CONSOLE-E2E-AUTH-HELPER-UNIFICATION-DONE-A1

## Название/цель
Унифицировать live auth helper слой в `login/smoke/inspect_case`, чтобы убрать дублирование `startKeycloakLogin/loginThroughKeycloak/ensureLoggedIn` и снизить drift между e2e-спеками без изменения бизнес-поведения.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/TASK_PACKAGES/TP-2026-03-05-console-e2e-live-auth-hardening-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/e2e/login.spec.ts`
  - `console-web/e2e/smoke.spec.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - helper-функции Keycloak логина продублированы в нескольких e2e-файлах;
  - одинаковая логика расходится по timeout/selector fallback и recovery-path;
  - drift уже вызвал отдельный hardening блок для `inspect_case`.

## One web search (mandatory before implementation)
- **Query (exact):** `Playwright reusable authentication helper across multiple spec files fixtures best practices`
- **Date/time (local):** `2026-03-05T18:46:00+05:00`
- **Sources opened (from this query):**
  - `https://playwright.dev/docs/auth`
  - `https://playwright.dev/docs/test-fixtures`
- **Ready solutions found:** Playwright рекомендует переиспользование auth-state и вынос общих шагов в shared helpers/fixtures вместо копирования по spec-файлам.
- **Decision (`reuse/integrate/build`):** `integrate` — вынести общий Keycloak auth helper в `e2e/support` и подключить в `login/smoke/inspect_case`.
- **Rejected options:**
  - оставлять дублированные helper-реализации в каждом spec;
  - внедрять новый auth framework поверх текущего Playwright setup.
- **Source quality:** high-signal source = официальная документация Playwright.

## Root cause (mandatory)
- **Symptom:** auth-flow в e2e дублируется в целевых spec-файлах и расходится по поведению при gate/reload.
- **Minimal reproduction:**
  - `cd console-web && rg -n "startKeycloakLogin|loginThroughKeycloak|ensureLoggedIn" e2e/login.spec.ts e2e/smoke.spec.ts e2e/inspect_case.spec.ts`
- **Evidence:** найдено несколько локальных реализаций одних и тех же auth helper в целевых spec-файлах.
- **Five Whys:**
  1. Почему drift? helper логика скопирована в каждый spec.
  2. Почему копировали? локально быстрее для одного файла.
  3. Почему это ломает качество? исправления применяются не ко всем spec.
  4. Почему заметно сейчас? live auth hardening потребовал точечной правки только в `inspect_case`.
  5. Почему критично? future regressions в login/smoke/inspect_case станут вероятнее и дороже.
- **Root cause statement:** отсутствие единого shared auth helper для целевых e2e-спеков приводит к дрейфу auth-поведения и нестабильности поддержки.
- **Fix mechanism:** централизовать Keycloak auth helper API и перевести `login/smoke/inspect_case` на единый импортируемый слой.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse существующих selectors/env-контрактов (`E2E_USE_STORAGE_STATE`, `E2E_DETERMINISTIC_AUTH`, `logout-button`, baseURL fallback).
- **External reuse:** reuse Playwright shared helper pattern из официальной документации, без сторонних библиотек.

## Invariant
- Не включать route mocks в live lane.
- Не менять бизнес-логику `Заявки/Записи` и API-контракты.
- Не ослаблять e2e assertions до немых skip.

## Scope
- Создать общий auth helper модуль для Playwright.
- Перевести `login.spec.ts`, `smoke.spec.ts`, `inspect_case.spec.ts` на единый helper API.
- Сохранить reasoned behavior для auth-gate recovery.

## Out of scope
- Миграция `marketing/owner-admin/platform-admin/tenants-a11y` на новый helper.
- Изменения backend/Keycloak конфигурации.

## Touch-list (files/tables)
- `console-web/e2e/support/keycloak-auth.ts` (new)
- `console-web/e2e/login.spec.ts`
- `console-web/e2e/smoke.spec.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Добавить общий helper `keycloak-auth.ts` с `start/login/ensure/isAuthGate` API.
2. Мигрировать `login/smoke/inspect_case` на новый helper без изменения тестовых intent/assertion.
3. Прогнать lint + целевые Playwright checks (local mocked + live login/inspect).
4. Зафиксировать evidence в session/state.

## DoD
- В целевых spec-файлах нет локальных дубликатов `startKeycloakLogin/loginThroughKeycloak`.
- `login` и `inspect_case` live lanes проходят, mocked lane `inspect_case` проходит.
- Сессионные/канонические доки синхронизированы.

## Checks
- `cd console-web && rg -n "startKeycloakLogin|loginThroughKeycloak" e2e/login.spec.ts e2e/smoke.spec.ts e2e/inspect_case.spec.ts`
- `cd console-web && npm run lint -- --file e2e/support/keycloak-auth.ts --file e2e/login.spec.ts --file e2e/smoke.spec.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/login.spec.ts --project=chromium-login --reporter=line`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Output checks above.
- Скриншот `calendar_no_cases_context.png` при live fallback (если lane без кейсов).

## Release safety (mandatory for non-doc changes)
- **Strategy:** e2e-only изменение; rollout через PR/CI + live-e2e checks.
- **Go/no-go signals:** required checks green; нет новых auth-related flaky fail в `login/inspect_case` live lanes.
- **Rollback:** `git revert --no-edit HEAD`.
- **Post-release monitoring window:** 24ч на PR checks/live rerun по запросу.

## Rollback
- `git revert --no-edit HEAD`

## No-go
- Встраивать тестовые обходы в runtime код.
- Добавлять silent skip без reason-code.

## Риски/блокеры
- Live env может быть деградирован на стороне Keycloak/console.truffles.kz.
- Невалидный/просроченный storageState может дать ложный auth gate.

## Token / run budget (mandatory for expensive suites)
- `Max full runs:` 2
- `Planned cadence:` lint + local mocked first, затем live login/inspect.
- `Stop condition:` при двух подряд прогонах без новой evidence — stop-the-line и RCA update.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: другие e2e spec (`marketing/owner-admin/platform-admin/tenants-a11y`) еще имеют локальные auth helper дубликаты.
- `Why not in this block`: ограничиваем blast radius только login/smoke/inspect_case.
- `Risk if deferred`: частичный drift сохранится в нецелевых спеках.
- `Linked follow-up Task Package(s)`: `TP-2026-03-07-console-e2e-auth-helper-rollout-a1.md` (create if needed).
- `Expiry/trigger to stop deferral`: следующий auth-fix вне target trio.

## Next-block contract (mandatory)
- `Next block objective`: распространить unified auth helper на оставшиеся e2e spec с минимальным diff.
- `First deterministic check command`: `cd console-web && rg -n "startKeycloakLogin|loginThroughKeycloak" e2e/*.spec.ts`
- `Blocked-by conditions`: нет.
- `Owner role for closure`: Brain / Top Architect.
