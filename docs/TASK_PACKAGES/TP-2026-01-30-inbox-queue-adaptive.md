# Task Package: Inbox queue adaptive width + chat frame fix

Title/Goal
- Make the queue adaptive (shrinks when a case is open), keep filters compact, and fix chat frame/border rendering.

Canon refs
- AGENTS.md
- STATE.md (add GAP for queue width + chat frame issue)
- SPECS/CONTROL_PLANE.md
- docs/REPORTS/2026-01-30-inbox-ux-standard.md

Invariant
- UI-only changes; no API/RBAC/DB changes.
- Tenant/branch selection remains fail-closed.
- Take/resolve/send behavior unchanged.

Scope
- Adaptive queue width when a case is selected (variant 3).
- Compact filters area to preserve space for the case list.
- Fix chat frame/border rendering when a case is open.

Out of scope
- Backend/DB/contract changes.
- Role model changes.
- Changes to other pages beyond Inbox layout.

Touch-list
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseList.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/CaseConversation.tsx (if needed)
- console-web/src/app/globals.css (if needed)
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-inbox-queue-adaptive-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-inbox-queue-adaptive.md

Plan
1) Record GAP in STATE.md for queue width + chat frame issue.
2) Adjust queue width to be adaptive when a case is open.
3) Make filters compact (toggle/pill row) to free list space.
4) Fix chat frame/border rendering for open case view.
5) Run checks and capture evidence.

DoD
- Queue width shrinks when a case is selected; list remains readable.
- Filters occupy minimal vertical space.
- Chat frame/borders render cleanly.
- No regressions in core actions.

Checks
- npm --prefix console-web run lint

Evidence
- Lint output.
- Screenshot(s) of queue width (open/closed) and chat frame fix.
- STATE.md updated with GAP + resolution evidence (Top Architect).

Rollback
- git revert COMMIT_SHA

No-go
- Any API/DB/RBAC changes.
- Weakening tenant selection gates.

Branch
- feat/2026-01-30-inbox-queue-adaptive-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-queue-adaptive-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Over-compressing queue might hurt scanability; keep visual balance.
