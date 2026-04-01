# TP-2026-03-15-consultant-core-pending-resume-projection-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-PROJECTION-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-EXPECTED-REPLY-PROJECTION-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expected-reply-projection-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-STATE-SERVICE-RESTORE-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `pending_resume` snapshot/restore перестает собираться и восстанавливаться ad hoc в `truffles-api/app/services/state_service.py` и начинает проходить через `truffles-api/app/core/dialog_state_service.py` как canonical continuity bridge.

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
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '560,700p' truffles-api/app/services/state_service.py`
  - `sed -n '730,840p' truffles-api/app/services/state_service.py`
  - `sed -n '1000,1085p' truffles-api/app/services/state_service.py`
  - `rg -n "pending_resume|_capture_pending_resume_context|_restore_pending_resume_context" truffles-api/app/services/state_service.py truffles-api/tests/test_state_service.py`
- `FACT findings`:
  - `truffles-api/app/services/state_service.py` still owns the full `pending_resume` snapshot and restore semantics in `_capture_pending_resume_context(...)` and `_restore_pending_resume_context(...)`.
  - current capture path uses shallow copies for nested continuity carriers (`context_manager`, `booking`, `session_memory`, `intent_queue`), so `pending_resume` can drift with later in-memory mutations instead of acting as a stable snapshot.
  - current restore path also owns expected-reply trimming, session-memory reattachment, service-hint alias handling, and re-entry flag creation directly inside `state_service.py`.
  - `DialogStateService` now already owns projection normalization for `session_memory.interaction_state` and `expected_reply_*`, so `pending_resume` is the next safe continuity bridge point.
- `Detected drift (docs vs code)`: `pending_resume` is listed as a legacy continuity authority to remove, but its capture/restore semantics still live entirely in `state_service.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy module`
- **Date/time (local):** `2026-03-15 18:31 Asia/Almaty`
- **Why this query is precise:** this block snapshots and restores nested continuity payloads, and the implementation must prevent shallow-copy alias drift without inventing custom copy semantics.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard way to create stable nested snapshots without sharing later mutations with the original object graph.
- **Decision:** `reuse + integrate` — extend `DialogStateService` with pending-resume snapshot/restore helpers and use `deepcopy` for nested payload isolation rather than hand-rolling partial copy behavior.
- **Rejected options:**
  - widening this block into full `state_service` rewrite
  - touching frozen legacy semantic router files
  - keeping shallow-copy snapshot behavior and only moving code around
- **Open questions:** none for this bounded continuity slice.

## Root cause (mandatory)
- **Symptom:** `pending_resume` remains a live continuity authority because `state_service.py` still decides how to snapshot and restore its nested payloads.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/state_service.py` and see `_capture_pending_resume_context(...)` creating `resume_payload` with direct references from `context`.
  2. Inspect `_restore_pending_resume_context(...)` and see local restore semantics for `expected_reply_*`, `session_memory`, `booking`, `intent_queue`, and `re_entry_required`.
  3. Compare with prior continuity cuts: `DialogStateService` already owns projection normalization for `session_memory.interaction_state` and `expected_reply_*`, but `pending_resume` bypasses it.
- **Evidence to capture:**
  - `DialogStateService` contains pending-resume snapshot/restore helpers
  - `state_service.py` delegates to those helpers instead of owning the semantics directly
  - nested snapshot payloads are isolated from later source-context mutation
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because `pending_resume` still decides its own capture and restore semantics inside `state_service.py`.
  2. Why is that wrong? Because `pending_resume` is a legacy continuity carrier and should not remain its own truth source.
  3. Why does this matter now? Because `session_memory` and `expected_reply_*` already moved behind `DialogStateService`, so `pending_resume` is now the largest remaining bounded carrier.
  4. Why not rewrite the full state service? Because that would widen the block beyond a safe continuity cut.
  5. Why does this reduce future drift? Because one more multi-field continuity carrier stops owning its own rules after merge.
- **Root cause statement:** continuity ownership is still split because `state_service.py` both snapshots and restores `pending_resume` with shallow-copy nested payloads and local normalization rules, instead of delegating that carrier to the canonical dialog-state bridge.
- **Fix mechanism:**
  - add pending-resume snapshot/restore helpers to `DialogStateService`
  - route `_capture_pending_resume_context(...)` and `_restore_pending_resume_context(...)` through those helpers
  - add deterministic tests for snapshot isolation and restore compatibility behavior

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - official Python `copy` documentation for deep snapshot copying
- **Why not reinvent the wheel:** the repo already has the canonical bridge (`DialogStateService`) and a narrow state-service entrypoint; this block should connect them rather than creating another pending-resume helper layer.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity migration with snapshot-compatibility constraints and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No changes to the external `pending_resume` key name.
- No widening into full `state_service` refactor or generic resume policy changes.

## Scope
- Add pending-resume snapshot/restore helpers to `DialogStateService`.
- Route `state_service.py` capture/restore through those helpers.
- Add deterministic tests for nested snapshot isolation and restore compatibility behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- broad `state_service.py` cleanup
- frozen router edits
- changing handover state transitions
- removing `pending_resume` from context entirely

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-pending-resume-projection-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add pending-resume snapshot/restore helpers to `DialogStateService`.
3. Route `state_service.py` capture/restore through that bridge without changing public behavior.
4. Add deterministic tests for snapshot isolation and restore compatibility behavior.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded snapshot/restore semantics for `pending_resume`.
- `state_service.py` no longer authors those semantics directly.
- Nested snapshot payloads are isolated from later source-context mutation.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` with pending-resume bridge helpers
- updated `state_service.py` delegating capture/restore
- deterministic tests for snapshot isolation and restore compatibility
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires semantic router edits or broad state-service redesign, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** pending-resume tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP’s continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should collapse broader restore semantics or remaining state-service carriers separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual pending-resume slice being executed.

## Rollback
- Revert this TP’s `DialogStateService`, `state_service.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No changes to handover state transition policy.
- No new proof-path authority in tests.

## Risks/Blockers
- restore compatibility is wide: tests expect specific `pending_resume` restore behavior for `expected_reply_*`, `session_memory`, `service_hint` aliases, and `re_entry_required`.
- snapshot isolation changes object-identity semantics, so tests must verify values, not references.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader `state_service` restore logic and remaining continuity writers still exist after this cut.
- `Why not in this block`: they exceed a safe bounded carrier migration.
- `Risk if deferred`: continuity remains multi-writer even though `pending_resume` becomes a bridge instead of a local authority.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-state-service-restore-collapse-a922`
- `Expiry/trigger to stop deferral`: before any new pending-resume fields or restore behavior are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next continuity restore/writer authority after `pending_resume` is bridged.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume' && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: pending-resume snapshot/restore still authored in `state_service.py`; source-of-truth not synced; pending-resume tests absent for isolation.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated handover policy paths
- `Open risks`: accidentally changing restore payload semantics while centralizing the bridge
- `First command to verify`: `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume'`
