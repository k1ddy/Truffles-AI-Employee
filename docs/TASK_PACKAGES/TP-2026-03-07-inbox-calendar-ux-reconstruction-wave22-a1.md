# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE20-A1, CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE21-A1
- `UNLOCKS`: program closeout for the new inbox semantic model

## Название/цель
Закрыть программу доказательством, что новая панель `Заявки` не допускает плохие и нерабочие состояния при всех ключевых сценариях менеджера и администратора, включая связь с ботом и календарём записей.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one validation PR or validation follow-up after Wave20/Wave21 merges
- `Cleanup`: Brain / Top Architect after final closeout

## One web search (mandatory before implementation)
- **Query (exact):** `site:support.atlassian.com jira service management best practices managing queues at scale filters views validation and site:support.zendesk.com views tickets official`
- **Date/time (local):** `2026-03-07T10:05:00+05:00`
- **Sources opened:**
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- **Ready solutions found:** robust operator systems validate view/filter logic and role-specific states as part of queue governance, not as ad-hoc manual QA.
- **Decision (`reuse/integrate/build`):** `integrate` — extend the current deterministic e2e harness and explicit live-validation blocker model.
- **Rejected options:** merge without matrix proof; fake-pass live validation; visual-only signoff.
- **Source quality:** high-signal primary sources = official Atlassian and Zendesk docs.

## Root cause (mandatory)
- **Symptom:** point fixes keep regressing because there is no complete acceptance matrix over allowed/forbidden states.
- **Minimal reproduction:** combine role, queue/history mode, owner scope, case state, booking state, reopen, and history restore.
- **Evidence:** prior waves repeatedly found new contradictions only after live/operator review.
- **Five Whys:** the system lacked a final matrix proving semantic correctness across modes and roles.
- **Root cause statement:** without a bounded acceptance matrix and precise live evidence, the inbox/calendar system can still drift into contradictory edge states.
- **Fix mechanism:** codify deterministic matrix tests, role scenarios, forbidden states, and live no-mocks validation with explicit blocker handling.

## Invariant
- No fake green by skipping core scenarios silently.
- No merge without matrix proof.
- Live validation remains precise: `pass`, `fail`, or `blocked`, never ambiguous.

## Scope
- deterministic state matrix for manager/admin
- forbidden-state assertions across case/booking/history modes
- live validation runbook and explicit blockers

## Out of scope
- further feature expansion
- new product requirements outside this semantic program

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/e2e/*` if split by scenario becomes necessary
- `docs/runbooks/INBOX_SEMANTIC_WAVE22_VALIDATION.md`
- `docs/SESSIONS/*`
- `docs/TASK_PACKAGES/*` closeout docs

## Acceptance matrix slices (mandatory)
1. manager open queue
2. manager closed/history lookup
3. admin owner/unassigned/history modes
4. case linked to booking
5. booking updated after case action
6. closed case reopened
7. restored workspace prefs by role
8. live no-mocks proof with explicit safe case ids where mutation is required

## DoD
- All critical manager/admin states covered by deterministic tests.
- Forbidden states fail tests explicitly.
- Live no-mocks evidence is classified precisely.
- Program can be closed with an explicit semantic verdict.

## Checks
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`
- live no-mocks command with explicit safe environment values

## Evidence
- deterministic test output
- live validation output
- validation runbook with exact pass/blocked/fail classification rules
- closeout note in session/master TP

## Rollback
- revert validation-only diff if it introduces unstable or low-signal checks

## No-go
- Merge product changes without matrix proof.
- Treat fallback path as proof of the main scenario.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only optional future productivity features, not correctness gaps.
- `Why not in this block`: this wave is strictly for proof and closeout.
- `Risk if deferred`: semantic regressions stay invisible until operator complaints.
- `Linked follow-up Task Package(s)`: none expected if Wave22 closes green.
- `Expiry/trigger to stop deferral`: any red matrix slice or blocked live proof keeps the overall program open.

## Next-block contract (mandatory)
- `Next block objective`: close the new inbox semantic program with explicit go/no-go.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: unresolved live blockers or missing deterministic slices.
- `Owner role for closure`: Brain / Top Architect.
