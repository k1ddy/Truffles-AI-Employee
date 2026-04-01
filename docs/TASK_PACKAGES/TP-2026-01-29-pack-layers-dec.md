# TP-2026-01-29-pack-layers-dec

Title/goal
- Define a canonical pack layer model and resolution order (domain -> company -> client -> branch) plus tool-scope layering (CRM/Calendar/Calls/Channels) via DEC, and align specs without runtime changes.

Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: no explicit DEC for pack layer order)
- `SPECS/MULTI_TENANT.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/IMPERIUM_DECISIONS.yaml`

Invariant
- Facts only from packs/tools; no runtime behavior changes; Hard-LAW/policy/pending gates remain deterministic.

Scope
- Add DEC for pack layers and resolution order, including tool-scope layering.
- Align specs to reference the DEC and the same order.
- Record evidence in STATE.md.

Out of scope
- Any code/runtime changes (LLM budget, OOD gate, matcher thresholds, escalation text).
- Contract changes in `contracts/*`.
- Implementation of pack-resolver/tool-registry or auto-enrichment pipeline.
- Tests/live-check.

Touch-list (files)
- `docs/IMPERIUM_DECISIONS.yaml`
- `SPECS/MULTI_TENANT.md`
- `SPECS/ARCHITECTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-01-29-pack-layers-a1.md`
- `docs/SESSION_INDEX.md`

Plan
1) Create session log via `scripts/session_start.sh`.
2) Add GAP entry to STATE.md (pack layer order not canonized).
3) Add DEC entry (pack layer model + resolution order + tool-scope layering) in `docs/IMPERIUM_DECISIONS.yaml`.
4) Align `SPECS/MULTI_TENANT.md` and `SPECS/ARCHITECTURE.md` to the DEC.
5) Update STATE.md with DONE + evidence.
6) Run `scripts/session_check.sh`.

DoD
- DEC exists with clear layer order, tool-scope layering, and conflict resolution.
- Specs reference the DEC and use the same ordering.
- STATE.md updated with evidence.
- Specs and docs updated; session log/index updated.

Checks
- `scripts/session_check.sh`

Evidence
- Doc diff + DEC entry + spec updates; STATE.md note with evidence paths.

Rollback
- Revert the doc commit.

No-go
- Any runtime or behavior change.
- Adding a new layer without explicit DEC.
- Changing Hard-LAW/policy gates or `_legacy.py`.

Risks/Blockers
- None expected; doc-only changes.

Branch + Worktree + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-01-29-pack-layers-a1`
- Worktree: `/home/zhan/worktrees/2026-01-29-pack-layers-a1`
- Base ref: `origin/main`
- Merge policy: standard merge (not doc-only fast path)
- Cleanup: `scripts/session_end.sh --status done` and remove worktree/branch
