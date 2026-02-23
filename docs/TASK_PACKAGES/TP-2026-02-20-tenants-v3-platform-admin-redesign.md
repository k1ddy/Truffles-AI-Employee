# TP-2026-02-20-tenants-v3-platform-admin-redesign

## Название/цель
Довести `/tenants` до реального `platform_admin control tower` для полного цикла управления компаниями:
онбординг -> эксплуатация -> изменения -> вывод/восстановление, без скрытых состояний и с предсказуемым поведением на большом масштабе.

## Revision
- `2026-02-22`: глубокая перепроверка на `main@9b804d69` и фиксация остаточных системных проблем.
- `2026-02-22`: Wave 5/6 hardening — deterministic e2e/a11y lane без skip, auth-setup decoupling, KPI contrast fix.
- `2026-02-23`: recovery update — критерий `tenants/page.tsx <= 1200 LOC` переведен в рекомендательный, обязательный фокус приемки: рабочая ценность `/tenants` (deterministic scope + actionable flow + полная видимость company scope).

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP по Tenants/Platform Admin)
- `STRUCTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `SPECS/CONTROL_PLANE.md`
- `TECH.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`

## Product intent (смысл вкладки)
`/tenants` должен быть единой рабочей точкой для platform_admin:
1. Видеть портфель компаний/клиентов/филиалов и их состояние.
2. Быстро определять риск и следующий шаг по каждой единице управления.
3. Выполнять действия безопасно, с audit/evidence.
4. Масштабироваться до очень большого количества компаний и ниш без деградации UX и latency.

## Execution status (FACT, по текущему коду)
| Wave | Статус | Что подтверждено | Что не закрыто |
|---|---|---|---|
| Wave 1 IA boundary | `partial` | Режим `All` убран, default = `portfolio` (`console-web/src/components/TenantsTopControls.tsx:211`) | Страница всё еще смешивает несколько доменов в одном монолите (`console-web/src/app/tenants/page.tsx`) |
| Wave 2 Context kernel | `partial` | Явные `page filters` и `context` есть (`console-web/src/components/TenantsTopControls.tsx:91`, `console-web/src/components/TenantsTopControls.tsx:166`) | Детерминизм состояния нарушен (см. `F1`, `F2`) |
| Wave 3 Data contract | `done/partial` | Typed weekly snapshot schema + table/fallback (`truffles-api/app/schemas/console.py:249`, `truffles-api/app/routers/console.py:13434`) | Модель аналитики и fleet-агрегации не рассчитана на очень большой объём (`F5`) |
| Wave 4 Decomposition/perf | `partial` | Вынесены отдельные панели (`console-web/src/components/TenantsOperationalKpiPanel.tsx`) | `tenants/page.tsx` остается 3768 LOC, основная оркестрация внутри (`F4`) |
| Wave 5 A11y/copy | `done/partial` | `A11Y_FAIL_ON_THRESHOLDS=1` проходит в deterministic lane (desktop/mobile), KPI contrast исправлен (`console-web/src/components/TenantsOperationalKpiPanel.tsx`) | Остался бизнес-copy cleanup в отдельных секциях (`F7`) |
| Wave 6 E2E realism | `done` | `platform-admin.spec.ts` стабилизирован: deterministic auth/session, нет `test.skip`, сценарии A/B/C/D/E hard-fail (`console-web/e2e/platform-admin.spec.ts`, `console-web/playwright.config.ts`) | Нет |
| Feature flag rollout | `partial` | `NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER` уже в коде (`console-web/src/app/tenants/page.tsx:850`) | Shadow/canary/full rollout + наблюдение ещё не формализованы (`Wave 6`) |

## Critical problems (FACT, deep check)
### F1. Branch scope теряется после `Взять из рабочего контура`
Evidence:
- `setBranchContextAndPageFilters` обновляет только `branch`, не поднимая parent scope (`console-web/src/app/tenants/page.tsx:1555`).
- `applyContextToPageFilters` читает scope из storage (`console-web/src/app/tenants/page.tsx:1559`).
- `ConsoleShell` перезаписывает storage значением `selected_branch_id` из `/me` (`console-web/src/components/ConsoleShell.tsx:1464`).
- `/me` возвращает `selected_branch_id` только как `effective_branch_id`; при несовпадении branch/client он становится `null` (`truffles-api/app/services/console_auth.py:305`, `truffles-api/app/routers/console.py:493`).
Impact:
- branch фильтр может сбрасываться визуально "сам".
- кнопки выглядят "нерабочими", потому что фактический state откатывается.

### F2. Два конкурирующих источника истины для контекста
Evidence:
- Header context (`ConsoleShell`) и page-level context (`TenantsTopControls`) существуют одновременно (`console-web/src/components/ConsoleShell.tsx:851`, `console-web/src/components/TenantsTopControls.tsx:166`).
- В header при единственной опции контрол превращается в статичный `span` (не интерактивный UX) (`console-web/src/components/ConsoleShell.tsx:871`, `console-web/src/components/ConsoleShell.tsx:913`).
Impact:
- Пользователь не понимает, чем отличаются "контур" и "фильтры".
- При масштабном управлении это вызывает ошибки выбора области действий.

### F3. Branch list в cockpit режиме неполный по контракту
Evidence:
- `company-cockpit` при отсутствии `client_id` выбирает первого клиента и отдает branches только для него (`truffles-api/app/routers/console.py:13431`).
- UI переключается на cockpit-ветку и отключает `load more` для branches (`console-web/src/app/tenants/page.tsx:1239`, `console-web/src/app/tenants/page.tsx:3583`).
Impact:
- для компании с большим числом клиентов/филиалов список неполный, создается ложная картина данных.

### F4. Монолит страницы сохраняется (высокий regression risk)
Evidence:
- `console-web/src/app/tenants/page.tsx` = ~3900 LOC.
- Внутри одной страницы: context orchestration, filters, CRUD, lifecycle modal, branch-change pipeline, KPI, snapshots, onboarding.
Impact:
- любое изменение цепляет много сценариев.
- сложнее изолировать баги и удерживать инварианты.

### F5. Серверные fleet-агрегации не готовы к "10M+ компаний" в текущем виде
Evidence:
- `_build_fleet_client_details_map` грузит branches для набора клиентов и считает агрегаты в Python (`truffles-api/app/routers/console.py:3281`).
- `_build_fleet_summary_for_scope` сканирует батчами клиентов и на каждый батч строит heavy details (`truffles-api/app/routers/console.py:3623`).
- `list_fleet_attention` проходит по всем active clients в scope и пересчитывает сигналы (`truffles-api/app/routers/console.py:15061`).
Impact:
- latency растет вместе с размером портфеля.
- при крупном флоте будет упор в CPU/DB, нестабильный UX и timeout-риск.

### F6. A11y debt: контраст KPI карточек
Evidence:
- KPI-карточки переведены на статусные high-contrast labels (`kpiLabelClass`) вместо `text-muted-foreground` на tint background (`console-web/src/components/TenantsOperationalKpiPanel.tsx`).
- Локальный fail-closed a11y lane зелёный (`A11Y_FAIL_ON_THRESHOLDS=1`), artifacts обновлены (`docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-*-axe.json`).
Impact:
- Локальный fail-closed a11y gate закрыт.
- Нужен runtime recheck после deploy, чтобы подтвердить отсутствие расхождения между локальным билдом и production bundle.

### F7. Смешение бизнес и технического copy
Evidence:
- `Action Queue` в бизнес-зоне (`console-web/src/components/TenantsActionQueuePanel.tsx:54`).
- `Threshold drill-down` (`console-web/src/components/TenantsOperationalKpiPanel.tsx:275`).
- debug-надпись `page filter client_id` в рабочем UI (`console-web/src/app/tenants/page.tsx:3216`).
Impact:
- когнитивный шум и ошибки интерпретации оператором.

### F8. E2E-контур не является жесткой страховкой от регрессий
Evidence:
- `platform-admin.spec.ts` работает в deterministic lane (`E2E_DETERMINISTIC_AUTH=1`) и проходит `14/14` без `test.skip`.
- `tenants-a11y.spec.ts` переведён на deterministic mocks + жёсткий `expect(tenantsAvailable).toBe(true)` вместо `test.skip`.
Impact:
- Контур стал воспроизводимым и fail-closed.
- Остаточный риск: warnings окружения (`NO_COLOR/FORCE_COLOR`, npm env warning) не влияют на pass/fail, но требуют отдельной hygiene-задачи.

## Root-cause map
1. Нет единой state machine для `global context` и `page filters`.
2. API `company-cockpit` смешивает summary и branch-list для "выбранного клиента", что не покрывает управление портфелем.
3. Fleet аналитика рассчитывается синхронно "на лету" вместо read-model/предагрегации.
4. Страница остается orchestration-монолитом.
5. Тестовый контур допускает "soft skip", а не контрактную проверку.

## Invariant
1. Никакой скрытой фильтрации: пользователь всегда понимает, почему видит именно этот список.
2. Любое действие `platform_admin` имеет предсказуемую область (`company/client/branch`) и audit след.
3. Для `/tenants` источник фильтрации данных только явный `page filters` (query state), не implicit header drift.
4. Масштабирование не ломает UX: list/portfolio/cockpit работают курсорно и воспроизводимо.

## Scope
### In scope
1. Полный довод `Tenants V3` под `platform_admin`.
2. Исправление state drift между context и page filters.
3. Ревизия API контрактов для branches/cockpit/fleet summary под масштаб.
4. Завершение decomposition `tenants/page.tsx`.
5. Жесткие e2e + a11y + perf quality gates.

### Out of scope
1. Редизайн страниц owner/admin/manager вне `platform_admin`.
2. Изменение runtime LLM/core behavior.
3. Переписывание всей Console с нуля.
4. Жесткий LOC-лимит для `tenants/page.tsx` как самостоятельный gate.

## Recovery priority (2026-02-23)
1. P0: Убрать state-drift и silent reset (`company/client/branch`) — вкладка должна перестать "самопереключаться".
2. P0: Сделать действия на вкладке утилитарными:
- "В контекст",
- "Взять из рабочего контура",
- переходы в `Company Workspace` / `Integrations` / `Cases`.
3. P0: Зафиксировать контракт тестами A/B/C/D/E без skip.
4. P1: Упростить copy и убрать тех-шум из business режима.

## Scope state contract (single source of truth)
### Контуры
1. `Global context`:
- хранится в `localStorage` (`console:company_id/client_id/branch_id`).
- используется для межстраничной навигации и заголовков API.
2. `Page filters` (`/tenants`):
- хранится только в URL query (`company_id/client_id/branch_id`).
- определяет выборки таблиц и карточек Tenants.

### Приоритет
1. Данные `/tenants` читаются только из `page filters`.
2. `Global context` на `/tenants` не фильтрует списки "тихо".
3. `Взять из рабочего контура` = явный одноразовый sync из `global context` в `page filters`.

### Правило атомарности
1. `branch` нельзя устанавливать без согласованного `client/company` chain.
2. Если выбран branch, система должна либо:
- иметь валидную цепочку `company_id + client_id + branch_id`, либо
- отклонять действие с понятным сообщением, а не молча сбрасывать state.

## Control behavior matrix (целевой контракт)
| Контрол | Где | Меняет `global context` | Меняет `page filters` | Контракт |
|---|---|---|---|---|
| `В контекст` (client row) | Clients | Да | Да | `company+client` синхронизированы |
| `В контекст` (branch row) | Branches | Да | Да | `company+client+branch` синхронизированы |
| `Взять из рабочего контура` | Filters | Нет | Да | query получает полный валидный scope |
| `Сбросить фильтры` | Filters | Нет | Да | query очищен, global context сохранен |
| `Сбросить контур` | Context | Да | Нет | storage очищен, query не трогаем |

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/app/tenants/use-tenants-page-filters.ts`
- `console-web/src/components/TenantsTopControls.tsx`
- `console-web/src/components/TenantsOperationalKpiPanel.tsx`
- `console-web/src/components/TenantsActionQueuePanel.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/console-context-storage.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/e2e/tenants-a11y.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_tenants_*.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/REPORTS/2026-02-20-tenants-v3-redesign-plan.md`

## Plan (full implementation waves)
### Wave 0. Stop regression and state determinism (P0)
1. Fix `branch apply` drift:
- `setBranchContextAndPageFilters` должен писать полную chain (`company/client/branch`) на основе branch row.
- `applyContextToPageFilters` должен валидировать scope перед применением.
2. Убрать auto-wipe branch в `ConsoleShell` при `selected_branch_id = null`, если branch не требует принудительного выбора.
3. Внедрить unit+e2e state-machine тесты на A/B/C/D сценарии.
Expected result:
- кнопки и синхронизация работают предсказуемо, без silent reset.

### Wave 1. API contract alignment for portfolio scale (P0)
1. Расширить branches API:
- добавить server filter `branch_id` и `company_id` (без client lock-in).
2. Исправить cockpit contract:
- branch list не должен ограничиваться первым клиентом по умолчанию в портфельном сценарии.
3. В UI включить cursor pagination для всех server-contract веток (включая cockpit).
Expected result:
- список филиалов полный и управляемый на больших клиентах/компаниях.

### Wave 2. IA/UX simplification for platform_admin (P1)
1. Оставить один ясный сценарий:
- верх: `Фильтры страницы`;
- отдельный компактный блок: `Рабочий контур` только как cross-page state.
2. Удалить debug copy из business режима:
- `page filter client_id`, `Threshold drill-down`, `Action Queue` (заменить на RU business labels).
3. Убрать дублирующую информацию, которая не влияет на действие.
Expected result:
- оператор за 3 шага понимает "где я / что вижу / что делать дальше".

### Wave 3. Decomposition completion (P1)
1. Выделить остаточные секции в компоненты + hooks:
- `TenantsFleetAttentionPanel`
- `TenantsPortfolioCompaniesPanel`
- `TenantsClientsPanel`
- `TenantsChangeManagementPanel`
- `TenantsDecommissionPanel`
- `useTenantsDataQueries`
- `useTenantsActions`
2. Оставить `page.tsx` только orchestrator/composition.
Expected result:
- снижение regression surface, ускорение последующих итераций.

### Wave 4. Fleet read-model and performance hardening (P0 for 10M+)
1. Ввести read-model для портфеля:
- предагрегированные counters/scores по client/company (background refresh + incremental updates).
2. Перевести тяжелые вычисления fleet attention/summary из request-time в precompute.
3. Добавить индексы и verify планы запросов для `clients/branches/audit/outbox`.
4. Зафиксировать SLO:
- `/admin/tenants/portfolio` p95 < 1200ms (fleet slice),
- `/admin/tenants/company-cockpit` p95 < 1000ms,
- branch list page switch p95 < 800ms.
Expected result:
- управление не деградирует с ростом числа компаний и ниш.

### Wave 5. Quality gates hard close (P0)
1. A11y:
- устранить `critical/serious` (контраст KPI, focus, semantics).
2. E2E:
- убрать skip-зависимость от случайного контекста;
- сделать seed lane с фиксированными tenant fixtures.
3. Ввести обязательные contract checks для scenario A/B/C/D/E.
Expected result:
- зеленые и воспроизводимые проверки перед merge/release.

### Wave 6. Controlled rollout and guardrails (P1)
1. Добавить feature flag:
- `TENANTS_V3_CONTROL_TOWER`.
2. Rollout policy:
- shadow mode -> canary -> full.
3. Добавить dashboard наблюдения:
- state-drift incidents,
- cockpit pagination errors,
- a11y gate status,
- e2e scenario pass-rate.
Expected result:
- релиз контролируемый, откат предсказуемый.

## DoD (полный)
1. Scenario A/B/C/D/E проходят детерминированно без skip.
2. `branch` после `В контекст` + `Взять из рабочего контура` не теряется.
3. В `Tenants` нет технического copy в business режиме.
4. `/tenants` даёт операционную пользу: platform_admin может за <= 3 действия выбрать scope и перейти к следующему рабочему шагу без скрытых фильтров.
5. `portfolio/cockpit/branches` поддерживают курсорный скролл без "первого клиента" ловушки.
6. A11y: `critical=0`, `serious=0` для desktop/mobile.
7. Perf SLO выполняются на тестовом профиле крупного флота.
8. Feature flag rollout + rollback документированы и проверены.

## Checks
- `corepack pnpm -C console-web run lint`
- `corepack pnpm -C console-web run build`
- `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 corepack pnpm -C console-web exec playwright test e2e/platform-admin.spec.ts --project=chromium --workers=1`
- `PLAYWRIGHT_BASE_URL=http://localhost:3100 CI=1 E2E_DETERMINISTIC_AUTH=1 A11Y_FAIL_ON_THRESHOLDS=1 corepack pnpm -C console-web exec playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `pytest -q truffles-api/tests/test_console_tenants_list.py` (includes weekly-snapshot contract tests)
- `pytest -q truffles-api/tests/test_console_fleet_attention.py`
- `scripts/session_check.sh`

## Evidence
1. UI before/after screenshots:
- filters/context behavior,
- cockpit branches pagination,
- mode transitions,
- updated a11y artifacts: `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-desktop.png`, `docs/REPORTS/artifacts/2026-02-20-tenants-a11y/tenants-mobile.png`.
2. API evidence:
- openapi diff,
- sample requests/responses for portfolio/cockpit/branches.
3. Quality evidence:
- e2e logs по A/B/C/D/E (`14 passed`),
- axe JSON desktop/mobile (`critical=0`, `serious=0`),
- perf summary with p95.
4. State evidence:
- `localStorage scope` vs `query filters` trace before/after critical actions.

## Rollback
1. `TENANTS_V3_CONTROL_TOWER=0` возвращает предыдущий UI path.
2. API backward compatibility сохраняется минимум 1 release cycle.
3. Read-model fallback:
- при деградации precompute использовать текущий on-demand path временно.

## No-go
1. Нельзя мерджить с `test.skip` в ключевых сценариях A/B/C/D/E.
2. Нельзя оставлять mixed business/technical copy в default platform_admin UX.
3. Нельзя принимать release при `axe critical/serious > 0`.
4. Нельзя оставлять branch-list зависимым от "первого клиента" при company scope.
5. Нельзя считать масштабные fleet-агрегации только в request-time при целевом росте.

## Риски/блокеры
1. Большой blast radius у `tenants/page.tsx` и `console.py`.
2. Возможен drift контрактов при параллельной работе над API.
3. Риск скрытых state-регрессий при изменениях `ConsoleShell`/storage sync.
4. Риск ложного green без seed lane и hard-fail e2e/a11y.

## Worktree/branch policy
- Branch: `feat/2026-02-21-tenants-v3-ux-contract-a250`
- Worktree: `/home/zhan/worktrees/2026-02-21-tenants-v3-ux-contract-a250`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после полного закрытия waves
