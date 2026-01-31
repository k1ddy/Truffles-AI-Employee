# Task Package: Inbox UX v3 fixes (adaptive queue + nav collapse + macros error)

Title/Goal
- Improve Inbox UX v3 by making the queue adaptive when a case is open, fixing chat frame/double border, restoring reliable nav collapse, and unblocking quick replies.

Canon refs
- AGENTS.md
- STATE.md (add GAP for queue width + quick replies error + chat frame/double border + nav collapse)
- SPECS/CONTROL_PLANE.md

Invariant
- UI-only changes (console-web); no API/RBAC/DB changes.
- Selection gates stay fail-closed.
- Case take/resolve/send behavior unchanged.

Scope
- Adaptive queue width when a case is open (variant 3) + compact filters in queue.
- Fix chat frame/double border in Inbox and single-case view.
- Make details toggle/hide action obvious.
- Restore sidebar collapse (icons-only) and slightly reduce sidebar width.
- Fix quick replies load UX (selection-aware + resilient error state).

Out of scope
- Backend/DB/contract changes.
- Role model changes.
- Layout changes outside ConsoleShell/Inbox/Case views.

Touch-list
- console-web/src/components/ConsoleShell.tsx
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseView.tsx
- console-web/src/components/CaseConversation.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/CaseList.tsx
- console-web/src/components/InboxMacros.tsx
- console-web/e2e/smoke.spec.ts
- console-web/src/app/globals.css (only if needed)
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-inbox-ux-v3-fix-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-v3-fix.md

Plan
1) Record GAP in STATE.md for queue width + macros error + chat frame/double border + nav collapse.
2) Adjust Inbox grid widths for open/closed case; tighten queue column on open case.
3) Compact queue filters when case is open (toggle or collapse).
4) Fix chat frame/double border in Inbox and Case view.
5) Make details toggle obvious (header and panel close action).
6) Restore sidebar collapse behavior + reduce width slightly.
7) Improve quick replies error UX (selection-aware message + retry).
8) Stabilize console-e2e-live locator for case navigation (avoid strict-mode collisions).
9) Run console-web lint and capture evidence.

DoD
- Queue width shrinks when case selected; list remains readable.
- Filters occupy minimal vertical space when case open.
- Chat frame renders with single border/rounded shape.
- Details toggle is easy to find and closes panel reliably.
- Sidebar collapses to icons and expands back; width reduced slightly.
- Quick replies load without generic error (clear selection guidance + retry).

Checks
- npm --prefix console-web run lint

Evidence
- Lint output file.
- Screenshot(s) for: queue width open/closed + chat frame + details toggle + sidebar collapsed.
- STATE.md updated with GAP + resolution evidence (Top Architect).

Rollback
- git revert COMMIT_SHA

No-go
- Any API/DB/RBAC changes.
- Weakening tenant selection gates.

Branch
- feat/2026-01-30-inbox-ux-v3-fix-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-ux-v3-fix-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Over-compressing queue filters may reduce scanability; keep summary visible.
