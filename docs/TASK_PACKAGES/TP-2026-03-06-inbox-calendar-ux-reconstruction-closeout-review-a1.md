# TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-REVIEW-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-PARTB-A1
- `UNLOCKS`: none

## Название/цель
Зафиксировать merge-ready closure decision по ТЗ для `Заявки/Записи`: не добавлять бесконечные фичи вслепую, а явно решить, что уже закрыто в `PR #932`, какие residual gaps остаются допустимыми и требуется ли отдельный follow-up после merge.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: review current `PR #932`, do not open a new PR for closure analysis
- `Cleanup`: Brain / Top Architect after merge or explicit stop-the-line

## FACT pre-check (before implementation)
- `PR #932` already contains Waves `7 -> 10 Part B`.
- Product blocks already in branch/PR:
  - action macros,
  - embedded bookings workspace,
  - context-preserving inbox/calendar flow,
  - supervisor/admin queue governance,
  - factual assignee load hints,
  - recommended routing action.
- Deterministic evidence already exists locally for all recent blocks:
  - `pytest` / `generate_openapi --check` / `generate:api` / `lint` / `build` / `Playwright inspect_case localhost`.
- PR checks are expected to be the final external merge gate; closeout review must not silently broaden scope while `PR #932` is already mergeable apart from running checks.

## One web search (mandatory before implementation)
- **Query (exact):** `Atlassian best practices for managing queues at scale official documentation`
- **Date/time (local):** `2026-03-06T13:37:34+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
- **Ready solutions found:** at scale, queue quality is driven by clear views, ownership visibility, and low-friction operating surfaces; advanced policy automation can remain a separate maturity step if the operator workspace already provides deterministic queue control.
- **Decision (`reuse/integrate/build`):** `reuse` — use the already implemented Waves `1-10` evidence and compare it against the original TЗ instead of inventing another product wave by inertia.
- **Rejected options:** declaring full closure without explicit review; opening a new feature wave only because more CRM patterns exist on the market.
- **Source quality:** high-signal primary source = official Atlassian support documentation.

## Root cause (mandatory)
- **Symptom:** after multiple waves the product may be either merged too early with hidden gaps or kept open indefinitely because “ещё можно улучшить”.
- **Minimal reproduction:** inspect the current branch: many operator capabilities are already added, but without a closeout decision there is no disciplined answer to “всё ли выполнено по ТЗ?”.
- **Evidence:** session log + master TP + `PR #932` commit stack show that the branch now spans connected workspace, SLA contract, actions, macros, queue governance and routing assistance.
- **Five Whys:**
  1. Почему нужен отдельный review block? Потому что без него нет формального merge-go/no-go against the original TЗ.
  2. Почему нельзя просто продолжать добавлять функции? Потому что это ломает atomic discipline и размывает понятие “достаточно для closure”.
  3. Почему review должен опираться на бизнес-логику, а не на вкус? Потому что user ТЗ говорит о конечной пользе для менеджеров/админов, а не о бесконечном chase за всеми CRM-фичами мира.
  4. Почему residuals допустимы? Потому что не каждая advanced maturity feature обязательна для закрытия исходных болей, если core operator workflow уже решён и documented.
  5. Почему всё ещё нужен follow-up option? Потому что если review найдёт незакрытый бизнес-critical gap, он должен стать отдельным bounded TP, а не “скрытым хвостом”.
- **Root cause statement:** после крупных product waves отсутствует формализованный closure review, из-за чего граница между “ТЗ закрыто” и “есть future maturity backlog” остаётся неявной.
- **Fix mechanism:** зафиксировать explicit coverage matrix, merge-go/no-go decision и residual-debt decision для `PR #932`.

## Reuse-first plan (mandatory)
- **Reuse:** existing TP/session evidence, screenshots, local checks, PR check status, original TЗ coverage map.
- **Integrate:** map implemented waves back to the user’s original complaints and operator business flows.
- **Build only if needed:** new follow-up TP only if closeout review finds a business-critical gap still not covered.

## Invariant
- Do not reopen scope by default.
- Do not mark closure without explicit evidence mapping to the original TЗ.
- Do not hide unresolved business-critical gaps behind vague “future improvement” wording.
- Do not change runtime behavior in this review block unless a P0/P1 defect is discovered.

## Scope
- evaluate coverage of original user TЗ against actual branch state;
- classify each remaining gap as `blocking` or `accepted residual`;
- produce merge-ready conclusion for `PR #932`;
- decide whether separate follow-up after merge is required.

## Out of scope
- New operator features.
- New routing engine or SLA redesign.
- Visual refactor beyond current implemented surfaces.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Create the closeout-review TP and move session canon to the active review block.
2. Build a factual closure matrix: original requirement -> implemented waves -> evidence -> closure state.
3. Record merge-go/no-go and accepted residuals.
4. If a business-critical gap remains, open one bounded follow-up TP; otherwise stop scope growth and wait for merge.

## Closure matrix (review output)
| Original requirement | Classification | Implemented waves | Blocking? | Notes |
|---|---|---|---|---|
| `1. Нет связи между вкладками` | `closed` | `Wave1`, `Wave8` | no | Tabs are linked both ways and keep operator context. |
| `2. Менеджер скроллит вниз, чтобы понять контекст` | `closed` | `Wave1`, `Wave5` | no | First screen now shows action, context, and reply surface without legacy SLA clutter. |
| `3. Непонятные SLA цифры и термины` | `closed` | `Wave5` | no | Abstract SLA copy replaced by action-driven states and due/overdue wording. |
| `4. Вкладка Записи не удобна для управления` | `closed with accepted residual` | `Wave2`, `Wave8`, `Wave9`, `Wave10` | no | Calendar/Bookings are now part of the same operator workspace; future policy-routing automation is a maturity step, not a blocker for current management flow. |
| `5. Капитальная реконструкция с ориентацией на мировые CRM` | `closed with accepted residual` | `Wave1` -> `Wave10` | no | Current PR reaches operator-workspace parity for the user’s pain points; advanced maturity features remain future backlog. |
| `6. Недостающие функции/опции должны быть проанализированы и вписаны` | `closed with accepted residual` | `Wave6`, `Wave7`, `Wave9`, `Wave10` | no | Missing operator-critical capabilities were added; anything further must become a separate bounded TP instead of staying implicit. |
| `7. Всё должно быть связано, интуитивно и без дублей` | `closed` | cross-wave invariant | no | Current branch keeps actions inside existing tabs and removes major duplicate/friction paths. |

## Merge-ready decision (review output)
- `Decision`: `merge-go`, if `PR #932` required checks are green.
- `Blocking gaps found`: none against the original user ТЗ.
- `Accepted residuals after merge`:
  - policy-based routing automation (`round-robin/capacity/presence`) beyond the current explicit operator-assist model,
  - richer custom business-status taxonomy beyond the current action-driven lifecycle,
  - optional supervisor maturity features that are not required to operate the current queue/calendar workflow.
- `Reason these residuals are accepted`: they improve maturity at scale, but they do not reopen the original pains about context loss, confusing SLA, weak bookings workflow, or lack of operator actions in the current tabs.

## DoD
- There is an explicit answer whether `PR #932` is sufficient for the original TЗ.
- Every original requirement is classified as `closed`, `closed with accepted residual`, or `still blocking`.
- Residuals are concrete and bounded, not hand-wavy.
- Session canon points to the closeout review as the active decision block.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Requirement coverage map|Wave10|closeout review|Next-block contract" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md`
- `SESSION_AGENT=a1 scripts/session_check.sh`
- `gh pr view 932 --json statusCheckRollup,mergeStateStatus,url`

## Evidence
- `PR #932` status and checks.
- Existing local deterministic evidence already listed in session log.
- Updated master/session docs with explicit closure decision.

## Release safety (mandatory)
- **Rollout:** no new runtime change in this block; review only.
- **Go/no-go:** merge only if `PR #932` checks are green and review classifies remaining gaps as accepted residuals rather than blockers.
- **Rollback:** if review finds a blocker, stop merge and open exactly one bounded follow-up TP.

## Rollback
- Revert doc-only closeout review if it is found inconsistent.
- If review opens a blocker, reset active block to the new follow-up TP instead of merging.

## No-go
- Declaring closure because “много уже сделано” without mapping to the original TЗ.
- Creating a new feature wave without first classifying whether the gap is actually blocking.
- Mixing accepted residuals and blockers in the same decision line.

## Риски/блокеры
- There is a temptation to keep expanding toward every advanced CRM pattern even when original manager pain is already addressed.
- The opposite risk is undercalling a residual that still blocks admin-scale operation.
- Merge decision must wait for actual PR checks, not just local evidence.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: likely future maturity items include policy-based routing automation and possibly richer business-status taxonomy, but only if closeout review confirms they are not blocking the original TЗ.
- `Why not in this block`: this block is a decision gate, not a stealth implementation wave.
- `Risk if deferred`: if a truly blocking gap is misclassified as residual, merge would leave hidden operator pain in production.
- `Linked follow-up Task Package(s)`: create only if the review identifies a blocking gap.
- `Expiry/trigger to stop deferral`: if review cannot state a clear closure decision for each original requirement, deferral is not allowed.

## Next-block contract (mandatory)
- `Next block objective`: either stop scope growth and wait for merge of `PR #932`, or open one bounded follow-up only for a review-confirmed blocker.
- `First deterministic check command`: `gh pr view 932 --json statusCheckRollup,mergeStateStatus,url`
- `Blocked-by conditions`: closeout decision is blocked while required PR checks are red or while requirement classification is still ambiguous.
- `Owner role for closure`: Brain / Top Architect.
