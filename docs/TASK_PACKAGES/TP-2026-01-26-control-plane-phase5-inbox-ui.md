Title: Control Plane Phase 5 — Inbox UX (3-pane + Explain/Trace + Macros)
Owner: Top Architect
Date: 2026-01-26

Canon refs:
- SPECS/CONTROL_PLANE.md (Inbox UX scope + Phase 5)
- docs/CONSOLE_GUIDE.md (Inbox UI contract + routes)
- STRATEGY/REQUIREMENTS.md (quality + role safety)
- STATE.md (Control Plane roadmap)

Invariant:
- Fail-closed tenant context (selection_required / branch_selection_required).
- Role-gated navigation (owner/admin/manager/support) stays unchanged.
- No backend/API changes; only console-web UI.

Scope:
- Build Inbox 3-pane layout inside ConsoleShell (list + conversation + details).
- Integrate CaseList selection with CaseView details on the same screen.
- Add detail cards: Context, Explain, Trace, Telegram trail (collapsible, empty state allowed).
- Add Macros panel (quick replies) that can prefill message input.

Out of scope:
- Any backend changes or new endpoints.
- Macro persistence, analytics, or message templates CRUD.
- Realtime sync (websocket), SLA backend logic, or ops integrations.

Touch-list (files/tables):
- console-web/src/app/page.tsx
- console-web/src/components/CaseList.tsx
- console-web/src/components/CaseView.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/* (new Inbox UI pieces)
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-01-26-control-plane-phase5-inbox-ui.md
- STATE.md
- STRUCTURE.md

Plan:
1) Add Task Package + update STRUCTURE/STATE.
2) Create Inbox layout shell (3-pane) and route-level structure.
3) Wire CaseList selection into CaseView (selected case drives middle + right panes).
4) Add Explain/Trace/Context/Telegram cards with collapse + empty state.
5) Add Macros panel and hook it to ChatInterface draft input.
6) Update docs + run lint.

DoD:
- Inbox shows 3-pane layout with list + conversation + details.
- Selecting a case updates conversation and details in-place.
- Explain/Trace/Context/Telegram cards visible with empty state.
- Macros can prefill the reply input.
- No backend/API changes.
- Lint passes.

Checks:
- npm --prefix console-web install
- npm --prefix console-web run lint

Evidence:
- Lint output.
- Manual UI smoke in local console (screenshot optional) for Inbox 3-pane.

Rollback:
- Revert console-web UI changes.

No-go:
- Do not change backend routes, schemas, or DB.
- Do not weaken RBAC or selection gating.

Branch/Worktree:
- Branch: feat/control-plane-phase5-inbox-ui
- Worktree: /home/zhan/worktrees/control-plane-phase5-inbox-ui
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch/worktree after merge
