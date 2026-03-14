# TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1

## Block identity
- `BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE32-A1`
- `PARENT_BLOCK_ID`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1`
- `DEPENDS_ON`: `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE30-A1`
- `UNLOCKS`: bounded operator-surface simplification waves for `Заявки` and `Записи`; no routing v2 until this audit is closed

## Название/цель
Выполнить полный deep audit по `Заявки` и `Записи`: отдельно разобрать визуальный шум, action hierarchy, смешение поверхностей и реальное functional/test coverage, чтобы следующий блок был не очередным spot-fix, а целевой reconstruction plan с жёстким DoD.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: docs-only PR or include into the next implementation PR
- `Cleanup`: Brain / Top Architect after merge

## Invariant
- Не ломать Wave24-30 contracts: queue state, saved views, team presets, shareable URLs, booking follow-up governance, routing profiles.
- Не открывать routing v2/capability work, пока visual/interaction architecture и operator workflow coverage не зафиксированы явно.
- Не делать очередной feature-layer поверх перегруженных first-screen surfaces без decomposition plan.

## Scope
- Провести deep audit `console-web/src/components/CaseList.tsx`, `console-web/src/components/InboxView.tsx`, `console-web/src/app/calendar/page.tsx`.
- Зафиксировать root causes visual/interaction overload и logic leakage.
- Зафиксировать фактическое test coverage состояние: backend contract checks, frontend operator-flow coverage, layout proof gaps.
- Обновить canonical docs/backlog и определить следующий execution order.

## Out of scope
- Любая runtime/UI implementation правка в этом блоке.
- Новый routing layer, capability modeling, skill/presence automation.
- Полный redesign design system вне текущего operator problem statement.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## One web search (mandatory before implementation)
- `Query`: `help desk queue best practices filters views reduce noise official`
- `Date/time`: `2026-03-08T10:03:13+05:00` (audit session record time; exact query executed in this session before drafting)
- `Opened sources`:
  - Atlassian: `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
  - Atlassian: `https://support.atlassian.com/jira-service-management-cloud/docs/what-are-queues/`
  - HubSpot: `https://knowledge.hubspot.com/help-desk/search-for-tickets-in-help-desk`
  - Zendesk: `https://support.zendesk.com/hc/en-us/articles/4408832792986-Managing-your-views`
- `Found reusable solutions`:
  - keep a small number of high-value queue states on first screen;
  - separate shared/admin-managed views from personal views on one model;
  - use filters/views to focus work, not to expose every management action inline.
- `Decision`: `integrate/build`
- `Reason`: reusable product principles exist, but the actual decomposition must be built inside current Inbox/Calendar surfaces and contracts.
- `Rejected alternatives`:
  - keep adding new inline buttons/fields inside current `CaseList`/`calendar/page.tsx`;
  - jump to routing v2 before fixing operator surface architecture;
  - solve visual overload only with cosmetic spacing tweaks.

## Root cause (mandatory)
- `Symptom`: `Заявки` and `Записи` feel noisy, crowded, and action-ambiguous; controls wrap, compete, and expose internal state-machine details directly on first screen.
- `Minimal reproduction`: open Inbox or Calendar operator surfaces after Wave24-30 and compare the first visible control density to the actual primary task (pick queue slice, find item, act, move on).
- `Evidence`:
  - `console-web/src/components/CaseList.tsx` is `3291` lines; `console-web/src/app/calendar/page.tsx` is `2354` lines.
  - `CaseList` combines queue-state restore/persist (`console-web/src/components/CaseList.tsx:749`, `console-web/src/components/CaseList.tsx:1768`) with first-screen controls (`console-web/src/components/CaseList.tsx:2013`, `console-web/src/components/CaseList.tsx:2054`, `console-web/src/components/CaseList.tsx:2404`, `console-web/src/components/CaseList.tsx:2710`).
  - `calendar/page.tsx` combines queue-state restore/persist (`console-web/src/app/calendar/page.tsx:362`, `console-web/src/app/calendar/page.tsx:767`) with dense queue controls and saved-view management (`console-web/src/app/calendar/page.tsx:1634`, `console-web/src/app/calendar/page.tsx:1693`, `console-web/src/app/calendar/page.tsx:1740`, `console-web/src/app/calendar/page.tsx:2258`).
  - Targeted backend contract suite is green: `cd truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_calendar_noshow_followup_router.py tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py` -> `103 passed`.
  - Targeted frontend operator-flow run on isolated local server is only partially green: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3101 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|manager history modes hide queue views and keep owner scope role-gated|manage and apply action macro|action feedback hides raw sync reason codes and keeps reopen internal-only|booking no-show reopens resolved case and preserves case-booking semantics"` -> `4 passed`, `1 failed`; failing assertion: `inbox-list` width `0` in `inspect first case`.
- `Five Whys`:
  1. Why is the first screen noisy? Because multiple domains are rendered inline together: queue mode, filters, saved views, share, display prefs, bulk actions, follow-up governance.
  2. Why are these domains inline? Because every new maturity feature was attached to the same surface orchestrators instead of being decomposed into primary/secondary surfaces.
  3. Why did that happen? Because Waves24-30 correctly prioritized server-owned correctness and governance contracts first.
  4. Why is the UX now failing despite correct contracts? Because interaction architecture was not rebuilt after those contracts landed.
  5. Why is this risky now? Because backend coverage is stronger than frontend workflow/layout coverage, so interaction regressions can ship while contract tests stay green.
- `Root cause statement`: the remaining defect is not missing server truth; it is surface orchestration debt. `CaseList` and `calendar/page.tsx` are overgrown operator shells that leak control/state complexity directly onto the first screen.
- `Fix mechanism`: freeze further maturity add-ons, decompose the surfaces into primary queue header + secondary drawers/sheets/panels, and add explicit workflow/layout proof for the new operator paths.

## Plan (1..N)
1. Record audit evidence for screen anatomy, code hotspots, and current coverage.
2. Translate findings into canonical backlog items and one artifact report.
3. Update master/session/state docs so Wave32 becomes the active owner-approved next block.
4. Define the next bounded implementation waves for surface simplification and operator proof.

## DoD
- There is one explicit audit artifact covering both visual and functional debt.
- `UX_BACKLOG` includes open items for Inbox density, Calendar density, and operator coverage gaps.
- Master/session/state/structure docs all point to Wave32 as the active next block.
- The next execution order is explicit and blocks further routing work until operator-surface debt is addressed.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && wc -l console-web/src/components/CaseList.tsx console-web/src/app/calendar/page.tsx`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "cases-saved-views|cases-filter-compact-layout|cases-bulk-toolbar|calendar-queue-controls|calendar-saved-views|calendar-follow-up-governance-card" console-web/src/components/CaseList.tsx console-web/src/app/calendar/page.tsx`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1/truffles-api && pytest -q tests/test_console_saved_views_api.py tests/test_console_queue_state_api.py tests/test_calendar_noshow_followup_router.py tests/test_console_cases_helpers.py tests/test_console_routing_profiles_api.py`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1/console-web && PLAYWRIGHT_BASE_URL=http://localhost:3101 npx playwright test e2e/inspect_case.spec.ts --project chromium --grep "inspect first case|manager history modes hide queue views and keep owner scope role-gated|manage and apply action macro|action feedback hides raw sync reason codes and keeps reopen internal-only|booking no-show reopens resolved case and preserves case-booking semantics"`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && python3 scripts/check_console_audit_governance.py --pretty`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `console-web/test-results/inspect_case-inspect-first-case-chromium/error-context.md`
- `103 passed` backend contract suite
- `4 passed / 1 failed` targeted operator Playwright lane on isolated `http://localhost:3101`

## Release safety (mandatory)
- `Rollout`: docs-only audit; no runtime rollout.
- `Go/no-go`: merge only if canon points to the same next block and audit governance/session checks stay green.
- `Rollback`: revert docs-only changeset and restore previous task-package pointer.

## Rollback
- `git revert REVISION_SHA`
- Re-run `python3 scripts/check_console_audit_governance.py --pretty` and `SESSION_AGENT=a1 scripts/session_check.sh`.

## No-go
- Do not solve this block with cosmetic spacing-only tweaks.
- Do not add more inline controls to `CaseList` or `calendar/page.tsx` before decomposition.
- Do not reopen routing v2/capability work while first-screen action hierarchy is unresolved.

## Риски/блокеры
- If Wave32 is ignored, the team will keep shipping correct server contracts on top of a degraded operator surface.
- If coverage remains backend-heavy and frontend-light, layout/interaction regressions will continue to escape.
- If saved views/share/presets stay inline, medium-width and mobile-adjacent layouts will keep wrapping and competing.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: no runtime fix yet; operator surface debt remains open after the audit.
- `Why not in this block`: this block exists to prevent another round of blind spot fixes and to define the real next execution slices.
- `Risk if deferred`: more controls will accumulate on already crowded surfaces and routing/governance work will keep overshadowing usability.
- `Linked follow-up Task Package(s)`: expected follow-ups are `Wave33` (Inbox surface decomposition), `Wave34` (Calendar surface decomposition), `Wave35` (operator workflow/layout proof).
- `Expiry/trigger to stop deferral`: any new user-facing Inbox/Calendar feature request must first map to one of the Wave33-35 follow-ups or explicitly supersede this audit.

## Next-block contract (mandatory)
- `Next block objective`: execute Wave33 Inbox surface decomposition: first-screen reduction, saved-view/share extraction into secondary surfaces, and bulk-action demotion from inline panels to a dedicated sheet.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave32|Wave33|UX-34|UX-35|UX-36" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md`
- `Blocked-by conditions`: any attempt to add more inline actions, skip e2e/layout proof, or continue routing expansion before surface decomposition blocks immediately.
- `Owner role for closure`: Brain / Top Architect.
