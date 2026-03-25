# Page: Audit

Route
- `/audit`

UI entry points
- `console-web/src/app/audit/page.tsx`

Roles
- Read: platform_admin, owner, admin, support.

Layout
- Header with title and link back to Inbox.
- Table with columns: Time, Event, Actor, Entity, Details.

Event rendering
- Event type badge uses local label map (case_taken, case_resolved, message_sent, settings_changed, login_failed, access_denied).
- Entity label mapping (handover, conversation, message, agent, client, branch).

API endpoints used
- `GET /console/v1/audit?limit=100`.

Backend handlers
- `truffles-api/app/routers/console.py`: `list_audit_events`.

Data sources
- `audit_events` table.

Related code
- UI: `console-web/src/app/audit/page.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
