# REPORT-2026-02-20-tenants-create-company-audit-contract-a133

- TP: `docs/TASK_PACKAGES/TP-2026-02-20-tenants-create-company-audit-contract-a133.md`
- Branch/worktree: `feat/2026-02-20-tenants-create-company-audit-contract-a133` / `/home/zhan/worktrees/2026-02-20-tenants-create-company-audit-contract-a133`

## Scope

- Fix `500 Internal Server Error` during `POST /console/v1/admin/companies` (Quick Create + ProvisioningWizard path).
- Ensure `company_created` audit event always satisfies DB `audit_events.client_id NOT NULL`.
- Add regression tests.

## Implementation

1) Backend create_company fix
- File: `truffles-api/app/routers/console.py`
- Change:
  - `record_audit_event(...)` now receives:
    - `actor=context.agent`
    - `client_id=context.client.id`
- Result:
  - `company_created` audit event is client-scoped and compatible with DB constraint.

2) Audit ORM contract alignment
- File: `truffles-api/app/services/audit_service.py`
- Change:
  - `AuditEvent.client_id` updated from `nullable=True` to `nullable=False`.
- Result:
  - ORM contract matches runtime DB schema for `audit_events.client_id`.

3) Regression test coverage
- File: `truffles-api/tests/test_console_admin_provisioning.py`
- Added test:
  - `test_create_company_records_client_scoped_audit`
- Assertions:
  - `create_company` succeeds.
  - audit called with `client_id == context.client.id`.
  - audit `event_type == company_created`.
  - `db.commit()` executed.

## Validation

- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/audit_service.py truffles-api/tests/test_console_admin_provisioning.py` -> PASS
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/audit_service.py truffles-api/tests/test_console_admin_provisioning.py` -> PASS
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_tenants_list.py` -> PASS (`45 passed`)

## Impact

- Fixes provisioning breakage for:
  - `console-web/src/app/tenants/page.tsx` (`handleQuickCreateCompany`)
  - `console-web/src/components/ProvisioningWizard.tsx` (`createCompanyMutation`)
- Prevents repeated 500s caused by audit insert violating `client_id NOT NULL`.
