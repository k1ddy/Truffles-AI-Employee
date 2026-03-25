# Task Package: Console sidebar toggle deploy + verify

Title/Goal
- Merge PR #458, run console-web lint, deploy console-web, and capture evidence for the sidebar toggle + Inbox details overlay.

Canon refs
- AGENTS.md
- STATE.md (NOW: add DONE for deploy evidence)
- SPECS/CONTROL_PLANE.md
- docs/TASK_PACKAGES/TP-2026-01-30-console-sidebar-toggle.md

Invariant
- No code changes; deploy only.
- Selection gates remain fail-closed.

Scope
- Merge PR #458.
- Install console-web deps and run lint.
- Deploy console-web and verify build info.
- Update STATE + session log with evidence.

Out of scope
- Any new UI/code changes.
- API/DB/RBAC changes.

Touch-list
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-console-sidebar-toggle-deploy-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-console-sidebar-toggle-deploy.md

Plan
1) Merge PR #458 (sidebar toggle + details overlay).
2) Pull latest main into deploy worktree.
3) Install deps and run lint; save output to /tmp.
4) Run console-web deploy script; capture build info evidence.
5) Update STATE + session log; close session.

DoD
- PR #458 merged.
- Lint run recorded (or explicit block reason logged).
- console-web running with new build info evidence.
- STATE updated with evidence pointers.

Checks
- npm --prefix console-web install
- npm --prefix console-web run lint

Evidence
- Lint output file in /tmp.
- Build info evidence (bundle or settings build info).
- STATE updated with deploy line + evidence pointers (Top Architect).

Rollback
- git revert MERGE_COMMIT_SHA

No-go
- Any code edits in this session.
- Skipping evidence capture.

Branch
- feat/2026-01-30-console-sidebar-toggle-deploy-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-console-sidebar-toggle-deploy-a1

Base ref
- origin/main

Merge policy
- No PR (doc-only updates go to main fast-forward).

Cleanup
- scripts/session_end.sh; remove worktree/branch after push.

Risks/Blockers
- npm install requires network; if blocked, record as GAP.
