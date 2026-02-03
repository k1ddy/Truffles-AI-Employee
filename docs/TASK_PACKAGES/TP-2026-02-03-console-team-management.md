# TP-2026-02-03-console-team-management

- Название/цель: Team invite/disable для пользователей + управление working_hours/availability у Specialists.
- Canon refs: `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `SPECS/CONTROL_PLANE.md` §8, `docs/CONSOLE_GUIDE.md`.
- Invariant:
  - RBAC fail-closed; owner/admin only for mutations.
  - Tenant isolation без обходов.
  - Booking flow без изменений.
- Scope:
  - Добавить admin update agent (disable/enable) + audit.
  - UI: invite/create user + disable toggle.
  - Добавить update specialist (working_hours/services/is_active) + UI editor.
  - Обновить OpenAPI + типы.
- Out of scope:
  - Integrations/Insights.
  - Inbox actions/metrics.
- Touch-list:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `truffles-api/app/routers/calendar.py`
  - `truffles-api/app/models/specialist.py`
  - `console-web/src/app/team/page.tsx`
  - `console-web/src/types/api.generated.ts`
  - `truffles-api/tests/*`
- Plan:
  1. PATCH /console/v1/admin/agents/{id} (is_active) + audit.
  2. UI: invite/create + enable/disable.
  3. PATCH /calendar/specialists/{id} (working_hours/services/is_active).
  4. UI: Specialists editor.
  5. Tests + lint.
- DoD:
  - Invite/disable работает с RBAC.
  - Specialists можно обновлять (working_hours/availability).
  - Tests/lint зелёные.
- Checks:
  - `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint`
- Evidence:
  - Логи тестов/линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Новые DB миграции без решения.
  - Изменения booking provider.
- Риски/блокеры:
  - Уточнить схему working_hours/availability.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-team-management-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-team-management-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
