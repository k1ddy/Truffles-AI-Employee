# TP-2026-03-27-consultant-core-workstream1-dormant-shadow-lane-collapse-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-dormant-shadow-lane-collapse`
- `PARENT_BLOCK_ID`: `WS1-closeout-dedup-direct-import-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-dedup-direct-import-cut-a922.md`
- `UNLOCKS`: `WS1-closeout-shadow-only-proof`

## Название/цель
Схлопнуть оставшиеся dormant owner-adjacent residue lanes после active webhook mesh closeout: убрать вторую booking-owner lane из `app/core`, превратить `app/webhook.py` в тонкий compatibility delegate и зафиксировать, что `reasoning_core` остаётся только shadow-only compat shell без app-runtime importers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/files/app_core_booking_prompt_owner.md`
- `docs/system_forensics/files/app_services_reasoning_core.md`
- `docs/system_forensics/files/app_webhook.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/booking_prompt_owner.py`
  - `truffles-api/app/webhook.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `rg -n "resolve_pending_booking_reactivation_candidate|booking_prompt_owner" truffles-api`
  - `rg -n "from app import webhook|app\.webhook" truffles-api/app truffles-api/tests`
  - `rg -n "reasoning_core" truffles-api/app truffles-api/tests`
- `FACT findings`:
  - `app/core/booking_prompt_owner.py` has visible repo callers only from `truffles-api/tests/test_reasoning_core.py`; no visible `app/` caller remains.
  - `app/webhook.py` is unmounted; visible direct repo usage is the single compatibility test for `handle_webhook(...)`.
  - `reasoning_core.py` has no visible `app/` importers and already delegates public runtime entrypoints straight to `consultant_core_v2`, but repo still needs proof that it is shadow-only.

## One web search (mandatory before implementation)
- **Query (exact):** `site:fastapi.tiangolo.com FastAPI APIRouter path operation function official docs`
- **Date/time (local):** `2026-03-27 22:35 +05`
- **Why this query is precise:** this block collapses `app/webhook.py` into a minimal FastAPI compatibility delegate while keeping route handlers valid and bounded.
- **Sources opened (from this query):**
  - `FastAPI official APIRouter reference`: `https://fastapi.tiangolo.com/reference/apirouter/`
- **Source quality:** FastAPI official documentation (primary source).
- **Existing solutions found:** route handlers can remain thin delegates; compatibility routers do not need to warehouse helper logic.
- **Decision:** `build` — keep `app/webhook.py` as a tiny delegate-only compatibility shim, not a shadow helper warehouse.
- **Rejected options:**
  - keep dormant helper families in `app/webhook.py`: rejected because they preserve duplicate deterministic authority in an unmounted module.
  - keep `booking_prompt_owner.py` under `app/core`: rejected because it preserves a second owner-adjacent semantic lane inside runtime code despite test-only visibility.

## Root cause (mandatory)
- **Symptom:** after active mesh cleanup, dormant app-level residue still preserves alternate owner/control paths in runtime packages.
- **Minimal reproduction:**
  - `rg -n "resolve_pending_booking_reactivation_candidate|booking_prompt_owner" truffles-api`
  - `rg -n "from app import webhook|app\.webhook" truffles-api/app truffles-api/tests`
  - `rg -n "reasoning_core" truffles-api/app truffles-api/tests`
- **Evidence to capture:**
  - `booking_prompt_owner.py` removed from `app/core` and preserved only as test shadow helper
  - `app/webhook.py` reduced to thin delegates only
  - architecture proof that `reasoning_core.py` has no app-runtime importers
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 still open after active mesh cleanup? Because dormant owner-adjacent compatibility lanes still exist in runtime packages.
  2. Why is that a problem? Because they preserve alternative semantic/control authority even if they are not mounted today.
  3. Why does `booking_prompt_owner.py` matter? Because it is a second booking-owner lane inside `app/core` and still callable from repo code.
  4. Why does `app/webhook.py` matter? Because it still warehouses stale helper families that duplicate extracted owners.
  5. Why not postpone until later workstreams? Because Workstream 1 criterion 4 requires legacy owner-adjacent paths to become shadow-only or deleted before claiming closeout.
- **Root cause statement:** dormant compatibility residue still lives in runtime packages (`app/core/booking_prompt_owner.py`, `app/webhook.py`) and lacks a hard proof boundary for `reasoning_core.py`, so Workstream 1 cannot honestly claim those paths are shadow-only or removed.
- **Fix mechanism:** move the booking owner residue out of `app/core` into test-only shadow support, collapse `app/webhook.py` to delegate-only wrappers, and add architecture proof that `reasoning_core.py` has no app-runtime importers.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse active owners already extracted in `app.routers.webhook.http` and `app.routers.public_entrypoint_contract`.
  - Reuse existing booking-prompt-owner logic as test-only shadow support instead of reimplementing candidate rules.
- **External reuse:**
  - No external package is needed.
- **Why not reinvent the wheel:** this block removes dormant runtime authority by relocating or collapsing existing code, not by inventing new behavior.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`

## Invariant
- public compatibility `app.webhook.handle_webhook(...)` must keep delegating through `handle_public_webhook_payload(...)`.
- tests that intentionally cover booking reactivation shadow behavior must keep their current deterministic semantics.
- no new semantic owner path may be introduced.

## Scope
- Remove `booking_prompt_owner.py` from `app/core` by relocating it to test-only shadow support.
- Collapse `app/webhook.py` to thin delegates only.
- Add architecture proof for shadow-only residue status.
- Update focused deterministic tests and repo truth.

## Out of scope
- `decision.py` deletion
- `reasoning_core.py` full helper extraction
- Workstream 2+

## Touch-list
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/tests/support_booking_prompt_owner_shadow.py`
- `truffles-api/app/webhook.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-dormant-shadow-lane-collapse-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Relocate `booking_prompt_owner.py` from `app/core` into a test-only shadow helper and update tests.
2. Replace `app/webhook.py` helper warehouse with a thin compatibility delegate.
3. Add architecture guards proving `app/webhook.py` stays thin and `reasoning_core.py` has no app-runtime importers.
4. Run focused deterministic checks.
5. Update repo truth once for the whole block.

## DoD
- `truffles-api/app/core/booking_prompt_owner.py` no longer exists as runtime code.
- `truffles-api/app/webhook.py` contains only thin compatibility delegates.
- architecture tests prove `reasoning_core.py` has no app-runtime importers.
- focused regressions pass.

## Checks
- `python3 -m py_compile truffles-api/app/webhook.py truffles-api/tests/support_booking_prompt_owner_shadow.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- deleted runtime `booking_prompt_owner.py`
- thin `app/webhook.py`
- passing focused regressions and architecture proof

## Rollback
- Restore `app/core/booking_prompt_owner.py`, restore the old `app/webhook.py`, and revert focused tests/docs together.

## No-go
- no new runtime caller for the moved booking owner shadow helper
- no semantic logic added back into `app/webhook.py`
- no claim that Workstream 1 is done before dormant residue proof is complete

## Risks/Blockers
- hidden out-of-repo importers of `app.webhook` or `booking_prompt_owner.py` are `не знаю`
- architecture guards may expose other app-runtime importers that were not visible in the first grep pass

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `reasoning_core.py` still keeps compatibility helpers, but after this block it should be provably shadow-only from the app import graph.
- `Why not in this block`: full helper extraction from `reasoning_core.py` is larger than the current closeout cut.
- `Risk if deferred`: Workstream 1 could still overstate closeout if shadow-only proof is not explicit.
- `Linked follow-up Task Package(s)`: `WS1-closeout-shadow-only-proof`
- `Expiry/trigger to stop deferral`: if any app-runtime importer of `reasoning_core.py` appears, or `app/webhook.py` regrows helper families, this deferral stops being valid.

## Next-block contract (mandatory)
- `Next block objective`: prove or finish remaining shadow-only status for `reasoning_core.py` and any other owner-adjacent dormant residue, then decide honest Workstream 1 closeout status.
- `First deterministic check command`: `rg -n "app\.services\.reasoning_core|reasoning_core" truffles-api/app | sed -n '1,120p'`
- `Blocked-by conditions`: hidden app-runtime importer or external compatibility requirement makes `reasoning_core.py` still active.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - removed `truffles-api/app/core/booking_prompt_owner.py` from runtime code and preserved its coverage-only behavior in `truffles-api/tests/support_booking_prompt_owner_shadow.py`
  - collapsed `truffles-api/app/webhook.py` into thin compatibility delegates only
  - added architecture proof that `reasoning_core.py` has no app-runtime importers and `app/webhook.py` cannot regrow shadow helper families unnoticed
- `Files touched`:
  - `truffles-api/app/core/booking_prompt_owner.py` (deleted)
  - `truffles-api/tests/support_booking_prompt_owner_shadow.py`
  - `truffles-api/app/webhook.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/webhook.py truffles-api/tests/support_booking_prompt_owner_shadow.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py` -> `26 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"` -> `1 passed, 191 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `8 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - `app/core/booking_prompt_owner.py` no longer exists
  - `app/webhook.py` now exposes only delegate handlers
  - `reasoning_core.py` has no app-runtime importers in the repo import graph
- `Realistic/local behavior checks`:
  - not run in this bounded block; no `llm-quality` acceptance run was part of this cut
- `Authority removed`:
  - dormant second booking-owner lane from runtime code
  - dormant root-level webhook helper warehouse from runtime code
- `Residual debt left for next block`:
  - `reasoning_core.py` still keeps compatibility helpers even though the repo import graph now makes it shadow-only
  - final Workstream 1 closeout still needs explicit proof against remaining completion criteria
