# Page: Tenants (Platform Admin)

Route
- `/tenants`

UI entry points
- `console-web/src/app/tenants/page.tsx`

Roles
- Read/write: platform_admin only.

Sections
- Workspace modes:
  - `All` (all zones),
  - `Portfolio` (risk + companies + client portfolio),
  - `Onboarding` (wizard focus),
  - `Change Management` (branch changes focus),
  - `Decommission` (client lifecycle archive/restore focus).
- Decommission center with quick lifecycle filters (`active` / `archived` / `all`).
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
- Edit mode fields: slug, company_id.
- Contract note: `company_id` становится immutable после появления филиалов у клиента (guard в backend + UI lock).
- Save/Cancel buttons in inline editor.
- Lifecycle actions:
  - `Архивировать` / `Восстановить` open inline confirmation block.
  - Reason is required.
  - Explicit confirm checkbox required before action.
  - API uses dedicated endpoints (`archive` / `restore`), status is not editable via `PATCH`.
- "Показать еще" loads next page (cursor-based).
- Save triggers `PATCH /console/v1/admin/clients/{id}`.
- Lifecycle triggers `POST /console/v1/admin/clients/{id}/archive|restore`.

Branch section
- Search input.
- Rows show name/slug/timezone/phone/instance_id/telegram_chat_id/knowledge_tag/is_active.
- "В контекст" sets branch context (keeps company/client).
- Edit mode fields:
  - name, slug, timezone, phone, instance_id, telegram_chat_id, knowledge_tag, is_active.
  - Input-contract panel показывает ожидаемые форматы (`slug`, `timezone`, `phone`, `telegram_chat_id`, `knowledge_tag`).
  - Active филиал requires instance_id.
  - Deactivation or instance_id removal requires confirmation.
- Change management buttons:
  - `Черновик + проверка` -> create draft + validate.
  - `Применить` -> publish validated change.
  - `Откат` -> rollback published change.
  - `Отмена` -> close editor.
- Includes diff preview + validation errors + recent change history.
- "Показать еще" loads next page (cursor-based).
- Change flow triggers:
  - `POST /console/v1/admin/branch-changes/draft`
  - `POST /console/v1/admin/branch-changes/{id}/validate`
  - `POST /console/v1/admin/branch-changes/{id}/publish`
  - `POST /console/v1/admin/branch-changes/{id}/rollback`
- Destructive publish/rollback may require confirmation:
  - `POST /console/v1/confirmations` (action `branch_deactivate`) when destructive.
  - `PATCH /console/v1/admin/branches/{id}` is executed by publish/rollback backend flow.

Context shortcuts
- Buttons labeled \"В контекст\" set localStorage (`console:company_id`, `console:client_id`, `console:branch_id`) and refetch `/console/v1/me`.

Workspace guide
- Верхний guide-блок описывает назначение зон (`Portfolio`, `Onboarding`, `Change Management`, `Decommission`) и pre-Go-Live checklist для операторов.

Provisioning Wizard
- Same wizard as Settings, with `accessSection="tenants"`.
- Steps: филиал → интеграции → команда → Telegram → знания → booking → go/no-go.
- Schema-driven onboarding forms are the primary path for:
  - `billing_info` (contract + ISO currency),
  - `working_hours` (days + time range),
  - `booking_settings` (duration/buffer constraints),
  - `onboarding_contract.purchased` (channels/providers/features).
- Go/No-Go includes:
  - `Domain template preset` (beauty/clinic/legal/ecom) to prefill purchased capabilities.
  - `Readiness score` (required checks completion %) with explicit blockers list.
- `Advanced JSON (expert)` is available as fallback and can be synced both ways with form state.
- See `docs/CONSOLE_AUDIT/pages/settings.md` for step-by-step detail.

API endpoints used
- List: `GET /console/v1/admin/companies|clients|branches`.
- Direct update: `PATCH /console/v1/admin/companies/{id}`; `PATCH /console/v1/admin/clients/{id}`.
- Client lifecycle: `POST /console/v1/admin/clients/{id}/archive|restore`.
- Branch changes: `POST /console/v1/admin/branch-changes/draft|{id}/validate|{id}/publish|{id}/rollback`; `GET /console/v1/admin/branch-changes`.
- Confirmations: `POST /console/v1/confirmations` (branch deactivation).

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_companies`, `list_clients`, `list_branches`.
  - `patch_company`, `patch_client`.
  - `archive_client`, `restore_client`.
  - `draft_branch_change`, `validate_branch_change`, `publish_branch_change`, `rollback_branch_change`.
  - `patch_branch` (called by branch change publish/rollback flow).
  - `create_confirmation`.

Data sources
- `companies`, `clients`, `branches`.
- `console_confirmations` for destructive safeguards.

Related code
- UI: `console-web/src/app/tenants/page.tsx`, `console-web/src/components/ProvisioningWizard.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
