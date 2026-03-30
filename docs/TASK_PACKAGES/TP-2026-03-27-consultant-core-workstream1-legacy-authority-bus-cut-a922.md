# TP-2026-03-27-consultant-core-workstream1-legacy-authority-bus-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-legacy-authority-bus-cut`
- `PARENT_BLOCK_ID`: `WS1-F8-memory-profile-canonical-read-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-memory-profile-canonical-read-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-active-legacy-mesh-cut`

## Название/цель
Зафиксировать execution-only closeout для `Workstream 1` и убрать главный structural blocker: `_legacy.py` больше не должен быть ambient wildcard bus поверх `decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/files/app_routers_webhook_legacy.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_context_manager.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/_legacy.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `sed -n '1,220p' truffles-api/app/routers/webhook/_legacy.py`
  - `rg -n "from \\. import _legacy as legacy|app\\.routers\\.webhook\\._legacy" truffles-api/app truffles-api/tests`
- `FACT findings`:
  - `_legacy.py` currently imports `decision` as a whole and re-exports every non-dunder symbol via `for _name, _value in _decision.__dict__.items()`.
  - `docs/system_forensics/files/app_routers_webhook_decision.md:89` already identifies `_legacy.py` fanout as the structural blocker that keeps `decision.py` symbols live across the webhook stack.
  - Active modules and tests depend on a wide but finite compatibility surface; the problem is ambient uncontrolled re-export, not absence of a surface boundary.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python module __getattr__ explicit exports documentation`
- **Date/time (local):** `2026-03-27 15:26 +05`
- **Why this query is precise:** this block converts a dynamic module compatibility bus into an explicit governed export boundary.
- **Sources opened (from this query):**
  - `Python Data Model`: `https://docs.python.org/3.15/reference/datamodel.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** Python supports module-level attribute customization, but that is a dynamic hook and not the right fit for shrinking a legacy authority bus.
- **Decision:** `build` — keep `_legacy.py` as a static explicit export adapter instead of dynamic fallback or wildcard namespace mirroring.
- **Rejected options:**
  - module-level `__getattr__` fallback: rejected because it preserves hidden growth and weakens auditability.
  - keep `decision.__dict__` mirroring: rejected because it keeps `_legacy.py` as an uncontrolled authority fanout.

## Root cause (mandatory)
- **Symptom:** `Workstream 1` remains open even after runtime-core cleanup because the legacy webhook mesh still depends on `_legacy.py` as a broad compatibility authority bus.
- **Minimal reproduction:**
  - `sed -n '1,220p' truffles-api/app/routers/webhook/_legacy.py`
  - `rg -n "from \\. import _legacy as legacy" truffles-api/app/routers/webhook`
- **Evidence to capture:**
  - `_legacy.py` becomes an explicit allowlisted adapter surface
  - no ambient `decision.__dict__` mirroring remains
  - current consumers still work through the narrowed explicit surface
- **Five Whys (or equivalent):**
  1. Why is the legacy webhook mesh still hard to demote? Because `_legacy.py` exposes nearly all of `decision.py` ambiently.
  2. Why does that matter? Because any symbol inside `decision.py` can stay accidentally live without an explicit compatibility decision.
  3. Why is that bad for `Workstream 1`? Because legacy owner-adjacent paths cannot become governed/shadow-only while the wildcard bus exists.
  4. Why not jump directly to deleting all consumers? Because the consumers are still live and need a bounded compatibility surface during strangler cutover.
  5. Why is a bounded fix possible now? Because the actual compatibility surface is finite and can be enumerated from current repo consumers.
- **Root cause statement:** `_legacy.py` currently acts as an uncontrolled wildcard export bus over `decision.py`, so legacy webhook modules retain ambient semantic/control authority without an explicit governed boundary.
- **Fix mechanism:** replace wildcard mirroring with an explicit allowlisted adapter surface derived from current consumers, add an architecture guard against wildcard regrowth, and keep further semantic cuts moving through governed named exports only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse the existing module split; do not invent a new compatibility layer.
  - Reuse current repo consumers as the source of truth for the temporary export allowlist.
- **External reuse:**
  - Python official module export guidance was consulted; no external library is needed.
- **Why not reinvent the wheel:** the codebase already has extracted modules and a compatibility adapter; this block only governs the adapter boundary.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** this is the first large closeout cut after analysis freeze; the goal is authority removal, not another analysis round.

## Invariant
- `_legacy.py` may remain only as an explicit compatibility adapter.
- No new semantic owner path may be created.
- Active consumers must keep working through the governed surface during this block.
- No wildcard or hidden fallback export growth is allowed back into `_legacy.py`.

## Scope
- Replace `_legacy.py` wildcard `decision.__dict__` mirroring with an explicit allowlist.
- Keep only explicit shared/runtime/handover exports and explicit `decision.py` compatibility exports.
- Add deterministic guard coverage for the new adapter boundary.
- Update repo truth/docs for the macro-block execution mode and this authority cut.

## Out of scope
- Full removal of all `_legacy.py` consumers.
- Full demotion of `response.py`, `booking.py`, `info.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`.
- `Workstream 2+`.

## Touch-list
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-legacy-authority-bus-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Freeze the current compatibility surface to an explicit allowlist derived from repo consumers.
2. Remove wildcard namespace mirroring from `_legacy.py`.
3. Add an architecture test that fails if wildcard mirroring returns.
4. Run deterministic checks, then update repo truth once for the whole block.

## DoD
- `_legacy.py` no longer mirrors `decision.__dict__`.
- Compatibility exports are explicit and finite.
- Architecture test fails if wildcard mirroring is reintroduced.
- Deterministic checks prove the cut without breaking current compatibility consumers.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/_legacy.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_handover_adapter_exports_owner_surface_symbols or legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `git diff --check`

## Evidence
- Diff showing `_legacy.py` moved from wildcard mirroring to explicit allowlist.
- Architecture guard proving wildcard regrowth is blocked.
- Compatibility tests proving the narrowed adapter still serves current callers.

## Rollback
- Revert `_legacy.py`, the architecture guard, and TP/STATE/STRUCTURE updates together.

## No-go
- No new wildcard mirroring.
- No hidden `__getattr__` fallback.
- No claim that `Workstream 1` is done after this block.
- No expansion into unrelated package-seam or outbox work.

## Risks/Blockers
- Tests may patch `_legacy` names that are easy to miss if the allowlist is incomplete.
- Some compatibility names may only be exercised by broad suites.
- This block removes the structural blocker, not the whole live semantic mesh.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: live webhook consumers still use `_legacy.py`; `decision.py` still contains mixed live helpers and dormant residue; active legacy mesh modules still hold semantic/control authority.
- `Why not in this block`: governing the adapter boundary is the fastest first cut before consumer-by-consumer demotion.
- `Risk if deferred`: wildcard export growth would keep reintroducing implicit authority and make the larger mesh cut slower and less auditable.
- `Linked follow-up Task Package(s)`: `WS1-closeout-active-legacy-mesh-cut`
- `Expiry/trigger to stop deferral`: if `_legacy.py` remains wildcard-based after this block, `Workstream 1` closeout must be considered blocked.

## Next-block contract (mandatory)
- `Next block objective`: cut the live webhook mesh off ambient `_legacy` semantics by demoting `context_manager.py`, `response.py`, `booking.py`, `info.py`, `pending.py`, `policy.py`, `guards.py`, and `dedup.py` to bounded helpers.
- `First deterministic check command`: `rg -n "from \\. import _legacy as legacy" truffles-api/app/routers/webhook`
- `Blocked-by conditions`: explicit allowlist still missing active compatibility names, or wildcard mirroring remains in `_legacy.py`.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `_legacy.py` is no longer an ambient wildcard mirror over `decision.py`; it is now a governed explicit compatibility adapter with a finite allowlist derived from current repo consumers.
  - wildcard export growth from `decision.py` can no longer silently become live through `_legacy.py`.
  - current compatibility consumers still resolve through the adapter while the next large mesh-demotion block is prepared.
- `Files touched`:
  - `truffles-api/app/routers/webhook/_legacy.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-legacy-authority-bus-cut-a922.md`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/_legacy.py truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `5 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_handover_adapter_exports_owner_surface_symbols or legacy_webhook_compat_routes_through_public_entrypoint_contract"` -> `4 passed, 188 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_response.py truffles-api/tests/test_webhook_dedup.py` -> `16 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - added architecture guard proving `_legacy.py` keeps an explicit `_DECISION_EXPORTS` allowlist and no longer mirrors `decision.__dict__`.
  - compatibility smoke tests still prove legacy adapter exports and the public-entrypoint compatibility route.
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut.
- `Authority removed`:
  - uncontrolled wildcard fanout from `decision.py` into the legacy webhook mesh.
- `Residual debt left for next block`:
  - active webhook modules still import `_legacy.py` and still hold semantic/control authority even though the adapter boundary is now explicit.
  - `booking_prompt_owner.py`, `reasoning_core.py`, and `app/webhook.py` remain owner-adjacent residue to classify or delete later in Workstream 1.
