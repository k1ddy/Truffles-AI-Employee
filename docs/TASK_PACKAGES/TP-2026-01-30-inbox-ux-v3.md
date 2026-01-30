# Task Package: Inbox UX v3 (chat-first clarity)

Title/Goal
- Make Inbox handling obvious and fast: wider chat, quick replies at composer, clear RU labels, details tabs (Context/Case/Consultant), diagnostics hidden.

Canon refs
- AGENTS.md
- STATE.md (NOW: Inbox UX marked DONE; add GAP for "Inbox UX still uncomfortable" in this session)
- SPECS/CONTROL_PLANE.md (Inbox UX standard)
- docs/REPORTS/2026-01-30-inbox-ux-standard.md

Invariant
- UI-only changes; no API/RBAC/DB changes.
- Tenant/branch selection remains fail-closed.
- Take/resolve/send behavior unchanged.

Scope
- Rework Inbox layout per standard with chat-first width and context strip.
- Move quick replies/macros next to composer; ensure macros manageable.
- Details tabs for Context/Case/Consultant; diagnostics gated by role.
- RU operator copy; remove tech labels from primary UI.

Out of scope
- Backend/DB/contract changes.
- Role model changes.
- Changes to other pages beyond copy alignment.
- Build metadata wiring (Settings build info).

Touch-list
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseView.tsx
- console-web/src/components/CaseConversation.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/CaseDetailsPanel.tsx
- console-web/src/components/InboxMacros.tsx
- console-web/src/components/CaseList.tsx
- console-web/src/app/globals.css (if needed)
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-inbox-ux-v3-a1.md
- docs/SESSION_INDEX.md
- docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-v3.md

Plan
1) Record GAP in STATE.md for "Inbox UX still uncomfortable".
2) Review current Inbox UI vs standard and user feedback.
3) Adjust layout to widen chat and reposition quick replies near composer.
4) Refactor details into tabs and gate diagnostics by role.
5) RU copy pass; ensure no cross-tab leakage.
6) Run checks and capture evidence.

DoD
- Chat area is wider and readable.
- Quick replies sit next to composer and are actionable.
- Details tabs are clear and in RU; diagnostics hidden by default.
- No regressions in core actions.

Checks
- npm --prefix console-web run lint

Evidence
- Lint output.
- Screenshot(s) of Inbox layout and details tabs.
- STATE.md updated with GAP and resolution evidence (Top Architect, pre-merge).

Rollback
- git revert COMMIT_SHA

No-go
- Any API/DB/RBAC changes.
- Removing diagnostics entirely.
- Changing selection gating.

Branch
- feat/2026-01-30-inbox-ux-v3-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-ux-v3-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Layout regressions in small widths; need careful responsive checks.
