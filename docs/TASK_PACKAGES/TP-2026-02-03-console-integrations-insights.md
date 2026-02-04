# TP-2026-02-03-console-integrations-insights

- Название/цель: Добавить Insights/Analytics страницу (read-only) для владельцев/админов.
- Canon refs: `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `SPECS/CONTROL_PLANE.md` (IA), `docs/CONSOLE_GUIDE.md`.
- Invariant:
  - Только read-only UI; без изменений в данных.
  - RBAC fail-closed.
- Scope:
  - Новая страница `/insights` (read-only).
  - Навигация + RBAC gating (owner/admin).
  - Метрики из существующего `/console/v1/metrics/daily`.
- Out of scope:
  - Integrations registry.
  - Новая аналитическая платформа или новые источники данных.
- Touch-list:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/app/insights/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/pages/global-shell.md`
  - `docs/CONSOLE_AUDIT/pages/insights.md`
  - `docs/CONSOLE_AUDIT/roles/owner.md`
  - `docs/CONSOLE_AUDIT/roles/admin.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Зафиксировать RBAC для Insights и минимальный набор метрик.
  2. Реализовать `/insights` (read-only) на `/metrics/daily`.
  3. Обновить навигацию + docs (audit pages/index + structure).
  4. Lint/tests + запись в `STATE.md`.
- DoD:
  - Insights доступен owner/admin, данные отображаются, нет write-действий.
  - Навигация обновлена, RBAC fail-closed.
  - Lint зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - Test waiver: новый e2e/units test не добавляем (нет готового harness/fixtures для Insights); ручная проверка после deploy.
- Evidence:
  - Логи линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Новые данные/метрики без явного решения.
- Риски/блокеры:
  - Метрики `/metrics/daily` gated как Ops; убедиться, что RBAC в UI согласован.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-insights-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-insights-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
