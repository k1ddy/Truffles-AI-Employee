# TP-2026-03-28-consultant-core-workstream5-webhook-package-compat-lazy-export-cut-a922

## Title / Goal
Remove the last app-runtime `webhook.__init__ -> decision.py` import by routing active package exports to direct owners and using module-level lazy compatibility export only for the test-only `'_should_block_expected_reply_by_info'` surface.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_webhook.md`

## One Web Search (mandatory before implementation)
- Query: `Python module __getattr__ lazy import official docs`
- Date/time: `2026-03-28T08:55:00+05:00`
- Opened sources:
  - `https://peps.python.org/pep-0562/`
- High-signal source quality:
  - Python language PEP for module-level `__getattr__` and lazy attribute access; it explicitly covers lazy submodule/name loading and `from module import name` behavior.
- Found reusable idea:
  - keep a compatibility export on a package module via module-level `__getattr__` so active imports do not eagerly load the heavy legacy module.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - we need to preserve the package compatibility export for tests while removing the last eager app-runtime import edge into `decision.py`.
- Rejected options:
  - keep the eager `from ...decision import ...` in `webhook.__init__`: rejected because app imports of the package still load `decision.py`.
  - delete the compatibility export entirely: rejected because the package surface is still used by tests and should be demoted, not broken silently.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/__init__.py` still imports `decision.py` eagerly for `_process_outbox_rows` and `_should_block_expected_reply_by_info`, so app imports of `app.routers.webhook` still load the legacy mesh entry module.

### Minimal Reproduction
1. Inspect `truffles-api/app/routers/webhook/__init__.py`.
2. Confirm it still imports from `app.routers.webhook.decision`.
3. Confirm active app consumers import the package for `_process_outbox_rows`:
   - `truffles-api/app/routers/outbox_service.py`
   - `truffles-api/app/routers/admin.py`
   - `truffles-api/app/routers/console.py`
   - `truffles-api/app/workers/outbox.py`
4. Confirm `_process_outbox_rows` already lives in `outbox.py`, so the package can point there directly.

### Evidence
- `rg -n "from app\.routers\.webhook\.decision import|_process_outbox_rows|_should_block_expected_reply_by_info" truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py`
- `rg -n "async def _process_outbox_rows|def _should_block_expected_reply_by_info" truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/webhook/decision.py`

### Five Whys
1. Why does app runtime still touch `decision.py`?
   - Because the webhook package init eagerly imports it.
2. Why is that wrong now?
   - Because the active app export `_process_outbox_rows` already has a direct owner in `outbox.py`.
3. Why does the compatibility helper still matter?
   - Because tests still use the package-level `_should_block_expected_reply_by_info` surface.
4. Why not keep the eager import for tests?
   - Because it keeps app package imports coupled to `decision.py`.
5. Why use module-level `__getattr__`?
   - Because it preserves compatibility without eager runtime import of the legacy module.

### Root Cause Statement
The webhook package init still acts as an eager compatibility bridge into `decision.py`, even though its active outbox export already has a direct owner and the remaining decision-bound helper is test-only.

### Fix Mechanism
Import `_process_outbox_rows` directly from `outbox.py`, expose package constants directly from stable owners, and use module-level `__getattr__` only for the residual test-only decision helper export.

## Invariant
- Active outbox processing behavior stays unchanged.
- Package compatibility for tests stays intact.
- No new semantic/control authority is introduced.

## Scope
- Remove eager `decision.py` import from `webhook.__init__`.
- Route active package exports to direct owners.
- Keep only lazy compatibility export for the remaining test-only decision helper.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Deleting `decision.py`.
- Reworking test-only imports outside the package compatibility surface.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/tests/test_webhook_booking.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Remove eager `decision.py` import from `webhook.__init__`.
2. Route active exports to direct owners and add lazy compatibility export for the residual helper.
3. Add focused tests and architecture guard updates.
4. Update repo truth.

## DoD
- `webhook.__init__` no longer imports `decision.py` eagerly.
- Package compatibility tests stay green.
- Focused deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/__init__.py truffles-api/tests/test_webhook_booking.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_booking.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_outbox_service_app.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_eager_decision_import or app_runtime_has_no_legacy_adapter_importers"`
- `git diff --check`

## Evidence
- Updated TP
- Focused package compatibility pytest output
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
- `decision.py` and `_legacy.py` still survive as compatibility/test surfaces after the eager package import edge is removed.

### Why not in this block
- This family is bounded to the last app-runtime eager package import edge, not final deletion of the compatibility modules.

### Risk if deferred
- App imports of `app.routers.webhook` keep loading `decision.py` even though active runtime no longer needs it.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `webhook.__init__` still eagerly imports `decision.py`.

## Next-block Contract (mandatory)
### Next block objective
After this cut, run the Workstream 5 closeout proof pass and decide whether the remaining `decision.py` / `_legacy.py` surface is compatibility-only.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "webhook_package_init_has_no_eager_decision_import or app_runtime_has_no_legacy_adapter_importers"`

### Blocked-by conditions
- This block must first prove that active package imports no longer eagerly load `decision.py` and that package compatibility tests remain green.

### Owner role for closure
- Brain / Top Architect
