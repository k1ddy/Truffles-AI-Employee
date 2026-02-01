# Page: Inbox (Cases)

Routes
- `/` (inbox list + conversation + details)
- `/cases/{id}` (loads inbox with preselected case)

UI entry points
- `console-web/src/app/page.tsx`
- `console-web/src/app/cases/[id]/page.tsx`
- `console-web/src/components/InboxView.tsx`

Roles
- Read: platform_admin, owner, admin, manager, support.
- Write (take/resolve/send/macros): platform_admin, owner, admin, manager.
- Diagnostics tab visible to: platform_admin, owner, admin, support.

Layout
- 3-pane layout on desktop: Queue (left), Chat (center), Details (right toggle).
- Mobile: details open as right-side overlay.

Queue (CaseList)
- Component: `console-web/src/components/CaseList.tsx`.
- Default filters: `status=open`, sort=activity, limit=20.
- Search input: "Телефон / имя / ID" (debounced 300ms).
- Filters:
  - Status: Открытые / Все / Ожидает / В работе / Закрыта.
  - Sort: Активные / Новые / Срочные (SLA).
  - Assigned: "Мои" toggle.
  - Advanced (expandable): Branch, date from/to, "Есть ошибки", "В очереди".
- Refresh button: re-fetches cases.
- Load more button when `has_more`.
- Auto refresh: every 10s (foreground only).

Case rows (compact view)
- Shows customer name/phone, status badge, preview, branch, last activity, SLA.
- Tags: "Нужно ответить", "На связи", "Ошибка".
- Click selects case and routes to `/cases/{id}`.

Conversation (CaseConversation)
- Component: `console-web/src/components/CaseConversation.tsx`.
- Header:
  - Case ID, SLA badge, status, assigned manager, needs_reply tag.
  - "Детали" / "Скрыть детали" toggle button (opens/closes Details panel).
  - Actions:
    - "Взять заявку" (when status pending + write access).
    - "Закрыть заявку" (when status active + write access).
    - Read-only roles see "Только просмотр".
- Context strip: "Суть запроса" or "Последнее сообщение" + last inbound time.

Chat (ChatInterface)
- Component: `console-web/src/components/ChatInterface.tsx`.
- Messages list (oldest first); roles: Клиент / Менеджер / Бот.
- Media rendering:
  - photo: inline image + open link.
  - audio: audio player + open link.
  - document: label + open link.
- Composer:
  - Text area with auto-grow (min 44px, max 220px).
  - Enter (no shift) sends; Shift+Enter inserts newline.
  - Escape clears input + attachments.
  - Attachments (📎): image/audio/document; video blocked.
  - Accepts: image/*, audio/*, .pdf, .doc/.docx, .xls/.xlsx, .txt.
  - Attachment preview shows label/name/size + "Убрать" button.
  - Text area doubles as media caption when a file is attached.
  - Send button disabled when empty and no attachment.
  - When sending is disabled (not active/assigned), composer shows "Возьмите заявку, чтобы отвечать клиенту".
- Quick replies (macros) appear above composer.

Details panel (CaseDetailsPanel)
- Tabs: Контекст / Заявка / Консультант / Диагностика (role-gated).
- Контекст: client name/phone, remote_jid, context summary + raw message.
- Заявка: status, SLA, channel, trigger, last in/out, delivery flags.
- Консультант: assigned manager, status, last outbound.
- Диагностика:
  - decision_meta summary groups (action/intent/source/policy/etc).
  - decision_trace stages list and key stage tags.
  - Telegram delivery trail + links.

Quick replies (Macros)
- Component: `console-web/src/components/InboxMacros.tsx`.
- Modes: Use (select macro) and Manage (create/update/toggle active).
- Scopes: personal or team.
- Chips show up to 6 active macros; selecting appends text into composer.
- Manage view includes search filter, edit/update, and active/inactive toggle.
- Error handling includes selection-gate hints (company/client/branch).

API endpoints used (Console API)
- List cases: `GET /console/v1/cases`.
- Case detail: `GET /console/v1/cases/{id}`.
- Case messages: `GET /console/v1/cases/{id}/messages`.
- Take/resolve: `POST /console/v1/cases/{id}/take|resolve`.
- Send text: `POST /console/v1/conversations/{conversation_id}/messages`.
- Send media: `POST /console/v1/conversations/{conversation_id}/messages/media`.
- Macros: `GET/POST/PATCH /console/v1/inbox/macros`.

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_cases`, `get_case`, `get_case_messages`, `take_case`, `resolve_case`.
  - `send_manager_message`, `send_manager_media`.
  - `list_inbox_macros`, `create_inbox_macro`, `update_inbox_macro`.

Data sources
- `handovers`, `conversations`, `messages`, `users` (case list + details).
- `outbox_messages` (delivery flags + ops counts).
- `console_macros` (quick replies).
- `conversations.context.decision_trace` (diagnostics).

System interactions
- Take/resolve uses `state_service` and records audit + Telegram sync.
- Send text/media:
  - WhatsApp via `chatflow_service` and `process_console_media_upload`.
  - Telegram echo when topic exists (`resolve_telegram_routing`, `TelegramService`).
- Idempotency enforced via `console_idempotency`.

Related code
- UI: `console-web/src/components/InboxView.tsx`, `CaseList.tsx`, `CaseConversation.tsx`, `ChatInterface.tsx`, `CaseDetailsPanel.tsx`.
- Backend: `truffles-api/app/routers/console.py`, `app/services/state_service.py`, `app/services/manager_message_service.py`.
