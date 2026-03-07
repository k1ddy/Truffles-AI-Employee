# TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-live-proof-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-LIVE-PROOF-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1
- `UNLOCKS`: final semantic program closeout after explicit live proof

## Название/цель
Закрыть последний оставшийся blocker программы: получить live no-mocks evidence по explicit safe case и не допустить fake-pass, если safe case для мутации не предоставлен.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`
- `docs/runbooks/INBOX_SEMANTIC_WAVE22_VALIDATION.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: one bounded follow-up PR if code/reporting clarity changes; otherwise closure by evidence only
- `Cleanup`: Brain / Top Architect after final live closeout

## One web search (mandatory before implementation)
- **Query (exact):** `site:playwright.dev annotations skip test official playwright`
- **Date/time (local):** `2026-03-07T15:01:56+05:00`
- **Sources opened:**
  - `https://playwright.dev/docs/test-annotations`
- **Ready solutions found:** Playwright supports declaration-time tags/annotations and runtime `test.info().annotations` for machine-readable blocker reasons in reporter output.
- **Decision (`reuse/integrate/build`):** `integrate` — keep the current live validation lane but add machine-readable tags and blocker annotations instead of inventing a separate reporting path.
- **Rejected options:** free-text skip reasons only; separate custom reporter just for this blocker.
- **Source quality:** high-signal primary source = official Playwright documentation.

## Root cause (mandatory)
- **Symptom:** deterministic proof is merged, but the last live mutation proof can still look ambiguous in CI/output when no safe live case exists.
- **Minimal reproduction:** run the live validation lane without `INSPECT_CASE_LIVE_CASE_ID`; the result is intentionally skipped, but without explicit follow-up canon it remains easy to misread as completion.
- **Evidence:** `PR #944` merged Wave22 deterministic proof; targeted live lane still returns `1 skipped` without a safe case.
- **Five Whys:** the program needs one more bounded closure step because the remaining uncertainty is operational evidence, not product code semantics.
- **Root cause statement:** the only open gap is explicit live mutation evidence on a safe case; until that case exists, the program must stay in a precise blocked state instead of being silently treated as closed.
- **Fix mechanism:** split live proof into its own closure TP, annotate the test lane with machine-readable blocker reasons, and require explicit pass/fail/blocked evidence.

## Invariant
- No mutation against an unknown live case.
- No fake green from skipped live proof.
- Deterministic proof from `PR #944` remains the baseline and is not weakened.

## Scope
- machine-readable blocker annotations/tags in the existing live validation test
- canon split for the remaining live-proof blocker
- explicit closure criteria for safe-case validation

## Out of scope
- new product features
- changing inbox/calendar semantics already merged via Waves 20-22

## Touch-list
- `console-web/e2e/inspect_case.spec.ts`
- `docs/runbooks/INBOX_SEMANTIC_WAVE22_VALIDATION.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md`

## Plan
1. Split the remaining live-proof blocker into a dedicated TP in canon.
2. Tag/annotate the live validation test so reporter output carries exact blocker semantics.
3. Re-run lint + deterministic `inspect_case` + targeted live lane.
4. Keep the block open until Brain/Top Architect provide or approve a safe live case id.

## DoD
- Canon no longer implies Wave22 is fully closed after `PR #944`.
- Live proof test emits machine-readable blocker metadata.
- Targeted checks are green locally, and live lane is explicitly `blocked` without safe case.

## Checks
- `cd console-web && npm run lint -- --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line --workers=1`
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --grep @wave22-live-proof --project=chromium --reporter=line --workers=1`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- updated `inspect_case` reporter metadata for the live-proof lane
- deterministic and targeted live test output
- session/master TP note that classifies the program as `blocked` until a safe live case exists

## Rollback
- revert the live-proof annotation/doc split if it destabilizes the current validation lane

## No-go
- Treat `skip` without blocker classification as closure.
- Run the live lane on an arbitrary customer case.
- Open a new product wave while this blocker is unresolved.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: only the need for a safe explicit live case id provided by Brain/Top Architect.
- `Why not in this block`: safe-case selection is an operational approval step, not an engineering-only implementation detail.
- `Risk if deferred`: the semantic program stays operationally unclosed even though merged product semantics are green.
- `Linked follow-up Task Package(s)`: none beyond this closure block.
- `Expiry/trigger to stop deferral`: once a safe explicit live case id is available, this block must be executed immediately.

## Next-block contract (mandatory)
- `Next block objective`: run and classify the real live mutation proof on the approved safe case.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line --workers=1`
- `Blocked-by conditions`: no approved safe live case id; live auth env unavailable.
- `Owner role for closure`: Brain / Top Architect.
