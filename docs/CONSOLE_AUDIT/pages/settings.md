# Page: Settings

Route
- `/settings`

UI entry points
- `console-web/src/app/settings/page.tsx`
- Provisioning wizard: `console-web/src/components/ProvisioningWizard.tsx`

Roles
- Read: platform_admin, owner, admin.
- Write: platform_admin, owner, admin.

Header
- Build info shows `NEXT_PUBLIC_BUILD_SHA` + `NEXT_PUBLIC_BUILD_TIME`.
- "Назад в Inbox" link in the header.

Provisioning Wizard
- Embedded at top (accessSection "settings").
- Read-only banner shown when role lacks write access.
- Company card:
  - Existing Company ID input (optional).
  - Name + billing_info guided fields (contract, currency) with apply/load JSON controls and raw JSON textarea.
  - "Создать компанию" button.
- Client card:
  - Existing Client ID input (optional).
  - Client slug + Company ID inputs.
  - "Создать клиента" button; requires company_id.
- Step chips: show status (hint / Готово / Пропущено); locked steps disabled.
- Steps:
  - Филиал (branch_draft): name, slug, timezone, phone; "Создать филиал" / "Обновить филиал".
  - Интеграции: instance_id + "Активировать филиал после сохранения"; "Сохранить instance_id".
  - Команда: create agent (name, role, OIDC subject, branch_id for manager) + created agents list.
  - Telegram: telegram_chat_id input; "Сохранить chat_id"; shows current chat_id.
  - Знания: knowledge_tag input; "Сохранить knowledge_tag".
  - Booking: working_hours guided days/time + JSON details; booking_settings guided duration/buffer + JSON details; "Сохранить booking данные".
  - Go/No-Go: capabilities overrides (domain_slug, channels, providers, booking_mode, knowledge_upload/analytics/auto_learn),
    readiness checklist, "Специалисты добавлены" checkbox, "Сохранить capabilities", effective capabilities summary cards + raw JSON.
- Controls: "Сбросить" resets local form state; "Назад"/"Далее" navigation.
  - "Далее" calls onboarding advance and is blocked when required fields are missing or the step is locked.

Settings cards
- Simple business settings (owner/admin/platform_admin write):
  - Preset profiles:
    - `Быстрый сервис` (5 / 30 / 60)
    - `Сбалансированный` (10 / 45 / 120)
    - `Бережный к команде` (15 / 60 / 180)
  - Manual fields:
    - first reminder (`5-60`)
    - second reminder (`30-180`)
    - escalation timeout (`30-360`)
  - Validation rule: `reminder_1 < reminder_2 < escalation_timeout`.
  - Save action: `PATCH /console/v1/settings`.
- Owner explainability card:
  - business-language impact preview for configured values,
  - guidance to switch profile based on queue pressure visible in `Team KPI`.
- SLA and reminders (read-only from bot_config): reminder_1/2, auto-close, reminders enabled, owner escalation.
- Quiet hours (read-only): enabled, start, end.
- Bot behavior (read-only): tone, autolearn_enabled, booking_enabled.

Telegram connector (client scope)
- Buttons:
  - Verify: `POST /console/v1/telegram/verify` (scope=client).
  - Test: `POST /console/v1/telegram/test` (scope=client).
- Buttons are disabled for read-only roles and show toast with code or error.

Branches section
- Lists branches with instance_id, telegram_chat_id, active status.
- Per-branch buttons:
  - Verify (scope=branch).
  - Send test (scope=branch).
- Verify/test buttons are disabled when telegram_chat_id is missing.

Team link
- Card linking to `/team`.

API endpoints used
- Settings: `GET /console/v1/settings`.
- Settings update: `PATCH /console/v1/settings`.
- Telegram verify/test: `POST /console/v1/telegram/verify|test`.
- Provisioning wizard:
  - `GET/POST /console/v1/admin/companies|clients|branches|agents`.
  - `PATCH /console/v1/admin/branches/{id}`.
  - `GET/PATCH /console/v1/admin/capabilities`.
  - `GET /console/v1/onboarding/status` + `POST /console/v1/onboarding/advance`.

Backend handlers
- `truffles-api/app/routers/console.py` for settings, telegram, admin, onboarding.

Data sources
- `client_settings` (bot config, telegram bot token).
- `branches` (instance_id, telegram_chat_id, is_active).

Related code
- UI: `console-web/src/app/settings/page.tsx`, `console-web/src/components/ProvisioningWizard.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
