# TP-2026-03-27-consultant-core-workstream1-dedup-direct-import-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-dedup-direct-import-cut`
- `PARENT_BLOCK_ID`: `WS1-closeout-policy-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-policy-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-owner-adjacent-residue-scan`

## Название/цель
Снять ambient `_legacy.py` dependence с `dedup.py`, чтобы последний active webhook mesh consumer больше не тянул compatibility bus даже для env-gating helpers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_routers_webhook_dedup.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/webhook/dedup.py`
  - `truffles-api/tests/test_webhook_dedup.py`
- `Baseline commands`:
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/dedup.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_dedup.py`
- `FACT findings`:
  - `dedup.py` still imported `_legacy.py` for `_is_env_enabled(...)` in debounce and fast-dedup gates.
  - That dependency is small and can be narrowed to explicit delayed `decision.py` access without behavior change.
  - This is the last active webhook mesh consumer still pulling ambient `_legacy.py` after the prior macro cuts.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python import system import_module official documentation`
- **Date/time (local):** `2026-03-27 22:22 +05`
- **Why this query is precise:** this block removes the last function-local `_legacy.py` imports from the active webhook mesh and keeps only explicit delayed module access where import timing still matters.
- **Sources opened (from this query):**
  - `Python import system / importlib migration reference`: `https://docs.python.org/3/library/importlib.html`
- **Source quality:** Python official documentation (primary source).
- **Existing solutions found:** official docs recommend explicit programmatic imports when import timing matters instead of broad compatibility namespaces.
- **Decision:** `build` — keep `dedup.py` on a narrow delayed `decision.py` accessor and remove `_legacy.py` entirely from the active dedup path.
- **Rejected options:**
  - keep `_legacy.py` just for `_is_env_enabled`: rejected because it preserves ambient authority for the last active consumer.
  - re-home `_is_env_enabled` globally in this block: rejected because it is beyond the bounded Workstream 1 closeout cut.

## Root cause (mandatory)
- **Symptom:** `dedup.py` still routes env-gating through `_legacy.py`.
- **Minimal reproduction:**
  - `rg -n "from \\. import _legacy as legacy|legacy\\." truffles-api/app/routers/webhook/dedup.py`
- **Evidence to capture:**
  - `dedup.py` no longer imports `_legacy.py`
  - focused dedup regressions still pass
  - remaining decision-era dependence is explicit and narrow
- **Five Whys (or equivalent):**
  1. Why does `_legacy.py` still matter after policy/info/booking/response/context cuts? Because dedup still imports it for env-gating helpers.
  2. Why is that bad? Because the active webhook mesh is still not fully detached from the ambient compatibility bus.
  3. Why does that block honest Workstream 1 reporting? Because criterion 4 requires active owner-adjacent legacy paths to be shadow-only or removed.
  4. Why not defer? Because this is the last active mesh consumer and the cut is bounded.
  5. Why is a bounded fix possible? Because the dependency surface is only `_is_env_enabled(...)`.
- **Root cause statement:** `dedup.py` still reaches into `_legacy.py` for runtime env parsing, leaving one ambient compatibility dependency alive on the active webhook mesh.
- **Fix mechanism:** add a narrow delayed `decision.py` accessor inside `dedup.py`, replace `_legacy.py` reads with explicit `decision_router._is_env_enabled(...)`, and update focused tests where patch points have already moved to direct owners.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse the delayed accessor pattern already used across the webhook mesh cuts.
  - Reuse the existing `decision.py` `_is_env_enabled(...)` implementation instead of inventing a new env parser in `dedup.py`.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block only removes the final ambient bus import from the active dedup path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- `dedup.py` must preserve debounce, buffer, and fast-dedup gate behavior.
- no new semantic owner path may be introduced.
- any remaining `decision.py` dependency must be explicit, not ambient via `_legacy.py`.

## Scope
- Remove `_legacy.py` import/use from `dedup.py`.
- Keep only explicit delayed `decision.py` access for `_is_env_enabled(...)`.
- Update focused deterministic tests and repo truth.

## Out of scope
- re-homing `_is_env_enabled(...)` out of `decision.py`
- dormant residue cleanup (`booking_prompt_owner.py`, `reasoning_core.py`, `app/webhook.py`)
- Workstream 2+

## Touch-list
- `truffles-api/app/routers/webhook/dedup.py`
- `truffles-api/tests/test_webhook_dedup.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-dedup-direct-import-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add a narrow delayed `decision.py` accessor inside `dedup.py`.
2. Replace `_legacy.py` env reads with explicit `decision_router._is_env_enabled(...)`.
3. Update focused tests if stale legacy patch points surface.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `dedup.py` no longer imports `_legacy.py`.
- focused dedup regressions pass.
- remaining `decision.py` dependency in `dedup.py` is explicit and narrow.
- repo truth reflects the reduced authority.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/dedup.py truffles-api/tests/test_webhook_dedup.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_dedup.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- diff showing `dedup.py` without `_legacy.py`
- passing focused dedup regressions
- explicit statement that the active webhook mesh no longer imports `_legacy.py`

## Rollback
- Revert `dedup.py`, focused tests, and doc updates together.

## No-go
- no reintroduction of `_legacy.py` into `dedup.py`
- no semantic rewrite added under import-cleanup cover
- no claim that Workstream 1 is closed by this block alone

## Risks/Blockers
- stale tests may still patch legacy locations in adjacent guards/dedup helpers
- `_is_env_enabled(...)` is still a decision-era residue until later re-home/delete work

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: active webhook mesh is cleaned from ambient `_legacy.py`, but dormant owner-adjacent residue still remains in `booking_prompt_owner.py`, `reasoning_core.py`, and `app/webhook.py`; `dedup.py` still keeps explicit delayed `decision.py` residue for `_is_env_enabled(...)`.
- `Why not in this block`: this block is limited to the last active mesh consumer.
- `Risk if deferred`: the active mesh would still retain one ambient compatibility dependency and Workstream 1 closeout would remain dishonest.
- `Linked follow-up Task Package(s)`: `WS1-closeout-owner-adjacent-residue-scan`
- `Expiry/trigger to stop deferral`: if any active webhook mesh consumer still imports `_legacy.py`, the closeout claim is invalid.

## Next-block contract (mandatory)
- `Next block objective`: close remaining owner-adjacent dormant residue (`booking_prompt_owner.py`, `reasoning_core.py`, `app/webhook.py`) into `shadow-only/delete` status.
- `First deterministic check command`: `rg -n "booking_prompt_owner|reasoning_core|app/webhook.py" docs/system_forensics/files docs/system_forensics/final STATE.md`
- `Blocked-by conditions`: active-mesh closeout exposes hidden non-test callers or active routes that keep dormant residue live.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `dedup.py` no longer imports `_legacy.py`.
  - the active dedup/debounce flow now uses one explicit delayed `decision.py` accessor only for `_is_env_enabled(...)`.
  - focused guards-adjacent dedup tests now patch direct owners instead of the compatibility bus.
- `Files touched`:
  - `truffles-api/app/routers/webhook/dedup.py`
  - `truffles-api/tests/test_webhook_dedup.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/routers/webhook/dedup.py truffles-api/tests/test_webhook_dedup.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_webhook_dedup.py` -> `8 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"` -> `1 passed, 191 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `5 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `rg -n "from \\. import _legacy as legacy|_legacy" truffles-api/app/routers/webhook/dedup.py` -> no matches
  - active webhook mesh consumers `context_manager.py`, `response.py`, `booking.py`, `info.py`, `policy.py`, `pending.py`, `guards.py`, and `dedup.py` now all avoid `_legacy.py` imports
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - the last ambient `_legacy.py` import from the active webhook mesh
- `Residual debt left for next block`:
  - dormant owner-adjacent residue still remains outside the active mesh
  - `dedup.py` still carries explicit delayed `decision.py` residue for `_is_env_enabled(...)`
