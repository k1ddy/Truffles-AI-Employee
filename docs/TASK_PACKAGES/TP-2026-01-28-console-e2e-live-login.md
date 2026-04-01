# TP-2026-01-28 — console-e2e-live login stabilization

- Title/goal: stabilize Playwright live login flow when Keycloak provider form is missing/redirected, so console-e2e-live passes.
- Canon refs: `STATE.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant: no auth/RBAC changes; no disabling or bypassing live e2e; storageState remains deterministic.
- Scope: console-web Playwright global setup login flow only.
- Out of scope: backend/auth config changes, CI workflow changes, product UI.
- Touch-list:
  - `console-web/e2e/global-setup.ts`
  - `STATE.md`, `docs/SESSIONS/SESSION-2026-01-28-console-e2e-live-login-a2.md`, `docs/SESSION_INDEX.md`
- Plan:
  1) Add GAP to `STATE.md` with CI evidence (Keycloak provider form timeout).
  2) Update login flow to handle direct redirect/no provider form and already-authenticated state.
  3) Run `npm --prefix console-web run lint`.
  4) Commit, PR, CI (workflow_dispatch), capture run URL.
  5) Update `STATE.md` to DONE with CI evidence before merge.
- DoD:
  - console-e2e-live passes in CI.
  - storageState is created without bypassing auth.
  - No changes outside Playwright harness.
- Checks: `npm --prefix console-web run lint`.
- Evidence: CI run URL + failing/green job logs; `STATE.md` updated with evidence.
- Rollback: revert PR merge commit.
- No-go: disabling live e2e, bypassing login, auth provider changes.
- Branch / Worktree:
  - Branch: `feat/2026-01-28-console-e2e-live-login-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-console-e2e-live-login-a2`
  - Base ref: `origin/main`
  - Merge policy: PR (no rebase)
  - Cleanup: delete branch/worktree after merge
