# TP-2026-03-27-consultant-core-workstream1-secondary-helper-mesh-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-secondary-helper-mesh-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-dormant-shadow-lane-collapse`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-dormant-shadow-lane-collapse-a922.md`
- `UNLOCKS`: `WS1-closeout-helper-shadow-proof`

## Название/цель
Снять remaining `_legacy.py` authority из secondary webhook helper mesh: перевести `branch_selection.py`, `shield.py`, `session_memory.py`, `trace.py` на direct owner imports / local helper ownership и убрать зависимость от ambient legacy adapter.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/branch_selection.py`
  - `truffles-api/app/routers/webhook/shield.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_branch_routing_instance.py`
  - `truffles-api/tests/test_shield_trace_contract.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook/branch_selection.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/trace.py`
  - `rg -n "SHIELD_|SESSION_MEMORY_" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "_record_decision_trace|_set_router_observability|_set_context_manager|_set_expected_reply_type|_set_intent_queue|_set_booking_context|_clear_service_hint" truffles-api/app/routers/webhook/{branch_selection.py,shield.py,session_memory.py,trace.py,context_manager.py,booking.py,guards.py}`
- `FACT findings`:
  - `branch_selection.py` still uses `_legacy.py` for text normalization, user branch preference persistence, and trace recording even though direct/local owners already exist.
  - `shield.py` still uses `_legacy.py` for shield constants, context access, trace/meta writes, escalation bridge, and state constants.
  - `session_memory.py` still uses `_legacy.py` for local constants and setter hooks despite extracted direct owners existing in `context_manager.py`, `guards.py`, and `booking.py`.
  - `trace.py` still routes trace persistence through `_legacy.py`, so even direct trace consumers keep the legacy adapter live.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/reference import statement python reference`
- **Date/time (local):** `2026-03-27 23:20 +05`
- **Why this query is precise:** this block replaces ambient legacy import fanout with explicit imports and delayed direct owner access where cycles remain.
- **Sources opened (from this query):**
  - `Python Language Reference / import system`: `https://docs.python.org/3.15/reference/import.html`
- **Source quality:** official Python documentation (primary source).
- **Existing solutions found:** Python import semantics allow explicit narrow imports and delayed in-function imports for cycle-sensitive edges; a compatibility adapter is not required to keep module binding working.
- **Decision:** `build` — replace `_legacy.py` with explicit owner imports and narrow delayed imports only where module cycles require them.
- **Rejected options:**
  - keep `_legacy.py` as helper bus for secondary modules: rejected because it preserves ambient authority after the primary mesh cut.
  - move all remaining helper logic into `decision.py`: rejected because it regrows the legacy god-file instead of reducing authority.

## Root cause (mandatory)
- **Symptom:** `_legacy.py` remains live because secondary helper modules still import it for constants, trace writes, context setters, and escalation helpers.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook/branch_selection.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/trace.py`
- **Evidence to capture:**
  - target helper modules no longer import `_legacy.py`
  - `trace.py` persists traces through direct context-manager hooks
  - architecture guard freezes the no-`_legacy` state for this helper cluster
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still open after the active mesh cut? Because helper-stage `_legacy.py` imports still keep the adapter live.
  2. Why does that matter? Because ambient legacy imports keep old authority reachable from current runtime helpers.
  3. Why are these helpers still coupled to `_legacy.py`? Because they inherited constants and setters from the old monolith instead of owning or directly importing them.
  4. Why not leave them for later? Because criterion 4 requires legacy owner-adjacent paths to be shadow-only or deleted before Workstream 1 closeout.
  5. Why is `_record_decision_trace` especially important? Because it is a shared helper; if it routes through `_legacy.py`, the adapter stays active even after most business paths were cleaned up.
- **Root cause statement:** secondary webhook helpers still use `_legacy.py` as an ambient import bus for constants and direct owner hooks, so legacy authority remains reachable beyond the already cleaned primary mesh.
- **Fix mechanism:** move helper-owned constants into the helper modules, switch to direct owner imports or narrow delayed imports for cycle-sensitive edges, and freeze the new boundary with architecture tests.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse extracted owners already present in `context_manager.py`, `booking.py`, `guards.py`, `trace.py`, `handover_owner_service.py`, and `state_machine.py`.
  - Reuse helper-local functions already present in `branch_selection.py` for user branch persistence.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block rebinds existing owners directly; it does not change product behavior or introduce new helper families.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `3`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- branch-selection, shield, session-memory, and trace behavior must stay deterministic.
- no new semantic owner or compatibility authority path may be introduced.
- `decision.py` may remain as legacy residue, but it must not be required as the ambient adapter for these helpers.

## Scope
- Remove `_legacy.py` imports from `branch_selection.py`, `shield.py`, `session_memory.py`, and `trace.py`.
- Give helper modules direct/local ownership of their constants and direct owner hooks.
- Add architecture proof freezing the no-`_legacy` state for this helper cluster.
- Update focused deterministic tests and repo truth.

## Out of scope
- `outbox.py` / `media.py` cleanup
- deleting `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/branch_selection.py`
- `truffles-api/app/routers/webhook/shield.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_branch_routing_instance.py`
- `truffles-api/tests/test_shield_trace_contract.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-secondary-helper-mesh-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Rebind `branch_selection.py` and `trace.py` away from `_legacy.py` using direct/local owners.
2. Rebind `shield.py` and `session_memory.py` away from `_legacy.py`, moving helper constants to their owning modules.
3. Update `decision.py` imports if helper-owned constants need to stay re-exported there.
4. Add architecture freeze guards for the helper cluster.
5. Run focused deterministic checks once for the whole block.
6. Update repo truth once for the whole block.

## DoD
- target helper modules contain no `_legacy.py` import.
- trace persistence no longer routes through `_legacy.py`.
- focused regressions pass.
- architecture guard freezes the helper cluster boundary.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/branch_selection.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/trace.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_branch_routing_instance.py truffles-api/tests/test_shield_trace_contract.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_branch_routing_instance.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_shield_trace_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "session_memory or expected_reply"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- helper cluster no longer imports `_legacy.py`
- passing focused regressions
- architecture freeze guard for the helper cluster

## Rollback
- Restore `_legacy.py` imports in the four helper modules and revert the helper-owned constant move together with tests/docs.

## No-go
- no new wildcard or ambient adapter exports
- no helper logic moved back into `_legacy.py`
- no claim that Workstream 1 is done before remaining `_legacy.py` users are reassessed

## Risks/Blockers
- `media.py` and `outbox.py` still remain outside this block and may keep additional legacy residue.
- hidden import cycles may require delayed direct imports instead of top-level imports.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `media.py`, `outbox.py`, `decision.py`, and selected service-side `_legacy` consumers remain after this helper cluster cut.
- `Why not in this block`: they are a larger residue family than the current helper-stage authority cut.
- `Risk if deferred`: Workstream 1 closeout remains blocked until those remaining `_legacy.py` consumers are either demoted or proven shadow-only.
- `Linked follow-up Task Package(s)`: `WS1-closeout-remaining-legacy-helper-proof`
- `Expiry/trigger to stop deferral`: if any new business-path helper starts importing `_legacy.py`, the remaining residue boundary expands and this deferral stops being valid.

## Next-block contract (mandatory)
- `Next block objective`: reassess remaining `_legacy.py` consumers (`media.py`, `outbox.py`, service-side callers) and decide the final closeout path for Workstream 1.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook truffles-api/app/services | sed -n '1,200p'`
- `Blocked-by conditions`: helper cut reveals hidden runtime cycles or remaining `_legacy.py` consumers stay active on the default path.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - removed `_legacy.py` from the secondary helper mesh (`branch_selection.py`, `shield.py`, `session_memory.py`, `trace.py`)
  - trace persistence now writes through direct `context_manager.py` hooks instead of the compatibility adapter
  - helper-local constants and setter hooks now live with the helper modules or their explicit owners instead of the ambient legacy bus
- `Files touched`:
  - `truffles-api/app/routers/webhook/branch_selection.py`
  - `truffles-api/app/routers/webhook/shield.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/branch_selection.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/trace.py truffles-api/tests/test_branch_routing_instance.py truffles-api/tests/test_shield_trace_contract.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_branch_routing_instance.py` -> `20 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_shield_trace_contract.py` -> `13 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "session_memory or expected_reply"` -> `20 passed, 60 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "expected_reply_contract_bypasses_human_request or expected_reply_contract_prefers_session_memory_pending_question_contract"` -> `2 passed, 190 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `9 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook/branch_selection.py truffles-api/app/routers/webhook/shield.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/trace.py` -> no matches
  - architecture guard now freezes the helper cluster against `_legacy.py` reintroduction
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - `_legacy.py` is no longer the secondary helper mesh authority bus for branch selection, shield, session memory, or trace persistence
- `Residual debt left for next block`:
  - remaining `_legacy.py` consumers are now narrowed to `media.py`, `outbox.py`, `decision.py`, `__init__.py`, and selected service-side compatibility callers
