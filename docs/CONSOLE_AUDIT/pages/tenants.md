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
- View preset:
  - `Operator` (упрощённый операционный контур),
  - `Platform` (расширенные technical details / IDs / trace emphasis).
- `Action Queue` with prioritized operational tasks and direct CTA (`context`, `cases`, `integrations`, workspace switch).
- Decommission center with quick lifecycle filters (`active` / `archived` / `all`).
- Companies list with search and inline edit.
- Clients list with search and inline edit.
- Branches list with search and inline edit.
- Provisioning Wizard embedded at the bottom (`accessSection="tenants"`).
- Header shows current context (company/client/branch IDs).
- Onboarding workspace hint now includes explicit verify loop: after execute in `Workspace`, operator is prompted to verify in `Ops` and return to `Tenants`.

Company section
- Search input.
- Rows show name + id.
- Selected row shows "Выбрана"; "В контекст" sets company context and clears client/branch.
- Edit mode fields: name (+ optional advanced `billing_info` JSON in expert details).
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
  - `Архивировать` / `Восстановить` open lifecycle modal.
  - Modal includes impact preview (client/company, lifecycle transition, branch impact).
  - Modal includes mandatory pre-submit checklist (context/impact/owner alignment).
  - Reason is required.
  - Explicit confirm checkbox required before action.
  - API uses dedicated endpoints (`archive` / `restore`), status is not editable via `PATCH`.
  - Submit button is disabled until reason + checklist + confirm are complete.
  - Client row shows persistent lifecycle timeline:
    - session actions are persisted in localStorage (`tenants:client-lifecycle-audit:v2`);
    - selected client is enriched by API audit feed (`GET /console/v1/audit`, `entity_type=client`, `entity_id=<selected_client>`).
  - Timeline supports filter by result (`all` / `success` / `error`) and manual API refresh.
  - Timeline entries include source tag (`session`/`api`) + result/reason/time/trace_id (if present).
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
- Branch edit shows impact preview before publish/rollback (activation transition + confirmation requirement hint).
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

Operational KPI panel
- Panel `Операционные KPI` (Portfolio/All in `active` lifecycle mode) aggregates proxy-metrics from:
  - `clients summary`,
  - `fleet attention summary`,
  - recent `branch changes` (window: last 100).
- KPI cards:
  - onboarding coverage (proxy),
  - go-live readiness (proxy),
  - service stability,
  - decommission share,
  - publish failure rate (proxy),
  - rollback share (proxy),
  - blocked signals count.
- UI explicitly labels these values as proxy metrics and shows branch-change window counters.
- KPI threshold model is embedded in UI (`ok` / `warn` / `critical`) with per-metric rules and visual status chips.
- Threshold drill-down section:
  - explicit threshold condition (`warn`/`critical`) per KPI,
  - reason line (why breach / normal),
  - action CTA that opens relevant workspace area (`Portfolio`/`Onboarding`/`Change Management`/`Decommission`).
- Export/report controls:
  - `Экспорт JSON`,
  - `Экспорт CSV`,
  - `Weekly snapshot` (persisted in localStorage `tenants:operational-weekly-snapshots:v1`).
- Weekly snapshots panel stores capped history and shows quick delta for change-failure metric vs previous snapshot.
- Alert hooks panel:
  - generates operator payload (`severity`, `breaches`, summary counters),
  - supports payload copy,
  - operator-triggered `metrics_snapshot` job dry-run/execute via `/console/v1/ops/jobs/run`.

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
  - `Readiness Timeline` (step-by-step status + missing requirements).
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
