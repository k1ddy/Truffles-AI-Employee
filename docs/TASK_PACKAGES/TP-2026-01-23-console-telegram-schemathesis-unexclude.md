Title: Remove Schemathesis exclude for /telegram/health after deploy
Owner: Top Architect
Date: 2026-01-23

Canon refs:
- STATE.md (CI status + evidence)
- AGENTS.md (stop-the-line + one-issue flow)
- contracts/console_api/openapi.v1.yaml (contract source of truth)
- .github/workflows/ci.yml (console-contract job)

Invariant:
- Contract smoke must reflect real prod behavior (no permanent exclusions).
- No changes to core webhook pipeline behavior.

Scope:
- Remove `--exclude-path /telegram/health` from console-contract CI step.
- Record evidence that /console/v1/telegram/health is live on prod.

Out of scope:
- Any backend changes or deployments.

Touch-list (files/tables):
- .github/workflows/ci.yml
- docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-schemathesis-unexclude.md
- STRUCTURE.md
- STATE.md

Plan:
1) Verify /console/v1/telegram/health returns 200 on prod.
2) Remove Schemathesis exclude from CI workflow.
3) Run CI and record evidence in STATE.md.

DoD:
- console-contract job tests /telegram/health and passes.
- CI green; evidence recorded in STATE.md.

Checks:
- CI run (workflow_dispatch on main).

Evidence:
- curl result (HTTP 200) + CI run URL in STATE.md.

Rollback:
- Re-add the exclude line if /telegram/health breaks again.

No-go:
- Leaving the exclusion without evidence-based reason.

Branch/Worktree:
- Branch: fix/remove-telegram-health-exclude
- Worktree: /home/zhan/truffles-main
- Base: main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
