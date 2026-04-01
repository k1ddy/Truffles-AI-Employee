# TP-2026-03-17-consultant-core-pending-resume-resolved-handoff-boundary-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-RESOLVED-HANDOFF-BOUNDARY-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-RESIDUAL-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework for the next surviving pending-resume authority seam after Block U. This block must delete or make unreachable the resolved-handoff pending-resume restore coordinator in frozen `decision.py` by moving that authority into a non-frozen owner surface, without claiming closure of handover reuse or the broader pending lifecycle.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922.md`
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
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-resolved-handoff-boundary-frozen-rework-implementation-a922.md`
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
  - `sed -n '8488,8565p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10770,10805p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_restore_resolved_handoff_resume_boundary|resolved_handoff_resume_boundary|pending_resume_restored' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_prepare_resolved_handoff_resume_boundary_restore|_capture_pending_resume_context|_restore_pending_resume_context' truffles-api/app/services/state_service.py`
- `FACT findings`:
  - `truffles-api/app/services/state_service.py` already owns resolved-handoff resume-boundary preparation via `_prepare_resolved_handoff_resume_boundary_restore(...)`.
  - frozen `truffles-api/app/routers/webhook/decision.py:8520-8561` still owns the resolved-handoff restore coordinator: `BOT_ACTIVE` eligibility, booking-state reapplication, expected-reply restoration, trace write, and decision-meta updates.
  - frozen `truffles-api/app/routers/webhook/decision.py:10781-10787` still decides when that coordinator runs during inbound processing.
  - `_sync_pending_resume_on_handover_reuse(...)` remains another pending-resume residual in `decision.py`, but it is a different seam bound to active handover reuse and is not required to delete the resolved-handoff restore coordinator.
  - existing deterministic coverage already proves resolved-handoff restore behavior in `truffles-api/tests/test_message_endpoint.py` and restore preparation in `truffles-api/tests/test_state_service.py`.
- `Detected drift (docs vs code)`:
  - current canon correctly points to a post-waiver audit next move after Block U, and the code scan now proves the next bounded deletable seam is the resolved-handoff restore coordinator, not `pending.py` and not the already-deleted activation/preserve cluster.

## One web search (mandatory before implementation)
- **Query (exact):** `Move Function site:refactoring.com/catalog`
- **Date/time (local):** `2026-03-17 22:31 +0500`
- **Why this query is precise:** the surviving function in frozen `decision.py` mostly orchestrates data and helpers already owned by `state_service.py`, so the implementation must move that coordinator authority to the owner surface instead of adding another wrapper.
- **Sources opened (from this query):**
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** when behavior uses another module's data and collaborators more than its current home, move the function so the old site becomes a thin call or disappears.
- **Decision:** `reuse/integrate` — extend `state_service.py` with one resolved-handoff restore owner surface that already consumes the existing restore preparation, then delete the frozen coordinator helper in `decision.py`.
- **Rejected options:**
  - leave the coordinator in `decision.py` and add another thin wrapper around it
  - reopen `pending.py`
  - broaden this block into handover reuse or whole pending lifecycle rewrite

## Root cause (mandatory)
- **Symptom:** after Block U, pending-resume activation/preserve authority moved out of frozen `decision.py`, but the resolved-handoff restore path still makes live coordinator decisions there.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8520-8561`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:10781-10787`.
  3. inspect `truffles-api/app/services/state_service.py:765-802`.
  4. compare with endpoint tests around resolved-handoff restore in `truffles-api/tests/test_message_endpoint.py`.
- **Evidence:**
  - code scan from the baseline `sed` and `rg` commands above
  - existing owner-surface preparation in `state_service.py`
  - deterministic resolved-handoff restore tests already present in endpoint/state-service coverage
- **Five Whys (or equivalent):**
  1. Why is pending-resume still not single-owner? Because one restore coordinator remains in frozen `decision.py`.
  2. Why did Block U not remove it? Because Block U was scoped to activation/preserve and timeout reuse, not resolved-handoff restore.
  3. Why is this seam now the next honest target? Because the restore preparation already lives in `state_service.py`, so the surviving frozen code is coordinator authority rather than missing primitives.
  4. Why would another wrapper-only cut be false progress? Because the old helper would stay live in frozen `decision.py`.
  5. Why is this an admissible implementation block? Because deleting `_restore_resolved_handoff_resume_boundary(...)` makes one old authority seam unreachable without widening into handover reuse.
- **Root cause statement:** the surviving old authority is the resolved-handoff pending-resume restore coordinator in frozen `decision.py`, which still decides eligibility, state reapplication, expected-reply restoration, and trace/meta writes after owner-surface preparation has already been computed in `state_service.py`.
- **Fix mechanism:** move the resolved-handoff restore coordinator into one non-frozen `state_service.py` owner surface with runtime hooks, then replace the frozen helper and callsite with bounded invocation.

## Old authority seam to delete/reduce (mandatory)
- **FACT:** target seam in frozen `decision.py` is `_restore_resolved_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8520-8561`.
- **FACT:** target seam in frozen `decision.py` is exercised from the inbound coordinator at `truffles-api/app/routers/webhook/decision.py:10781-10787`.
- **FACT:** this block does **not** claim deletion of `_sync_pending_resume_on_handover_reuse(...)`.
- **FACT:** this block does **not** claim closure of broader pending lifecycle ownership.
- **INFERENCE:** the block is admissible only if `_restore_resolved_handoff_resume_boundary(...)` is deleted or becomes unreachable as live authority in frozen `decision.py`.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/state_service.py`
  - `_prepare_resolved_handoff_resume_boundary_restore(...)`
  - existing `PendingResumeBoundaryRuntimeHooks`
  - existing resolved-handoff endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
  - existing owner-surface coverage in `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - Martin Fowler `Move Function`
- **Why reuse wins here:** the repo already has the restore preparation and the runtime hook contract shape. The missing work is to move the last coordinator authority out of frozen `decision.py`, not invent new pending semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-pending-resume-resolved-handoff-boundary`
- **Why this profile fits:** this is one bounded frozen-file rework against a single proven seam with targeted tests and canon sync.

## Invariant
- no edits to `truffles-api/app/routers/webhook/booking.py`
- no semantic hardcode additions
- no claim of full pending-lifecycle closure
- resolved-handoff restore behavior must remain contract-stable for booking state, expected reply, trace, and decision meta

## Scope
- add one non-frozen owner-surface runtime contract in `truffles-api/app/services/state_service.py` for resolved-handoff restore
- delete or reduce the frozen resolved-handoff restore coordinator in `truffles-api/app/routers/webhook/decision.py`
- add targeted deterministic coverage for the new owner-surface contract if needed
- sync canon/evidence after implementation

## Out of scope
- `booking.py`
- `pending.py`
- `_sync_pending_resume_on_handover_reuse(...)`
- broader pending lifecycle rewrite
- semantic-owner work
- proof-path work

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-resolved-handoff-boundary-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one `state_service.py` owner-surface function that applies resolved-handoff restore from the existing restore preparation and runtime hooks.
2. Delete `_restore_resolved_handoff_resume_boundary(...)` from frozen `decision.py` and replace its callsite with bounded owner-surface invocation.
3. Record the scoped frozen-file waiver update in `docs/LEGACY_SUNSET.yaml`.
4. Prove the seam with targeted deterministic tests plus required governance checks.
5. Sync canon/session/state with FACT-only evidence.

## DoD
- frozen `decision.py` no longer owns the resolved-handoff pending-resume restore coordinator inline
- `truffles-api/app/services/state_service.py` owns that restore contract
- `_restore_resolved_handoff_resume_boundary(...)` is deleted from frozen `decision.py`
- targeted resolved-handoff tests stay green
- required governance checks stay green
- no broader pending lifecycle closure claim appears in docs or code

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'resolved_handoff_resume_boundary or pending_resume'`

## Evidence
- deleted frozen helper body for resolved-handoff restore in `decision.py`
- new non-frozen owner-surface contract in `state_service.py`
- targeted deterministic test results
- updated canon/session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted resolved-handoff tests only
- **Stop condition:** if the change cannot delete or make unreachable `_restore_resolved_handoff_resume_boundary(...)`, stop and record a `GAP` instead of leaving a wrapper-only cut
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with deterministic closure before any rollout
- **Go/no-go signals:**
  - `_restore_resolved_handoff_resume_boundary(...)` is deleted or unreachable in `decision.py`
  - resolved-handoff targeted tests stay green
  - governance checks stay green
- **Rollback:** revert the `state_service.py` owner-surface addition, the frozen callsite reduction, and matching waiver lines, then rerun targeted checks
- **Post-release monitoring window:** the first manager-resume conversations must preserve booking state, expected-reply restoration, trace evidence, and decision meta without reviving the frozen coordinator path

## Rollback
1. Revert `truffles-api/app/services/state_service.py` and `truffles-api/app/routers/webhook/decision.py`.
2. Restore `docs/LEGACY_SUNSET.yaml` waiver scope.
3. Regenerate packet and rerun targeted checks.

## No-go
- no `booking.py` edits
- no new wrapper counted as progress unless the old coordinator becomes unreachable
- no broad pending lifecycle rewrite
- no weakened quality gates

## Risks / blockers
- resolved-handoff restore writes both context and decision evidence, so an incomplete owner contract can split live authority between `state_service.py` and `decision.py`
- continuity guard pressure around `pending_resume` tokens may require aliasing at the frozen callsite, not new semantic lines in `decision.py`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `_sync_pending_resume_on_handover_reuse(...)` remains in frozen `decision.py`
  - `_derive_pending_booking_resume_boundary_payload(...)` thin wrapper still remains in frozen `decision.py`
  - broader pending lifecycle ownership remains outside this seam
- **Why not in this block:**
  - this block is limited to the resolved-handoff restore coordinator and must not widen into active handover reuse
- **Risk if deferred:**
  - the team would continue carrying live pending-resume authority in frozen `decision.py` even after the activation/preserve seam was removed
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-reuse-sync-residual-audit-a922` (to be authored after runtime evidence)
- **Expiry/trigger to stop deferral:**
  - immediately after this bounded resolved-handoff restore cut lands

## Next-block contract (mandatory)
- **Next block objective:** run one residual audit for the surviving pending-resume authority after the resolved-handoff restore coordinator is deleted
- **First deterministic check command:** `rg -n '_sync_pending_resume_on_handover_reuse|_derive_pending_booking_resume_boundary_payload|pending_resume' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if `_restore_resolved_handoff_resume_boundary(...)` still remains live in frozen `decision.py`, stop and record `GAP` instead of advancing
- **Owner role for closure:** `Top Architect`
