Title: Console Contract — Unexclude Knowledge Endpoints
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- contracts/console_api/openapi.v1.yaml
- docs/CONSOLE_GUIDE.md
- TECH.md (deploy verify)

Invariant:
- Console contract smoke must reflect prod; no false green/false red.
- Do not change API behavior or schemas.

Scope:
- Remove temporary Schemathesis excludes for /knowledge/current and /knowledge/history.

Out of scope:
- Any API code changes or DB migrations.
- Changes to CI deploy/livecheck logic.

Touch-list (files):
- .github/workflows/ci.yml
- docs/TASK_PACKAGES/TP-2026-01-25-console-contract-knowledge-unexclude.md
- STRUCTURE.md
- STATE.md (Brain only, end)

Plan:
1) Remove /knowledge/* excludes from Schemathesis job in ci.yml.
2) Open PR and run CI.
3) Record evidence (CI run URL) in STATE.md.

DoD:
- Schemathesis includes /knowledge/current and /knowledge/history.
- CI green on main after merge.

Checks:
- CI run on PR.

Evidence:
- CI run URL with console-contract job green.

Rollback:
- Revert the ci.yml change.

No-go:
- Do not modify OpenAPI or API code in this change.

Risks/Blockers:
- Prod API not yet updated would cause Schemathesis 404.

Branch/Worktree:
- Branch: ops/console-contract-knowledge-unexclude
- Worktree: /home/zhan/truffles-main
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
