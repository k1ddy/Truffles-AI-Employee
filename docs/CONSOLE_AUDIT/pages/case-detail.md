# Page: Case detail (deep link)

Route
- `/cases/{id}`

UI entry points
- `console-web/src/app/cases/[id]/page.tsx`
- `console-web/src/components/CaseView.tsx`

Purpose
- Deep link into a specific case while still using the Inbox UI components.

Layout
- Main layout: Chat panel with optional details panel (desktop) or inline details (mobile).
- Toggle for details uses the same `CaseDetailsPanel` as Inbox.

Key elements
- Case header: ID, SLA, status, assigned manager, take/resolve actions.
- Context strip: "Суть запроса" or last inbound message.
- Chat composer: send text/media (if case active and user has write access).
- Quick replies: macros panel above composer.

Behavior
- Uses the same data hooks as Inbox: `useCaseData` (case + messages) with auto refresh.
- Diagnostics tab visibility follows role (support/admin/owner/platform_admin only).
- Details toggle is local to the page; Inbox list pane is not shown here.

API endpoints used
- `GET /console/v1/cases/{id}`
- `GET /console/v1/cases/{id}/messages`
- `POST /console/v1/cases/{id}/take|resolve`
- `POST /console/v1/conversations/{conversation_id}/messages`
- `POST /console/v1/conversations/{conversation_id}/messages/media`
- `GET/POST/PATCH /console/v1/inbox/macros`

Related code
- UI: `console-web/src/components/CaseView.tsx`, `CaseConversation.tsx`, `CaseDetailsPanel.tsx`, `ChatInterface.tsx`, `InboxMacros.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
