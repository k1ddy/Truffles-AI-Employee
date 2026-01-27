# SESSION 2026-01-27-console-ux-selection — Console UX selection + E2E recovery

- status: active
- owner: Hands
- task_package: docs/TASK_PACKAGES/TP-2026-01-27-console-ux-selection.md
- branch: feat/console-ux-selection
- worktree: /home/zhan/worktrees/console-ux-selection
- base_ref: origin/main
- scope: Improve console context selection UX and make console-e2e resilient to profile load retries.
- done:
  - Added profile retry handling + selection fallback in Playwright login/smoke tests.
  - Verified console-web lint passes.
- next:
  - Wait for CI on PR #401 and merge if green.
  - Continue UX polish after merge (Inbox/Knowledge follow-ups).
- evidence:
  - `npm --prefix console-web run lint`
- last_updated: 2026-01-27
