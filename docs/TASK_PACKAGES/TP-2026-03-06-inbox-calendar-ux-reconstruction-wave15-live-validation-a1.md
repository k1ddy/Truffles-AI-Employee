# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-LIVE-VALIDATION-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1

## Название/цель
Подтвердить на live backend без mocks, что операторский feedback contract после Wave15 больше не показывает raw technical errors и не искажает результат действий `Вернуть в работу` и одного sync-bearing действия.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: no code-only merge from this TP; evidence gate for next product block
- `Cleanup`: Brain / Top Architect after merge of dependent code block

## FACT pre-check (before implementation)
- Wave15 is required first; live validation is not valid against pre-Wave15 UX.
- Previous live lanes could not safely prove mutation paths without an explicit case/scenario.
- This TP exists to prevent false `pass` and to keep real-backend evidence separate from deterministic mock proof.
- Current blocker (fact, 2026-03-06): `INSPECT_CASE_LIVE_CASE_ID` is still unset in the live E2E environment, so the new dedicated mutation test skips with a precise reason and the generic live lane only reaches no-case fallback evidence.

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.zendesk.com Defining SLA policies due soon overdue paused`
- **Date/time (local):** `2026-03-06T18:35:51+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408829459866-Defining-SLA-policies`
- **Ready solutions found:** operator-facing states must stay action-oriented and should not collapse distinct internal states into misleading public outcomes.
- **Decision (`reuse/integrate/build`):** `reuse/integrate` — validate the existing live lane with stricter evidence expectations rather than inventing a new manual QA protocol.
- **Rejected options:** mark local mock evidence as sufficient for live-sensitive feedback fixes.
- **Source quality:** high-signal primary source = official Zendesk support documentation.

## Root cause (mandatory)
- **Symptom:** local deterministic coverage proves reopen semantics, but live reports can still reveal environment-specific feedback leaks or adjacent sync paths.
- **Minimal reproduction:** perform `resolved -> reopen` and one sync-bearing action on a safe live case after Wave15 merge.
- **Evidence:** earlier live flows required fallback because a safe explicit case was not available.
- **Five Whys:**
  1. Why is local proof insufficient here? Because the reported issue happened on live.
  2. Why can live differ? Because real transport/config state differs from mocks.
  3. Why not treat absence of a case as pass? Because that would be false evidence.
  4. Why isolate this in a separate TP? Because live validation has different blockers and should not be mixed with code completion.
  5. Why gate Wave16 by this? Because further UI work should not hide unresolved semantic regressions.
- **Root cause statement:** live evidence for operator feedback is a distinct acceptance step and was previously under-specified.
- **Fix mechanism:** require a safe explicit live scenario and capture deterministic mutation evidence plus screenshot/log proof.

## Invariant
- No fake live pass.
- No mutation against an unsafe or unknown case.
- Evidence must include both action outcome and absence of raw technical text.

## Scope
- Validate `Вернуть в работу` on live after Wave15 merge.
- Validate one sync-bearing action on live after Wave15 merge.
- Capture screenshot/log evidence and update session canon.

## Out of scope
- New code changes unrelated to validation.
- Broad exploratory live testing across all actions.

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Obtain safe explicit live case/scenario.
2. Run the live no-mocks lane against `reopen` and one sync-bearing action.
3. Record screenshot/log evidence or precise blocker.
4. Only then unlock Wave16 implementation closure.

## DoD
- Live evidence exists for `reopen` and one sync-bearing action after Wave15 merge.
- No raw technical toast text is visible in operator UX.
- If safe live mutation cannot be performed, the TP closes as `blocked with precise reason`, not `pass`.

## Checks
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 INSPECT_CASE_LIVE_CASE_ID=<safe-case-id> npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Playwright live output.
- Screenshot artifact.
- Session log with exact blocker or pass condition.

## Release safety (mandatory)
- **Rollout:** validation-only gate.
- **Go/no-go:** Wave16 should not be claimed ready-for-closure if live validation reveals semantic drift.
- **Rollback:** none; this TP is evidence-only.

## Rollback
- Not applicable; validation gate only.

## No-go
- Using fallback/no-case live output as proof of mutation correctness.
- Treating local mocks as replacement for live proof.

## Риски/блокеры
- Safe explicit live case may be unavailable.
- Role/scope on live may hide the required actions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: action area UX and queue rail UX remain outside this validation-only block.
- `Why not in this block`: this TP exists only to prove Wave15 on live.
- `Risk if deferred`: unresolved live drift can be mistaken for UX-only noise later.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `Expiry/trigger to stop deferral`: if live proof remains blocked through the next product wave, stop-the-line and escalate.

## Next-block contract (mandatory)
- `Next block objective`: execute Wave16 action-surface and queue-rail simplification after Wave15 semantics are proven or precisely blocked on live.
- `First deterministic check command`: `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx`
- `Blocked-by conditions`: missing safe explicit live case/scenario.
- `Owner role for closure`: Brain / Top Architect.
