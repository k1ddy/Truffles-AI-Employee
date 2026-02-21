# REPORT-2026-02-20-tenants-v3-redesign-plan

## Scope
- Deep-gap анализ `platform_admin` для `Tenants`.
- Цель: подтвердить системные причины неудобства управления компаниями (onboarding -> operate -> change -> decommission) и подготовить полный план редизайна.

## Wave 0 baseline run (2026-02-20, UTC)
1. Worktree/session initialized for redesign lane.
- Worktree: `/home/zhan/worktrees/2026-02-20-tenants-v3-redesign-a250`
- Branch: `feat/2026-02-20-tenants-v3-redesign-a250`

2. Baseline dependencies in worktree prepared.
- Команда: `npm --prefix console-web ci`
- Результат: install completed (`added 511 packages`).

3. Live Tenants smoke (platform_admin lane) validated.
- Команда: `npx playwright test e2e/platform-admin.spec.ts --grep "Platform Admin Tenants"`
- Результат: `8 passed (1.1m)` after retry.
- Наблюдение: первый прогон дал network/auth flake (`chrome-error://chromewebdata`, затем timeout в global-setup), повторный запуск зелёный.

4. Tenants a11y lane currently unstable/insufficient.
- Команда: `npx playwright test e2e/tenants-a11y.spec.ts`
- Результат: tests skipped (`2 skipped`, setup may pass) из-за условия availability/gate в тесте.
- Вывод: для baseline не хватает жёсткого fail-closed a11y lane (сейчас skip допускает ложный green).

5. Runtime health snapshot unstable/unhealthy.
- Команда: `curl -sS https://console.truffles.kz/api/health/full` (3 последовательных прогона).
- Результат: `status=unhealthy`, API `HTTP 502`, build hash `2934de8a`.

6. Platform KPI snapshot captured twice and показал дрейф runtime.
- Команда:
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_tenants_v3_wave0_20260220.json`
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_tenants_v3_wave0_20260220_r2.json`
- Результат:
  - Run-1 получил `console_health=healthy` (`version=098ee34b`) и outbox hints.
  - Run-2 получил `console_health=502` + `admin/version=2934de8a`.
- Вывод: live runtime нестабилен во времени, baseline должен хранить оба слепка.

## Verified facts
1. Текущая страница `Tenants` остаётся высокосвязанным монолитом.
- `console-web/src/app/tenants/page.tsx` содержит ~3961 LOC.
- Внутри страницы смешаны несколько независимых доменов (quick-create, KPI/reporting, fleet-risk, lifecycle modal, branch-change pipeline, wizard).

2. Контекст выступает скрытым фильтром списков.
- `clients` query зависит от `selectedCompanyId`.
- `branches` query зависит от `selectedClientId`.
- Это приводит к восприятию "данные пропали" при неочевидном контексте.

3. Weekly snapshots не имеют строгого typed-контракта и реализованы через audit events + local fallback.
- OpenAPI хранит `snapshot` как `object`.
- Backend фильтрует week_key постфактум на ограниченном батче.
- UI при серверной ошибке пишет успешный локальный save.

4. A11y/UX debt системный, не только точечный.
- В quick-create филиала есть placeholder-only inputs без явных label.
- Исторический live-отчёт фиксирует `critical/serious` axe-проблемы.

5. E2E-покрытие Tenants содержит мягкие early-return ветки.
- Часть тестов успешно завершается при отсутствии ключевых элементов/данных.
- Это снижает ценность регрессионного контроля.

## Root cause summary
1. Нет чёткой границы ответственности между `Tenants`, `Integrations`, `Company Workspace`.
2. Global context и page-level filters не разведены в UX-модели.
3. Память операционного цикла (`weekly snapshots`) построена как "audit + cache", а не как отдельный контракт данных.
4. Большой монолит UI/API делает целевую эволюцию медленной и рискованной.

## Wave 1-2 initial implementation (worktree only)
1. Workspace contract shifted to portfolio-first.
- `workspaceMode` default changed from `all` to `portfolio`.
- Removed `Все зоны` mode/button.
- Section rendering now follows single active workspace mode.

2. Added explicit Context Lens in Tenants header.
- New panel `tenants-context-lens` shows active company/client/branch filters.
- Added controls:
  - `tenants-context-clear-branch`
  - `tenants-context-clear-client`
  - `tenants-context-clear-all`
- Goal: make context-driven filtering explicit and reversible on-page.

3. Error summary now strictly mode-scoped.
- Removed legacy `all` scope branch; active scope follows current workspace mode.

4. Updated Tenants smoke contract for new IA.
- `console-web/e2e/platform-admin.spec.ts` no longer expects `tenants-mode-all`.
- Added assertion for `tenants-context-lens` visibility in workspace mode flow.

## Validation after implementation
1. Local static checks: pass.
- `npm --prefix console-web run lint -- --file src/app/tenants/page.tsx --file e2e/platform-admin.spec.ts`
- `npx tsc --noEmit`
- `npm --prefix console-web run build`

2. Live smoke against deployed `console.truffles.kz`: expected mismatch.
- Command: `... playwright test e2e/platform-admin.spec.ts --grep "Platform Admin Tenants" --retries=1`
- Result: fail on `tenants-context-lens` not found (deployed build does not include local worktree changes yet).

## Output artifact
- Полный план редизайна и реализации оформлен в:
  - `docs/TASK_PACKAGES/TP-2026-02-20-tenants-v3-platform-admin-redesign.md`
