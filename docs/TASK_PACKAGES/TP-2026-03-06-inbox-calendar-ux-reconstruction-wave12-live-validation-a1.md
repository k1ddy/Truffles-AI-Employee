# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-LIVE-VALIDATION-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-A1

## Название/цель
После merge `PR #934` проверить Wave12 на live backend без route mocks: подтвердить, что policy-routing реально работает в текущем production scope, а если live-контур не может это доказать — зафиксировать точный blocker или внести минимальный fix в том же worktree.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: no PR if this block is doc/evidence only; one bounded PR only if a reproducible product/e2e gap is fixed
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/e2e/inspect_case.spec.ts`
  - `console-web/case_inspection.png`
  - `console-web/calendar_case_context.png`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
  - `truffles-api/app/routers/console.py` (only if reproducible backend gap appears)
  - `truffles-api/tests/test_console_cases_helpers.py` (only if reproducible backend gap appears)
- `Baseline findings`:
  - `PR #934` merged on `2026-03-06T10:58:01Z` with merge commit `128252329dbc784336a363e16d710ae8f9427eea`.
  - Wave12 is locally green, but no live no-mocks evidence yet for the real `policy-routing` click path.
  - Existing live lane can fall back to calendar/no-cases when the authenticated scope has no accessible active case, so a green live run can still miss the actual routing mutation.

## One web search (mandatory before implementation)
- **Query (exact):** `Playwright APIRequestContext authentication official docs`
- **Date/time (local):** `2026-03-06T20:03:00+05:00`
- **Sources opened:**
  - `https://playwright.dev/docs/api-testing`
  - `https://playwright.dev/docs/auth`
- **Ready solutions found:** official Playwright guidance supports authenticated API-assisted setup/discovery before UI assertions, which matches our need to discover an accessible live case or explicitly gate on a missing scoped fixture instead of pretending the scenario was validated.
- **Decision (`reuse/integrate/build`):** `integrate` — reuse the existing live `inspect_case` lane and only add bounded live-targeting logic if the current scope cannot prove the policy-routing path.
- **Rejected options:** blind manual UI clicking without a deterministic case target; route mocks on live lane; inventing a second standalone live test flow before proving the current lane insufficient.
- **Source quality:** high-signal primary source = official Playwright documentation.

## Root cause (mandatory)
- **Symptom:** Wave12 merged, but there is still no proof that `Назначить по политике` / `Распределить по политике` works on the live backend.
- **Minimal reproduction:** run `inspect_case` against `https://console.truffles.kz` with mocks disabled; if the current authenticated scope has no accessible active case, the lane can validate only the fallback surface and skip the actual routing mutation.
- **Evidence:** prior live lanes for inbox features already showed `cases workspace unavailable` / `calendar no-cases fallback` behavior; Wave12 has no dedicated live evidence yet.
- **Five Whys:**
  1. Why is merge not enough? Because local mock coverage does not prove live behavior.
  2. Why can the existing live lane miss the real action? Because it can pass via fallback when no inspectable case exists.
  3. Why is that risky? Because routing is a mutation path, not a read-only surface.
  4. Why can this still be acceptable? Because the blocker may be environment scope, not product logic.
  5. Why do we need a bounded validation TP? Because we must separate `live blocker` from `real bug` and avoid building new features on unverified behavior.
- **Root cause statement:** the current merged feature is locally verified but not yet proven in a live no-mocks mutation path, and the existing live lane can legitimately degrade to a non-mutating fallback when scope data is missing.
- **Fix mechanism:** first run the live lane as-is; if it cannot reach a real routing mutation, either record the blocker precisely or add the smallest possible case-targeting improvement in the same lane.

## Reuse-first plan (mandatory)
- **Reuse:** current `inspect_case` live lane, shared Keycloak auth helper, existing live case discovery, existing screenshots/evidence flow.
- **Integrate:** only extend the live lane if the current scope cannot hit the policy-routing path.
- **Build only if needed:** one bounded live-targeting addition such as env-driven case targeting or explicit API discovery for an eligible active case.

## Invariant
- Не ослаблять live-check до route-mocks.
- Не считать fallback-only прогон доказательством policy-routing mutation.
- Не вносить новый продуктовый scope без доказанного live gap.
- Не менять бизнес-логику routing без воспроизводимого evidence.

## Scope
- `Part A (this TP)`:
  - verify merged Wave12 behavior on live backend without mocks;
  - collect screenshots/log evidence;
  - explicitly classify result as `validated`, `blocked by live scope`, or `bug reproduced`.
- `Part B (only if needed)`:
  - minimal e2e or product fix to make the live path provable;
  - rerun the same live scenario after the fix.

## Out of scope
- Presence/capacity-aware routing.
- New routing policies beyond `least_open_cases`.
- New queue UX work unrelated to proving the live path.

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/case_inspection.png`
- `console-web/calendar_case_context.png`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `truffles-api/app/routers/console.py` (only if a real backend bug is found)
- `truffles-api/tests/test_console_cases_helpers.py` (only if a real backend bug is found)

## Plan (1..N)
1. Зафиксировать новый live-validation TP и перевести session canon на него.
2. Прогнать live no-mocks `inspect_case` для Wave12.
3. Если live lane не доходит до policy-routing mutation, классифицировать blocker и при необходимости сделать минимальный live-targeting fix.
4. Обновить канон и evidence.

## DoD
- Есть one of: `live validated`, `live blocked with precise reason`, or `bug fixed and revalidated`.
- Evidence содержит не только общий pass, но и ясное понимание был ли выполнен реальный routing mutation path.
- Если был найден bug, fix остаётся bounded и повторно проверен тем же сценарием.

## Checks
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`
- `cd console-web && npm run lint -- --file e2e/inspect_case.spec.ts` (only if the live lane code changes)

## Evidence
- Live Playwright output.
- Updated screenshots if the lane reached the routing path.
- Session log with exact outcome classification.

## Release safety (mandatory)
- **Rollout:** validation-first; no new rollout unless a real bug requires a bounded fix.
- **Go/no-go:** live run must either prove the mutation or explain why it could not be reached.
- **Rollback:** revert only the bounded follow-up fix if one is needed.

## Rollback
- `git revert REVISION_SHA`
- Re-run the same live validation command.

## No-go
- Treating calendar fallback as proof of routing mutation.
- Adding route mocks to a live lane.
- Expanding this block into presence/capacity routing.

## Риски/блокеры
- The authenticated live scope may simply not contain a safe active case for mutation.
- Live auth/session state may drift and hide the real blocker behind an auth gate.
- A live-targeting improvement must not mutate arbitrary production data without a clear case contract.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: even a successful live validation will not close future presence/capacity-aware routing maturity work.
- `Why not in this block`: this block proves the shipped contract before opening a new maturity wave.
- `Risk if deferred`: continuing feature work without live proof can hide integration bugs behind local green checks.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`, `TBD Wave13 only after live outcome is classified`.
- `Expiry/trigger to stop deferral`: if Wave12 live validation cannot hit the mutation path twice in a row, a deterministic live-targeting follow-up becomes mandatory before any larger routing wave.

## Next-block contract (mandatory)
- `Next block objective`: after live validation, either close Wave12 as fully validated or open the smallest needed follow-up (`live-targeting fix` or `Wave13 presence/capacity routing`).
- `First deterministic check command`: `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: live scope must expose an inspectable active case or the lane must explicitly report why it cannot.
- `Owner role for closure`: Brain / Top Architect.
