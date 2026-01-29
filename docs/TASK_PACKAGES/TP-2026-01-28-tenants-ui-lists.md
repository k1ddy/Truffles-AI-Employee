# TP-2026-01-28 — Tenants UI lists (read-only)

- Title/goal: add read-only Tenants lists for companies/clients/branches with basic search and context switching.
- Canon refs: `STATE.md`, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: no backend/DB changes; no RBAC expansion for non-platform roles; selection gates remain fail-closed.
- Scope: console-web only — enhance `/tenants` page with read-only lists and search filters; use existing `/me` data.
- Out of scope: new admin list endpoints, tenant CRUD, provisioning logic changes, Knowledge UX, Trace/Explain.
- Touch-list:
  - `console-web/src/app/tenants/page.tsx`
  - `STATE.md`, `docs/SESSIONS/SESSION-2026-01-28-tenants-ui-lists-a2.md`, `docs/SESSION_INDEX.md`
- Plan:
  1) Add GAP to `STATE.md`: Tenants read-only lists missing.
  2) Extend `/tenants` UI with Companies/Clients/Branches sections.
  3) Add search filters for clients/branches and a context switch action (localStorage + refetch).
  4) Run `npm --prefix console-web run lint`.
  5) Update `STATE.md` to DONE with evidence (lint + CI URL).
  6) Update session log + index; commit, PR, CI.
- DoD:
  - Tenants page shows read-only lists for companies/clients and branches (selected client).
  - Search filters work; context switch updates selection and refreshes data.
  - Lint clean; CI green; `STATE.md` updated with evidence before merge.
- Checks: `npm --prefix console-web run lint`
- Evidence: lint output + CI run URL; `STATE.md` updated in PR.
- Rollback: revert PR.
- No-go: backend/DB changes; exposing Tenants to non-platform roles; bypassing selection gates.
- Branch / Worktree:
  - Branch: `feat/2026-01-28-tenants-ui-lists-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-tenants-ui-lists-a2`
  - Base ref: `origin/main`
  - Merge policy: PR (no rebase)
  - Cleanup: delete branch/worktree after merge
