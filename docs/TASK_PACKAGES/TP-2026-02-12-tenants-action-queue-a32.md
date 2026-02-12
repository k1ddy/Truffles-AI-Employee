# TP-2026-02-12-tenants-action-queue-a32

- Название/цель: Tenants control center uplift. Усилить операционный смысл вкладки Tenants: Action Queue, role preset, safer edit flow, readability и readiness timeline.
- Canon refs: `AGENTS.md`, `STATE.md` (тенант-аудит и gaps по UX/operability), `docs/CONSOLE_AUDIT/pages/tenants.md`.
- Invariant: не ломать API-контракты tenants/provisioning/lifecycle, сохранить текущие validate/publish/rollback и archive/restore.
- Scope:
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/e2e/smoke.spec.ts`
  - `docs/CONSOLE_AUDIT/pages/tenants.md`
- Out of scope:
  - backend schema migration
  - новые API endpoints
  - деструктивные live действия в production data
- Touch-list:
  - `console-web/src/app/tenants/page.tsx`
  - `console-web/src/components/ProvisioningWizard.tsx`
  - `console-web/e2e/smoke.spec.ts`
  - `docs/CONSOLE_AUDIT/pages/tenants.md`
- Plan:
  1. Добавить Action Queue + intent actions + view preset.
  2. Упростить operator-путь, оставить technical details в platform preset.
  3. Добавить readiness timeline и улучшить Go-Live wording.
  4. Обновить smoke assertions и page-doc.
  5. Прогнать lint/build/pytest.
- DoD:
  - UI отражает Action Queue и view preset.
  - Wizard показывает readiness timeline.
  - lint/build и профильный pytest green.
  - docs синхронизированы с новым поведением.
- Checks:
  - `npm --prefix console-web run lint`
  - `npm --prefix console-web run build`
  - `pytest -q truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_fleet_attention.py truffles-api/tests/test_console_provisioning_validation.py truffles-api/tests/test_console_access_admin_pr2.py`
- Evidence:
  - git diff/stat
  - logs lint/build/pytest
  - updated test selectors in smoke
- Rollback:
  - revert commit on feature branch or rollback PR merge commit.
- No-go:
  - нельзя убирать lifecycle guards.
  - нельзя заменять deterministic checks на ручные утверждения.
- Риски/блокеры:
  - текущая среда не запускает Chromium Playwright runtime.
  - remote sync зависит от сетевой доступности GitHub.
