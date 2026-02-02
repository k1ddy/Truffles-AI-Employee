# Web Console UX backlog (implemented issues)

Scope
- Only implemented behavior (code-backed).
- Canon gaps live in `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.

Sources
- `docs/REPORTS/2026-02-01-console-web-fact-audit.md`
- `console-web/src/**` (UI)
- `truffles-api/app/routers/console.py` (API)

Resolved findings (fixed)
- Return-to-bot resolved state (PR #493) — CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21575689168.
- Branch gating for messages/media (PR #494) — CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21576082316.
- Inbox load more append (PR #495) — CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21575902168.
- SLA sort server-side (PR #496) — CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21575159164.
- Calendar default date local (PR #497) — CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21578194809, build `4614530` (`2026-02-01T00:01:02Z`).

Open UX debt / code smells (implemented)

| ID | Area | Issue | Impact | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| UX-01 | Calendar | Error banner renders raw JSON payload for specialists load failure. | Non-user-friendly error output, potential data leakage. | `console-web/src/app/calendar/page.tsx` (specialistsError `<pre>`). | Open |
| UX-02 | Calendar | Date input locked to `min=today`; past bookings cannot be viewed from UI. | No historical review/reschedule from calendar UI. | `console-web/src/app/calendar/page.tsx` (`min={formatDate(new Date())}`). | Open |
| UX-03 | Inbox | Auto-refresh every 10s without pause/indicator. | Queue can change while scrolling or selecting a case. | `console-web/src/components/CaseList.tsx` (`refetchInterval: 10000`). | Open |
| UX-04 | Settings / Provisioning | JSON-only inputs for `billing_info`, `working_hours`, `booking_settings`. | High error rate; no guided forms or inline validation. | `console-web/src/components/ProvisioningWizard.tsx` (JSON textareas + `parseOptionalJson`). | Open |
| UX-05 | Settings / Provisioning | Effective capabilities displayed as raw JSON block. | Hard to read/verify changes; no schema help. | `console-web/src/components/ProvisioningWizard.tsx` (effective JSON preview). | Open |

Related inventory docs
- `docs/CONSOLE_AUDIT/pages/inbox.md`
- `docs/CONSOLE_AUDIT/pages/calendar.md`
- `docs/CONSOLE_AUDIT/pages/settings.md`
