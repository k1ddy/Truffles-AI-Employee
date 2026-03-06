# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-PARTB-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-CLOSEOUT-A1

## Название/цель
Сделать routing assistance практически полезным в точке действия: добавить one-click recommendation в существующие surface `Передать` и bulk reassign, используя factual load counts из Wave10 Part A и не превращая это в скрытую автоматику.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: continue inside existing PR `#932`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
  - `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
- `Baseline findings`:
  - Wave10 Part A already surfaces factual `open_case_count`, but operator still has to manually spot the best option in the list.
  - Current reassignment flow preserves human approval, so a recommendation CTA can speed up routing without hiding business logic.
  - There is still no one-click assist for “pick the least loaded manager in scope”.

## One web search (mandatory before implementation)
- **Query (exact):** `Intercom assign conversations teammates official documentation`
- **Date/time (local):** `2026-03-06T13:16:19+05:00`
- **Sources opened:**
  - `https://www.intercom.com/help/en/articles/6892686-balance-conversation-assignment`
- **Ready solutions found:** mature inbox tools keep the human in control but expose balanced-assignment shortcuts based on current workload instead of flat name lists.
- **Decision (`reuse/integrate/build`):** `integrate` — add explicit recommendation CTA on top of the current selects, using the already available load counts.
- **Rejected options:** silent auto-submit; hidden auto-selection without explanation; new routing page.
- **Source quality:** high-signal primary source = official Intercom Help documentation.

## Root cause (mandatory)
- **Symptom:** Part A reduced blindness, but the operator still spends time scanning the assignee list manually.
- **Minimal reproduction:** open `Передать` for a case with several managers, see factual counts, but still manually compare and choose each time.
- **Evidence:** `CaseConversation` and `CaseList` currently render load hints only as passive labels; there is no recommended-assignee action.
- **Five Whys:**
  1. Почему routing assist ещё не завершён? Потому что данные уже есть, но не превращены в действие.
  2. Почему passive labels недостаточны? Потому что supervisor всё равно делает одинаковое микро-решение вручную.
  3. Почему нельзя auto-assign silently? Потому что ТЗ требует понятной бизнес-логики и человеческого контроля.
  4. Почему CTA должен жить в текущем UI? Потому что нельзя плодить новые экраны ради одной routing-операции.
  5. Почему блок bounded? Потому что это последний action-layer поверх уже внедрённых load signals, без перехода к policy engine.
- **Root cause statement:** routing assistance stays slower than necessary because factual load signals are visible but not actionable in one click.
- **Fix mechanism:** compute a deterministic recommended assignee from current load data and expose an explicit recommendation CTA in current reassignment surfaces.

## Reuse-first plan (mandatory)
- **Reuse:** Wave10 Part A assignee counts, existing reassign selects, current mutation flows.
- **Integrate:** add recommendation CTA/hint without changing backend contracts or introducing auto-routing.
- **Build only if needed:** only frontend recommendation logic and deterministic assertions.

## Invariant
- No hidden auto-submit or silent reassignment.
- Recommendation must stay explainable (`least open cases in scope`).
- Do not break Wave6/Wave10 Part A reassign flows or manager readability.
- Keep everything inside current `Заявки` tab surfaces.

## Scope
- add deterministic recommended-assignee resolver based on `open_case_count` and stable tie-breaks;
- add `Выбрать рекомендацию` CTA in case reassign and bulk reassign panels;
- show short explanation why this assignee is recommended;
- cover the new CTA in deterministic inspect-case lane.

## Out of scope
- Automatic reassignment without confirmation.
- Capacity/presence engine.
- New backend endpoints or policy automation.

## Touch-list
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Create Wave10 Part B TP and move session canon to the new active block.
2. Add deterministic recommended-assignee resolver for single-case and bulk reassign flows.
3. Expose `Выбрать рекомендацию` CTA + explanation in current panels.
4. Update inspect-case lane and push the additive slice into PR `#932`.

## DoD
- Reassign panels expose a clear recommendation CTA when a better assignee exists.
- Recommendation is based only on factual load counts and deterministic tie-breaks.
- Human confirmation remains explicit.
- Deterministic inspect-case lane covers the new assist flow.

## Checks
- `cd console-web && npm run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Lint/build/Playwright outputs.
- Updated session log with Wave10 Part B status.

## Release safety (mandatory)
- **Rollout:** continue in PR `#932`; recommendation CTA is additive and optional.
- **Go/no-go:** reassignment still requires manual confirmation and recommended target matches visible load data.
- **Rollback:** revert Wave10 Part B diff; Part A load hints remain intact.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave10 Part B checks.

## No-go
- Auto-submitting reassignment after clicking recommendation.
- Recommending on hidden criteria not visible to the operator.
- Introducing a second routing screen.

## Риски/блокеры
- Recommendation should not point to current assignee in the single-case flow unless no better alternative exists.
- Tie-break must stay deterministic to avoid flaky e2e assertions.
- CTA copy must stay compact and understandable for Russian-speaking operators.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: recommendation stays heuristic (`least open cases`) and does not become a full routing policy engine.
- `Why not in this block`: policy automation requires a separate decision about capacity/presence signals.
- `Risk if deferred`: operators get faster manual routing now, but still not policy-driven automation.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `Expiry/trigger to stop deferral`: if operator routing still requires repeated manual re-checks after this assist lands, a separate routing-policy wave becomes mandatory.

## Next-block contract (mandatory)
- `Next block objective`: decide whether the current inbox routing assist is sufficient for the user TЗ or whether a dedicated policy-routing follow-up is still required.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: recommendation CTA must not regress current selection, bulk behavior, or default case focus.
- `Owner role for closure`: Brain / Top Architect.
