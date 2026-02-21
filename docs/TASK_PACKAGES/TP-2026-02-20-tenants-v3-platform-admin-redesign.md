# TP-2026-02-20-tenants-v3-platform-admin-redesign

## Название/цель
Полный редизайн `Tenants` для роли `platform_admin` как единого контура управления компаниями: от старта онбординга до ежедневного портфельного управления, controlled change, decommission и операционного контроля платформы без потери прозрачности и без скрытых фильтров.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP по Tenants/Platform Admin)
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`

## Product intent (смысл вкладки)
`/tenants` должен быть platform-level control tower:
1. Видеть весь портфель компаний и их состояние.
2. Понимать стадию жизненного цикла каждой компании/клиента/филиала.
3. Запускать действия безопасно и предсказуемо (с audit и подтверждением).
4. Управлять масштабом (десятки/сотни компаний) без деградации UX.

## Evidence: deep problems (FACT)
1. Монолит и смешение доменов в одном экране.
- `console-web/src/app/tenants/page.tsx` ~3961 LOC.
- Одновременно смешаны: quick-create, KPI, fleet-risk, lifecycle modal, branch-change pipeline, onboarding wizard.

2. Скрытая фильтрация через глобальный контекст и эффект "пропавших данных".
- Запросы клиентов/филиалов жёстко завязаны на `selectedCompanyId`/`selectedClientId`:
  - `console-web/src/app/tenants/page.tsx:1018`
  - `console-web/src/app/tenants/page.tsx:1048`
- В UI это выглядит как "список неполный", хотя это фильтр контекста.

3. Контекст-бар не масштабируется на большой флот.
- Простые `select`-контролы без поиска/виртуализации:
  - `console-web/src/components/ConsoleShell.tsx:855`
  - `console-web/src/components/ConsoleShell.tsx:878`
  - `console-web/src/components/ConsoleShell.tsx:898`

4. Неполная/нестрогая серверная память weekly snapshots.
- Snapshot контракт типизирован как `object` (без схемы):
  - `contracts/console_api/openapi.v1.yaml:12684`
  - `contracts/console_api/openapi.v1.yaml:12738`
- Поиск по week_key выполняется после ограниченного батча (`limit*4`), что даёт риск пропуска старых недель:
  - `truffles-api/app/routers/console.py:12864`
  - `truffles-api/app/routers/console.py:12867`
  - `truffles-api/app/routers/console.py:12870`
- Update existing weekly record делает полный scan по клиенту:
  - `truffles-api/app/routers/console.py:12914`
  - `truffles-api/app/routers/console.py:12928`

5. Ложнопозитивный UX при серверной ошибке snapshot.
- При ошибке API UI пишет "сохранён локально", что визуально похоже на success и скрывает деградацию server-side audit trail:
  - `console-web/src/app/tenants/page.tsx:1677`
  - `console-web/src/app/tenants/page.tsx:1680`

6. Календарная неделя считается не ISO-алгоритмом.
- Ключ недели считается через `ceil(dayOfYear/7)`:
  - `console-web/src/app/tenants/page.tsx:421`
- Возможны ошибки на границах года и несогласованность отчётности.

7. A11y и IA debt остаются системной зоной риска.
- Исторические live-артефакты показывают `critical/serious` нарушения:
  - `docs/REPORTS/2026-02-20-tenants-a11y-evidence-a201.md`
- В quick-create блоке поля филиала не имеют явных label (placeholder-only):
  - `console-web/src/app/tenants/page.tsx:2443`
  - `console-web/src/app/tenants/page.tsx:2481`

8. Smoke/e2e для Tenants частично "мягкие" и допускают ранний `return`.
- Примеры skip-like веток:
  - `console-web/e2e/platform-admin.spec.ts:287`
  - `console-web/e2e/platform-admin.spec.ts:333`
  - `console-web/e2e/platform-admin.spec.ts:349`
  - `console-web/e2e/platform-admin.spec.ts:537`

## Root-cause map
1. Нет чёткой архитектурной границы между тремя platform-admin поверхностями:
- `Tenants` (должен быть control tower),
- `Integrations` (fleet health),
- `Company Workspace` (branch execution).

2. Глобальный контекст используется как скрытый data-filter, а не как явная "линза".

3. Данные weekly/history хранятся в аудите и local cache вместо выделенного операционного хранилища.

4. Огромные UI/Router модули замедляют доставку изменений и делают регрессии вероятными.

## Redesign target state (V3)
### IA (platform_admin only)
1. `/tenants` = Portfolio Control Tower.
- Таблично-карточный обзор всех компаний/клиентов.
- Статусы lifecycle: `onboarding`, `go_live_ready`, `operating`, `degraded`, `decommissioned`.
- Явные фильтры портфеля (не скрытые через context bar).

2. `/company-workspace` = Execution Console.
- Только операции по выбранной компании/клиенту/филиалу.
- Draft/validate/publish/rollback, go-live decisions, provider actions.

3. `/integrations` = Fleet Diagnostics.
- Read-first техническая матрица.
- Все mutate-действия через явный переход в workspace.

### UX model
1. Убрать режим `All`.
- По умолчанию открывается `Portfolio` (единая стартовая точка).

2. Ввести `Context Lens`.
- `Global context` (header) и `page filters` (тенантная линза) разведены.
- Всегда видимый chip-бар активных фильтров с `Reset`.

3. Two-level action architecture.
- `Primary`: открыть контур компании (company cockpit drawer/page).
- `Secondary`: конкретные действия (create/change/archive/repair).

4. Company Journey Timeline (внутри company cockpit).
- История lifecycle, change, incidents, go-live decisions, weekly snapshots.
- Единый audit trail и статус последнего шага.

5. Copy system.
- Единый язык интерфейса (RU-first или EN-first, но без микса в одной зоне).
- Операторские тексты без технического шума в default mode.

## Scope
### Product/UX
- Полный IA/UX редизайн `Tenants` под control tower.
- Разграничение зон ответственности `Tenants`/`Integrations`/`Company Workspace`.
- Контекст и фильтры без скрытых ограничений.

### Frontend
- Декомпозиция `tenants/page.tsx` на модули:
  - `TenantsPortfolioBoard`
  - `TenantsCompanyCockpit`
  - `TenantsLifecyclePanel`
  - `TenantsChangePanel`
  - `TenantsSnapshotPanel`
  - `TenantsFiltersBar`
- Внедрение server-driven table state (filters/sort/pagination).
- A11y hardening на уровне design primitives.

### Backend/API
- Новый server contract для control tower summary:
  - `GET /console/v1/admin/tenants/portfolio`
  - `GET /console/v1/admin/tenants/company-cockpit`
- Выделенный snapshot contract/table:
  - `tenants_weekly_snapshots` (typed schema, unique `(client_id, iso_week)`).
- Оптимизация запросов и индексов:
  - `audit_events(client_id, event_type, entity_type, created_at desc)` если audit остаётся источником части history.

### Data/migrations
- Миграция historical weekly snapshots из `audit_events` в `tenants_weekly_snapshots`.
- Backfill job + data validation report.

## Out of scope
- Изменение ролевой модели кроме `platform_admin`.
- Полный редизайн owner/admin/manager страниц.
- Изменение логики LLM/runtime decision pipeline.

## Touch-list
- `console-web/src/app/tenants/page.tsx` (split/orchestrator)
- `console-web/src/components/ConsoleShell.tsx` (context lens + global context UX)
- `console-web/src/components/ProvisioningWizard.tsx` (remove deep embed from Tenants; keep deep-link)
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/e2e/tenants-a11y.spec.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/migrations/*` (new snapshots table/indexes)
- `truffles-api/tests/test_console_tenants_*.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/REPORTS/2026-02-20-tenants-v3-redesign-plan.md`

## Plan (implementation waves)
1. Wave 0: Discovery lock + contract freeze (2-3 days)
- Подтвердить baseline UX/API/perf/a11y.
- Зафиксировать обязательные сценарии управления компаниями E2E.
- Freeze текущий API-контракт и подготовить migration plan.

2. Wave 1: Information architecture and navigation boundary (3-4 days)
- Удалить `All` режим, включить `Portfolio` default.
- Явно развести "портфельный обзор" и "исполнение".
- Ввести переходы `Tenants -> Company Workspace/Integrations` с сохранением lens.

3. Wave 2: Context Lens kernel (3-4 days)
- Разделить global context и page filters.
- Ввести видимый filter chip bar + reset + clear explanations.
- Убрать "тихую" фильтрацию списков по заголовочному контексту без явной индикации.

4. Wave 3: Data contract hardening (4-6 days)
- Добавить typed snapshots table + API.
- Мигрировать историю и сделать fallback read-only при ошибках миграции.
- Исправить week key на ISO-week.
- Запретить ложный success при server-failure snapshot.

5. Wave 4: UI decomposition + performance (5-7 days)
- Разбить `tenants/page.tsx` на модули.
- Вынести query/cache orchestration в domain hooks.
- Оптимизировать heavy запросы (fleet filters + summaries) и индексацию.

6. Wave 5: A11y + copy + quality gates (3-4 days)
- Убрать `critical/serious` axe violations.
- Добавить labels для всех controls, контраст, focus order, modal semantics.
- Устранить RU/EN copy mix.

7. Wave 6: E2E realism and rollout (3-4 days)
- Ужесточить e2e: убрать early-pass ветки.
- Добавить data-seeded test lane без skip-поведения.
- Включить feature flag rollout: `TENANTS_V3_CONTROL_TOWER`.

## DoD
1. Platform-admin проходит полный путь:
- onboarding start -> go-live readiness -> change -> decommission -> restore,
- без перехода в "поисковый квест" по вкладкам.

2. В `Tenants` нет скрытой фильтрации.
- Любой active filter виден и сбрасывается явно.

3. Snapshot/history полностью server-backed.
- Нет "успеха" при недоступном сервере.
- Snapshot schema typed и валидируется.

4. A11y: `critical=0`, `serious=0` (desktop/mobile, live lane).

5. E2E покрывает реальные mutate-сценарии без fallback-return.

6. Performance:
- p95 загрузки portfolio list и company cockpit в целевых SLO.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --grep "Platform Admin Tenants"`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz ... npx playwright test e2e/tenants-a11y.spec.ts --project=chromium --workers=1 --reporter=list`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `pytest -q truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_fleet_attention.py`
- `scripts/session_check.sh`

## Evidence
- Before/after screenshots (portfolio, cockpit, change, decommission flows).
- UX trace with recorded actions and resulting state.
- API contract diff (`openapi`), migration output, backfill report.
- Axe JSON (desktop/mobile) + pass logs.
- E2E logs for core platform-admin journeys.

## Rollback
1. UI rollback через `TENANTS_V3_CONTROL_TOWER=0`.
2. API backward compatibility для V2 consumers сохраняется минимум 1 release.
3. Snapshot migration reversible: source audit-events данные не удалять до post-release validation.

## No-go
- Нельзя возвращать скрытую фильтрацию списков через header context.
- Нельзя оставлять snapshot как local-only source.
- Нельзя принимать релиз при `axe critical/serious > 0`.
- Нельзя добавлять новые mutate-действия в `Integrations` (read-first contract).

## Риски/блокеры
1. Большой blast radius из-за монолитов (`tenants/page.tsx`, `console.py`).
2. Риск дрейфа контрактов при параллельных правках Console APIs.
3. Риск data-loss/duplication при миграции snapshots из audit log.
4. Риск ложного green в e2e без seed-данных (skip-like поведение).

## Worktree/branch policy
- Один worktree на весь V3 редизайн.
- Merge-only policy (no rebase).
- Mandatory evidence + session logs per wave.
