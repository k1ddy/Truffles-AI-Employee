# TP-2026-03-27-consultant-core-workstream1-context-manager-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-context-manager-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-continuity-transport-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-continuity-transport-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-response-direct-import-cut`

## Название/цель
Снять ambient `_legacy.py` dependence с `context_manager.py`, чтобы continuity/state bridge читал decision-era residue явно, а не через compatibility bus.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/routers/webhook/_legacy.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/context_manager.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_service_carryover or legacy_class_carryover or legacy_consult_context"`
- `FACT findings`:
  - `context_manager.py` still depended on `_legacy.py` for bridge keys, continuity TTLs, pending-question projection fallback, class/service carryover normalization, consult-context transforms, and memory-profile keys.
  - most of that dependency is just decision-era residue, not a reason for an ambient compatibility bus.
  - tests still touched `_legacy.py` via module aliases, so `_legacy.py` explicit allowlist also needed to cover alias-based repo consumers.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python import statement local imports circular dependency official`
- **Date/time (local):** `2026-03-27 16:52 +05`
- **Why this query is precise:** this block replaces function-local ambient compatibility imports with explicit delayed decision access and must stay safe under module initialization.
- **Sources opened (from this query):**
  - `Python builtins / import()` docs: `https://docs.python.org/3.12/library/functions.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** Python import mechanics support delayed module access where package context is unambiguous.
- **Decision:** `build` — use one local `_decision_runtime()` accessor in `context_manager.py` instead of `_legacy.py`.
- **Rejected options:**
  - keep `_legacy.py` for convenience: rejected because it preserves ambient authority.
  - top-level direct `decision.py` imports everywhere: rejected because delayed access is safer in this cycle-heavy bridge module.

## Root cause (mandatory)
- **Symptom:** `context_manager.py` remained one of the largest active `_legacy.py` consumers even after the bus and continuity/transport cuts.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/context_manager.py`
- **Evidence to capture:**
  - `_legacy.py` is no longer imported from `context_manager.py`
  - continuity/carryover tests still pass
  - explicit `_legacy.py` adapter still covers repo alias consumers through a governed allowlist
- **Five Whys (or equivalent):**
  1. Why was `context_manager.py` still coupled to `_legacy.py`? Because bridge keys, TTLs, transforms, and fallback helpers were all pulled from the bus.
  2. Why is that bad? Because the canonical state bridge remained tied to the legacy compatibility namespace instead of explicit owners.
  3. Why does that block Workstream 1? Because active owner-adjacent bridge code still read legacy authority ambiently.
  4. Why not postpone until state unification? Because Workstream 1 specifically requires legacy owner-adjacent paths to become shadow-only or deleted.
  5. Why is a bounded fix possible? Because the remaining dependency surface is finite and can be routed through one explicit delayed decision accessor.
- **Root cause statement:** `context_manager.py` kept bridge/state continuity semantics coupled to `_legacy.py`, so the canonical continuity bridge still depended on ambient legacy authority instead of explicit owned helpers.
- **Fix mechanism:** replace `_legacy.py` reads with one local explicit `_decision_runtime()` accessor, keep bridge logic intact, and refresh `_legacy.py` allowlist to cover repo alias consumers explicitly.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse current bridge logic and `DialogStateService`.
  - Reuse the explicit `_decision_runtime()` pattern already introduced in other files.
- **External reuse:**
  - No external library is needed.
- **Why not reinvent the wheel:** this block only reroutes the dependency boundary; it does not redesign continuity semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `context_manager.py` must preserve current continuity behavior.
- no new semantic owner path may appear.
- any remaining decision-era dependency must be explicit, not ambient.

## Scope
- Remove `_legacy.py` import/use from `context_manager.py`.
- Refresh `_legacy.py` explicit export list so test alias consumers remain governed and explicit.
- Run focused continuity tests and architecture guard.

## Out of scope
- `response.py`
- `booking.py`, `info.py`, `policy.py`, `dedup.py`
- full deletion of `decision.py`

## Touch-list
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-context-manager-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Replace `_legacy.py` dependence in `context_manager.py` with delayed explicit `decision` access.
2. Refresh `_legacy.py` allowlist to include alias-based repo consumers explicitly.
3. Run focused continuity and legacy-boundary checks.
4. Update repo truth once for the whole block.

## DoD
- `context_manager.py` no longer imports `_legacy.py`
- focused continuity tests pass
- `_legacy.py` remains explicit/governed and now covers alias-based repo consumers explicitly

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/_legacy.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/trace.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_service_carryover or legacy_class_carryover or legacy_consult_context or set_expected_reply_context_records_canonical_pending_question_contract_in_evidence or expected_reply_contract_prefers_canonical_context_question_contract_over_stale_projection or expected_reply_contract_prefers_session_memory_pending_question_contract or expected_reply_contract_bypasses_human_request"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py truffles-api/tests/test_pending_pack_lexicons.py`
- `git diff --check`

## Evidence
- diff showing `context_manager.py` without `_legacy.py`
- passing continuity-focused regressions
- governed `_legacy.py` export surface still explicit

## Rollback
- Revert `context_manager.py`, `_legacy.py`, and doc updates together.

## No-go
- no reintroduction of wildcard bus access
- no semantic rewrite hidden in the bridge
- no claim that active legacy mesh is fully closed by this block

## Risks/Blockers
- alias-based test consumers can expose missing explicit exports
- `decision.py` still owns many residual constants/helpers

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `response.py`, `booking.py`, `info.py`, `policy.py`, and `dedup.py` still depend on decision-era helpers; `context_manager.py` still uses delayed direct `decision` access because those helpers/constants are not yet re-homed.
- `Why not in this block`: this cut is limited to the state/continuity bridge.
- `Risk if deferred`: active bridge authority would stay coupled to the legacy bus.
- `Linked follow-up Task Package(s)`: `WS1-closeout-response-direct-import-cut`
- `Expiry/trigger to stop deferral`: if `context_manager.py` still imports `_legacy.py`, the active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: remove ambient `_legacy.py` dependence from `response.py`.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/response.py`
- `Blocked-by conditions`: response-stage tests reveal unresolved owner/helper placement that requires a narrower extraction first.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `context_manager.py` no longer depends on `_legacy.py`; bridge/state continuity now reads decision-era residue through one explicit delayed `decision` accessor.
  - `_legacy.py` explicit allowlist was refreshed so repo alias consumers remain explicit/governed instead of silently missing behind wildcard behavior.
- `Files touched`:
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/routers/webhook/_legacy.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/_legacy.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/trace.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_service_carryover or legacy_class_carryover or legacy_consult_context or set_expected_reply_context_records_canonical_pending_question_contract_in_evidence or expected_reply_contract_prefers_canonical_context_question_contract_over_stale_projection or expected_reply_contract_prefers_session_memory_pending_question_contract or expected_reply_contract_bypasses_human_request"` -> `9 passed, 183 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py truffles-api/tests/test_pending_pack_lexicons.py` -> `11 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - grep now shows no `_legacy.py` import/use in `context_manager.py`
  - continuity regressions still prove canonical class/service/consult carryover and pending-question projection behavior
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` authority from the canonical continuity bridge
- `Residual debt left for next block`:
  - `response.py` remains the next large active `_legacy.py` consumer
  - `booking.py`, `info.py`, `policy.py`, and `dedup.py` still remain in the active mesh
