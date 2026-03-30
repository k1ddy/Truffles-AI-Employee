# TP-2026-03-27-consultant-core-workstream1-continuity-transport-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-continuity-transport-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-legacy-authority-bus-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-legacy-authority-bus-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-active-legacy-mesh-cut`

## Название/цель
Снять ambient `_legacy.py` authority с continuity/transport helpers, начав с `pending.py` и `guards.py`: эти live modules должны читать explicit narrow imports, а не wildcard compatibility bus.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_pending.md`
- `docs/system_forensics/files/app_routers_webhook_guards.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/tests/test_pending_pack_lexicons.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
- `FACT findings`:
  - `pending.py` and `guards.py` still route live continuity, mute, reengage, pending-status, and clarify transport through `_legacy.py`.
  - Most touched dependencies already have explicit owners (`context_manager.py`, `trace.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`); `_legacy.py` is only the ambient bus.
  - A small subset of decision-era helpers/constants still has no narrower home yet, so this block must access them explicitly rather than ambiently.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python import statement execution module initialization circular imports official`
- **Date/time (local):** `2026-03-27 16:08 +05`
- **Why this query is precise:** this block replaces ambient compatibility imports with explicit module imports and a few runtime direct imports that must remain safe under Python module initialization.
- **Sources opened (from this query):**
  - `Python import internals / circular import note`: `https://docs.python.org/id/3.6/library/imp.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** Python import initialization tolerates circular imports as long as runtime access is delayed until module initialization completes.
- **Decision:** `build` — use explicit direct imports for stable dependencies and delayed `decision` access only where no narrower owner exists yet.
- **Rejected options:**
  - keep `_legacy.py` as the runtime dependency: rejected because it preserves ambient authority.
  - broad extraction of all remaining decision helpers first: rejected because it is larger than this bounded closeout cut.

## Root cause (mandatory)
- **Symptom:** after `_legacy.py` was governed, `pending.py` and `guards.py` still kept continuity/transport behavior coupled to the compatibility bus.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py`
- **Evidence to capture:**
  - those modules no longer import `_legacy.py`
  - transport behavior still works through explicit dependencies
  - tests patch the real module owners instead of the ambient bus
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after the explicit allowlist cut? Because live continuity modules still import it directly.
  2. Why is that bad? Because transport/routing authority still flows through the compatibility bus instead of explicit owned boundaries.
  3. Why does that block Workstream 1? Because criterion 4 requires legacy owner-adjacent paths to become shadow-only or deleted, not just governed but still live.
  4. Why not delete these modules now? Because they are still active runtime helpers and need a bounded demotion first.
  5. Why is a bounded cut possible? Because their dependencies are mostly already extracted; only a few decision-era helpers require delayed explicit access.
- **Root cause statement:** `pending.py` and `guards.py` still depend on `_legacy.py` as an ambient helper namespace, so continuity and transport authority remain coupled to the legacy compatibility bus even after that bus became explicit.
- **Fix mechanism:** replace `_legacy.py` reads with explicit imports from the real owners, extract router-observability helper into `trace.py`, and use delayed direct access to `decision.py` only for the small residual helper set that still lacks a narrower home.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse `context_manager.py`, `trace.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`, `telegram_service.py`, and `escalation_service.py` as the real owners.
  - Reuse `decision.py` only through explicit delayed access for still-unmoved residual helpers/constants.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** the extracted owners already exist; the block only reroutes consumers to them.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is a large consumer demotion cut within the active continuity/transport cluster.

## Invariant
- No new semantic owner may be introduced.
- `pending.py` and `guards.py` must stay behaviorally compatible while losing ambient `_legacy.py` dependency.
- Any remaining `decision.py` dependency must be explicit and narrow.

## Scope
- Remove `_legacy.py` imports from `pending.py` and `guards.py`.
- Move router-observability helper to `trace.py`.
- Update focused tests to patch the real module surfaces.
- Update repo truth/docs.

## Out of scope
- `context_manager.py`
- `response.py`, `booking.py`, `info.py`, `policy.py`, `dedup.py`
- deletion of `decision.py`
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-continuity-transport-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Extract router-observability helper into `trace.py`.
2. Replace `_legacy.py` dependence in `pending.py` with explicit imports and delayed narrow `decision` access.
3. Replace `_legacy.py` dependence in `guards.py` with explicit imports and delayed narrow `decision` access.
4. Update focused tests and run deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `pending.py` and `guards.py` no longer import `_legacy.py`.
- Focused continuity/guard regressions pass.
- Router-observability helper no longer needs to be reached through `_legacy.py` in these modules.
- Repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/trace.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "clarify_limit_escalation_passes_active_handover_hooks"`
- `git diff --check`

## Evidence
- Diff proving `pending.py` and `guards.py` no longer import `_legacy.py`
- Focused deterministic tests proving continuity/guard behavior still works
- `STATE.md` entry naming the authority removed

## Rollback
- Revert `trace.py`, `pending.py`, `guards.py`, focused tests, and doc updates together.

## No-go
- No new `_legacy.py` reads in these modules.
- No new semantic logic hidden in trace helpers.
- No claim that all active webhook mesh debt is solved by this block.

## Risks/Blockers
- Direct imports can expose circular-import mistakes if a dependency is not actually narrow.
- Some decision-era constants/helpers still have no cleaner home and remain explicit residual debt.
- Broader message-endpoint suites may still pin legacy patch points outside this block.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `context_manager.py`, `response.py`, `booking.py`, `info.py`, `policy.py`, and `dedup.py` still consume legacy decision-era helpers; some `decision.py` helpers/constants are still directly referenced by `pending.py` and `guards.py`.
- `Why not in this block`: this cut is limited to the continuity/transport cluster.
- `Risk if deferred`: active continuity behavior would keep ambient legacy bus authority.
- `Linked follow-up Task Package(s)`: `WS1-closeout-active-legacy-mesh-cut`
- `Expiry/trigger to stop deferral`: if these modules still import `_legacy.py` after this block, the active-mesh closeout is not progressing honestly.

## Next-block contract (mandatory)
- `Next block objective`: cut `_legacy.py` dependency from the remaining active mesh consumers, starting with `context_manager.py` and then `response.py`.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/response.py`
- `Blocked-by conditions`: focused regressions fail, or direct imports expose unresolved cycle debt that needs a narrower owner extraction first.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `pending.py` and `guards.py` no longer read the ambient `_legacy.py` namespace.
  - continuity/transport reads now go through explicit owners (`context_manager.py`, `trace.py`, `handover_owner_service.py`, `message_service.py`, `ai_service.py`, `telegram_service.py`, `escalation_service.py`).
  - remaining decision-era helper dependence is now explicit and local via delayed `decision` access instead of ambient `_legacy` fanout.
- `Files touched`:
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/tests/test_pending_pack_lexicons.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/trace.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/guards.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_pending_pack_lexicons.py` -> `6 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "clarify_limit_escalation_passes_active_handover_hooks"` -> `1 passed, 191 deselected`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - grep now shows no `_legacy.py` import/use in `pending.py` or `guards.py`
  - focused tests now patch the real module owners instead of the ambient compatibility bus
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - ambient `_legacy.py` continuity/transport authority in `pending.py` and `guards.py`
- `Residual debt left for next block`:
  - `context_manager.py`, `response.py`, `booking.py`, `info.py`, `policy.py`, and `dedup.py` still need the same treatment
  - some decision-era constants/helpers still need extraction to eliminate even the remaining explicit delayed `decision` dependency
