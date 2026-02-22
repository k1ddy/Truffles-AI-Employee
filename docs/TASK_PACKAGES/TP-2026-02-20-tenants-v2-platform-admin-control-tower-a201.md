# TP-2026-02-20-tenants-v2-platform-admin-control-tower-a201

## Название/цель
Tenants V2 для `platform_admin`: превратить вкладку `/tenants` в полный контур управления компаниями от старта онбординга до полного операционного управления (portfolio/changes/decommission), с безопасными действиями, прозрачным контекстом, командным аудитом и сниженной когнитивной нагрузкой.

## Canon refs
- AGENTS.md (Task Package, one-issue flow, stop-the-line, fitness gates)
- STATE.md NOW/GAP (console tenants UX debt, runtime observability, platform_admin control loop)
- docs/CONSOLE_AUDIT/pages/tenants.md
- SPECS/CONTROL_PLANE.md
- SPECS/SYSTEM_REFERENCE.md
- TECH.md

## Product intent (добавление к цели)
`Tenants` для `platform_admin` должен закрывать весь жизненный цикл компаний как единый управляемый контур:
1. `Start` — онбординг и запуск нового клиента/филиала.
2. `Stabilize` — ежедневный операционный контроль (KPI, риски, Action Queue, incidents).
3. `Change` — controlled change (draft/validate/publish/rollback).
4. `Operate at scale` — управление портфелем компаний и контекстом без потери фокуса.
5. `Decommission/Return` — архив/восстановление с audit trail и прозрачным impact.

## Invariant
- Tenants остается `platform_admin only`; расширение ролей запрещено.
- Любое risky действие (lifecycle/change) остается traceable и auditable.
- Нельзя ухудшить консистентность контекста (company/client/branch) между header и page body.
- Нельзя деградировать доступность (A11y): целевой уровень минимум WCAG AA без critical/serious нарушений.
- Нельзя хранить weekly-operational history только в localStorage как единственный источник.

## Scope
- Переработка UX/IA Tenants под company management lifecycle.
- Декомпозиция монолитной страницы на секции/модули.
- Контекст, ошибки, доступность, безопасность отображения идентификаторов.
- KPI/weekly snapshot/reporting как server-backed auditable workflow.
- Тесты (frontend+api+e2e+axe) и evidence.

## Out of scope
- Изменение ролевого дизайна для owner/admin/manager/support.
- Полный redesign всех других вкладок Console.
- Изменение бизнес-контрактов escalation/consultant вне необходимых интеграционных точек Tenants.

## Problems to close (fact list)
1. Context mismatch: header показывает branch, Tenants body показывает `—`.
2. Global error leakage: ошибки из одной зоны шумят в другой зоне.
3. A11y defects: missing labels/select-name/date-name, contrast gaps.
4. Information overload: `All` режим перегружен действиями и формами.
5. Sensitive identifiers exposure: `instance_id` показан открытым текстом.
6. Weekly operational memory local-only: нет server-side audit trail.
7. Mixed language/copy inconsistency в критичных operator flows.
8. Monolithic page complexity (высокий риск регрессий и замедление delivery).

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/use-inline-error-summary.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts` (если контракт расширится)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_*`
- `console-web/e2e/platform-admin.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/REPORTS/2026-02-20-tenants-v2-platform-admin-control-tower-a201.md`

## Plan (1..N)
1. Baseline + safety lock
- Зафиксировать baseline UX/API/A11y (скриншоты, axe, key flows, API snapshots).
- Подтвердить проблемные точки evidence-артефактами.

2. IA and lifecycle orchestration (core UX)
- Явно встроить lifecycle model управления компаниями (Start/Stabilize/Change/Decommission).
- Пересобрать workspace modes под управление компаниями, а не под набор разрозненных блоков.
- Установить `Portfolio` как default focus (с быстрыми переходами в execution zones).

3. Context consistency kernel
- Вынести единый resolver отображения контекста (company/client/branch) и использовать и в header и в Tenants body.
- Убрать расхождение `selected_branch_id` vs fallback отображения.

4. Error architecture
- Разделить error summary по доменам (quick-create / lifecycle / changes / kpi-hooks).
- Сделать scoped clear + auto-clear при успешной операции внутри соответствующей зоны.

5. A11y hardening
- Добавить корректные labels/aria-labelledby/aria-label для `select`, `date`, полей фильтров и автопилота.
- Исправить контраст в guide/help secondary text.
- Проверить keyboard/focus порядок в modal и actionable blocks.

6. Sensitive data display policy
- Маскировать `instance_id` и другие чувствительные технические идентификаторы в списках.
- Добавить explicit reveal/copy behavior (при необходимости) c audit событием.

7. Server-backed operational memory
- Добавить API для weekly snapshots Tenants (create/list) с actor/scope/source metadata.
- Перевести UI snapshot workflow на серверный источник; localStorage оставить как fallback cache.

8. Decomposition + maintainability
- Разделить `tenants/page.tsx` на модульные секции и hooks.
- Сохранить поведение/контракты, но уменьшить связность и blast radius.

9. Verification and release gate
- Прогнать unit/integration/e2e/axe.
- Сформировать evidence report и обновить audit docs.

## DoD
- Context на header и Tenants совпадает по branch отображению.
- Ошибки одной зоны не загрязняют другие зоны.
- Axe на Tenants desktop/mobile: `critical=0`, `serious=0`.
- Sensitive IDs скрыты по умолчанию.
- Weekly snapshots доступны серверно и auditable.
- Page decomposition выполнена без потери функций (ключевые потоки проходят e2e).
- Evidence сохранён в report + session log.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --grep "Tenants"`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_admin_provisioning.py`
- `node`/Playwright + axe scripted checks for `/tenants` desktop/mobile

## Evidence
- Screenshots before/after по режимам Tenants и ключевым действиям.
- `axe` отчёты desktop/mobile.
- API payload snapshots (`/api/proxy/me`, tenants/admin endpoints, snapshots endpoints).
- e2e output по основным flows (`portfolio`, `onboarding`, `changes`, `decommission`).
- Tech report: `docs/REPORTS/2026-02-20-tenants-v2-platform-admin-control-tower-a201.md`.
- STATE.md update выполняется Brain/Top Architect при приёмке.

## Rollback
- UI rollback через feature flag `TENANTS_V2_ENABLED` (или revert PR).
- Backend snapshots endpoints backward-compatible; при rollback UI можно временно вернуться к read-only local fallback.

## No-go
- Нельзя расширять доступ к Tenants за пределы `platform_admin`.
- Нельзя убирать confirmations для destructive actions.
- Нельзя принимать релиз при `axe critical/serious` на Tenants.
- Нельзя делать local-only snapshots единственным source of truth.

## Branch/Worktree
- Branch: `feat/2026-02-20-tenants-v2-platform-admin-control-tower-a201`
- Worktree: `/home/zhan/worktrees/2026-02-20-tenants-v2-platform-admin-control-tower-a201`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после merge удалить branch/worktree (Brain или Top Architect)

## Fitness Functions impacted
- P1-7 Trace on early returns: не ломаем stage/trace flows и audit semantics.
- P1-8 decision_meta integrity: контекст и операции остаются auditable.
- P2-13 Stage order snapshot: изменения UI/API без скрытого изменения контрактов decision pipeline.
- P2-15 Local-first realism gate: live UX/API evidence + deterministic checks обязательны.

## Risks/blockers
- Большой объем монолита `tenants/page.tsx` повышает риск непреднамеренных регрессий.
- Возможен контрактный дрейф при добавлении snapshots API (требуется OpenAPI sync).
- Переход с local snapshot на server snapshot требует миграционной совместимости UX.
