# Universal Control Plane v1 — Phase 2 Report (slice 1, a500)

Date
- 2026-02-22

Phase goal
- Harden tenant hierarchy governance: `company/client` write and client lifecycle actions are platform-admin-only.

FACT baseline (before changes)
- `create/update company`, `create/update/archive/restore client` were gated by generic provisioning write permission and could pass for non-platform roles depending on membership scope.
- Phase 1 already locked capabilities write to platform-admin-only, but tenant hierarchy write contract remained broader.

Contract delta (Phase 2 slice 1)
- Added explicit `_require_platform_admin(context)` gate to:
  - `POST /admin/companies`
  - `PATCH /admin/companies/{company_id}`
  - `POST /admin/clients`
  - `PATCH /admin/clients/{client_id}`
  - `POST /admin/clients/{client_id}/archive`
  - `POST /admin/clients/{client_id}/restore`
- Canon update in `SPECS/CONTROL_PLANE.md` for tenant hierarchy write restriction.

Implemented changes
- `truffles-api/app/routers/console.py`
  - tightened tenant hierarchy write messages.
  - injected explicit platform-admin gate for six handlers listed above.
- `truffles-api/tests/test_console_admin_provisioning.py`
  - added:
    - `test_create_company_requires_platform_admin`
    - `test_update_client_requires_platform_admin`
    - `test_restore_client_requires_platform_admin`
  - kept existing success-path checks for platform-admin role.
- `SPECS/CONTROL_PLANE.md`
  - added canonical note that `/admin/companies*` and `/admin/clients*` write operations are platform-admin-only.

Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_admin_provisioning.py`
  - pass
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "platform_admin or capabilities or tenant"`
  - pass (`10 passed, 10 deselected`)
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
  - pass (`20 passed`)

Evidence
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-a500.md`

FACT
- Tenant hierarchy write boundary is now fail-closed to platform-admin.
- Deterministic tests for provisioning scope are green after hardening.

GAP / residual risks
- Remaining `/admin/*` provisioning actions (e.g. branch change, memberships, branch-level lifecycle tooling) still need role contract normalization in later Phase 2 slices.
- No live-check needed for this slice because changes are deterministic console RBAC checks.

Phase 2 slice 1 verdict
- Passed.
