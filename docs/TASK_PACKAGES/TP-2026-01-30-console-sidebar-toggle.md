# Task Package: Console sidebar toggle + Inbox details usability

Title/Goal
- Make the left navigation slimmer, add a collapsible icon-only mode, and fix Inbox details behavior so the chat stays usable.

Canon refs
- AGENTS.md
- STATE.md (add GAP: "Inbox UX sidebar/details/chat неудобны")
- SPECS/CONTROL_PLANE.md
- docs/REPORTS/2026-01-30-inbox-ux-standard.md

Invariant
- UI-only changes; no API/RBAC/DB changes.
- Tenant/branch selection remains fail-closed.
- Take/resolve/send behavior unchanged.

Scope
- Reduce sidebar width without breaking existing visual language.
- Add collapse/expand mode with icon-only nav labels.
- Keep chat layout stable when opening details on smaller screens.
- Make "Hide details" control easy to find and understand.

Out of scope
- Backend/DB/contract changes.
- Role model changes.
- Changes to other pages beyond layout navigation and Inbox behavior.

Touch-list
- console-web/src/components/ConsoleShell.tsx
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseConversation.tsx (if needed)
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-console-sidebar-toggle-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-console-sidebar-toggle.md

Plan
1) Record GAP in STATE.md for the sidebar/details/chat UX issues.
2) Adjust sidebar width and add a collapse toggle with icon-only nav.
3) Fix Inbox details drawer/overlay on small screens so chat stays usable.
4) Improve "Hide details" affordance in the Inbox flow.
5) Run checks and capture evidence.

DoD
- Sidebar is slimmer and supports collapse/expand with clear icons.
- Chat remains usable after opening details on smaller screens.
- "Hide details" is easy to find and use.
- No regressions in core actions.

Checks
- npm --prefix console-web run lint
- npm --prefix console-web run test:e2e:smoke (waived: requires console creds)

Evidence
- Lint output.
- Screenshots of sidebar expanded/collapsed and Inbox with details open.
- STATE.md updated with GAP + resolution evidence (Top Architect).

Rollback
- git revert COMMIT_SHA

No-go
- Any API/DB/RBAC changes.
- Weakening tenant selection gates.

Branch
- feat/2026-01-30-console-sidebar-toggle-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-console-sidebar-toggle-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Collapsed nav may reduce discoverability; icons must be clear and labeled via tooltip.
- Responsive layout regressions on small screens.
