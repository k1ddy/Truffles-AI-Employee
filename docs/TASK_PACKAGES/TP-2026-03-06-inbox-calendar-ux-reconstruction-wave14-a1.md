# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE14-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE14-CLOSEOUT-A1

## Название/цель
Перевести queue views в `Заявках` с локальных predicate/hints на server-owned contract: менеджер должен видеть реальные серверные выборки и реальные counts по рабочим view, а не «только в текущей выборке» из догруженных карточек.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one bounded PR after deterministic checks + local queue evidence
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Wave13` merged via `PR #935` on `2026-03-06`; queue cards now show a clearer business status, but queue views still are not fully server-owned.
- In `CaseList`, `needs_reply` and `delivery` still depend on `localPredicate`, and the UI warns that the view only applies to the currently loaded selection.
- This means queue counts and slices are still approximation-based when the manager has not loaded the whole queue.
- The existing operator goal is already clear: same tabs, same workspace, but more trustworthy queue semantics at scale.

## One web search (mandatory before implementation)
- **Query (exact):** `Atlassian Jira Service Management queue best practices official`
- **Date/time (local):** `2026-03-06T20:44:00+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
- **Ready solutions found:** queue views at scale must be stable, explicit, and backed by server-side filtering rather than client-side approximation over a partial page.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the current queue UI, but move view semantics to backend `queue_view` filtering and remove approximation hints from the operator flow.
- **Rejected options:** keep local predicates and only tweak copy; add a second queue screen; add counts without fixing the underlying selection semantics.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** the queue looks cleaner after Wave13, but some view slices are still not trustworthy on large queues.
- **Minimal reproduction:** open `Заявки`, switch to `Требуют ответа` or `Проблемы доставки`, and observe that the UI warns the view only filters the currently loaded cards.
- **Evidence:** `CaseList.tsx` still uses `localPredicate`/`localHint` for queue views instead of server-owned query semantics.
- **Five Whys:**
  1. Why are view counts approximate? Because the queue slice is applied after pagination on the client.
  2. Why is that risky? Because the manager can believe a queue is empty or small when only the current page was filtered.
  3. Why does this persist after Wave13? Because Wave13 fixed status readability, not queue selection ownership.
  4. Why is this a business issue? Because queue prioritization must remain trustworthy when volume grows.
  5. Why fix it now? Because the left rail is now visually simpler, so the next bottleneck is the correctness of queue slices themselves.
- **Root cause statement:** queue view semantics still live partially in the frontend over paginated data, so the operator sees approximated slices instead of a server-owned queue contract.
- **Fix mechanism:** add backend `queue_view` filtering for operator slices and wire the current queue views to that contract, removing client-only hints/predicates from the main flow.

## Reuse-first plan (mandatory)
- **Reuse:** existing `GET /cases`, queue signal/business status derivation, current queue view controls, existing `inspect_case` mock lane.
- **Integrate:** add a bounded `queue_view` query contract and reuse current view buttons instead of creating a new queue IA.
- **Build only if needed:** one parser + one SQL/filter helper + queue view wiring; no new top-level route.

## Invariant
- Keep the current `Заявки` workspace; no new tab/screen.
- Queue view semantics must stay understandable in plain business copy.
- Do not regress existing manual filters, owner filters, SLA sorting, or bulk selection.
- If a queue view becomes server-owned, the UI must stop describing it as local-only.

## Scope
- `Part A backend queue-view contract`:
  - add `queue_view` query param to `GET /cases`;
  - support bounded operator views needed by current UI;
  - keep counts/pagination consistent with the selected queue view.
- `Part B frontend queue migration`:
  - wire current queue view buttons to the backend contract;
  - remove local-only hinting for migrated views;
  - update labels so the operator sees business-facing view names.

## Out of scope
- Full analytics dashboard by queue view.
- New routing automation or presence/capacity logic.
- Separate admin queue builder UI.
- Live no-mocks mutation validation for Wave12 beyond the already documented safe-case blocker.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Обновить session canon после merge `PR #935` и открыть Wave14 как новый active block.
2. Добавить backend `queue_view` contract и deterministic coverage.
3. Перевести queue views в `CaseList` на backend-owned semantics и убрать local-only hints.
4. Обновить inspect-case lane, screenshots и canon.

## DoD
- `GET /cases` supports bounded server-owned queue views used by the inbox UI.
- Current queue buttons use server filtering instead of `localPredicate` for migrated views.
- Queue counts reflect the active server view, not only the loaded page.
- Deterministic checks are green and queue flow remains intact.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file src/lib/api-client.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for touch-list.
- Targeted pytest/OpenAPI outputs.
- Local Playwright output.
- Updated queue screenshot.
- Session log with Wave14 progress.

## Progress update
- Backend implemented: `GET /cases` now accepts `queue_view` and applies bounded server-side queue slices on the same filtered/count query.
- Frontend implemented: `CaseList` queue views now use server-owned semantics, `waiting_client` and `snoozed` are explicit operator views, and legacy stored `paused` state is normalized to `waiting_client`.
- Deterministic coverage implemented: helper tests cover `queue_view` parsing, OpenAPI contract checks expose the new param, and `inspect_case` asserts that queue views reduce the visible row set to the server-backed slice.
- Current closure state: code + deterministic checks are green locally; next step is PR.

## Release safety (mandatory)
- **Rollout:** bounded queue-contract/UI change only.
- **Go/no-go:** merge only if queue view switching, filters, counts, and bulk selection still behave coherently.
- **Rollback:** revert the bounded Wave14 commit/PR and regenerate API types if needed.

## Rollback
- `git revert REVISION_SHA`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`

## No-go
- Keeping server and client queue semantics different for the same view name.
- Adding new queue views without a real backend contract.
- Leaving the local-only warning for a view that is already server-owned.
- Expanding this block into queue analytics or routing automation.

## Риски/блокеры
- Queue-view SQL rules can drift from business-status logic if duplicated carelessly.
- Some legacy persisted `activeViewId` values may need normalization.
- `queue_view` must not break owner filters or branch-scoped access rules.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no aggregate per-view counters across the whole queue bar; no end-user status naming; no presence-aware routing.
- `Why not in this block`: this block fixes queue-slice correctness before any analytics/maturity layer.
- `Risk if deferred`: even a visually clean rail would still give approximate queue slices on large datasets.
- `Linked follow-up Task Package(s)`: `TBD Wave14 closeout / potential Wave15 if queue counters or server-side business-status reporting become necessary`.
- `Expiry/trigger to stop deferral`: if managers still need a local-only legend after this block, the queue contract is still incomplete and follow-up becomes mandatory.

## Next-block contract (mandatory)
- `Next block objective`: open and merge the bounded Wave14 PR, then decide whether queue counters/reporting need a separate follow-up.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: queue-view rules must stay aligned with existing branch access, owner filters, and bulk-selection flow.
- `Owner role for closure`: Brain / Top Architect.
