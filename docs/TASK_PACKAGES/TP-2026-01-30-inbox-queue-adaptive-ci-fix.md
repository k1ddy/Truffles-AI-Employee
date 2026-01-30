# Task Package: Inbox queue adaptive CI fix (case details visibility)

Title/Goal
- Fix PR #459 CI failure by ensuring case details are visible after selecting a case in Inbox (desktop).

Canon refs
- AGENTS.md
- STATE.md (STOP-LINE: red CI)
- docs/SESSION_START_PROMPT.txt

Invariant
- Case details are visible after selecting a case on desktop.
- E2E selectors and flows remain stable (no test-only bypass).
- No regressions in Inbox layout/actions outside the targeted fix.

Scope
- Adjust details panel visibility logic in Inbox view to default open on case selection (desktop).
- Keep details toggle behavior intact.

Out of scope
- Backend/API/DB changes.
- Data seed changes.
- Playwright test changes to bypass the failure.

Touch-list
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseConversation.tsx (only if needed)
- docs/SESSIONS/SESSION-2026-01-30-inbox-queue-adaptive-ci-fix-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-inbox-queue-adaptive-ci-fix.md
- STRUCTURE.md
- STATE.md

Plan
1) Start session on top of origin/feat/2026-01-30-inbox-queue-adaptive-a1.
2) Make details panel default visible after selecting a case (desktop), preserve toggle.
3) Run lint and capture evidence.
4) Push fix and verify CI green for console-e2e-live.

DoD
- console-e2e-live passes on PR #459.
- Case details visible after selecting a case on desktop.
- Lint clean.

Checks
- npm --prefix console-web run lint

Evidence
- CI run URL with console-e2e-live green and log snippet.
- Lint output.
- STATE.md updated by Top Architect with evidence.

Rollback
- git revert COMMIT_SHA

No-go
- Rebase.
- Test-only bypass.
- Behavior changes outside Inbox view.

Branch
- feat/2026-01-30-inbox-queue-adaptive-ci-fix-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-queue-adaptive-ci-fix-a1

Base ref
- origin/feat/2026-01-30-inbox-queue-adaptive-a1

Merge policy
- Fast-forward update to PR branch; no rebase.

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- If details panel only renders after data load, default-open must wait for case detail to avoid empty render.
