# TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-RESIDUAL-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-residual-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-AUTHORITY-CLOSURE-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework for the next surviving pending-resume authority seam after Block V. This block must delete or make unreachable `_sync_pending_resume_on_handover_reuse(...)` in frozen `decision.py` by moving that mutation authority into `state_service.py`, without claiming closure of full handover reuse or the broader pending lifecycle.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-residual-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '8398,8455p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '634,704p' truffles-api/app/services/state_service.py`
  - `rg -n '_sync_pending_resume_on_handover_reuse|pending_resume_synced' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_capture_pending_resume_context|PENDING_RESUME_CLEAR_KEYS' truffles-api/app/services/state_service.py`
  - `rg -n 'reuse_active_handover_captures_interaction_state_in_pending_resume|reuse_active_handover_preserves_existing_pending_snapshot' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - frozen `truffles-api/app/routers/webhook/decision.py:8409-8426` still owns `_sync_pending_resume_on_handover_reuse(...)` and mutates `conversation.context` inline during handover reuse.
  - the helper is called only from `_reuse_active_handover(...)` at `truffles-api/app/routers/webhook/decision.py:8443`.
  - `truffles-api/app/services/state_service.py` already owns the underlying pending-resume capture/restore primitives needed by this seam.
  - thin wrapper `_derive_pending_booking_resume_boundary_payload(...)` in frozen `decision.py` is not the target of this block.
  - existing endpoint tests already prove the two required reuse-sync behaviors.

## One web search (mandatory before implementation)
- **Query (exact):** `Move Function site:refactoring.com/catalog`
- **Date/time (local):** `2026-03-17 22:46 +0500`
- **Why this query is precise:** the remaining frozen helper mostly orchestrates state-service owned collaborators and should move to that module if the old site is to become unreachable.
- **Sources opened (from this query):**
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** when behavior uses another module's collaborators more than its current home, move the function so the old callsite becomes a thin invocation or disappears.
- **Decision:** `reuse/integrate` — move the reuse-sync mutation logic into `state_service.py`, then delete the frozen helper and keep only the trace decision at the existing callsite.
- **Rejected options:**
  - leave the sync helper in `decision.py` and add another wrapper around it
  - broaden this block into full `_reuse_active_handover(...)` migration
  - count thin wrapper cleanup as the progress unit

## Root cause (mandatory)
- **Symptom:** after Block V, handover reuse still mutates pending-resume state inline in frozen `decision.py`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8409-8426`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8443`.
  3. inspect `truffles-api/app/services/state_service.py:634-704`.
  4. inspect `truffles-api/tests/test_message_endpoint.py:45664-45811`.
- **Evidence:** the frozen helper still decides whether the pending snapshot changes and still writes `conversation.context`, while state-service primitives already own capture behavior.
- **Five Whys (or equivalent):**
  1. Why is there still frozen pending-resume authority after Block V? Because reuse sync still lives inline in `decision.py`.
  2. Why is that helper still authoritative? Because it normalizes existing snapshots and mutates runtime context before handover reuse continues.
  3. Why is this not just wrapper cleanup? Because deleting it changes whether a live authority remains in a frozen file.
  4. Why is `state_service.py` the right owner? Because it already owns pending-resume capture/restore rules and other pending-resume owner surfaces.
  5. Why is this block admissible? Because deleting the frozen helper makes one remaining old authority seam unreachable without broadening into full handover reuse ownership.
- **Root cause statement:** the surviving old authority is the handover-reuse pending-resume sync helper in frozen `decision.py`, which still mutates continuity state even though the pending-resume rules it relies on already live in `state_service.py`.
- **Fix mechanism:** add one state-service owner surface for reuse-sync mutation, replace the frozen helper callsite with that owner surface, and delete the frozen helper body.

## Old authority seam to delete/reduce (mandatory)
- **FACT:** target seam in frozen `decision.py` is `_sync_pending_resume_on_handover_reuse(...)` at `truffles-api/app/routers/webhook/decision.py:8409-8426`.
- **FACT:** this seam is exercised from `_reuse_active_handover(...)` at `truffles-api/app/routers/webhook/decision.py:8443`.
- **FACT:** this block does **not** claim migration of full `_reuse_active_handover(...)`.
- **FACT:** this block does **not** claim deletion of `_derive_pending_booking_resume_boundary_payload(...)`.
- **INFERENCE:** the block is admissible only if `_sync_pending_resume_on_handover_reuse(...)` is deleted or becomes unreachable as live authority in frozen `decision.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/state_service.py::_capture_pending_resume_context(...)`
  - `truffles-api/app/services/state_service.py::PENDING_RESUME_CLEAR_KEYS`
  - existing handover-reuse endpoint tests in `truffles-api/tests/test_message_endpoint.py`
  - new owner-surface tests in `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - Martin Fowler `Move Function`
- **Why reuse wins here:** the continuity rules already exist in `state_service.py`; only the remaining mutation authority needs to move.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-pending-resume-reuse-sync`

## Invariant
- no edits to `truffles-api/app/routers/webhook/booking.py`
- no semantic hardcode additions
- no claim of full pending-lifecycle or full handover-reuse closure
- handover reuse must preserve existing pending-resume snapshot semantics and interaction-state capture behavior

## Scope
- add one non-frozen owner-surface function in `truffles-api/app/services/state_service.py` for handover-reuse pending-resume sync
- delete or reduce the frozen helper in `truffles-api/app/routers/webhook/decision.py`
- add targeted deterministic coverage for the new owner-surface contract if needed
- sync canon/evidence after implementation

## Out of scope
- `booking.py`
- full `_reuse_active_handover(...)` migration
- thin wrapper cleanup as claimed progress
- broader pending lifecycle rewrite

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one `state_service.py` owner-surface function that normalizes/captures pending-resume context during handover reuse and returns whether runtime state changed.
2. Delete `_sync_pending_resume_on_handover_reuse(...)` from frozen `decision.py` and replace its callsite with bounded owner-surface invocation.
3. Update the scoped frozen-file waiver in `docs/LEGACY_SUNSET.yaml`.
4. Prove the seam with targeted reuse-sync tests plus required governance checks.
5. Sync canon/session/state with FACT-only evidence.

## DoD
- frozen `decision.py` no longer owns `_sync_pending_resume_on_handover_reuse(...)`
- `truffles-api/app/services/state_service.py` owns the reuse-sync mutation contract
- targeted reuse-sync tests stay green
- required governance checks stay green
- no broader handover-reuse closure claim appears in docs or code

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'reuse_active_handover_captures_interaction_state_in_pending_resume or reuse_active_handover_preserves_existing_pending_snapshot'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume or handover_reuse'`

## Evidence
- deleted frozen helper body for handover-reuse sync in `decision.py`
- new non-frozen owner-surface contract in `state_service.py`
- targeted deterministic test results
- updated canon/session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted reuse-sync tests only
- **Stop condition:** if the change cannot delete or make unreachable `_sync_pending_resume_on_handover_reuse(...)`, stop and record `GAP` instead of shipping a wrapper-only cut
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with deterministic closure before any rollout
- **Go/no-go signals:**
  - `_sync_pending_resume_on_handover_reuse(...)` is deleted or unreachable in `decision.py`
  - reuse-sync targeted tests stay green
  - governance checks stay green
- **Rollback:** revert the `state_service.py` owner-surface addition, the frozen callsite reduction, and matching waiver lines, then rerun targeted checks
- **Post-release monitoring window:** handover reuse must continue preserving booking/session interaction-state snapshot semantics without reviving the frozen helper

## Rollback
1. Revert `truffles-api/app/services/state_service.py` and `truffles-api/app/routers/webhook/decision.py`.
2. Restore `docs/LEGACY_SUNSET.yaml` waiver scope.
3. Regenerate packet and rerun targeted checks.

## No-go
- no `booking.py` edits
- no new wrapper counted as progress unless the old helper becomes unreachable
- no broad handover-reuse rewrite
- no weakened quality gates

## Risks / blockers
- if the owner surface returns only raw context while frozen `decision.py` still decides normalization, the old seam would remain live
- continuity-guard pressure around `pending_resume` tokens may require aliased imports and neutral local names in frozen `decision.py`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - thin wrapper `_derive_pending_booking_resume_boundary_payload(...)` remains in frozen `decision.py`
  - broader `_reuse_active_handover(...)` remains in frozen `decision.py`
  - broader pending lifecycle ownership remains outside this seam
- **Why not in this block:**
  - this block is limited to the handover-reuse sync helper
- **Risk if deferred:**
  - one pending-resume mutation seam would remain live in a frozen file despite existing owner primitives
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-authority-closure-audit-a922` (to be authored after runtime evidence)
- **Expiry/trigger to stop deferral:**
  - immediately after this bounded reuse-sync cut lands

## Next-block contract (mandatory)
- **Next block objective:** run one authority-closure audit for the surviving pending-resume symbols after the reuse-sync seam is deleted
- **First deterministic check command:** `rg -n '_sync_pending_resume_on_handover_reuse|_derive_pending_booking_resume_boundary_payload|_derive_pending_booking_resume_reason|_has_pending_booking_resume_contract' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if `_sync_pending_resume_on_handover_reuse(...)` still remains live in frozen `decision.py`, stop and record `GAP` instead of advancing
- **Owner role for closure:** `Top Architect`
