# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-LIVE-VALIDATION-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-CLOSEOUT-A1

## Название/цель
Ввести server-owned business status для заявок и убрать лишний badge-noise в `Заявках`: менеджер должен видеть один понятный рабочий статус заявки, отдельный next action по SLA и текстовую привязку к владельцу без технической мешанины из raw status/human lock/error chips.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one bounded PR after deterministic checks + local-first visual evidence
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Wave11` already widened and regrouped the left rail, but the compact queue still renders several competing pills (`status`, `SLA`, `owner`, `pause`, `error`, `priority`, `recent dialog`) on the same card.
- `Wave12 live validation` now has a precise blocker classification: the live no-mocks lane cannot safely prove the routing mutation without an explicit active `INSPECT_CASE_LIVE_CASE_ID`; fallback-only runs are no longer misreported as mutation evidence.
- Backend already computes action-oriented queue signals (`sla_action_state`, `attention_reason`, `priority_tier`) but there is no normalized business status contract for the operator lifecycle.
- Current UI still exposes raw `handover.status` (`pending/active/resolved`) as the main badge, which is too technical and too coarse for daily queue work.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk custom ticket statuses official documentation`
- **Date/time (local):** `2026-03-06T20:24:00+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4412575861018-Creating-custom-ticket-statuses`
- **Ready solutions found:** mature helpdesks keep custom statuses anchored to a stable lifecycle category, use an explicit agent-facing name, and optionally separate end-user wording.
- **Decision (`reuse/integrate/build`):** `integrate` — derive a bounded set of server-owned operator statuses from the existing case lifecycle and queue signals, then simplify the UI around that contract instead of piling more one-off badges into the rail.
- **Rejected options:** keep raw `pending/active/resolved` as the main operator status; invent front-only copy with no backend contract; add another queue lane without reducing current chip noise.
- **Source quality:** high-signal primary source = official Zendesk documentation.

## Root cause (mandatory)
- **Symptom:** even after Wave11, the left rail and case header still feel crowded and harder to parse than they should.
- **Minimal reproduction:** open `Заявки`, look at the compact queue card or case header, and compare the visible signals: one raw status badge, one SLA badge, one owner badge, and several optional technical pills (`Пауза`, `Ошибка`, `Недавний диалог`, priority).
- **Evidence:** current `CaseList.tsx`, `CaseConversation.tsx`, and `labels.ts` still compose multiple partially overlapping chips from different semantic layers.
- **Five Whys:**
  1. Why is the rail still noisy? Because business status and next action are not separated cleanly.
  2. Why is raw status insufficient? Because `pending/active/resolved` does not explain whether the team waits on the client, deferred the case, or needs to fix delivery.
  3. Why do extra pills accumulate? Because each sub-state was surfaced as its own visual patch.
  4. Why does that hurt business logic? Because the manager has to infer one working state from several technical hints.
  5. Why fix this now? Because the user explicitly called out left-side readability and intuitive business logic as still critical.
- **Root cause statement:** the inbox has action-driven SLA but still lacks a single server-owned operator status contract, so the UI leaks raw backend state and compensates with extra chips.
- **Fix mechanism:** add a normalized business-status contract to case payloads, then refactor queue cards and case header to show one primary business status + one next action + concise owner/context text.

## Reuse-first plan (mandatory)
- **Reuse:** existing `_build_case_queue_signals`, `ConsoleCase` payload, `getCaseSlaIndicator`, current queue/card layouts, existing `inspect_case` mock lane.
- **Integrate:** add business-status derivation next to queue signal derivation and wire it through existing surfaces.
- **Build only if needed:** one new helper for status derivation/presentation; no new route, no new top-level tab, no free-form status system.

## Invariant
- SLA remains the single next-action signal; business status must not replace or duplicate it.
- No fake statuses that are not supported by current data.
- Compact rail should become simpler, not denser.
- Raw `handover.status` may still exist for API compatibility, but it must stop being the primary operator badge in the main UI.

## Scope
- `Part A backend contract`:
  - derive `business_status_code` and `business_status_label` for `ConsoleCase` list/get/action responses;
  - keep mapping bounded to current real states.
- `Part B frontend surfaces`:
  - replace raw status badge in compact queue and case header with the new business status;
  - reduce duplicate/technical pills in queue cards;
  - keep owner/context readable as text, not as competing status chips;
  - update inspect-case mocks/assertions and screenshot evidence.

## Out of scope
- Separate end-user status naming in runtime notifications.
- Full status administration UI.
- Presence/capacity routing.
- Server-side filtering by new business status if it requires a larger query-planner rewrite.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/index.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/src/utils/labels.ts`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Закрыть Wave12 live-validation классификацией и перевести session canon на Wave13.
2. Добавить backend business-status contract и tests/OpenAPI coverage.
3. Перевести compact queue + case header на новый contract, убрать лишние secondary chips.
4. Обновить inspect-case lane, screenshots, session canon и deterministic checks.

## DoD
- `ConsoleCase` exposes a stable business-status contract.
- Queue cards and case header use the business status as the main lifecycle badge.
- Visual badge count in compact queue is reduced without hiding the SLA next action.
- Deterministic backend/OpenAPI/frontend checks are green.
- Session canon reflects Wave12 live blocker classification and Wave13 as the active block.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/utils/labels.ts --file src/components/CaseList.tsx --file src/components/CaseConversation.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for the touch-list.
- Targeted pytest/OpenAPI outputs.
- Local Playwright output.
- Updated `console-web/case_inspection.png`.
- Session log with Wave12 live blocker classification and Wave13 progress.

## Release safety (mandatory)
- **Rollout:** bounded UI/contract change only; no hidden runtime automation.
- **Go/no-go:** merge only if backend contract and UI surfaces stay aligned and deterministic checks are green.
- **Rollback:** revert the bounded Wave13 commit/PR and regenerate API contract if needed.

## Rollback
- `git revert REVISION_SHA`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`

## No-go
- Replacing SLA with another generic status label.
- Adding a new status that cannot be derived from current case data.
- Keeping the old raw status badge and simply adding one more business-status badge beside it.
- Expanding this block into status admin UI or end-user notification redesign.

## Риски/блокеры
- If business-status mapping is too broad, it will become another confusing abstraction.
- If the UI removes too many cues, supervisors may lose quick visibility into errors or paused dialogs.
- OpenAPI/type sync must stay exact because `ConsoleCase` is already consumed by several surfaces.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no end-user-specific status naming yet; no server-side filtering/counts by the new business status; no presence-aware routing.
- `Why not in this block`: this block focuses on making the current operator surface readable and contract-driven without reopening planner-scale backend work.
- `Risk if deferred`: queue readability improves, but advanced reporting and filtering by business status will still remain future work.
- `Linked follow-up Task Package(s)`: `TBD Wave13 closeout / potential Wave14 if server-side business-status filtering becomes necessary`.
- `Expiry/trigger to stop deferral`: if managers still need extra legend/explanation after this block, the status contract is too weak and follow-up becomes mandatory.

## Next-block contract (mandatory)
- `Next block objective`: close Wave13 with contract + UI evidence, then decide whether a follow-up is needed for server-side business-status filtering/reporting.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: mapping must remain grounded in current data and must not regress inspect-case workspace flow.
- `Owner role for closure`: Brain / Top Architect.
