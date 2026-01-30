# Task Package: Inbox UX implementation (UI)

Title/Goal
- Implement Inbox UX standard in Console UI so case handling is faster, clearer, and diagnostics are gated.

Invariant
- UI-only changes; no API/RBAC/DB changes.
- Tenant selection stays fail-closed; no cross-tenant data.
- Diagnostics remain available but hidden by default for operators.

Scope
- Update Inbox UI layout to match the standard (queue signals, quick replies near composer, context strip, details tabs, diagnostics gating, RU copy, responsive behavior).
- Bring in the Inbox UX standard docs/spec if not already in main.

Out of scope
- Backend, DB, contracts, RBAC changes.
- Changes to other tabs (Knowledge/Team/Settings) beyond copy clarity.

Touch-list
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseList.tsx
- console-web/src/components/CaseConversation.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/InboxMacros.tsx
- console-web/src/components/CaseDetailsPanel.tsx
- console-web/src/app/cases/[id]/page.tsx (if needed)
- SPECS/CONTROL_PLANE.md
- docs/REPORTS/2026-01-30-inbox-ux-standard.md
- STRUCTURE.md
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-inbox-ux-implementation-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-implementation.md

Plan
1) Review current Inbox UI and map gaps to the standard.
2) Rework queue header/filters and list signals (sticky header, less noise).
3) Move quick replies to composer area; add context strip above chat.
4) Convert details into tabs (Context/Case/Consultant) + Diagnostics tab gated by role.
5) RU copy pass; responsive layout (3-pane -> 2-pane -> tabs).
6) Run checks; capture evidence; update STATE.md.

DoD
- Layout follows standard; diagnostics hidden by default.
- Quick replies are near composer; context strip present.
- No duplicate branch filter; RU copy for operator UI.
- No regressions in take/resolve/send.

Checks
- npm --prefix console-web run lint
- npm --prefix console-web run test:e2e:smoke (if creds available)

Evidence
- Screenshot(s) of Inbox new layout (paths recorded).
- Lint output and e2e output (or explicit waiver if blocked).
- Update STATE.md with evidence pointers.

Rollback
- git revert COMMIT_SHA

No-go
- Any API/RBAC/DB changes.
- Removing diagnostics entirely.
- Weakening selection gates.

Branch
- feat/2026-01-30-inbox-ux-implementation-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-ux-implementation-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Responsive layout regression in 3-pane grid.
- Existing diagnostics data may be sparse; ensure empty states are clear.
