# TP-2026-03-27-consultant-core-workstream1-response-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-response-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-context-manager-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-context-manager-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-remaining-active-mesh-cut`

## Название/цель
Снять ambient `_legacy.py` dependence с `response.py`, чтобы response-stage orchestration читал явные owner surfaces и использовал direct delayed `decision` access только для ещё не перенесённых residue helpers/constants.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/tests/test_webhook_response.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/response.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `FACT findings`:
  - `response.py` remains the largest active `_legacy.py` consumer in the webhook mesh.
  - Most live reads already have narrower owners (`context_manager.py`, `trace.py`, `booking.py`, `policy.py`, `media.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`, `pack_runtime_service.py`, `state_service.py`).
  - The remaining `decision.py` dependencies are finite and can be reached explicitly through one delayed accessor instead of the ambient compatibility bus.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org importlib import_module programmatically import a module Python documentation`
- **Date/time (local):** `2026-03-27 18:08 +05`
- **Why this query is precise:** this block replaces function-local `_legacy.py` imports with explicit owner imports and delayed module access for residual decision-era helpers.
- **Sources opened (from this query):**
  - `Python official importlib docs`: `https://docs.python.org/3/library/importlib.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** official docs recommend `importlib.import_module()` / programmatic module access for explicit dynamic importing when import timing matters.
- **Decision:** `build` — keep `response.py` on explicit owners and add one local delayed decision accessor instead of ambient `_legacy.py`.
- **Rejected options:**
  - keep `_legacy.py` as convenience namespace: rejected because it preserves ambient authority in the hottest remaining active mesh file.
  - broad extraction of every residual `decision.py` helper before touching `response.py`: rejected because it is larger than this bounded Workstream 1 closeout cut.

## Root cause (mandatory)
- **Symptom:** `response.py` still depends on `_legacy.py` across response composition, clarify flow, consult flow, escalation flow, and low-confidence handling.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/response.py`
- **Evidence to capture:**
  - `response.py` no longer imports `_legacy.py`
  - focused response/message regressions still pass
  - any remaining decision-era dependency is explicit and narrow
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after the bus and continuity cuts? Because the main response-stage orchestrator still imports it directly.
  2. Why is that bad? Because live reply/routing/escalation logic still flows through the compatibility namespace instead of explicit owned boundaries.
  3. Why does that block Workstream 1? Because criterion 4 requires active owner-adjacent legacy paths to become shadow-only or deleted, not merely governed.
  4. Why not postpone until all decision helpers are re-homed? Because `_legacy.py` is the ambient authority surface; cutting that dependency is the high-leverage step now.
  5. Why is a bounded fix possible? Because most referenced helpers already have direct owners, and the remaining residue can be isolated behind one delayed `decision` accessor.
- **Root cause statement:** `response.py` still routes live response orchestration through `_legacy.py`, so active response-stage authority remains coupled to the legacy compatibility bus instead of explicit owner modules.
- **Fix mechanism:** replace `_legacy.py` reads with direct imports from the real owners, add one delayed `_decision_runtime()` accessor for the remaining `decision.py` residue, and update focused tests only where direct owner patch points change.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse existing owner modules: `context_manager.py`, `trace.py`, `booking.py`, `policy.py`, `media.py`, `session_memory.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`, `pack_runtime_service.py`, `state_service.py`.
  - Reuse direct delayed `decision` access pattern already introduced in `pending.py`, `guards.py`, and `context_manager.py`.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block only reroutes an active consumer off the compatibility bus; it does not redesign response semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `response.py` must preserve current response/clarify/escalation behavior.
- no new semantic owner path may be introduced.
- any remaining `decision.py` dependency must be explicit, not ambient via `_legacy.py`.

## Scope
- Remove `_legacy.py` import/use from `response.py`.
- Switch response-stage reads to explicit owners.
- Keep only delayed explicit `decision.py` access for residue not yet re-homed.
- Update focused deterministic tests and repo truth.

## Out of scope
- `booking.py`, `info.py`, `policy.py`, `dedup.py`
- deletion of `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/tests/test_webhook_response.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-response-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add explicit owner imports and a delayed `_decision_runtime()` accessor in `response.py`.
2. Replace `_legacy.py` calls with direct owner calls; keep explicit `decision_router.*` only for residue.
3. Update focused tests if patch points moved.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `response.py` no longer imports `_legacy.py`.
- focused response/message regressions pass.
- remaining `decision.py` dependency in `response.py` is explicit and narrow.
- repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/response.py truffles-api/tests/test_webhook_response.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "quiet_hours or low_confidence or style_reference or legacy_handover_adapter_exports_owner_surface_symbols or legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `git diff --check`

## Evidence
- diff showing `response.py` without `_legacy.py`
- passing response/message regressions
- explicit statement of remaining `decision.py` residue after the cut

## Rollback
- Revert `response.py`, focused tests, and doc updates together.

## No-go
- no reintroduction of `_legacy.py` into `response.py`
- no semantic rewrite added under the guise of import cleanup
- no claim that Workstream 1 is closed by this block alone

## Risks/Blockers
- direct imports can expose latent circular-import mistakes
- some response-stage helpers/constants still only exist in `decision.py`
- focused tests may still patch legacy locations that need narrow relocation

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `booking.py`, `info.py`, `policy.py`, and `dedup.py` still sit on the active legacy mesh; `response.py` may still keep explicit delayed `decision.py` residue where no narrower owner exists yet.
- `Why not in this block`: this block is limited to the largest remaining active response-stage consumer.
- `Risk if deferred`: the main webhook response path would continue to run through ambient legacy authority.
- `Linked follow-up Task Package(s)`: `WS1-closeout-remaining-active-mesh-cut`
- `Expiry/trigger to stop deferral`: if `response.py` still imports `_legacy.py`, active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: remove ambient `_legacy.py` dependence from the remaining active mesh consumers (`booking.py`, then `info.py`, `policy.py`, `dedup.py`).
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/dedup.py`
- `Blocked-by conditions`: direct-owner switch in `response.py` exposes a missing owner surface that needs extraction before the next active-mesh cut.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `response.py` no longer imports `_legacy.py`.
  - response-stage orchestration now reads explicit owners directly (`context_manager.py`, `guards.py`, `booking.py`, `policy.py`, `media.py`, `session_memory.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`, `pack_runtime_service.py`, `state_service.py`).
  - remaining response-stage `decision.py` dependence is explicit and narrow through `_decision_runtime()` only for residual helpers/constants that have not been re-homed yet.
- `Files touched`:
  - `truffles-api/app/routers/webhook/response.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/response.py truffles-api/tests/test_webhook_response.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py` -> `8 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "quiet_hours or low_confidence or style_reference or legacy_handover_adapter_exports_owner_surface_symbols or legacy_webhook_compat_routes_through_public_entrypoint_contract"` -> `6 passed, 186 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply or low_confidence or consult or style_reference or quiet_hours"` -> `20 passed, 172 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `5 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - grep now shows no `_legacy.py` import/use in `truffles-api/app/routers/webhook/response.py`
  - response/quiet-hours/expected-reply/low-confidence regressions still pass on direct owner surfaces
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` authority from the active webhook response-stage orchestrator
- `Residual debt left for next block`:
  - `booking.py`, `info.py`, `policy.py`, and `dedup.py` still remain on the active legacy mesh
  - `response.py` still carries explicit delayed `decision.py` residue for helpers/constants that are not yet re-homed
