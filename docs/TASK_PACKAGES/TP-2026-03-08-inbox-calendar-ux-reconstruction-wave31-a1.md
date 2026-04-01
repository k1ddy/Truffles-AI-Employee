# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE31-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1
- `UNLOCKS`: only a future bounded routing v2 / capability-input block if new server-owned assignee inputs become real after this re-check

## Название/цель
`Wave31` after Wave35 is a decision gate, not another feature wave: re-check whether the product has any real server-owned assignee capability inputs beyond Wave29/Wave30, and record an explicit no-go if routing v2 would still be fake maturity.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-08-inbox-calendar-ux-reconstruction-wave31-recheck-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `feat/2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1`
- `Merge policy`: docs-only PR over the closed Wave35 diff; no product/runtime code changes
- `Cleanup`: Brain / Top Architect after merge

## Invariant
- Не изобретать fake `skills`, `presence`, `shift` или “availability” в UI/local state.
- Не вводить routing v2, если входные capability signals всё ещё не server-owned и не тестируемы контрактно.
- Не ломать Wave24-30 queue/saved-view/share-link/follow-up governance/routing profile contracts.
- Не превращать Wave31 re-check в stealth routing implementation.

## Scope
- Повторно проверить after Wave35 closure, есть ли в системе реальные server-owned assignee capability inputs для следующего routing layer.
- Зафиксировать explicit no-go, если current routing truth всё ещё ограничен Wave29/Wave30 inputs.
- Синхронизировать master/session/state/backlog canon с этим решением.

## Out of scope
- Любой новый code diff по routing v2/capabilities.
- Новые assignee signals without server ownership.
- Любой rework Wave33/Wave34/Wave35 surfaces.

## Touch-list
- `STATE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`

## One web search (mandatory before implementation)
- Этот re-check не активирует implementation.
- Mandatory single search intentionally remains unused until a future execution TP opens real routing work.

## Root cause (mandatory)
- **Symptom:** после Wave30 routing стал управляемым, а после Wave33-Wave35 операторский UI/proof debt больше не маскирует решение — теперь нужно честно ответить, нужен ли routing v2 вообще.
- **Minimal reproduction:** попытка проектировать routing v2 без новых server-owned inputs быстро скатывается в fake capability modeling (`skills`, `presence`, `shift`) or local heuristics.
- **Evidence:** Wave29/Wave30 already cover explainable scoring, booking follow-up continuity, and assignee routing profiles; Wave32-Wave35 proved the dominant remaining risk was operator surface architecture and workflow proof, not missing routing layers.
- **Root cause statement:** следующий routing layer блокируется не отсутствием кода, а отсутствием новых подтверждённых server-owned assignee capability signals beyond the current Wave29/Wave30 contract.
- **Fix mechanism:** keep Wave31 in explicit no-go state until a future TP can prove new server-owned inputs and bounded operational value.

## Re-check outcome (2026-03-08)
- `Wave33`, `Wave34`, and `Wave35` are now opened as `PR #952`, `PR #953`, and `PR #954`; the owner-prioritized operator debt from `Wave32` has moved into review instead of reopening routing scope.
- Current routing contract still exposes only:
  - access/membership eligibility,
  - current open-case load,
  - booking follow-up continuity and overdue state,
  - SLA-sensitive scoring,
  - routing profiles (`available` / `paused` / `follow_up_only` + optional capacity).
- Current routing policy surface is still bounded to `least_open_cases` and `follow_up_sla_balance`; unknown `skills_presence` remains rejected by contract tests.
- There is still no server-owned assignee skills matrix, presence heartbeat, or shift/schedule model in the console runtime.
- **Decision:** `Wave31 = no-go / hold`. Do not open routing v2 or capability-aware code until a new TP can prove new server-owned inputs and bounded operational value.

## Plan (1..N)
1. Re-check current canon after Wave35 closure and PR opening.
2. Confirm whether any new server-owned capability inputs exist beyond Wave29/Wave30.
3. Record explicit no-go/hold if the answer remains no.

## DoD
- Wave31 ends with an explicit go/no-go decision rather than ambiguity.
- If there are no new server-owned capability inputs, routing v2 is explicitly blocked.
- Canon/state/session/backlog references all point to the same no-go decision.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave31|Wave35|routing v2|UX-34|UX-35|UX-36" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "SUPPORTED_CASE_ROUTING_POLICIES|CASE_ROUTING_POLICY_|ConsoleCaseRoutingPolicyType|normalize_case_routing_policy|skills_presence" truffles-api/app/services/console_case_routing.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_cases_helpers.py`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "skill|presence|shift|routing_status|max_open_case_count|follow_up_only" truffles-api/app console-web/src/app/team/page.tsx docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `truffles-api/app/services/console_case_routing.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- updated session/state pointers

## Release safety (mandatory)
- **Rollout:** docs-only decision gate; no runtime/product rollout.
- **Go/no-go:** merge only if the re-check stays evidence-based and does not smuggle in product behavior changes.
- **Rollback:** revert the docs-only Wave31 re-check commit; Wave29/Wave30 runtime behavior remains unchanged.

## Rollback
- `git revert REVISION_SHA`
- re-run the doc checks and `SESSION_AGENT=a1 scripts/session_check.sh`
- restore the previous task-package pointer only if the no-go decision must be withdrawn

## No-go
- Не стартовать Wave31 code changes из этого re-check.
- Не использовать этот TP как разрешение на fake capability routing.
- Не объявлять routing v2 “следующим обязательным шагом” без новых server-owned inputs.

## Риски/блокеры
- Главный риск — снова начать routing v2 discussion на уровне идей, а не фактов.
- Если backlog/status docs останутся несинхронными, команда снова сможет трактовать Wave31 как “почти стартовавший”.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: routing maturity remains bounded to Wave29/Wave30; no skills/presence/shift model exists yet.
- `Why not in this block`: the required inputs are still absent from the server model; pretending otherwise would create fake maturity.
- `Risk if deferred`: the team may reopen routing debates without factual inputs, but product behavior stays safer than a speculative routing v2.
- `Linked follow-up Task Package(s)`: a future execution TP must supersede this re-check explicitly and prove new server-owned capability inputs first.
- `Expiry/trigger to stop deferral`: when assignee skills, presence, or shift/schedule constraints become real server-owned facts with bounded operational value.

## Next-block contract (mandatory)
- `Next block objective`: no Wave31 implementation now; keep routing on Wave29/Wave30 and reopen only via a new execution TP with proven server-owned capability inputs.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "skills_presence|follow_up_sla_balance|routing_status|max_open_case_count" truffles-api/app/services/console_case_routing.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_cases_helpers.py docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`
- `Blocked-by conditions`: no real server-owned capability inputs; any attempt to fake them blocks immediately.
- `Owner role for closure`: Brain / Top Architect.
