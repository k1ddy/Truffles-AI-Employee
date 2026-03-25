# TP-2026-03-15-consultant-core-memory-carrier-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-MEMORY-CARRIER-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-EXPIRING-CARRIER-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expiring-carrier-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `memory_profile` и `memory_pending` перестают держать собственные normalize/expiry helpers в `truffles-api/app/routers/webhook/context_manager.py` и начинают проходить через centralized bridge в `truffles-api/app/core/dialog_state_service.py`.

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
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "_normalize_memory_profile|_get_memory_profile|_set_memory_profile|_get_memory_pending|_set_memory_pending" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/decision.py`
  - `rg -n "memory_profile|memory_pending" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_intent.py`
- `FACT findings`:
  - `context_manager.py` still owns the only normalize/expiry helpers for `memory_profile` and `memory_pending`.
  - `decision.py` consumes those helpers in two live lanes: policy-input memory hints and memory-consent update/writeback.
  - Existing tests already pin the externally visible behavior for memory hints and active-slot pruning in `truffles-api/tests/test_message_endpoint.py`.
  - `memory_pending` has no direct bridge coverage yet, so this block must add deterministic service tests for expiry and payload isolation.
- `Detected drift (docs vs code)`: continuity bridge already owns `session_memory`, `expected_reply_*`, `pending_resume`, canonical dialog-state, re-entry, confirmation, and expiring carriers, but `memory_*` still bypasses `DialogStateService` entirely.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy.deepcopy documentation`
- **Date/time (local):** `2026-03-15 19:16 Asia/Almaty`
- **Why this query is precise:** `memory_profile.items` and `memory_pending.items` carry nested mutable dict payloads; the bridge must avoid aliasing caller/context mutations when it centralizes these carriers.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard library mechanism for recursively copying nested mutable structures so bridge reads/writes do not share later mutations with the original payload.
- **Decision:** `reuse + integrate` — keep the bridge in `DialogStateService` and use `deepcopy(...)` for detached `memory_profile` / `memory_pending` payloads instead of inventing a custom copier.
- **Rejected options:**
  - another ad hoc helper module for memory carriers
  - widening this block into a full `state_service` or `decision.py` refactor
  - touching frozen legacy semantic router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `memory_profile` and `memory_pending` still define their own continuity semantics in `context_manager.py`.
- **Minimal reproduction:**
  1. Inspect `_normalize_memory_profile(...)`, `_get_memory_profile(...)`, `_set_memory_profile(...)`, `_get_memory_pending(...)`, and `_set_memory_pending(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Compare them with the already-centralized continuity bridges in `DialogStateService`.
  3. Trace the live call sites in `truffles-api/app/routers/webhook/decision.py`, where these helpers still feed policy input and memory-consent writeback.
- **Evidence to capture:**
  - `DialogStateService` owns bounded normalize/get/set behavior for both memory carriers.
  - `context_manager.py` delegates those helpers instead of authoring memory normalization locally.
  - existing memory-profile behavior tests keep passing after the bridge cut.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because `memory_*` carriers still have router-local normalize/expiry logic.
  2. Why is that a problem? Because the target architecture requires one continuity authority, not helper-specific carrier rules.
  3. Why is this the next safe cut? Because `memory_profile` and `memory_pending` are tightly paired and already used together by the same decision lanes.
  4. Why not widen into `decision.py` migration? Because the current goal is bounded continuity collapse without touching frozen semantic router files.
  5. Why does this reduce future drift? Because another pair of live continuity carriers stops defining its own semantics outside `DialogStateService`.
- **Root cause statement:** continuity ownership is still split because `memory_profile` and `memory_pending` keep their payload normalization and expiry behavior in `context_manager.py` instead of flowing through the dialog-state bridge.
- **Fix mechanism:**
  - add centralized memory-carrier normalize/get/set helpers to `DialogStateService`
  - route `context_manager.py` `memory_*` helpers through that bridge
  - add deterministic service coverage for normalization, expiry, and payload isolation
  - re-run existing memory-profile compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - existing memory-profile behavior tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation for nested payload isolation
- **Why not reinvent the wheel:** the repo already has the right continuity bridge seam and Python already provides the correct nested-copy primitive.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `9`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for paired memory carriers with deterministic local verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible `memory_profile` / `memory_pending` shape for valid flows.
- No widening into `decision.py` semantics or general state-service cleanup.

## Scope
- Add centralized memory-carrier helpers to `DialogStateService` for `memory_profile` and `memory_pending`.
- Route `context_manager.py` memory helper APIs through that bridge.
- Add deterministic service coverage and reuse existing memory-profile compatibility tests.
- Sync source-of-truth/state/session docs.

## Out of scope
- full `context_manager.py` rewrite
- `decision.py` semantic migration
- frozen router edits
- broader continuity-writer guard tightening

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-memory-carrier-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this memory-carrier TP with RCA and one web search.
2. Add centralized `memory_profile` / `memory_pending` helpers to `DialogStateService`.
3. Route `context_manager.py` memory helpers through that bridge without changing legacy APIs.
4. Add deterministic service coverage and run targeted compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded normalize/get/set semantics for `memory_profile` and `memory_pending`.
- `context_manager.py` no longer authors those memory-carrier rules directly.
- Existing memory-profile compatibility tests keep passing.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_llm_policy_core_receives_memory_hints_and_writes_meta or test_llm_policy_core_memory_profile_drops_date_only_datetime_from_active_slots'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` memory-carrier bridge helpers
- updated `context_manager.py` delegating `memory_profile` and `memory_pending`
- deterministic service coverage plus targeted memory-profile compatibility tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or a broader semantic migration, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** memory bridge tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the remaining broader context/state writer collapse separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual memory-carrier bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new proof-path authority in tests.

## Risks/Blockers
- `memory_profile.items` is consumed by policy-input shaping, so over-normalization could silently change retrieved memory hints.
- `memory_pending` currently has thin coverage and needs explicit bridge tests to avoid payload/expiry regressions.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader context/state continuity writers still remain outside the bounded bridges, and the main semantic happy-path still lives in the legacy router.
- `Why not in this block`: that would exceed a safe bounded continuity cut.
- `Risk if deferred`: continuity will still have multiple live writer surfaces even after `memory_*` is centralized.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new continuity carrier or memory-side behavior is added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the remaining broader context/state writer ownership after the memory-carrier bridge.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: memory-carrier rules still authored in `context_manager.py`; source-of-truth not synced; deterministic coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated richer semantic planner slices
- `Open risks`: changing memory-hint payload shape that policy-core tests already pin
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_llm_policy_core_receives_memory_hints_and_writes_meta or test_llm_policy_core_memory_profile_drops_date_only_datetime_from_active_slots'`
