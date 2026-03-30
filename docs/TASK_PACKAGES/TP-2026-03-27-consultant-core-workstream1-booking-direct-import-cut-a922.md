# TP-2026-03-27-consultant-core-workstream1-booking-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-booking-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-response-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-response-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-remaining-active-mesh-cut`

## Название/цель
Снять ambient `_legacy.py` dependence с `booking.py`, чтобы booking flow читал явные owner surfaces и использовал delayed direct `decision.py` access только для оставшегося residue helper/constants.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/tests/test_booking_prompt_leak_guard.py`
  - `truffles-api/tests/test_booking_info_interrupt_contract.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/booking.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py`
- `FACT findings`:
  - `booking.py` is still a large active `_legacy.py` consumer across slot parsing, carryover, booking prompts, clarify/escalation flow, and booking commit routing.
  - A significant part of those reads already has real owners (`ai_service.py`, `intent_service.py`, `trace.py`, `handover_owner_service.py`, `state_service.py`, `context_manager.py`, `response.py`, `runtime_primitives.py`).
  - The remaining `decision.py` dependency surface is finite and can be isolated behind one delayed accessor instead of the ambient compatibility bus.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org importlib import_module circular imports Python official documentation`
- **Date/time (local):** `2026-03-27 18:22 +05`
- **Why this query is precise:** this block replaces function-local `_legacy.py` imports with explicit owner imports and delayed module access for residual decision-era helpers in a cycle-prone webhook module.
- **Sources opened (from this query):**
  - `Python official importlib docs`: `https://docs.python.org/3/library/importlib.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** official docs support explicit programmatic module access via `importlib.import_module()` / import machinery semantics when import timing matters.
- **Decision:** `build` — keep `booking.py` on explicit owners and add delayed local accessors for cycle-sensitive modules instead of ambient `_legacy.py`.
- **Rejected options:**
  - keep `_legacy.py` as convenience namespace: rejected because it preserves ambient authority in another active booking owner-adjacent path.
  - broad extraction of every remaining booking helper before this cut: rejected because it is larger than this bounded Workstream 1 closeout block.

## Root cause (mandatory)
- **Symptom:** `booking.py` still depends on `_legacy.py` across slot parsing, follow-up prompts, clarify/escalation, and booking completion routing.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/booking.py`
- **Evidence to capture:**
  - `booking.py` no longer imports `_legacy.py`
  - focused booking/message regressions still pass
  - any remaining `decision.py` dependency is explicit and narrow
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after the bus, continuity, context, and response cuts? Because the live booking flow still imports it directly.
  2. Why is that bad? Because booking flow authority still runs through the compatibility namespace instead of explicit owned boundaries.
  3. Why does that block Workstream 1? Because criterion 4 requires active owner-adjacent legacy paths to become shadow-only or deleted.
  4. Why not wait for a later extraction? Because booking is a remaining active mesh hotspot and still carries live authority now.
  5. Why is a bounded fix possible? Because many dependencies already have owners, and the remaining residue can be isolated behind delayed direct `decision.py` access.
- **Root cause statement:** `booking.py` still routes live booking orchestration through `_legacy.py`, so active booking-stage authority remains coupled to the legacy compatibility bus instead of explicit owner modules.
- **Fix mechanism:** replace `_legacy.py` reads with direct owner calls, use delayed module access for cycle-sensitive context/decision residue, and update focused booking/message tests only where direct owner patch points move.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse existing owner modules: `ai_service.py`, `intent_service.py`, `trace.py`, `handover_owner_service.py`, `state_service.py`, `context_manager.py`, `response.py`, `runtime_primitives.py`.
  - Reuse delayed accessor pattern already used in `pending.py`, `guards.py`, `context_manager.py`, and `response.py`.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block only reroutes an active consumer off the compatibility bus.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `booking.py` must preserve current booking-slot, clarify, escalation, and commit behavior.
- no new semantic owner path may be introduced.
- any remaining `decision.py` dependency must be explicit, not ambient via `_legacy.py`.

## Scope
- Remove `_legacy.py` import/use from `booking.py`.
- Switch booking-stage reads to explicit owners.
- Keep only delayed explicit `decision.py` / cycle-sensitive module access for residue not yet re-homed.
- Update focused deterministic tests and repo truth.

## Out of scope
- `info.py`, `policy.py`, `dedup.py`
- deletion of `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_booking_prompt_leak_guard.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-booking-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add explicit owner imports plus delayed accessors for cycle-sensitive modules in `booking.py`.
2. Replace `_legacy.py` calls with direct owner calls; keep explicit `decision_router.*` only for residue.
3. Update focused tests if patch points moved.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `booking.py` no longer imports `_legacy.py`.
- focused booking/message regressions pass.
- remaining `decision.py` dependency in `booking.py` is explicit and narrow.
- repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_prompt or booking_interrupt or booking_cancel or booking_reengage or booking_info"`
- `git diff --check`

## Evidence
- diff showing `booking.py` without `_legacy.py`
- passing focused booking/message regressions
- explicit statement of remaining `decision.py` residue after the cut

## Rollback
- Revert `booking.py`, focused tests, and doc updates together.

## No-go
- no reintroduction of `_legacy.py` into `booking.py`
- no semantic rewrite added under import-cleanup cover
- no claim that Workstream 1 is closed by this block alone

## Risks/Blockers
- direct imports can expose latent circular-import mistakes in the booking/webhook cluster
- some booking helpers/constants still only exist in `decision.py`
- focused tests may still patch legacy locations that need narrow relocation

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `info.py`, `policy.py`, and `dedup.py` still remain on the active legacy mesh; `booking.py` may still keep explicit delayed `decision.py` residue where no narrower owner exists yet.
- `Why not in this block`: this block is limited to the active booking hotspot.
- `Risk if deferred`: the booking control path would continue to run through ambient legacy authority.
- `Linked follow-up Task Package(s)`: `WS1-closeout-remaining-active-mesh-cut`
- `Expiry/trigger to stop deferral`: if `booking.py` still imports `_legacy.py`, active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: remove ambient `_legacy.py` dependence from the remaining active mesh consumers (`info.py`, then `policy.py`, `dedup.py`).
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/dedup.py`
- `Blocked-by conditions`: direct-owner switch in `booking.py` exposes a missing owner surface that needs extraction before the next active-mesh cut.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `booking.py` no longer imports `_legacy.py`.
  - booking-stage orchestration now reads explicit owners directly (`ai_service.py`, `intent_service.py`, `trace.py`, `handover_owner_service.py`, `state_service.py`) and uses delayed accessors only for cycle-sensitive router owners (`context_manager.py`, `guards.py`) plus remaining `decision.py` residue.
  - remaining `decision.py` dependence in `booking.py` is explicit and narrow through `_decision_runtime()` only for helpers/constants not yet re-homed.
- `Files touched`:
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py` -> `15 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_prompt or booking_interrupt or booking_cancel or booking_reengage or booking_info"` -> `5 passed, 187 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_interrupt or booking_same_day or booking_human_request"` -> `4 passed, 188 deselected`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - grep now shows no `_legacy.py` import/use in `truffles-api/app/routers/webhook/booking.py`
  - booking prompt / booking interrupt / booking escalation hook regressions still pass on direct owner surfaces
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` authority from the active webhook booking-stage flow
- `Residual debt left for next block`:
  - `info.py`, `policy.py`, and `dedup.py` still remain on the active legacy mesh
  - `booking.py` still carries explicit delayed `decision.py` residue for helpers/constants that are not yet re-homed
