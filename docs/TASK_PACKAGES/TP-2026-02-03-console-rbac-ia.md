# TP-2026-02-03-console-rbac-ia

- Название/цель: Закрыть RBAC/IA gaps из console audit: Team directory для manager (read-only), provisioning read-only для support, Specialist/Viewer роли, Ops short/full по роли.
- Canon refs: `STATE.md`, `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `SPECS/CONTROL_PLANE.md`.
- Invariant:
  - RBAC fail-closed, без расширения прав owner/admin.
  - Tenant selection gate без обходов.
  - Нет изменений в core pipeline (trace/meta/outbox).
- Scope:
  - Добавить Specialist/Viewer роли в API/UI (RBAC + labels).
  - Дать manager доступ к Team directory (read-only).
  - Дать support доступ к Provisioning (read-only).
  - Разделить Ops: short для owner/admin/support, full для platform_admin.
  - Обновить audit docs при необходимости.
- Out of scope:
  - Inbox escalation/metrics.
  - Team invite/disable и specialist availability.
  - Integrations/Insights страницы.
- Touch-list:
  - `truffles-api/app/services/console_auth.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/components/OpsPage.tsx`
  - `console-web/src/app/team/page.tsx`
  - `console-web/src/app/settings/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/src/types/api.generated.ts`
  - `truffles-api/tests/test_console_rbac.py`
  - `docs/CONSOLE_AUDIT/roles/*`
- Plan:
  1. Обновить RBAC в backend (roles + matrix + tests).
  2. Обновить OpenAPI и сгенерировать типы в console-web.
  3. UI gating/labels + Team directory read-only для manager.
  4. Provisioning read-only для support (view-only).
  5. Ops short/full по роли.
  6. Lint/tests + doc update.
- DoD:
  - Specialist/Viewer роли валидны в API/UI и имеют ожидаемый доступ.
  - Manager видит Team directory read-only, без edit.
  - Support видит Provisioning read-only, без edit.
  - Ops short/full разделён по роли.
  - Lint/tests зелёные.
- Checks:
  - `pytest -q truffles-api/tests/test_console_rbac.py`
  - `pytest -q truffles-api/tests/test_console_auth_access.py -k role`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint`
- Evidence:
  - Логи тестов/линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge при изменении поведения.
- Rollback:
  - Реверт коммита.
- No-go:
  - Расширение write-доступа.
  - Обход selection gate.
  - Изменения core pipeline.
- Риски/блокеры:
  - Уточнить матрицу Viewer и Specialist (если нужно).
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-rbac-ia-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-rbac-ia-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
