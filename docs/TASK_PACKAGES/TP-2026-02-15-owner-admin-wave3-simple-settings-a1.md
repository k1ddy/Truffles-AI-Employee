# TP-2026-02-15-owner-admin-wave3-simple-settings-a1

- Название/цель: Закрыть Wave-3 для owner/admin control-plane: добавить простые бизнес-настройки SLA + explainability в `Settings`, устранить баг `PATCH /settings`, закрепить e2e и live-check evidence.
- Canon refs: `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/SESSIONS/SESSION-2026-02-15-owner-admin-business-deep-audit-a1.md`.

## Invariant
- Не ослаблять tenancy/RBAC: write только для `owner/admin/platform_admin`.
- Не менять runtime-пайплайн эскалации и reminder-service вне контрактного update settings.
- Не подменять evidence тестами без trace/meta подтверждения.

## Scope
- Backend:
  - исправить `PATCH /console/v1/settings` (map request -> real DB fields + validation).
  - добавить deterministic unit tests на mapping/validation.
- Frontend:
  - добавить owner/admin “простые настройки” с preset-профилями.
  - добавить explainability-блок “как это влияет на бизнес”.
- QA/evidence:
  - owner/admin e2e smoke suite.
  - live-check evidence (`decision_trace`, `decision_meta`, outbox status).

## Out of scope
- Перестройка reminder/escalation алгоритмов.
- Изменение provisioning wizard логики.
- Новые billing/contract продукты.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/app/settings/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/pages/settings.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave3-simple-settings-v1.md`
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-business-deep-audit-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Исправить backend settings update и добавить validation/mapping tests.
2. Добавить UI простых настроек и explainability в `Settings`.
3. Добавить/расширить owner-admin e2e smoke.
4. Подтвердить live-check evidence по decision_meta/trace.
5. Зафиксировать отчёт, backlog и session evidence.

## DoD
- `PATCH /console/v1/settings` изменяет реальные поля `client_settings` и валидирует диапазоны/порядок.
- В `/settings` есть owner/admin-friendly simple settings + explainability и write-gate.
- Owner/admin smoke suite покрывает новые поверхности.
- Есть live-check evidence с `decision_meta`, `decision_trace`, outbox status.
- Проверки `ruff`, `pytest`, `next lint` зелёные.

## Checks
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- PR #679 commits + check runs.
- live-check logs:
  - `/tmp/livecheck_owner_wave2_20260215-143909.log`
  - `/tmp/livecheck_owner_wave2_explain_LC-DEDUP-20260215-093909-5a48bffa.log`
- session/report docs в этом пакете.

## Rollback
- Revert коммиты Wave-3 (settings/simple UX + router fix + e2e), не трогая Wave-1/Wave-2.

## No-go
- Нельзя писать в несуществующие поля ORM (silent no-op).
- Нельзя добавлять owner/admin write-path без backend RBAC.
- Нельзя принимать DoD без live-check/trace evidence.

## Risks/блокеры
- `console.py` остаётся крупным модулем; helper-функции нужно держать локальными и тестируемыми.
- В средах без данных explainability должен корректно показывать guidance без ложной точности.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-business-audit-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-business-audit-a1`
- Base ref: `origin/main`
- Merge policy: update existing PR `#679`
- Cleanup: Brain/Top Architect after merge
