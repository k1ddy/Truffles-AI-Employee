# TP-2026-03-27-consultant-core-workstream1-final-legacy-compat-residue-demotion-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-final-legacy-compat-residue-demotion`
- `PARENT_BLOCK_ID`: `WS1-closeout-media-outbox-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-media-outbox-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-proof-pass`

## Название/цель
Снять remaining `_legacy.py` compatibility residue из `__init__.py` и `tool_registry_service.py`, затем убрать безопасную первую волну `legacy.*` rebinding в `decision.py`, где прямые owners уже импортированы или определены локально.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_services_tool_registry_service.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/__init__.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\.|from app\\.routers\\.webhook\\._legacy import" truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py`
  - `rg -n "is_greeting_message|classify_intent|EXPECTED_REPLY_TIME|TIME_PATTERN|_resolve_controller_signal_class|DomainIntent|_set_router_observability" truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - `__init__.py` still re-exports runtime primitives and `ConversationState` through `_legacy.py` even though direct owners already exist.
  - `tool_registry_service.py` still imports `_legacy.py` inside calendar/catalog missing-slot handlers only for booking prompts and expected-reply constants.
  - `decision.py` still uses many `legacy.*` calls, but several safe groups already have direct imports/local defs, so the adapter residue is partly stale aliasing rather than a hard dependency.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/reference import statement python reference`
- **Date/time (local):** `2026-03-27 15:55 +05`
- **Why this query is precise:** this block replaces ambient compatibility adapter imports with explicit imports and narrow local bindings while preserving import safety.
- **Sources opened (from this query):**
  - `Python Language Reference / The import system`: `https://docs.python.org/3.15/reference/import.html`
- **Source quality:** official Python documentation (primary source).
- **Existing solutions found:** Python import semantics support explicit imports and narrow delayed binding instead of wildcard compatibility adapters.
- **Decision:** `build` — remove `_legacy.py` from the remaining easy consumers and rebind the safe `decision.py` groups directly.
- **Rejected options:**
  - keep `_legacy.py` in `__init__.py` / `tool_registry_service.py` for convenience: rejected because it leaves default-path compatibility residue alive.
  - rewrite the whole of `decision.py` in one cut: rejected because it raises unnecessary regression risk for this bounded block.

## Root cause (mandatory)
- **Symptom:** Workstream 1 still has `_legacy.py` residue after the active helper-family cuts.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\.|from app\\.routers\\.webhook\\._legacy import" truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py`
- **Evidence to capture:**
  - `__init__.py` and `tool_registry_service.py` no longer import `_legacy.py`
  - targeted `decision.py` functions no longer import `_legacy.py` for stale aliasing
  - focused regressions and architecture freeze guards stay green
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still open? Because `_legacy.py` still survives on exported runtime surfaces and service-side missing-slot logic.
  2. Why is that a blocker? Because criterion 4 requires legacy owner-adjacent paths to become shadow-only or deleted.
  3. Why do these residues survive? Because constants/helpers were left routed through the compatibility adapter even after direct owners existed.
  4. Why not ignore `decision.py` for now? Because part of its `_legacy.py` usage is already stale aliasing and keeps the residue larger than necessary.
  5. Why do a first-wave rebind instead of a total rewrite? Because the safe direct replacements are already visible in imports/local defs and can shrink authority without reopening unrelated controller/booking logic.
- **Root cause statement:** the remaining `_legacy.py` residue is partly real compatibility coupling and partly stale aliasing; until both are reduced, Workstream 1 cannot honestly claim that legacy owner-adjacent paths are shadow-only.
- **Fix mechanism:** replace trivial adapter imports with direct owners and cut the safe first-wave `decision.py` alias usage where direct names already exist.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse `runtime_primitives.py` for booking prompts and expected-reply constants
  - reuse direct imports and local helper defs already present in `decision.py`
- **External reuse:**
  - no external package is needed
- **Why not reinvent the wheel:** this block only rebinds existing owners and shrinks compatibility residue.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `3`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- public webhook exports remain stable for active callers
- tool missing-slot responses stay unchanged
- no new semantic owner path is introduced
- `decision.py` behavior remains unchanged apart from removing stale `_legacy.py` aliasing

## Scope
- remove `_legacy.py` from `truffles-api/app/routers/webhook/__init__.py`
- remove `_legacy.py` from `truffles-api/app/services/tool_registry_service.py`
- cut the safe first-wave `_legacy.py` aliasing in `truffles-api/app/routers/webhook/decision.py`
- add architecture proof for the new boundary
- update repo truth once for the whole block

## Out of scope
- deleting `decision.py`
- deleting `_legacy.py`
- deep controller/booking rewrite beyond the safe first-wave rebind
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-final-legacy-compat-residue-demotion-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Rebind `__init__.py` and `tool_registry_service.py` away from `_legacy.py` using direct runtime owners.
2. Rebind the safe `decision.py` groups that already have direct imports/local defs.
3. Add or extend architecture guards freezing the new residue boundary.
4. Run focused deterministic checks once for the whole block.
5. Update repo truth once for the whole block.

## DoD
- `__init__.py` and `tool_registry_service.py` contain no `_legacy.py` import
- targeted `decision.py` groups no longer import `_legacy.py`
- focused regressions pass
- architecture guard freezes the new boundary

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_info_interrupt_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "intent_shortcut or controller or expected_reply or class_router"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- `__init__.py` and `tool_registry_service.py` no longer import `_legacy.py`
- first-wave `decision.py` groups no longer rely on `_legacy.py`
- passing focused regressions
- architecture freeze guard for the new boundary

## Rollback
- restore the `_legacy.py` imports in these files and revert tests/docs together.

## No-go
- no new adapter/wildcard exports
- no semantic rewrite growth in `decision.py`
- no claim that Workstream 1 is done before the residual `decision.py` / `_legacy.py` shadow-only proof is complete

## Risks/Blockers
- `decision.py` still contains deeper `_legacy.py` residue beyond this safe first-wave
- direct imports must not create new import cycles

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: deeper `decision.py` / `_legacy.py` residue remains after the safe first-wave rebind.
- `Why not in this block`: the remaining residue mixes controller, consult, and trace plumbing and needs its own closeout/proof pass.
- `Risk if deferred`: Workstream 1 closeout still depends on proving the remaining residue is shadow-only or cutting it further.
- `Linked follow-up Task Package(s)`: `WS1-closeout-proof-pass`
- `Expiry/trigger to stop deferral`: if any new default-path file reintroduces `_legacy.py`, this deferral is no longer valid.

## Next-block contract (mandatory)
- `Next block objective`: perform the honest Workstream 1 closeout/proof pass against the remaining `decision.py` / `_legacy.py` residue.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\.|from app\\.routers\\.webhook\\._legacy import" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/_legacy.py`
- `Blocked-by conditions`: any focused regression shows behavior drift from the direct rebind.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - removed `_legacy.py` from `truffles-api/app/routers/webhook/__init__.py`
  - removed `_legacy.py` from `truffles-api/app/services/tool_registry_service.py`
  - cut the first large stale-alias slice in `truffles-api/app/routers/webhook/decision.py` so smalltalk/intent routing, expected-reply info blocking, controller meta, and class-router observability now read direct owners instead of `_legacy.py`
  - architecture proof now freezes this first-wave direct-owner boundary
- `Files touched`:
  - `truffles-api/app/routers/webhook/__init__.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-final-legacy-compat-residue-demotion-a922.md`
  - `STATE.md`
  - `STRUCTURE.md`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/__init__.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/tool_registry_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_info_interrupt_contract.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "detect_intent_signals or resolve_action or run_class_router_stage or expected_reply"` -> `15 passed, 177 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py` -> `13 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_booking_appointments.py -k "service_choice or missing_date or invalid_date or missing_start_at"` -> `1 passed, 89 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `11 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `rg -n "from app\.routers\.webhook\._legacy import|from \. import _legacy as legacy|from app\.routers\.webhook import _legacy as legacy" truffles-api/app/routers/webhook truffles-api/app/services` -> only `truffles-api/app/routers/webhook/decision.py:1265`, `:2093`, `:4721`
  - `__init__.py` and `tool_registry_service.py` now have no `_legacy.py` import
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - `_legacy.py` is no longer a live export/service helper bus outside `decision.py`
  - the remaining live residue is isolated to `decision.py`
- `Residual debt left for next block`:
  - remaining `decision.py` / `_legacy.py` residue still needs final shadow-only proof or direct-owner closeout before Workstream 1 can be called done
