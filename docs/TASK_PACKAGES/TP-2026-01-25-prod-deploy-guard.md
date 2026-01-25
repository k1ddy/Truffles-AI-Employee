Title: Prod Deploy Guard (GHCR-only) + Runbook Updates
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- TECH.md (deploy commands)
- docs/RUNBOOK.md (API restart procedure)
- docs/DEPLOYMENT_RUNBOOK.md (Docker rules)

Invariant:
- Prod deploy stays GHCR-only; no local compose build for API on prod.
- No behavioral changes to core API/console logic.
- No changes to CI deploy workflow logic.

Scope:
- Enforce GHCR-only defaults in /home/zhan/restart_api.sh.
- Update docs to forbid prod compose builds and document GHCR-only restart.

Out of scope:
- Changes to CI/CD pipeline or path filters.
- Any code changes in truffles-api/console-web.
- New monitoring workflow (already handled separately).

Touch-list (files):
- /home/zhan/restart_api.sh
- TECH.md
- docs/RUNBOOK.md
- docs/DEPLOYMENT_RUNBOOK.md
- docs/TASK_PACKAGES/TP-2026-01-25-prod-deploy-guard.md
- STRUCTURE.md
- STATE.md (Brain only, end)

Plan:
1) Update restart_api.sh defaults to GHCR main + require GHCR by default.
2) Update TECH.md and docs runbooks to remove/forbid prod docker-compose build usage.
3) Record Task Package in STRUCTURE.md and STATE.md.
4) Open PR.

DoD:
- restart_api.sh refuses non-GHCR image unless REQUIRE_GHCR=0 is explicitly set.
- Docs explicitly state prod API deploy uses GHCR + restart_api.sh only.
- No references remain to docker-compose build for prod API.

Checks:
- None (docs/script change only).

Evidence:
- PR link + diff.

Rollback:
- Revert restart_api.sh defaults and doc updates.

No-go:
- Do not change CI deploy workflow or livecheck logic.
- Do not modify API code or DB.

Risks/Blockers:
- Users with local dev habits on prod will need to switch to GHCR workflow.

Branch/Worktree:
- Branch: ops/ghcr-deploy-guard
- Worktree: /home/zhan/truffles-main
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
