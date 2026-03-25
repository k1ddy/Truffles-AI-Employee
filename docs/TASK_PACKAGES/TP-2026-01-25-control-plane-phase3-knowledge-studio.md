Title: Control Plane Phase 3 — Knowledge Studio (UI)
Owner: Top Architect
Date: 2026-01-25

Canon refs:
- SPECS/CONTROL_PLANE.md (Knowledge Studio pipeline + safety rules)
- STATE.md (Control Plane roadmap)
- STRATEGY/REQUIREMENTS.md (quality + safe-mode)
- docs/CONSOLE_GUIDE.md (Console UI map)

Invariant:
- Truth-first, no hallucinations; safe-mode on invalid knowledge.
- No changes to core webhook pipeline without separate DEC.
- Fail-closed: publish blocked on validation errors.

Scope:
- Knowledge Studio UI: Draft → Validate → Preview Diff → Publish → History → Rollback.
- Client/branch context visible and enforced.
- Warnings require explicit confirmation before publish.
- Audit entries on publish/rollback (UI display).

Out of scope:
- Backend/DB schema changes (separate TP if needed).
- RAG/Qdrant sync implementation.
- Automatic migrations of legacy packs.

Touch-list (files/tables):
- console-web/src/app/knowledge/* (new)
- console-web/src/components/KnowledgeStudio/*
- console-web/src/lib/api-client.ts (knowledge endpoints)
- console-web/src/types/api.generated.ts (regen if contract changes)
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-01-25-control-plane-phase3-knowledge-studio.md
- STATE.md
- STRUCTURE.md

Plan:
1) Define UI flow per SPECS (steps, gating, warnings).
2) Implement screens for draft/edit, validate, diff preview, publish, history, rollback.
3) Wire to `/console/v1/knowledge/*` endpoints (or stub read-only if backend missing).
4) Update docs + record evidence.

DoD:
- Publish blocked on validation errors.
- Rollback action available and logged in UI.
- Tenant context required for all actions.
- Evidence recorded (screenshots + API responses).

Checks:
- `npm --prefix console-web install`
- `npm --prefix console-web run lint`

Evidence:
- Screenshots of Knowledge Studio flow.
- API responses for validate/publish/rollback (if available).
- STATE.md updated with evidence.

Rollback:
- Revert UI changes.

No-go:
- No backend/API changes in this TP.

Branch/Worktree:
- Branch: feat/control-plane-phase3-knowledge-ui
- Worktree: /home/zhan/worktrees/control-plane-phase3-knowledge-ui
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch after merge
