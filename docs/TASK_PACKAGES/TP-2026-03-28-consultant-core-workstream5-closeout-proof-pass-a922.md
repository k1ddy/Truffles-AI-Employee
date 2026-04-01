# TP-2026-03-28-consultant-core-workstream5-closeout-proof-pass-a922

## Title / Goal
Prove whether `Workstream 5 — Legacy Mesh Strangler` is actually closed by freezing the remaining runtime boundary: no eager app-runtime `decision.py` imports, no live `decision_router` helper reads outside compatibility shells, and only compatibility-only residual surfaces left in `__init__.py` / `_legacy.py`.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_webhook.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com strangler fig application boundary refactoring`
- Date/time: `2026-03-28T09:02:00+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/OriginalStranglerFigApplication.html`
- High-signal source quality:
  - Martin Fowler primary source for the Strangler Fig pattern, emphasizing gradual replacement at boundaries, steady reduction of legacy surface, and risk-controlled cutover.
- Found reusable idea:
  - closure should be decided at the system boundary: once active traffic no longer depends on the legacy host and only compatibility shells remain, the strangler phase for that boundary is complete.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - Workstream 5 is a boundary-strangler problem; the close decision must be based on active runtime dependency edges, not on whether the legacy module file still exists.
- Rejected options:
  - declare Workstream 5 done just because the main helper clusters were moved: rejected because the remaining eager package/runtime edges still needed proof.
  - keep Workstream 5 open without boundary proof after active edges are removed: rejected because that hides actual completion and delays the next workstream without evidence.

## Root Cause (mandatory)
### Symptom
After the helper-cluster cuts, `decision.py` may still survive as a compatibility file, but Workstream 5 cannot close honestly until we prove that active app runtime no longer depends on it or on `_legacy.py` as a live authority path.

### Minimal Reproduction
1. Scan app/runtime files for eager imports of `decision.py` and `_legacy.py`.
2. Scan app/runtime files for `decision_router.*` or `_decision_runtime()` helper reads.
3. Confirm remaining package/adapter surfaces are compatibility-only:
   - `truffles-api/app/routers/webhook/__init__.py`
   - `truffles-api/app/routers/webhook/_legacy.py`
4. Run focused deterministic proof guards.

### Evidence
- `rg -n "from app\.routers\.webhook\.decision import|from \. import decision|app\.routers\.webhook\.decision|app\.routers\.webhook\._legacy|from \. import _legacy" truffles-api/app`
- `rg -n "_decision_runtime|decision_router\." truffles-api/app/routers/webhook/*.py truffles-api/app/services/*.py`
- focused architecture guard results

### Five Whys
1. Why is Workstream 5 still open after multiple helper cuts?
   - Because we had not yet proved that no active runtime boundary still depends on `decision.py`.
2. Why is that proof necessary?
   - Because Workstream 5 is about removing legacy mesh authority, not just moving code around.
3. Why can the files still exist after closure?
   - Because surviving compatibility shells may remain for tests or migration, as long as active runtime traffic no longer depends on them.
4. Why focus on eager imports and helper reads?
   - Because those are the concrete dependency edges that keep legacy authority alive on the runtime path.
5. Why add architecture guards?
   - Because closure without a frozen boundary will regress silently.

### Root Cause Statement
The remaining uncertainty in Workstream 5 is not about helper ownership anymore; it is about closure proof. We need a frozen, machine-checked guarantee that active runtime no longer imports or reads the legacy decision/helper mesh except through compatibility-only shells.

### Fix Mechanism
Add final architecture guards for eager import edges and helper reads, rerun the deterministic closeout envelope, and update repo truth to either mark Workstream 5 `done` or explicitly keep it `open`.

## Invariant
- No behavior changes on the active runtime path.
- No new helper ownership added back to `decision.py`.
- Closeout is evidence-based, not narrative-based.

## Scope
- Add final Workstream 5 architecture proof.
- Decide close status from actual app/runtime dependency edges.
- Update repo truth.

## Out of Scope
- Deleting `decision.py` or `_legacy.py`.
- Starting Workstream 6 implementation.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add final runtime-boundary guards for Workstream 5 closure.
2. Run the focused closeout envelope.
3. Update repo truth with the close decision.

## DoD
- Architecture guards prove no eager app-runtime `decision.py` imports remain.
- Architecture guards prove no live `decision_router` helper reads remain outside compatibility shells.
- Deterministic closeout envelope passes.
- Repo truth records an explicit close decision.

## Work Mode
- `closure`

## Checks
- `python3 -m py_compile truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_eager_decision_import or app_runtime_has_no_legacy_adapter_importers or app_runtime_has_no_eager_decision_importers or app_runtime_has_no_decision_helper_reads"`
- `git diff --check`

## Evidence
- Updated TP
- Focused architecture guard output
- `STATE.md` closeout entry

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No premature `done` without passing closeout evidence.
- No new compatibility facade in front of `decision.py`.
- No doc-only closeout without frozen guards.

## Risks / Blockers
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `Canon Sync Gate` remains red because worktree `AGENTS.md` diverges from `/home/zhan/AGENTS.md`; this block cannot claim session gate closure.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `decision.py` and `_legacy.py` may remain on disk as compatibility/test surfaces after Workstream 5 closes.

### Why not in this block
- This block is a closure proof, not a file-deletion program.

### Risk if deferred
- Workstream 5 completion remains ambiguous and can regress silently.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream6-durable-action-plane-entry-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral immediately if a new active app/runtime import edge to `decision.py` or `_legacy.py` appears.

## Next-block Contract (mandatory)
### Next block objective
If this closeout stays green, start Workstream 6 at the durable action-plane boundary.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_provider_gateway_integration.py`

### Blocked-by conditions
- Workstream 5 must first close with explicit deterministic evidence.

### Owner role for closure
- Brain / Top Architect
