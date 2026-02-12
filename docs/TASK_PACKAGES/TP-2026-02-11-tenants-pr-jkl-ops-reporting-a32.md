# TP-2026-02-11 Tenants PR-JKL Operational Control Completion (a32)

## Название/цель
Закрыть блоки `J/K/L` для вкладки `Tenants` одним PR: persistent lifecycle audit, KPI thresholds+drill-down+CTA, export/report + weekly snapshot + alert hooks, чтобы Platform Admin мог делать операционный контроль и онбординг без ручных обходов.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants follow-up after PR-I)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-i-operational-kpi-a31.md`

## Invariant
- RBAC/tenant isolation не ослабляются.
- Existing lifecycle/archive/restore and branch-change contracts не меняются.
- Backend/API side effects без явного operator action не добавляются.

## Scope
- `J`: Persistent lifecycle audit timeline в Tenants:
  - session lifecycle history хранится и восстанавливается из localStorage;
  - API audit feed (`/audit`) для selected client объединяется с session timeline;
  - unified timeline + фильтр по результату (all/success/error).
- `K`: KPI thresholds + drill-down + actionable CTA:
  - threshold model для KPI strip;
  - status/tone per KPI;
  - drill-down rows с объяснением, why-breach и кнопкой action.
- `L`: Export/report + weekly snapshot + alert hooks:
  - export KPI report в JSON/CSV;
  - weekly snapshots (persisted history, capped window) + delta vs previous;
  - alert hook preview payload + operator trigger для `metrics_snapshot` dry-run/execute.
- Smoke coverage + docs sync.

## Out of scope
- DB migrations/new backend endpoints.
- Изменение lifecycle backend semantics.
- Изменение IA за пределами вкладки `Tenants`.

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-jkl-ops-reporting-a32.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-jkl-ops-reporting-a32.md`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-jkl-ops-reporting-a32`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-jkl-ops-reporting-a32`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Добавить data/model слой для J/K/L в `tenants/page.tsx` (timeline merge, thresholds, report/snapshot builders).
2. Добавить UI блоки: lifecycle audit panel, KPI drill-down, export/snapshot/alert controls.
3. Подключить ops job hooks (`metrics_snapshot` dry-run/execute) и operator feedback.
4. Обновить Tenants smoke coverage для новых контрактов UI.
5. Обновить `tenants.md` (операционный контур J/K/L).
6. Прогнать checks и собрать evidence.

## DoD
- J/K/L функционально видимы в Tenants (platform_admin) и не ломают существующий flow.
- Lifecycle timeline не теряется после refresh (session persistence) и показывает API audit для selected client.
- KPI drill-down и CTA работают (переключения/действия из панели).
- Export/snapshot/alert-hook controls работают без backend contract breaks.
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
- checks output
- updated session/docs artifacts

## Rollback
- `git revert` commit(s) this PR by touch-list.

## No-go
- Не вводить скрытые side effects в read-path.
- Не менять lifecycle endpoints/semantics.
- Не добавлять hardcoded tenant-specific rules.

## Риски/блокеры
- Операторы могут трактовать proxy KPI как абсолютный SLA.
- Митигация: явные labels threshold/proxy + источник/окно + drill-down reasons.
