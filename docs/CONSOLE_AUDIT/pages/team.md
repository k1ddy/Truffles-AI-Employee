# Page: Team

Route
- `/team`

UI entry points
- `console-web/src/app/team/page.tsx`

Roles
- Read: platform_admin, owner, admin.
- Write (users + telegram link): platform_admin, owner, admin.

Header actions
- "Knowledge Studio" link when role has knowledge read access.
- "Provisioning" link to `/settings` when role has settings read access.

Tabs
- Пользователи (users)
- Специалисты (specialists)
- Tab buttons are pills with hint text (role/availability).

Users tab
- Data source:
  - If write access: `GET /console/v1/agents` (full list + identities).
  - If read-only: `GET /console/v1/settings` (agent list subset).
- Summary cards: total users, active users, owner/manager counts.
- "Открыть provisioning" link shown for write roles; read-only shows a hint.
- Cards per agent:
  - Role badge, active indicator, branch label.
  - Telegram status (connected or not).
  - "Подключить Telegram" / "Переподключить" button (creates link token).
  - Link token card: token, deep link, `/start <token>` instructions, expiration timestamp.
- Error/empty states include "Повторить" reload button.

Specialists tab
- Data source: `GET /calendar/specialists` (optional branch filter).
- Branch selector appears when multiple branches.
- Summary cards: specialists count, services count, access level.
- Specialist cards: name, branch, active badge, services list.
- Error/empty states: "Специалисты не найдены" and loading placeholder.

API endpoints used
- Agents list: `GET /console/v1/agents`.
- Telegram link: `POST /console/v1/agents/{id}/telegram/link`.
- Settings (fallback list): `GET /console/v1/settings`.
- Specialists: `GET /calendar/specialists`.

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_agents`, `link_agent_telegram`, `get_settings`.
- `truffles-api/app/routers/calendar.py`: `list_specialists`.

System interactions
- Telegram link token uses `agent_link_service` and `TelegramService` bot lookup.
- Audit events recorded on link creation.

Related code
- UI: `console-web/src/app/team/page.tsx`.
- Backend: `truffles-api/app/routers/console.py`, `truffles-api/app/routers/calendar.py`.
