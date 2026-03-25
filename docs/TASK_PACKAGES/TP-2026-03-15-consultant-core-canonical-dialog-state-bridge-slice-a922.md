# TP-2026-03-15-consultant-core-canonical-dialog-state-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CANONICAL-DIALOG-STATE-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-PROJECTION-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-pending-resume-projection-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-MANAGER-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: canonical dialog state normalization plus `pending_question_contract`/`interaction_state` bridging перестают авториться ad hoc в `truffles-api/app/routers/webhook/context_manager.py` и начинают проходить через `truffles-api/app/core/dialog_state_service.py`.

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
  - `sed -n '180,320p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '418,520p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '640,760p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "canonical_dialog_state|_sync_canonical_dialog_state|pending_question_contract|interaction_state" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_dialog_state_service.py`
- `FACT findings`:
  - `context_manager.py` still owns canonical dialog state normalization in `_get_canonical_dialog_state(...)` plus live builder semantics in `_set_canonical_pending_question_contract(...)` and `_set_canonical_interaction_state(...)`.
  - those two canonical sub-carriers (`pending_question_contract` and `interaction_state`) are central continuity state, but they still bypass `DialogStateService` even after the previous continuity cuts.
  - `_sync_canonical_dialog_state(...)` is the safest bridge point because many existing flows already route through it without touching frozen semantic router files.
  - existing tests in `truffles-api/tests/test_message_endpoint.py` already pin expected canonical interaction-state behavior, so a bridge cut can stay compatibility-safe.
- `Detected drift (docs vs code)`: `DialogState` is declared as target continuity owner, but canonical dialog state normalization and write semantics still live directly in `context_manager.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy module`
- **Date/time (local):** `2026-03-15 18:41 Asia/Almaty`
- **Why this query is precise:** this block moves canonical dialog state normalization into a shared bridge and must avoid mutating nested legacy state in-place while preserving compatibility.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3.9/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard way to create isolated nested dict snapshots before normalization without sharing later mutations with the original object graph.
- **Decision:** `reuse + integrate` — extend `DialogStateService` with canonical dialog state bridge helpers and use `deepcopy` where bridge operations need nested isolation.
- **Rejected options:**
  - widening this block into full `context_manager.py` rewrite
  - touching frozen legacy semantic router files
  - leaving canonical sub-state writes in `context_manager.py` and only moving tests/docs
- **Open questions:** none for this bounded continuity slice.

## Root cause (mandatory)
- **Symptom:** canonical dialog state remains a live continuity authority in `context_manager.py`, so continuity ownership is still split despite the earlier projection cuts.
- **Minimal reproduction:**
  1. Inspect `_get_canonical_dialog_state(...)` in `truffles-api/app/routers/webhook/context_manager.py` and see local normalization of `pending_question_contract` and `interaction_state`.
  2. Inspect `_set_canonical_pending_question_contract(...)` and `_set_canonical_interaction_state(...)` and see local builder semantics still authored in `context_manager.py`.
  3. Compare with `DialogStateService`, which now already owns several other continuity bridges.
- **Evidence to capture:**
  - `DialogStateService` contains canonical dialog state normalization/builder helpers for `pending_question_contract` and `interaction_state`
  - `context_manager.py` delegates those semantics instead of authoring them directly
  - existing canonical dialog state tests keep passing unchanged
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because canonical dialog state sub-carriers still own their own normalization rules in `context_manager.py`.
  2. Why is that wrong? Because `DialogState` is supposed to be the single continuity authority.
  3. Why focus on `pending_question_contract` and `interaction_state` first? Because they are the most central canonical sub-carriers and already covered by compatibility tests.
  4. Why not rewrite all of `context_manager.py` now? Because that would exceed a safe bounded cut.
  5. Why does this reduce drift? Because another live continuity authority stops deciding its own normalization rules after merge.
- **Root cause statement:** continuity ownership is still split because canonical dialog state normalization plus `pending_question_contract`/`interaction_state` builder semantics still live directly in `context_manager.py` instead of being routed through `DialogStateService`.
- **Fix mechanism:**
  - add canonical dialog state bridge helpers to `DialogStateService`
  - route `_get_canonical_dialog_state(...)`, `_set_canonical_pending_question_contract(...)`, and `_set_canonical_interaction_state(...)` through those helpers
  - add deterministic unit coverage plus run the existing canonical dialog state compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - existing targeted canonical state tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `copy` documentation for isolated nested normalization
- **Why not reinvent the wheel:** the repo already has a dialog-state bridge and existing canonical behavior tests; this block should connect them rather than invent another continuity helper path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration with strict compatibility boundaries and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No changes to external `context_manager.canonical_dialog_state` key shape for valid inputs.
- No widening into generic `context_manager.py` cleanup.

## Scope
- Add canonical dialog state bridge helpers to `DialogStateService` for `pending_question_contract` and `interaction_state` normalization/building.
- Route `context_manager.py` canonical state helpers through that bridge.
- Add deterministic tests for the bridge helpers and run targeted compatibility tests.
- Sync source-of-truth/state/session docs.

## Out of scope
- full `context_manager.py` rewrite
- referent or consult-state redesign
- frozen router edits
- broader continuity-writer guard tightening

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-canonical-dialog-state-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add canonical dialog state bridge helpers to `DialogStateService`.
3. Route `context_manager.py` canonical sub-state helpers through those bridge methods without changing legacy APIs.
4. Add deterministic unit coverage and run targeted compatibility tests.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded canonical dialog state bridge semantics for `pending_question_contract` and `interaction_state`.
- `context_manager.py` no longer authors those normalization/build rules directly.
- Existing compatibility tests keep passing.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'canonical_dialog_state_syncs_interaction_state_from_policy_contract or transport_degraded_pending_reentry_restores_booking_resume'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` canonical bridge helpers
- updated `context_manager.py` delegating canonical dialog state sub-state semantics
- deterministic unit coverage plus targeted canonical compatibility tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or broad `context_manager.py` redesign, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** canonical bridge tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP’s continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target remaining context-manager writer collapse or another isolated carrier separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual canonical dialog state bridge slice being executed.

## Rollback
- Revert this TP’s `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No changes to external canonical dialog state key names for valid payloads.
- No new proof-path authority in tests.

## Risks/Blockers
- compatibility surface is wide because canonical dialog state is reused by owner resolution, pending-resume restore, and booking followup flows.
- duplicated constants between bridge and router would be drift-prone if not kept in one place after this block.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader `context_manager.py` writer ownership and remaining continuity writers still remain after this cut.
- `Why not in this block`: a full collapse would exceed a safe bounded migration.
- `Risk if deferred`: continuity still has multiple writers even though canonical dialog state sub-carriers are bridged.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-manager-writer-collapse-a922`
- `Expiry/trigger to stop deferral`: before any new canonical dialog state behavior is added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next remaining continuity writer after canonical dialog state bridging.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: canonical dialog state sub-state still authored in `context_manager.py`; source-of-truth not synced; targeted compatibility tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated context-manager helpers
- `Open risks`: accidentally changing canonical dialog state shape while centralizing the bridge
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'canonical_dialog_state_syncs_interaction_state_from_policy_contract'`
