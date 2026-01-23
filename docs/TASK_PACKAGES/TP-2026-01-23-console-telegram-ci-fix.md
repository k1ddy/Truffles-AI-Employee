Title: CI fix for Console Telegram changes (ruff import + schemathesis exclude)
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (STOP-LINE: CI failures run 21276341412)
- AGENTS.md (stop-the-line + one-issue flow)
- contracts/console_api/openapi.v1.yaml (contract source of truth)
- contracts/console_api/schemathesis.toml (schemathesis config)
- .github/workflows/ci.yml (CI contract checks)

Invariant:
- No changes to core webhook pipeline behavior.
- Contract remains truth-first; temporary test exclusion must be explicit and documented.

Scope:
- Fix ruff import ordering in truffles-api/app/routers/console.py.
- Exclude /telegram/health from Schemathesis GET-only smoke until API is deployed.
- Record CI failure details and remediation in STATE.md.

Out of scope:
- Deploy to prod.
- Removing /telegram/health from the contract.

Touch-list (files/tables):
- truffles-api/app/routers/console.py
- .github/workflows/ci.yml
- docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-ci-fix.md
- STRUCTURE.md
- STATE.md

Plan:
1) Fix ruff import order in console router.
2) Add Schemathesis exclude for /telegram/health in CI command.
3) Record rationale + removal condition in STATE.md.
4) Rerun CI.

DoD:
- ruff passes for app/tests.
- console-contract job no longer fails on /telegram/health 404.
- CI green or only known waivers; STATE.md updated with evidence.

Checks:
- ruff check app tests
- CI run (workflow_dispatch)

Evidence:
- CI run URL + failed job/step/logs if any.
- STATE.md updated with stop-line and resolution.

Rollback:
- Revert import ordering + CI exclude.

No-go:
- Hiding failures without documenting waiver and removal condition.

Risks/Blockers:
- Endpoint not deployed; exclusion must be removed after deploy.

Branch/Worktree:
- Branch: feature/console-telegram-p0
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
