# Page: Tenants (Platform Admin)

Route
- `/tenants`

UI entry points
- `console-web/src/app/tenants/page.tsx`

Roles
- Read/write: platform_admin only.

Sections
- Companies list with search and inline edit.
- Clients list with search and inline edit.
- Branches list with search and inline edit.
- Provisioning Wizard embedded at the bottom (`accessSection="tenants"`).
- Header shows current context (company/client/branch IDs).

Company section
- Search input.
- Rows show name + id.
- Selected row shows "Выбрана"; "В контекст" sets company context and clears client/branch.
- Edit mode fields: name, billing_info JSON.
- Save/Cancel buttons in inline editor; billing_info validates JSON.
- "Показать еще" loads next page (cursor-based).
- Save triggers `PATCH /console/v1/admin/companies/{id}`.

Client section
- Search input.
- Rows show slug + company_id.
- Selected row shows "Выбран"; "В контекст" sets client context and clears branch.
- Edit mode fields: slug, company_id, status.
- Save/Cancel buttons in inline editor.
- "Показать еще" loads next page (cursor-based).
- Save triggers `PATCH /console/v1/admin/clients/{id}`.

Branch section
- Search input.
- Rows show name/slug/timezone/phone/instance_id/telegram_chat_id/knowledge_tag/is_active.
- "В контекст" sets branch context (keeps company/client).
- Edit mode fields:
  - name, slug, timezone, phone, instance_id, telegram_chat_id, knowledge_tag, is_active.
  - Active филиал requires instance_id.
  - Deactivation or instance_id removal requires confirmation reason input.
- Save/Cancel buttons in inline editor.
- "Показать еще" loads next page (cursor-based).
- Save triggers:
  - `POST /console/v1/confirmations` (action `branch_deactivate`) when destructive.
  - `PATCH /console/v1/admin/branches/{id}`.

Context shortcuts
- Buttons labeled \"В контекст\" set localStorage (`console:company_id`, `console:client_id`, `console:branch_id`) and refetch `/console/v1/me`.

Provisioning Wizard
- Same wizard as Settings, with `accessSection="tenants"`.
- Steps: филиал → интеграции → команда → Telegram → знания → booking → go/no-go.
- See `docs/CONSOLE_AUDIT/pages/settings.md` for step-by-step detail.

API endpoints used
- List: `GET /console/v1/admin/companies|clients|branches`.
- Update: `PATCH /console/v1/admin/companies/{id}`; `PATCH /console/v1/admin/clients/{id}`; `PATCH /console/v1/admin/branches/{id}`.
- Confirmations: `POST /console/v1/confirmations` (branch deactivation).

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_companies`, `list_clients`, `list_branches`.
  - `patch_company`, `patch_client`, `patch_branch`.
  - `create_confirmation`.

Data sources
- `companies`, `clients`, `branches`.
- `console_confirmations` for destructive safeguards.

Related code
- UI: `console-web/src/app/tenants/page.tsx`, `console-web/src/components/ProvisioningWizard.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
