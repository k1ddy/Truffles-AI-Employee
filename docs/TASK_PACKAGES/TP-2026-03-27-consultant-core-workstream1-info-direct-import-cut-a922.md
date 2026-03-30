# TP-2026-03-27-consultant-core-workstream1-info-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-info-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-booking-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-booking-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-remaining-active-mesh-cut`

## Название/цель
Снять ambient `_legacy.py` dependence с `info.py`, чтобы info/truth-gate flow читал явные owner surfaces и использовал delayed direct `decision.py` access только для оставшегося residue helper/constants.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/info.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "truth_gate_fallback or booking_interrupt_info or llm_guard"`
- `FACT findings`:
  - `info.py` still depended on `_legacy.py` across truth-gate reply composition, clarify/escalation flow, carryover handling, and handover routing.
  - Most of that dependency already has real owners (`trace.py`, `context_manager.py`, `guards.py`, `response.py`, `booking.py`, `handover_owner_service.py`, `state_service.py`, `ai_service.py`, `pack_runtime_service.py`).
  - The remaining `decision.py` dependency surface is finite and can be isolated behind explicit delayed accessors instead of the ambient compatibility bus.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org importlib import_module Python official documentation programmatic imports`
- **Date/time (local):** `2026-03-27 18:46 +05`
- **Why this query is precise:** this block replaces function-local `_legacy.py` imports with explicit owner imports and delayed module access for cycle-sensitive residue.
- **Sources opened (from this query):**
  - `Python official importlib docs`: `https://docs.python.org/3/library/importlib.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** official docs recommend explicit programmatic imports via `importlib.import_module()` / import machinery semantics when import timing matters.
- **Decision:** `build` — keep `info.py` on explicit owners and use delayed local accessors for cycle-sensitive router residue instead of ambient `_legacy.py`.
- **Rejected options:**
  - keep `_legacy.py` as convenience namespace: rejected because it preserves ambient authority in an active truth-gate path.
  - broad extraction of every remaining info helper before this cut: rejected because it is larger than this bounded Workstream 1 closeout block.

## Root cause (mandatory)
- **Symptom:** `info.py` still routes live truth-gate/info orchestration through `_legacy.py`.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/info.py`
- **Evidence to capture:**
  - `info.py` no longer imports `_legacy.py`
  - focused info/message regressions still pass
  - remaining `decision.py` dependency is explicit and narrow
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after bus/context/response/booking cuts? Because the live info/truth-gate flow still imports it directly.
  2. Why is that bad? Because info-stage authority still runs through the compatibility namespace instead of explicit owner boundaries.
  3. Why does that block Workstream 1? Because criterion 4 requires active owner-adjacent legacy paths to become shadow-only or deleted.
  4. Why not defer? Because `info.py` is still part of the active webhook mesh on the hot path.
  5. Why is a bounded fix possible? Because most dependencies already have owners and the remaining residue can be isolated behind delayed direct `decision.py` access.
- **Root cause statement:** `info.py` still routes live truth-gate/info behavior through `_legacy.py`, so active info-stage authority remains coupled to the legacy compatibility bus instead of explicit owner modules.
- **Fix mechanism:** replace `_legacy.py` reads with direct owner calls, keep delayed accessors for cycle-sensitive router owners, and update focused message tests where patch points move.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse existing owner modules: `trace.py`, `context_manager.py`, `guards.py`, `response.py`, `booking.py`, `handover_owner_service.py`, `state_service.py`, `ai_service.py`, `pack_runtime_service.py`.
  - Reuse delayed accessor pattern already used in `context_manager.py`, `response.py`, and `booking.py`.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block only reroutes an active consumer off the compatibility bus.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `info.py` must preserve current truth-gate/info reply, clarify, and escalation behavior.
- no new semantic owner path may be introduced.
- any remaining `decision.py` dependency must be explicit, not ambient via `_legacy.py`.

## Scope
- Remove `_legacy.py` import/use from `info.py`.
- Switch info-stage reads to explicit owners.
- Keep only delayed explicit `decision.py` / cycle-sensitive module access for residue not yet re-homed.
- Update focused deterministic tests and repo truth.

## Out of scope
- `policy.py`, `dedup.py`
- deletion of `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-info-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add explicit owner imports plus delayed accessors for cycle-sensitive modules in `info.py`.
2. Replace `_legacy.py` calls with direct owner calls; keep explicit `decision_router.*` only for residue.
3. Update focused tests if patch points moved.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `info.py` no longer imports `_legacy.py`.
- focused info/message regressions pass.
- remaining `decision.py` dependency in `info.py` is explicit and narrow.
- repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/info.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "truth_gate_fallback or booking_interrupt_info or llm_guard"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "service_clarify or info"`
- `git diff --check`

## Evidence
- diff showing `info.py` without `_legacy.py`
- passing focused info/message regressions
- explicit statement of remaining `decision.py` residue after the cut

## Rollback
- Revert `info.py`, focused tests, and doc updates together.

## No-go
- no reintroduction of `_legacy.py` into `info.py`
- no semantic rewrite added under import-cleanup cover
- no claim that Workstream 1 is closed by this block alone

## Risks/Blockers
- direct imports can expose latent circular-import mistakes in the webhook mesh
- some info helpers/constants still only exist in `decision.py`
- focused tests may still patch legacy locations that need narrow relocation

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `policy.py` and `dedup.py` still remain on the active legacy mesh; `info.py` may still keep explicit delayed `decision.py` residue where no narrower owner exists yet.
- `Why not in this block`: this block is limited to the active info/truth-gate hotspot.
- `Risk if deferred`: the info/truth-gate path would continue to run through ambient legacy authority.
- `Linked follow-up Task Package(s)`: `WS1-closeout-remaining-active-mesh-cut`
- `Expiry/trigger to stop deferral`: if `info.py` still imports `_legacy.py`, active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: remove ambient `_legacy.py` dependence from the remaining active mesh consumers (`policy.py`, then `dedup.py`).
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/dedup.py`
- `Blocked-by conditions`: direct-owner switch in `info.py` exposes a missing owner surface that needs extraction before the next active-mesh cut.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `info.py` no longer imports `_legacy.py`.
  - info/truth-gate flow now reads explicit owners directly (`trace.py`, `context_manager.py`, `guards.py`, `response.py`, `booking.py`, `handover_owner_service.py`, `state_service.py`, `ai_service.py`, `pack_runtime_service.py`) and keeps delayed accessors only for cycle-sensitive router owners plus remaining `decision.py` residue.
  - remaining `decision.py` dependence in `info.py` is explicit and narrow through `_decision_runtime()` only for helpers/constants not yet re-homed.
- `Files touched`:
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/info.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "truth_gate_fallback or booking_interrupt_info or llm_guard"` -> `3 passed, 189 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "service_clarify or info"` -> `14 passed, 178 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `5 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - grep now shows no `_legacy.py` import/use in `truffles-api/app/routers/webhook/info.py`
  - focused truth-gate/info regressions still pass on direct owner surfaces
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` authority from the active webhook info/truth-gate flow
- `Residual debt left for next block`:
  - `policy.py` and `dedup.py` still remain on the active legacy mesh
  - `info.py` still carries explicit delayed `decision.py` residue for helpers/constants that are not yet re-homed
