Title: DEC-014 Production Go/No-Go for live customers
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- STATE.md (facts/evidence)
- SPECS/CONTROL_PLANE.md (Control Plane scope)
- docs/IMPERIUM_DECISIONS.yaml (DEC registry)
- STRATEGY/REQUIREMENTS.md (quality gates)

Invariant:
- No behavior or API changes.
- Documentation only; no infra changes.

Scope:
- Add DEC for production readiness/go-no-go.
- Add Control Plane section for live-customer readiness checklist.
- Record status in STATE.md.

Out of scope:
- Fixing console-web build errors.
- Deployments or CI changes.

Touch-list (files/tables):
- docs/IMPERIUM_DECISIONS.yaml
- SPECS/CONTROL_PLANE.md
- STATE.md
- docs/TASK_PACKAGES/TP-2026-01-25-prod-gonogo-dec.md
- STRUCTURE.md

Plan:
1) Add DEC-014 in `docs/IMPERIUM_DECISIONS.yaml`.
2) Add "Production Go/No-Go" section to `SPECS/CONTROL_PLANE.md`.
3) Update `STATE.md` with plan/fact status.

DoD:
- DEC-014 added and referenced from Control Plane.
- STATE updated (FACT only with evidence; otherwise PLAN).

Checks:
- None (docs-only).

Evidence:
- PR/commit link after merge.

Rollback:
- Revert doc changes.

No-go:
- No code changes in this task.

Branch/Worktree:
- Branch: docs/dec-prod-gonogo
- Worktree: /home/zhan/worktrees/dec-prod-gonogo
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
