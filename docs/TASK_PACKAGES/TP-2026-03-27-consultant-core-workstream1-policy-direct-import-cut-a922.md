# TP-2026-03-27-consultant-core-workstream1-policy-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-policy-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-info-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-info-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-dedup-direct-import-cut`

## Название/цель
Снять ambient `_legacy.py` dependence с `policy.py`, чтобы policy-gate flow читал явные owner surfaces и использовал delayed direct `decision.py` / `context_manager.py` access только для оставшегося residue.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_policy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/tests/test_policy_handler_runtime.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/policy.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_message_endpoint.py -k "policy_handler or apply_policy_decision or _get_routing_policy or _should_escalate_to_pending"`
- `FACT findings`:
  - `policy.py` still depended on `_legacy.py` across routing policy lookup, escalation gating, text normalization, policy guard decisions, observability, and handover execution.
  - Most of that dependency already has real owners (`intent_service.py`, `trace.py`, `handover_owner_service.py`, `state_machine.py`, `state_service.py`).
  - The remaining `decision.py` dependency surface is finite (`ROUTING_MATRIX`, `_POLICY_HANDLERS`, `MSG_ESCALATED`, `_combine_sidecar`, `_contains_any`, `_is_hygiene_context_text`) and can be isolated behind explicit delayed accessors instead of the ambient compatibility bus.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python importlib import_module circular imports official docs`
- **Date/time (local):** `2026-03-27 22:09 +05`
- **Why this query is precise:** this block replaces function-local `_legacy.py` imports with explicit owner imports and delayed module access where router cycles still exist.
- **Sources opened (from this query):**
  - `Python official importlib docs`: `https://docs.python.org/3/library/importlib.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** official docs recommend explicit programmatic imports via `importlib.import_module()` / import machinery semantics when import timing matters.
- **Decision:** `build` — keep `policy.py` on explicit owners and use delayed local accessors for cycle-sensitive residue instead of ambient `_legacy.py`.
- **Rejected options:**
  - keep `_legacy.py` as convenience namespace: rejected because it preserves ambient authority in an active policy gate path.
  - broad re-home of every remaining decision-era helper before this cut: rejected because it is larger than this bounded Workstream 1 closeout block.

## Root cause (mandatory)
- **Symptom:** `policy.py` still routes live policy-gate behavior through `_legacy.py`.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/policy.py`
- **Evidence to capture:**
  - `policy.py` no longer imports `_legacy.py`
  - focused policy/message regressions still pass
  - remaining `decision.py` dependency is explicit and narrow
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after bus/context/response/booking/info cuts? Because the live policy gate still imports it directly.
  2. Why is that bad? Because policy-stage authority still runs through the compatibility namespace instead of explicit owner boundaries.
  3. Why does that block Workstream 1? Because criterion 4 requires active owner-adjacent legacy paths to become shadow-only or deleted.
  4. Why not defer? Because `policy.py` is still part of the active webhook mesh on the hot path.
  5. Why is a bounded fix possible? Because most dependencies already have owners and the remaining residue can be isolated behind delayed direct `decision.py` / `context_manager.py` access.
- **Root cause statement:** `policy.py` still routes live policy-gate behavior through `_legacy.py`, so active policy-stage authority remains coupled to the legacy compatibility bus instead of explicit owner modules.
- **Fix mechanism:** replace `_legacy.py` reads with direct owner calls, keep delayed accessors for cycle-sensitive router owners and decision-era residue, and update focused tests where patch points move.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse existing owner modules: `trace.py`, `handover_owner_service.py`, `state_machine.py`, `state_service.py`, `intent_service.py`.
  - Reuse delayed accessor pattern already used in `context_manager.py`, `response.py`, `booking.py`, and `info.py`.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block only reroutes an active consumer off the compatibility bus.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `policy.py` must preserve current hard-law/policy gating, escalation, and observability behavior.
- no new semantic owner path may be introduced.
- any remaining `decision.py` dependency must be explicit, not ambient via `_legacy.py`.

## Scope
- Remove `_legacy.py` import/use from `policy.py`.
- Switch policy-stage reads to explicit owners.
- Keep only delayed explicit `decision.py` / `context_manager.py` access for residue not yet re-homed.
- Update focused deterministic tests and repo truth.

## Out of scope
- `dedup.py`
- deletion of `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-policy-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add explicit owner imports plus delayed accessors for cycle-sensitive modules in `policy.py`.
2. Replace `_legacy.py` calls with direct owner calls; keep explicit `decision_router.*` only for residue.
3. Update focused tests if patch points moved.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `policy.py` no longer imports `_legacy.py`.
- focused policy/message regressions pass.
- remaining `decision.py` / `context_manager.py` dependency in `policy.py` is explicit and narrow.
- repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/policy.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_guard or policy_handler or handover_hooks or routing_policy or firebreak"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- diff showing `policy.py` without `_legacy.py`
- passing focused policy/message regressions
- explicit statement of remaining `decision.py` residue after the cut

## Rollback
- Revert `policy.py`, focused tests, and doc updates together.

## No-go
- no reintroduction of `_legacy.py` into `policy.py`
- no semantic rewrite added under import-cleanup cover
- no claim that Workstream 1 is closed by this block alone

## Risks/Blockers
- direct imports can expose latent circular-import mistakes in the webhook mesh
- some policy helpers/constants still only exist in `decision.py`
- focused tests may still patch legacy locations that need narrow relocation

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `dedup.py` still remains on the active legacy mesh; `policy.py` still keeps explicit delayed `decision.py` residue where no narrower owner exists yet.
- `Why not in this block`: this block is limited to the active policy hotspot.
- `Risk if deferred`: the policy gate would continue to run through ambient legacy authority.
- `Linked follow-up Task Package(s)`: `WS1-closeout-dedup-direct-import-cut`
- `Expiry/trigger to stop deferral`: if `policy.py` still imports `_legacy.py`, active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: remove ambient `_legacy.py` dependence from the last active mesh consumer `dedup.py`.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/dedup.py`
- `Blocked-by conditions`: direct-owner switch in `policy.py` exposes a missing owner surface that needs extraction before the final active-mesh cut.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `policy.py` no longer imports `_legacy.py`.
  - policy-gate flow now reads explicit owners directly (`intent_service.py`, `trace.py`, `handover_owner_service.py`, `state_machine.py`, `state_service.py`) and keeps delayed accessors only for `context_manager.py` plus remaining `decision.py` residue.
  - remaining `decision.py` dependence in `policy.py` is explicit and narrow through `_decision_runtime()` only for helpers/constants not yet re-homed.
- `Files touched`:
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/tests/test_policy_handler_runtime.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/policy.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py` -> `11 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py` -> `8 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_guard or policy_handler or handover_hooks or routing_policy or firebreak"` -> `13 passed, 179 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `5 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook/policy.py` -> no matches
  - focused policy-gate regressions still pass on direct owner surfaces
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` authority from the active webhook policy gate flow
- `Residual debt left for next block`:
  - `dedup.py` still remains on the active legacy mesh
  - `policy.py` still carries explicit delayed `decision.py` residue for helpers/constants that are not yet re-homed
