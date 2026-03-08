# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE14-A1
- `UNLOCKS`:
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-LIVE-VALIDATION-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1`

## Название/цель
Исправить операторский контракт feedback для действий по заявке: менеджер должен видеть факт выполнения бизнес-действия и отдельно видеть неблокирующие sync-проблемы в человеческом виде, без raw technical codes и без ложного ощущения, что сама операция не сработала.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one bounded PR after deterministic checks + local-first UX evidence
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Wave14` merged via `PR #936` on `2026-03-06`; queue views are now server-owned, but operator feedback after actions is still semantically unsafe.
- Frontend still builds operator error text from raw sync details: `console-web/src/components/CaseConversation.tsx:69`.
- Current toast flow can show raw technical strings such as `Клиент: chatflow_failed`, which leaks transport-level failure into manager UX.
- `reopen` is already intended to skip external sync in backend: `truffles-api/app/routers/console.py:1330`, so any client-facing sync error on `Вернуть в работу` is either stale live drift or a UI contract leak from adjacent action feedback.
- Manager-visible success and sync warnings are currently conflated: the UI shows a success toast for the action and then an error toast assembled from raw sync details, creating false ambiguity about the actual business outcome.

## One web search (mandatory before implementation)
- **Query (exact):** `site:knowledge.hubspot.com help desk manage tickets in help desk route tickets SLA goals`
- **Date/time (local):** `2026-03-06T18:35:51+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://knowledge.hubspot.com/help-desk/route-tickets-in-help-desk`
- **Ready solutions found:** operator workspace keeps the primary business outcome clear (`owner/status/reply state`) and does not force the manager to interpret transport-level mechanics as the main result of the ticket action.
- **Decision (`reuse/integrate/build`):** `integrate` — keep current action endpoints and sync objects, but add an operator-safe feedback layer and action-specific UX receipts instead of raw detail leakage.
- **Rejected options:** continue showing raw backend reason-codes in toast text; hide all sync failures completely; add a new diagnostics screen as the default operator surface.
- **Source quality:** high-signal primary source = official HubSpot knowledge base.

## Root cause (mandatory)
- **Symptom:** after case actions, managers can see raw technical strings like `Клиент: chatflow_failed`, and the UI implies the business action may have failed even when the case state changed successfully.
- **Minimal reproduction:** execute a case action with a successful state transition but failed side-effect notification; the UI shows a success toast and then a raw technical error toast assembled from `sync.client_notify.detail` / `sync.telegram.detail`.
- **Evidence:** `console-web/src/components/CaseConversation.tsx:69`, `console-web/src/components/CaseConversation.tsx:407`, `truffles-api/app/services/manager_message_service.py:241`, `truffles-api/app/routers/console.py:1330`.
- **Five Whys:**
  1. Why does the manager see `chatflow_failed`? Because frontend directly renders `sync.detail` values.
  2. Why is that harmful? Because `chatflow_failed` is transport/debug language, not operator language.
  3. Why does it create false failure semantics? Because action success and side-effect warning are rendered as competing toasts with equal severity.
  4. Why is `Вернуть в работу` specifically sensitive? Because reopening is an internal workflow action and should not visually inherit client-notify semantics.
  5. Why fix this before more UI polish? Because every later UX improvement remains untrustworthy if the operator cannot tell whether the action actually succeeded.
- **Root cause statement:** the operator feedback layer is not contract-owned; it leaks raw sync details from backend side-effects and conflates case-state success with secondary delivery failures.
- **Fix mechanism:** formalize action feedback as `business_outcome + operator_warning`, map raw sync reasons to human-safe copy, and suppress non-applicable sync warnings for `reopen`.

## Reuse-first plan (mandatory)
- **Reuse:** existing case action endpoints, `ConsoleCaseActionSync`, reopen-safe backend finalize helpers, current mutation hooks, existing deterministic tests.
- **Integrate:** add operator-facing feedback mapping on top of current sync contract and tighten action-specific semantics where needed.
- **Build only if needed:** one bounded mapping layer and minimal schema copy additions; no new route, no new tab.

## Invariant
- The actual business outcome of a case action must remain explicit and primary.
- `reopen` must not claim client-facing sync work if no client-facing work belongs to that action.
- No raw technical reason-code may be shown directly to managers in default UI.
- Macro actions and direct actions must not diverge in feedback semantics.

## Scope
- `Part A feedback contract`:
  - define operator-safe sync warning mapping for `telegram_edit_failed`, `chatflow_failed`, and similar known details;
  - separate success outcome from warning outcome in the UI;
  - keep transport details available only for logs/audit, not primary toast copy.
- `Part B action-specific receipts`:
  - `reopen`: only internal success copy, no client-facing sync warning surface;
  - `take/resolve/return/reassign/snooze`: action-specific success copy plus bounded warning copy if a secondary sync failed;
  - align `InboxMacros` and direct case actions to the same operator receipt model.

## Out of scope
- Full redesign of the action button area.
- Left rail / queue layout changes.
- New transport retry UI.
- Deep changes to Telegram/WhatsApp provider implementation.

## Touch-list
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/InboxMacros.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_inbox_macros.py`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Open Wave15 as the active post-Wave14 block and sync canon.
2. Define operator-safe mapping for raw sync details and action-specific severity rules.
3. Apply the contract to direct case actions and macro actions.
4. Update deterministic coverage to assert no raw transport reason leaks in operator surfaces.
5. Prepare the dedicated live-validation TP for post-merge proof on real backend.

## DoD
- No default operator toast shows raw reason-codes such as `chatflow_failed` or `telegram_edit_failed`.
- The business result of each case action remains primary and unambiguous.
- `Вернуть в работу` shows only internal workflow success semantics.
- Direct actions and action-macros use the same feedback model.
- Deterministic checks prove the new feedback contract.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/InboxMacros.tsx --file src/utils/labels.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff for touch-list.
- Targeted pytest output for reopen/macro sync semantics.
- Local Playwright output proving operator-safe feedback.
- Updated session log.

## Progress update
- Backend implemented: `ConsoleSyncStatus` now carries `operator_message`, and `_build_sync_status` maps raw failed details into operator-safe copy per sync target.
- Frontend implemented: direct case actions and action-macros now show success first and then bounded warning copy via follow-up toast, without leaking raw reason-codes.
- Deterministic coverage implemented: backend helper tests assert operator-safe mapping, reopen tests assert no operator warning on skipped sync, and `inspect_case` proves friendly warning copy for a sync-bearing macro plus internal-only reopen feedback.
- Current closure state: code + deterministic checks are green locally; next step is bounded PR, then Wave15 live validation on a safe explicit live case.

## Release safety (mandatory)
- **Rollout:** bounded UX/feedback contract only.
- **Go/no-go:** merge only if action state changes remain correct and no raw sync reason leaks in the deterministic lane.
- **Rollback:** revert the bounded Wave15 commit/PR.

## Rollback
- `git revert REVISION_SHA`
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## No-go
- Replacing raw reason-codes with different opaque codes in UI.
- Marking case action as failed when only a secondary notification failed.
- Leaving direct and macro flows with different toast semantics.
- Shipping this block without a dedicated live-validation follow-up.

## Риски/блокеры
- Some sync details may still arrive from legacy paths not covered by current action mutations.
- If mapping is implemented only in frontend, new backend detail strings can leak later.
- Live proof still requires a safe real case scenario.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: crowded action surface and overloaded left rail remain unresolved.
- `Why not in this block`: this block fixes semantic correctness first; layout polish without truthful feedback would still mislead managers.
- `Risk if deferred`: operator trust remains low even if buttons later look better.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `Expiry/trigger to stop deferral`: if any new live report still contains raw technical text in operator UX, Wave15 is not actually closed.

## Next-block contract (mandatory)
- `Next block objective`: after Wave15 merge, execute precise live validation for `resolved -> reopen` and one sync-bearing action on real backend.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `Blocked-by conditions`: safe explicit live case/scenario required for post-merge mutation proof.
- `Owner role for closure`: Brain / Top Architect.
