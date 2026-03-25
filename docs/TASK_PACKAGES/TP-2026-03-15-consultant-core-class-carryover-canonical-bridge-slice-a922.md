# TP-2026-03-15-consultant-core-class-carryover-canonical-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CLASS-CARRYOVER-CANONICAL-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MEMORY-CARRIER-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-memory-carrier-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `class_carryover` перестаёт жить только как локальный helper payload в `truffles-api/app/routers/webhook/context_manager.py` и начинает зеркалиться/читаться через canonical dialog-state bridge в `truffles-api/app/core/dialog_state_service.py`, при сохранении legacy fallback.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "_prune_class_carryover|_get_class_carryover|_set_class_carryover|_maybe_store_class_carryover" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py`
  - `rg -n "class_carryover" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_demo_salon_eval.py`
- `FACT findings`:
  - `context_manager.py` still owns the only storage/read/prune semantics for `class_carryover`.
  - live runtime call sites already flow through helper APIs, so the carrier can be bridged without touching frozen semantic router files.
  - `service_carryover` already prefers canonical dialog-state projection, but `class_carryover` still has only legacy local payload authority.
  - existing eval coverage already constrains the short-followup parking carryover trace.
- `Detected drift (docs vs code)`: canonical dialog-state already carries referents, consult state, pending question contract, and interaction state, but `class_carryover` still bypasses that bridge.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy.deepcopy documentation`
- **Date/time (local):** `2026-03-15 19:51 Asia/Almaty`
- **Why this query is precise:** `class_carryover` payload contains mutable list fields (`intents`, `info_sections`) that will now be mirrored under canonical dialog state; the bridge must avoid aliasing between legacy and canonical copies.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard library mechanism for recursively copying nested mutable structures so canonical and legacy carrier payloads cannot accidentally share later mutations.
- **Decision:** `reuse + integrate` — keep the new class-carryover mirror inside `DialogStateService` and use `deepcopy(...)` for canonical/legacy payload isolation instead of inventing a custom copier.
- **Rejected options:**
  - another helper module for class carryover only
  - widening into `service_carryover` / `consult_context` in the same block
  - touching frozen legacy semantic router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `class_carryover` is still owned only by router-local helpers.
- **Minimal reproduction:**
  1. Inspect `_get_class_carryover(...)`, `_set_class_carryover(...)`, and `_prune_class_carryover(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Compare with `service_carryover`, which already mirrors canonical dialog-state state.
  3. Follow `class_carryover` reads from `decision.py` and writes from `info.py` through the helper seam.
- **Evidence to capture:**
  - `DialogStateService` owns canonical mirror/read/clear helpers for `class_carryover`.
  - `context_manager.py` no longer authors the carrier purely as a local payload.
  - short-followup class carryover behavior remains green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because `class_carryover` exists only as a local helper payload.
  2. Why is that a problem? Because canonical dialog state is supposed to be the continuity convergence seam.
  3. Why bridge only `class_carryover` now? Because it is a bounded carrier with existing helper call sites and no need to touch frozen semantic files.
  4. Why not widen into `service_carryover` and `consult_context` now? Because that would broaden the risk surface beyond a safe slice.
  5. Why does this reduce drift? Because another live continuity carrier stops relying on a one-off router payload.
- **Root cause statement:** continuity ownership is still split because `class_carryover` has no canonical dialog-state mirror and remains defined only by router-local helper semantics.
- **Fix mechanism:**
  - add bounded canonical mirror/read/clear helpers for `class_carryover` in `DialogStateService`
  - route `context_manager.py` set/get/prune helpers through that bridge while keeping legacy fallback
  - add deterministic service coverage and a direct router-facing canonical read test

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - existing canonical dialog-state bridge helpers
  - existing carryover behavior test in `truffles-api/tests/test_demo_salon_eval.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation for mirrored payload isolation
- **Why not reinvent the wheel:** the repo already has a canonical dialog-state bridge and Python already provides the right nested-copy primitive.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `9`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for one helper-owned carryover carrier with deterministic local verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible `class_carryover` semantics for valid short-followup flows.
- No widening into `service_carryover`, `consult_context`, or semantic router edits.

## Scope
- Add bounded canonical `class_carryover` mirror/read/clear helpers to `DialogStateService`.
- Route `context_manager.py` class-carryover helper APIs through that bridge while preserving legacy fallback.
- Add deterministic service coverage and a router-facing canonical read test.
- Sync source-of-truth/state/session docs.

## Out of scope
- `service_carryover`
- `consult_context`
- broader canonical meta refactor
- frozen router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-class-carryover-canonical-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_demo_salon_eval.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this class-carryover TP with RCA and one web search.
2. Add bounded canonical mirror/read/clear helpers for `class_carryover` to `DialogStateService`.
3. Route `context_manager.py` class-carryover set/get/prune helpers through that bridge without touching frozen semantic router files.
4. Add deterministic service/router coverage and run targeted compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded canonical mirror/read/clear behavior for `class_carryover`.
- `context_manager.py` no longer treats `class_carryover` as a purely local payload.
- Existing short-followup carryover behavior remains green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_class_carryover'`
- `pytest -q truffles-api/tests/test_demo_salon_eval.py -k 'test_info_carryover_preserves_parking_for_short_followup'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` class-carryover canonical bridge helpers
- updated `context_manager.py` delegating `class_carryover` canonical mirror/read/clear behavior
- deterministic service/router coverage plus targeted carryover compatibility test
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or widening into multiple carryover carriers, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** class-carryover tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the remaining message-count carryovers separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual class-carryover bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No widening into `service_carryover` or `consult_context`.

## Risks/Blockers
- `class_carryover` is consumed by short-followup info logic, so shape drift in `intents` / `info_sections` could silently change followup routing.
- canonical mirror and legacy payload must stay detached to avoid accidental shared mutations.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `service_carryover`, `consult_context`, `compact_summary`, and `low_confidence_retry_count` still remain outside the dialog-state bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has several helper-owned message-count/state carriers even after `class_carryover` is mirrored canonically.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-service-and-consult-carryover-bridge-slice-a922`
- `Expiry/trigger to stop deferral`: before any new carryover semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the remaining message-count carryovers after `class_carryover` is mirrored canonically.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: class-carryover still authored only as a local helper payload; source-of-truth not synced; deterministic canonical-read test absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated carryover carriers
- `Open risks`: changing `class_carryover` `intents` / `info_sections` shape seen by short-followup info flows
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_class_carryover'`
