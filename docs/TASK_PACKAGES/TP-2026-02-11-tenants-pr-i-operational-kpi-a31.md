# TP-2026-02-11 Tenants PR-I Operational KPI Panel (a31)

## Название/цель
Добавить во вкладку `Tenants` операционную KPI-панель, чтобы platform_admin видел состояние онбординга/сервиса/изменений в одном месте и быстрее принимал решения.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants quality follow-up after PR-EF/PR-G/PR-H)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-h-quality-completion-a30.md`

## Invariant
- RBAC/tenant isolation не ослабляются.
- Existing lifecycle/modal/validation contracts остаются неизменными.
- API contracts не меняются (UI-only aggregation поверх существующих endpoints).

## Scope
- UI KPI strip в Tenants (`Portfolio`/`All` режимы):
  - onboarding coverage proxy,
  - go-live readiness proxy,
  - service stability,
  - decommission share,
  - branch-change publish failure rate (recent window),
  - rollback share (recent window),
  - blocked operations signals.
- Data inputs только из уже доступных API:
  - `clients summary`,
  - `fleet attention summary`,
  - `branch changes` list (recent).
- Явные подписи, формулы как proxy-метрики (без скрытой магии).
- Smoke and docs sync.

## Out of scope
- Backend migrations/new endpoints.
- Изменение go-live бизнес-правил.
- Дашборд за пределами страницы `Tenants`.

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-i-operational-kpi-a31.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-i-operational-kpi-a31.md`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-i-operational-kpi-a31`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-i-operational-kpi-a31`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Подключить recent branch changes query и вычисления KPI (memoized).
2. Добавить KPI panel/cards с data-testid и operator-first copy.
3. Обновить smoke-тесты Tenants для KPI контракта.
4. Обновить `tenants.md` с определением KPI и источников.
5. Прогнать checks и собрать evidence.

## DoD
- KPI-панель отображается в Tenants и обновляется без изменения backend contracts.
- KPI вычисляются из прозрачных источников (summary/attention/branch changes).
- Smoke по Tenants включает KPI presence contract.
- Checks зелёные.

## Checks
- `scripts/session_check.sh`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USE_STORAGE_STATE=1 E2E_USERNAME=admin E2E_PASSWORD=admin npx --prefix console-web playwright test console-web/e2e/smoke.spec.ts --project=chromium --grep "Tenants"`

## Evidence
- PR URL
- `git status -sb`
- `git diff --stat`
- outputs of checks
- updated docs/session artifacts

## Rollback
- `git revert` commit(s) PR-I by touch-list.

## No-go
- Не вводить псевдо-метрики без явной формулы/лейбла.
- Не использовать hardcoded values per tenant.
- Не менять backend endpoints/semantics в этой волне.

## Риски/блокеры
- KPI могут быть восприняты как абсолютная истина при proxy-расчётах.
- Митигация: явные labels `proxy`, источник и окно расчёта в UI copy.
