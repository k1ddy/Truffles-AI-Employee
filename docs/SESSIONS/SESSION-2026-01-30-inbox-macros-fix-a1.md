# SESSION 2026-01-30-inbox-macros-fix-a1 — Session 2026-01-30-inbox-macros-fix-a1

- status: done
- owner: Top Architect / Brain / Hands
- task_package: docs/TASK_PACKAGES/TP-2026-01-30-inbox-macros-fix.md
- branch: feat/2026-01-30-inbox-macros-fix-a1
- worktree: /home/zhan/worktrees/2026-01-30-inbox-macros-fix-a1
- base_ref: origin/main
- scope: Fix Inbox macros load error + remove double chat border in Console Inbox.
- done:
  - Session created.
  - Applied `truffles-api/migrations/017_add_console_macros.sql` on prod (console_macros table created).
  - Updated Inbox chat frame to avoid double border; added retry for macros load error.
  - Local lint failed: `next` binary missing (`npm --prefix console-web run lint`).
- next:
  - Run lint (or CI), push branch, update STATE.md with evidence.
- evidence:
  - docs/TASK_PACKAGES/TP-2026-01-30-inbox-macros-fix.md
  - /tmp/console_macros_migration_20260130.txt
- last_updated: 2026-01-30
