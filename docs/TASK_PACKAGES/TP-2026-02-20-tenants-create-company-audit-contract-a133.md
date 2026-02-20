# TP-2026-02-20-tenants-create-company-audit-contract-a133

- Название/цель: Устранить `500 Internal Server Error` при `Создать компанию` в `/tenants` и `ProvisioningWizard` через выравнивание audit-контракта (без хардкода/обходов) и покрыть регрессию тестами.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`, `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-end2end-tz.md`, `docs/REPORTS/2026-02-20-onboarding-wave678-a132.md`.

- Invariant:
  - Контур `FACT/COLLECT/HANDOFF` и onboarding hard-stop не меняются.
  - Provisioning API остается fail-closed по контрактам и RBAC.
  - Нет client-specific хардкода; только исправление общего контракта audit.

- Scope:
  - Backend fix в `create_company` для корректной записи audit события.
  - Выравнивание ORM-контракта `AuditEvent` с фактической схемой БД для `client_id`.
  - Добавление/усиление unit-тестов на `create_company` и audit-scoped поведение.

- Out of scope:
  - UI redesign вкладки `/tenants`.
  - Изменение бизнес-метрик onboarding throughput.
  - Любые правки provider/outbox runtime логики.

- Touch-list (файлы/таблицы):
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/audit_service.py`
  - `truffles-api/tests/test_console_admin_provisioning.py`
  - (read-only verification) таблица `audit_events` в БД `chatbot`

- Plan (1..N):
  1. Зафиксировать root cause по коду/схеме (`create_company` -> `record_audit_event` -> `audit_events.client_id NOT NULL`).
  2. Внести backend fix: гарантировать `client_id` при `company_created` audit событии.
  3. Выравнять ORM-модель `AuditEvent.client_id` с фактическим DB nullable-контрактом.
  4. Добавить тесты для `create_company` (успех + audit payload/client scope).
  5. Прогнать таргетные проверки (`pytest`, `py_compile`, `ruff`) и собрать evidence.

- DoD:
  - `POST /console/v1/admin/companies` не падает с `500` в штатном flow.
  - В audit событии `company_created` есть валидный `client_id`.
  - Тесты покрывают regression path и проходят локально.
  - `git diff` содержит только согласованные файлы из touch-list.

- Checks:
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/audit_service.py truffles-api/tests/test_console_admin_provisioning.py`
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/services/audit_service.py truffles-api/tests/test_console_admin_provisioning.py`
  - `pytest -q truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_tenants_list.py`

- Evidence:
  - До/после ссылки на проблемный код (`create_company`, `record_audit_event`, ORM contract).
  - Локальный test output по таргетным suite.
  - `git status -sb` + `git diff --stat`.
  - Запись в `docs/REPORTS/...` и `docs/SESSIONS/...` в рамках сессии (STATE обновляет Brain/Top Architect).

- Rollback:
  - `git revert SHA_ФИКСА` для отката изменения в ветке.

- No-go:
  - Не ослаблять RBAC/permission checks в provisioning.
  - Не обходить ошибку ручными DB правками или отключением audit.
  - Не добавлять client-specific исключения.

- Branch / Worktree / Base / Merge policy / Cleanup:
  - Branch: `feat/2026-02-20-tenants-create-company-audit-contract-a133`
  - Worktree: `/home/zhan/worktrees/2026-02-20-tenants-create-company-audit-contract-a133`
  - Base ref: `origin/main`
  - Merge policy: merge commit via PR (no rebase)
  - Cleanup: после merge удалить worktree/branch по стандартному процессу Brain/Top Architect

- Риски/блокеры:
  - Возможные дополнительные call-sites `record_audit_event` без `client_id` при `require_selection=False`.
  - Нужно удержать изменения точечными, чтобы не задеть другие audit потоки.
