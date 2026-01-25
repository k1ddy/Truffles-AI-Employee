Title: Control Plane Phase 4 — Team + Calendar UI
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- SPECS/CONTROL_PLANE.md (Team/Calendar scope + IA)
- SPECS/MULTI_TENANT.md (tenant context + branch scope)
- docs/CONSOLE_GUIDE.md (Console UI map + endpoints)
- STRATEGY/REQUIREMENTS.md (quality + role safety)
- STATE.md (Control Plane roadmap)

Invariant:
- Fail-closed tenant context (selection_required / branch_selection_required).
- Role-gated navigation and read-only constraints for managers.
- No changes to core webhook pipeline or booking logic.

Scope:
- Add Team page (Users + Specialists) with role-appropriate access.
- Users tab: list agents, show role/status, Telegram linking for owner/admin.
- Specialists tab: list specialists + services from /calendar/specialists.
- Calendar UI cleanup + alignment with ConsoleShell layout.
- Navigation update to include Team for owner/admin/manager.

Out of scope:
- Backend/API changes (team/specialist CRUD).
- DB migrations or data backfills.
- New capabilities or onboarding logic.

Touch-list (files/tables):
- console-web/src/components/ConsoleShell.tsx
- console-web/src/app/team/page.tsx
- console-web/src/app/calendar/page.tsx
- console-web/src/app/settings/page.tsx
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-01-25-control-plane-phase4-ui.md
- STATE.md
- STRUCTURE.md

Plan:
1) Add Task Package + update nav for Team.
2) Implement Team UI (Users + Specialists) with role gating.
3) Update Calendar UI to align with layout + remove debug noise.
4) Update docs + run lint.

DoD:
- Team page доступна из навигации и работает на owner/admin/manager.
- Users list отображает роли/статус; Telegram linking доступен owner/admin.
- Specialists list читает данные из /calendar/specialists и показывает услуги.
- Calendar UI не содержит debug-логов и визуально согласован.
- Lint проходит.

Checks:
- npm --prefix console-web install
- npm --prefix console-web run lint

Evidence:
- Lint output.
- Короткий manual UI smoke (Team + Calendar) в локальном env.

Rollback:
- Revert UI changes.

No-go:
- Не добавлять/изменять backend endpoints.
- Не менять права доступа в API.

Branch/Worktree:
- Branch: feat/control-plane-phase4-ui
- Worktree: /home/zhan/worktrees/control-plane-phase4-ui
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
