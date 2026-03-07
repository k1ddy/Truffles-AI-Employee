# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE20-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE21-A1

## Название/цель
Пересобрать information architecture панели `Заявки`, чтобы first-screen логически разделял `операционную очередь` и `историю/архив` и был удобен для менеджеров и администраторов без скрытых режимов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: split allowed and expected: `Part A operator mode contract`, `Part B history/archive rail`
- `Cleanup`: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:knowledge.hubspot.com help desk manage tickets in help desk table split board search filters closed tickets`
- **Date/time (local):** `2026-03-07T10:05:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/search-for-tickets-in-help-desk`
- **Ready solutions found:** first-screen operator layouts keep `search/status/owner` visible, while the rest of filters live in a side drawer or secondary filter layer.
- **Decision (`reuse/integrate/build`):** `integrate` — retain current inbox route and split workspace, but rebuild the left rail around operator modes and explicit filter hierarchy.
- **Rejected options:** leaving `Закрытые/Все` inside advanced filters; mixing queue views and archive filters in one line.
- **Source quality:** high-signal primary source = official HubSpot docs.

## Root cause (mandatory)
- **Symptom:** `Заявки` do not give a stable first-screen model for working with open, closed, and historical cases.
- **Minimal reproduction:** try to find a closed or old case from the same surface where you triage new escalations.
- **Evidence:** `console-web/src/components/CaseList.tsx:255`, `console-web/src/components/CaseList.tsx:1278`, `console-web/src/lib/inbox-case-filters.ts:70`.
- **Five Whys:** open queue and history are mixed; first-screen controls do not represent the actual business mode; users cannot infer what mode they are in.
- **Root cause statement:** the left rail lacks explicit operator modes and therefore hides critical history/archive access behind a secondary control.
- **Fix mechanism:** add explicit mode scope, separate queue views from history filters, redesign cards and filter drawer by mode.

## Invariant
- Existing case selection and workspace split must remain intact.
- Queue views stay only where they are semantically valid: open-mode.
- No hidden path to basic history access.

## Scope
- `Part A`: first-screen mode scope `Открытые / Закрытые / Все`.
- `Part B`: filter drawer + history/archive cards + mode-aware sort/filter contract, including backend `resolved_at` sorting and resolved-date filtering.

## Out of scope
- Case/booking semantic synchronization.
- Bot/action-state redesign.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/inbox-case-filters.ts`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`

## DoD
- `Открытые / Закрытые / Все` visible on first screen.
- Queue views only appear for `Открытые`.
- `Закрытые` and `Все` usable without `Уточнить очередь`.
- Cards and sorting differ correctly between open-mode and history-mode.
- `Закрытые` use `resolved_at` as the default timeline sort and never fake it with `created_at`.
- Resolved-date filters emit a dedicated history contract and do not silently reuse open-queue `date_from/date_to`.

## Checks
- `pytest -q truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_console_openapi_calendar_contract.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_console_openapi_calendar_contract.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-case-filters.ts --file src/lib/inbox-workspace.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## Evidence
- Updated screenshot for `Заявки` rail.
- Deterministic assertions for open/closed/all mode transitions.
- Contract evidence for `resolved_from/resolved_to` and `sort_by=resolved_at`.

## Rollback
- revert bounded Wave20 PR

## No-go
- Keep archive/history behind advanced toggle.
- Reuse queue chips in history mode.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: case-booking semantic chain still handled in follow-up wave.
- `Why not in this block`: this wave is only about panel IA and mode separation.
- `Risk if deferred`: without Wave21, history may still not fully explain booking-related outcomes.
- `Linked follow-up Task Package(s)`: `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`, `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`.
- `Expiry/trigger to stop deferral`: if open/closed/all mode lands but booking context still feels detached, Wave21 becomes mandatory immediately.

## Next-block contract (mandatory)
- `Next block objective`: reconnect the redesigned inbox panel with bot-origin semantics and booking lifecycle.
- `First deterministic check command`: `cd console-web && rg -n "resolved_at|resolved_from|resolved_to|Открытые|Закрытые|Все" src/components/CaseList.tsx truffles-api/app/routers/console.py`
- `Blocked-by conditions`: none for Wave20 closure; Wave21 begins only after Wave20 PR/merge evidence is green.
- `Owner role for closure`: Brain / Top Architect.
