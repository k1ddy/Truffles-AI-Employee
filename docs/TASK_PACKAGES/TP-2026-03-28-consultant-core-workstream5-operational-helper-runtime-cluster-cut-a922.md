# TP-2026-03-28-consultant-core-workstream5-operational-helper-runtime-cluster-cut-a922

## Title / Goal
Remove the remaining live `dedup.py` / `outbox.py` / `shield.py` dependency on `decision.py` by re-homing their small operational helper cluster into direct owners and leaving only compatibility aliases in `decision.py`.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_dedup.md`
- `docs/system_forensics/files/app_routers_webhook_outbox.md`
- `docs/system_forensics/files/app_routers_webhook_shield.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com extract small cohesive class from large class helper methods`
- Date/time: `2026-03-28T08:34:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/class-too-large.html`
- High-signal source quality:
  - Martin Fowler primary refactoring article on moving one cohesive helper slice at a time into a smaller owner while leaving compatibility call sites behind only as migration aliases.
- Found reusable idea:
  - move a narrow helper cluster into a small direct owner, switch live callers first, then keep the god-file as aliases only.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already follows this strangler pattern for `runtime_primitives.py`, `knowledge_runtime.py`, `pending_runtime.py`, and `booking_runtime.py`; the operational helper family can follow the same bounded extraction.
- Rejected options:
  - keep `dedup.py` / `outbox.py` / `shield.py` on `decision.py` until `media.py` is cut: rejected because these are already narrow operational helpers and can be removed cleanly now.
  - move everything, including media defaults, in one giant block: rejected because `media.py` is a separate larger family with different risk and test surface.

## Root Cause (mandatory)
### Symptom
`dedup.py`, `outbox.py`, and `shield.py` still read small operational helpers from `decision.py`, keeping the legacy god-file alive as a runtime helper bus even after the larger response/booking/info clusters were moved out.

### Minimal Reproduction
1. Inspect direct `decision_router.*` reads in:
   - `truffles-api/app/routers/webhook/dedup.py`
   - `truffles-api/app/routers/webhook/outbox.py`
   - `truffles-api/app/routers/webhook/shield.py`
2. Confirm those reads are only for small operational helpers:
   - `_is_env_enabled(...)`
   - `_find_message_by_message_id(...)`
   - `_find_message_by_conversation_created_at(...)`
   - `_ensure_rag_meta_defaults(...)`
   - `MSG_ESCALATED`
3. Confirm there is no longer a semantic reason for these helpers to stay owned by `decision.py`.

### Evidence
- `rg -n "_decision_runtime|decision_router\." truffles-api/app/routers/webhook/dedup.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/webhook/shield.py`
- `rg -n "def _is_env_enabled|def _find_message_by_message_id|def _find_message_by_conversation_created_at|def _ensure_rag_meta_defaults|MSG_ESCALATED" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/knowledge_runtime.py truffles-api/app/routers/webhook/http.py`

### Five Whys
1. Why do these modules still import `decision.py`?
   - Because their small helper residue was not cut when the larger live seams were removed.
2. Why is that wrong now?
   - Because `decision.py` remains the operational helper owner for modules that no longer need its stage orchestration surface.
3. Why does that matter?
   - Because it preserves live legacy authority in the runtime helper mesh and blocks Workstream 5 closeout.
4. Why not leave them for later?
   - Because these helpers are already cohesive, low-risk, and bounded by deterministic tests.
5. Why treat them as one family?
   - Because they form one operational helper cluster distinct from the larger `media.py` family.

### Root Cause Statement
After the larger helper extractions, a small operational residue remained: `dedup.py`, `outbox.py`, and `shield.py` still fetch basic env, message-lookup, rag-meta, and escalation helpers from `decision.py` instead of owning or importing them from narrow direct surfaces.

### Fix Mechanism
Localize env parsing in `dedup.py`, move shield escalation text to `runtime_primitives.MSG_ESCALATED`, let `outbox.py` own its message-lookup + rag-meta default helpers directly, and keep `decision.py` with compatibility aliases only.

## Invariant
- Dedup/debounce behavior stays unchanged.
- Outbox replay and rag-meta defaults stay unchanged.
- Shield escalation behavior stays unchanged.
- No new semantic routing is introduced.

## Scope
- Remove `decision.py` helper ownership from `dedup.py`, `outbox.py`, and `shield.py`.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Reworking `media.py` helper ownership.
- Deleting `decision.py`.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/dedup.py`
- `truffles-api/app/routers/webhook/outbox.py`
- `truffles-api/app/routers/webhook/shield.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/tests/test_webhook_dedup.py`
- `truffles-api/tests/test_provider_gateway_integration.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Re-home the small operational helpers to direct owners.
2. Switch `dedup.py`, `outbox.py`, and `shield.py` to those owners.
3. Leave compatibility aliases in `decision.py` only.
4. Add focused deterministic coverage and architecture guard updates.
5. Update repo truth.

## DoD
- `dedup.py`, `outbox.py`, and `shield.py` no longer read the moved helper cluster through `decision_router.*`.
- `_decision_runtime()` is gone from those modules.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/dedup.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_webhook_dedup.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_dedup.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_provider_gateway_integration.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "shield or escalation_reuses_active_handover or legacy_handover_adapter_exports_owner_surface_symbols"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "operational_helper_runtime_cluster_uses_narrow_owners or booking_runtime_cluster_uses_narrow_owners or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused dedup/outbox/shield pytest output
- Focused architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility facade in front of `decision.py`.
- No semantic regex/phrase growth in governed core.
- No doc-only closure without authority reduction.

## Risks / Blockers
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `Canon Sync Gate` remains red because worktree `AGENTS.md` diverges from `/home/zhan/AGENTS.md`; this block cannot claim session gate closure.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `media.py` will still depend on `decision.py` for its larger media-policy/runtime helper cluster after this cut.

### Why not in this block
- `media.py` is a separate larger family with a broader constant/policy/test surface.

### Risk if deferred
- `decision.py` remains the live supplier for the last large operational helper family.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-media-runtime-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `media.py` remains the only active `decision.py` helper consumer family.

## Next-block Contract (mandatory)
### Next block objective
After this cut, remove the remaining `media.py -> decision.py` helper cluster.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_media_policy.py`

### Blocked-by conditions
- This block must first prove that `dedup.py`, `outbox.py`, and `shield.py` no longer read the moved helper cluster from `decision.py` and that focused operational tests stay green.

### Owner role for closure
- Brain / Top Architect
