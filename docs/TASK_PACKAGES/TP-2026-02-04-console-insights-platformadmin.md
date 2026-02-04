# TP-2026-02-04-console-insights-platformadmin

- Название/цель: Открыть Insights/Analytics для platform_admin (read-only) и синхронизировать канон/аудит.
- Canon refs: `SPECS/CONTROL_PLANE.md` (IA), `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `STATE.md`.
- Invariant:
  - Только read-only UI; без изменений в данных или API.
  - RBAC fail-closed; write-права не расширяем.
- Scope:
  - Добавить Insights в IA для platform_admin (канон).
  - Разрешить read для platform_admin в UI RBAC.
  - Обновить audit docs + STATE.
- Out of scope:
  - Новые метрики/эндпоинты.
  - Integrations registry.
  - Backend/RBAC изменения на сервере.
- Touch-list:
  - `SPECS/CONTROL_PLANE.md`
  - `console-web/src/lib/api-client.ts`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/pages/insights.md`
  - `docs/CONSOLE_AUDIT/roles/platform_admin.md`
  - `STATE.md`
- Plan:
  1. Обновить канон IA (platform_admin включает Insights).
  2. Расширить ConsoleRBAC (insights read для platform_admin).
  3. Синхронизировать audit docs + STATE.
  4. Lint + evidence.
- DoD:
  - Platform Admin видит Insights в навигации и страницу с метриками.
  - Канон и audit синхронизированы.
  - Lint зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - Test waiver: новые e2e/units тесты не добавляем (узкое RBAC-расширение, нет harness).
- Evidence:
  - Лог линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Новые данные/метрики без решения.
- Риски/блокеры:
  - Несовпадение канона и UI RBAC.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-04-console-insights-platformadmin-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-04-console-insights-platformadmin-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
