Title: Control Plane Phase 3 — Knowledge Studio (Backend)
Owner: Top Architect
Date: 2026-01-26

Canon refs:
- SPECS/CONTROL_PLANE.md (Knowledge Studio pipeline + safety rules)
- docs/IMPERIUM_DECISIONS.yaml (DEC-014 knowledge_studio)
- STRATEGY/REQUIREMENTS.md (quality + safe-mode)
- docs/CONSOLE_GUIDE.md (Console API map)

Invariant:
- Truth-first: publish blocked on validation errors; warnings require explicit ack.
- Safe-mode on invalid/failed publish; assistant must not hallucinate.
- No behavioral drift in core pipeline beyond safe-mode gate; trace/meta must still be written on early return.
- No manual edits of runtime packs; pack YAML is generated only from DB.

Scope:
- DB registry for knowledge versions (draft/published/archived) with audit trail.
- Console endpoints: current/validate/publish/history/rollback under /console/v1/knowledge/*.
- Validation: schema + required fields (aligned with ops/sync_client.py), diff vs current published.
- Publish: generate pack YAML, store artifacts, sync Qdrant from published version only.
- Safe-mode flag per branch; set on invalid/failed publish; enforce handoff in runtime.

Out of scope:
- UI changes (Knowledge Studio UI already done).
- Full migration of existing file packs to DB registry.
- Non-knowledge pipeline refactors or new decision stages unrelated to safe-mode gate.

Touch-list (files/tables):
- truffles-api/migrations/014_add_knowledge_versions.sql
- truffles-api/app/models/knowledge_version.py
- truffles-api/app/models/branch.py (safe_mode fields)
- truffles-api/app/models/__init__.py
- truffles-api/app/schemas/console.py (knowledge requests/responses)
- truffles-api/app/routers/console.py (knowledge endpoints)
- truffles-api/app/routers/webhook/decision.py (safe-mode gate)
- truffles-api/app/services/knowledge_registry_service.py (new)
- truffles-api/app/services/knowledge_validation.py (new helpers)
- contracts/console_api/openapi.v1.yaml
- console-web/src/types/api.generated.ts (regen)
- docs/CONSOLE_GUIDE.md (API docs)
- STRUCTURE.md
- STATE.md (Brain only, end of session)

Plan:
1) Define DB schema + model (knowledge_versions) and safe-mode fields on branches.
2) Implement validation + diff + pack export (reuse required fields list from ops/sync_client.py).
3) Implement console endpoints with RBAC + branch selection; write audit events.
4) Implement publish/rollback logic with Qdrant sync and safe-mode updates.
5) Add safe-mode gate in decision pipeline (early handoff + trace/meta).
6) Update OpenAPI + regenerate types; update docs.
7) Local checks; open PR + CI.

DoD:
- /knowledge/current returns published version payload + version_id.
- /knowledge/validate returns valid/errors/warnings/diff; publish blocked on errors.
- /knowledge/publish stores new published version, archives previous, syncs Qdrant, writes audit.
- /knowledge/history returns versions; /knowledge/rollback restores version.
- Safe-mode is set on failed publish and enforced in runtime (handoff).
- OpenAPI + console types updated; docs updated.
- Evidence recorded in STATE.md (CI run + API curl/SQL).

Checks:
- python3 -m compileall truffles-api/app/models truffles-api/app/routers truffles-api/app/services
- pytest -q truffles-api/tests/test_console_knowledge.py
- ruff check truffles-api/app truffles-api/tests
- npm --prefix console-web run generate:api

Evidence:
- CI run URL + job logs.
- SQL: knowledge_versions rows; branch safe_mode flag.
- curl: /console/v1/knowledge/current|validate|publish|history|rollback.
- Qdrant sync log (if available).

Rollback:
- Revert migration + code changes; drop knowledge_versions table if needed.

No-go:
- No manual edits to runtime packs.
- No changes to console-web deploy pipeline.
- No changes to unrelated webhook stages.

Risks/Blockers:
- Qdrant/BGE connectivity in non-prod envs.
- Safe-mode gate requires careful trace/meta handling.

Branch/Worktree:
- Branch: feat/control-plane-knowledge-backend
- Worktree: /home/zhan/worktrees/control-plane-knowledge-backend
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch + worktree after merge
