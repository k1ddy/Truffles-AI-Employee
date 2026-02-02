# Report: Web Console fact audit (implemented only)

Scope
- Implemented UI + API only (no canon comparison).
- Tenant: demo_salon.
- Roles validated: platform_admin (admin creds), manager, support.

Evidence (runtime)
- Demo_salon context: `/tmp/console_web_fact_20260201/context_demo_salon.json`.
- Role evidence:
  - platform_admin `/me`: `/tmp/console_web_fact_20260201/me_admin_raw.json`.
  - manager `/me`: `/tmp/console_web_fact_20260201/me_manager_raw.json`.
  - support `/me`: `/tmp/console_web_fact_20260201/me_support_raw.json`.
- Inbox (admin):
  - case list: `/tmp/console_web_fact_20260201/cases_list_admin.json`.
  - case detail: `/tmp/console_web_fact_20260201/case_detail_admin.json`.
  - case messages: `/tmp/console_web_fact_20260201/case_messages_admin.json`.
  - macros: `/tmp/console_web_fact_20260201/macros_admin.json`.
- Settings/Team (admin):
  - settings: `/tmp/console_web_fact_20260201/settings_admin.json`.
  - agents: `/tmp/console_web_fact_20260201/agents_admin.json`.
- Knowledge (admin):
  - current: `/tmp/console_web_fact_20260201/knowledge_current_admin.json`.
  - history: `/tmp/console_web_fact_20260201/knowledge_history_admin.json`.
- Calendar (admin):
  - specialists: `/tmp/console_web_fact_20260201/calendar_specialists_admin.json`.
  - bookings: `/tmp/console_web_fact_20260201/calendar_bookings_admin.json`.
- Ops/Audit (admin):
  - health: `/tmp/console_web_fact_20260201/health_admin.json`.
  - metrics daily: `/tmp/console_web_fact_20260201/metrics_admin.json`.
  - telegram health: `/tmp/console_web_fact_20260201/telegram_health_admin.json`.
  - outbox: `/tmp/console_web_fact_20260201/outbox_admin.json`.
  - audit: `/tmp/console_web_fact_20260201/audit_admin.json`.
- RBAC probes:
  - manager settings denied: `/tmp/console_web_fact_20260201/settings_manager.json`.
  - support settings denied: `/tmp/console_web_fact_20260201/settings_support.json`.
  - support audit allowed: `/tmp/console_web_fact_20260201/audit_support.json`.
- UI routes (public HTML + chunks): `/tmp/console_web_fact_20260201/ui_*.status`, `/tmp/console_web_fact_20260201/ui_*_chunks.txt`.

Findings (bugs/UX issues)
1) Case return resolves instead of returning to bot.
   - `POST /console/v1/cases/{case_id}/return` calls `state_manager_resolve` and sets `resolution_notes` to "Returned to bot".
   - This closes the case (resolved) rather than returning it to pending/bot ownership.
   - Code: `truffles-api/app/routers/console.py:1777`, `truffles-api/app/routers/console.py:1837`, `truffles-api/app/routers/console.py:1849`.

2) Branch access missing for case messages and manager sends.
   - `GET /console/v1/cases/{case_id}/messages` checks only client_id; no branch restriction check.
   - `POST /console/v1/conversations/{conversation_id}/messages` and `/messages/media` also skip branch gating.
   - Impact: branch-restricted roles can access or send cross-branch if they know IDs.
   - Code: `truffles-api/app/routers/console.py:1919`, `truffles-api/app/routers/console.py:1935`, `truffles-api/app/routers/console.py:2218`, `truffles-api/app/routers/console.py:2392`.

3) Inbox "Load more" replaces list instead of appending.
   - UI sets cursor and replaces `data.items`; no accumulation state.
   - User loses previous page when loading more.
   - Code: `console-web/src/components/CaseList.tsx:172`, `console-web/src/components/CaseList.tsx:216`, `console-web/src/components/CaseList.tsx:233`.

4) SLA sort is client-side on a single page.
   - The API query does not include `sort_by=sla`; only activity/created_at are sent.
   - SLA ordering is applied after fetch on the current page only.
   - Code: `console-web/src/components/CaseList.tsx:185`, `console-web/src/components/CaseList.tsx:218`.

5) Calendar default date uses UTC conversion (potential day shift).
   - `formatDate` uses `toISOString()` which can shift the date for local timezones.
   - Risk: calendar opens on wrong day near local midnight.
   - Code: `console-web/src/app/calendar/page.tsx:80`.

Notes
- Knowledge and macros require branch selection; branch id used from settings in evidence.
- Admin credentials map to `platform_admin` role in `/me` response.
