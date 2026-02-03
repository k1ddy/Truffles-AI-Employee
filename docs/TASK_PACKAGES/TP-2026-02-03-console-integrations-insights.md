# TP-2026-02-03-console-integrations-insights

- Название/цель: Добавить Integrations registry и минимальный Insights/Analytics (read-only).
- Canon refs: `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `SPECS/CONTROL_PLANE.md` (IA), `docs/CONSOLE_GUIDE.md`.
- Invariant:
  - Только read-only UI; без изменений в данных.
  - RBAC fail-closed.
- Scope:
  - Новые страницы `/integrations` и `/insights`.
  - Навигация + RBAC gating.
  - Данные из существующих API (settings/telegram/metrics) или минимальный read-only endpoint при необходимости.
- Out of scope:
  - Новая аналитическая платформа.
  - Интеграции с внешними провайдерами.
- Touch-list:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/insights/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `truffles-api/app/services/console_auth.py` (если меняется RBAC)
  - `contracts/console_api/openapi.v1.yaml` (если добавляется endpoint)
  - `console-web/src/types/api.generated.ts`
- Plan:
  1. Определить минимальный набор данных + RBAC.
  2. Реализовать страницы (read-only) на существующих API.
  3. Обновить навигацию.
  4. Lint/tests + doc update.
- DoD:
  - Страницы доступны нужным ролям.
  - Данные загружаются, нет write-действий.
  - Lint зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - `npm --prefix console-web run generate:api` (если меняли OpenAPI)
- Evidence:
  - Логи линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Новые данные/метрики без явного решения.
- Риски/блокеры:
  - Уточнить минимальный набор метрик/интеграций.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-integrations-insights-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-integrations-insights-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
