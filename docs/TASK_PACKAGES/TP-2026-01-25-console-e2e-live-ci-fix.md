Title: Fix console-e2e-live CI (Keycloak login/storageState)
Owner: Brain
Date: 2026-01-25

Canon refs:
- AGENTS.md (stop-the-line + Task Package requirement)
- STATE.md (console-e2e-live red CI blocker)
- docs/CONSOLE_GUIDE.md (E2E auth flow + secrets)
- .github/workflows/ci.yml (console-e2e-live job)
- console-web/e2e/* (Playwright tests)

Invariant:
- Do not weaken auth or bypass Keycloak in production.
- Do not commit secrets or credentials.
- No changes to core webhook pipeline behavior.

Scope:
- Diagnose and fix console-e2e-live job (login/storageState/redirect stability).
- Adjust Playwright config/tests/CI env as needed for reliable auth.
- Update docs/STATE.md evidence after CI green.

Out of scope:
- Feature work in Console UI or Console API.
- Changing production Keycloak config beyond test-specific redirect URIs.

Touch-list (files/tables):
- .github/workflows/ci.yml
- console-web/e2e/*
- console-web/playwright.config.ts (if required)
- docs/CONSOLE_GUIDE.md (only if test flow changes)
- STATE.md

Plan:
1) Review console-e2e-live CI logs and current Playwright setup.
2) Reproduce/login flow using configured env; identify failure point (redirect/storageState).
3) Apply minimal fix (waits, baseURL, storageState generation, or CI env).
4) Run targeted e2e smoke locally if creds available.
5) Push PR, run CI, record evidence in STATE.md.

DoD:
- console-e2e-live passes on CI for PR and main.
- No secrets in git diff.
- Any behavioral change documented in STATE.md with evidence.

Checks:
- npm --prefix console-web run test:e2e:smoke (when creds available)
- CI: console-e2e-live job green

Evidence:
- CI run URL + console-e2e-live logs.
- STATE.md updated with evidence entry.

Rollback:
- Revert Playwright/CI adjustments and re-run CI.

No-go:
- Skipping CI or hiding failures without documenting waiver/removal condition.

Risks/Blockers:
- Missing or rotated Keycloak creds for CI.
- Keycloak redirect URIs not aligned with test baseURL.

Branch/Worktree:
- Branch: fix/console-e2e-live
- Worktree: /home/zhan/worktrees/console-e2e-live
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch/worktree after merge
