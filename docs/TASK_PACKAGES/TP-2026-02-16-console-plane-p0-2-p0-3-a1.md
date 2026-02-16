# TP-2026-02-16-console-plane-p0-2-p0-3-a1

- Название/цель: убрать основные причины жалоб на “подвисает/медленно” в Console Plane через один пакет P0: снизить polling-нагрузку в Inbox (P0-2) и удешевить hot-path `/console/v1/cases` (P0-3) без изменения продуктового поведения.
- Canon refs: `STATE.md` (NOW/GAP по runtime backlog и UX), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-08`, `UX-11`, `UX-12`), `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`, `SPECS/CONTROL_PLANE.md` (Inbox UX/RBAC), `AGENTS.md`.

## Invariant
- Не менять RBAC/tenant isolation/select-gate поведение.
- Не менять функциональный контракт Inbox (`filters`, `take/resolve/send`, cursor pagination).
- Не добавлять client-specific hardcode и не ломать fail-closed semantics.

## Scope
- P0-2 (frontend):
  - снизить частоту и фоновую интенсивность polling в Inbox paths;
  - убрать broad cache invalidation при переключении контекста в Shell.
- P0-3 (backend):
  - оптимизировать `list_cases` count-path (без тяжелых join/subquery на каждый refresh);
  - ограничить message/outbox subqueries клиентским scope в `/cases`.
- Обновить perf baseline/artefacts после правок.

## Out of scope
- Новый UI redesign.
- Миграции БД/индексов.
- Изменения бизнес-логики owner/admin страниц и Ops remediation flow.

## Touch-list
- `console-web/src/components/CaseList.tsx`
- `console-web/src/hooks/useCaseData.ts`
- `console-web/src/components/ConsoleShell.tsx`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_cases_helpers.py` (при необходимости helper-level checks)
- `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (status update)
- `STATE.md` (FACT + evidence)

## Plan
1. Зафиксировать baseline (SQL p50/p95 + health latency + polling footprint).
2. Внедрить Inbox polling-budget и scoped invalidation в `console-web`.
3. Внедрить оптимизацию `/cases` count/items path в `truffles-api`.
4. Прогнать targeted проверки (py_compile/pytest/lint/build) и переснять baseline.
5. Обновить evidence в report/STATE.

## DoD
- Снижение запросной нагрузки Inbox по коду (интервалы/фоновые refetch) без потери функционала.
- `list_cases` count-path больше не тянет полный тяжелый join graph каждый refresh.
- Message/outbox subqueries в `/cases` ограничены `client_id`.
- Targeted проверки зелёные.
- Есть before/after numbers в report и фактовая запись в `STATE.md`.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py`
- `pytest -q truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint -- --file src/components/CaseList.tsx --file src/hooks/useCaseData.ts --file src/components/ConsoleShell.tsx`
- `npm --prefix console-web run build`
- (evidence) perf scripts from `/tmp/console_perf_baseline_20260216/*`

## Evidence
- baseline artifacts (before/after) in `/tmp/console_perf_baseline_20260216`.
- SQL/health stats in `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`.
- diff on touch-list + command outputs from checks.

## Rollback
- Revert commit/PR with this package.
- For emergency mitigation keep previous polling intervals and count path by revert only (no data migration dependency).

## No-go
- Нельзя “чинить” метрики очисткой outbox/trace.
- Нельзя менять product behavior без отражения в каноне.
- Нельзя раздувать scope в рефактор всего `console.py`.

## Риски/блокеры
- Runtime outbox деградация может маскировать часть UX-улучшений.
- Без индексов дальнейший масштабный рост tenant-данных потребует отдельной DB wave.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-16-expected-reply-controller-a88` (по решению пользователя продолжать текущую ветку)
- Worktree: `/home/zhan/truffles-main`
- Base ref: текущий branch base без rebase
- Merge policy: PR -> main (no rebase)
- Cleanup: после merge удалить ветку/worktree по стандарту Brain/Top Architect
