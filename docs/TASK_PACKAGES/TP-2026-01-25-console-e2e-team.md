Title: Console E2E fix — Settings Team link + Team page
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- AGENTS.md (process + stop-line)
- STATE.md (facts/evidence)
- docs/CONSOLE_GUIDE.md (UI map)

Invariant:
- Do not change production behavior.
- Keep role gating intact; only adjust smoke expectations.

Scope:
- Update Playwright smoke to match new Team UI location.
- Validate Team page is reachable from Settings.

Out of scope:
- UI or API changes.
- New E2E scenarios beyond smoke.

Touch-list (files/tables):
- console-web/e2e/smoke.spec.ts
- docs/TASK_PACKAGES/TP-2026-01-25-console-e2e-team.md
- STRUCTURE.md

Plan:
1) Update Settings smoke test to expect Team link.
2) Add Team page visibility check.
3) Run lint.

DoD:
- console-e2e smoke no longer expects settings-team rows.
- Team page is covered by smoke check.
- Lint passes.

Checks:
- npm --prefix console-web run lint

Evidence:
- CI run URL + failed-to-pass delta in console-e2e.

Rollback:
- Revert test changes.

No-go:
- Do not bypass tests by weakening selectors unrelated to Team UI.

Branch/Worktree:
- Branch: fix/console-e2e-team
- Worktree: /home/zhan/worktrees/console-e2e-team
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
