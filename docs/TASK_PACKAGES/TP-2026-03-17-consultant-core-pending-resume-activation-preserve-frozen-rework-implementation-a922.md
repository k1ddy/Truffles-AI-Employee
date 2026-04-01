# TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-REWORK-PLAN-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework for the surviving pending-resume activation/preserve coordinator seam. This block must remove or reduce the frozen `decision.py` activation/preserve and pending-timeout reuse cluster to one non-frozen owner-surface invocation path in `state_service.py`, without claiming closure of the broader pending lifecycle.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922.md`
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
  - `sed -n '10620,10720p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '14950,15020p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_prepare_pending_handoff_resume_boundary_restore|_prepare_resolved_handoff_resume_boundary_restore|_restore_pending_resume_payload|_derive_pending_booking_resume_boundary_payload" truffles-api/app/services/state_service.py`
- `FACT findings`:
  - `truffles-api/app/services/state_service.py` already owns pending-resume restore preparation and boundary payload derivation through `_prepare_pending_handoff_resume_boundary_restore(...)`, `_prepare_resolved_handoff_resume_boundary_restore(...)`, `_restore_pending_resume_payload(...)`, and `_derive_pending_booking_resume_boundary_payload(...)`.
  - frozen `truffles-api/app/routers/webhook/decision.py:10627-10709` still decides `pending_resume_boundary_active`, optional restore, and `session_memory_reset_skipped` vs `handover` reset.
  - frozen `truffles-api/app/routers/webhook/decision.py:14960-15012` still decides pending-timeout reuse eligibility and re-derives the same boundary contract inline.
  - deleted helper bodies in `truffles-api/app/routers/webhook/pending.py` are no longer the live seam.
  - existing deterministic coverage already protects the seam in `truffles-api/tests/test_message_endpoint.py` and owner-surface preparation in `truffles-api/tests/test_state_service.py`.
- `Detected drift (docs vs code)`:
  - Block T correctly names the owner direction, but current runtime still leaves the coordinator decision power in frozen `decision.py`; progress now requires deleting or making that coordinator unreachable, not extending the plan.

## One web search (mandatory before implementation)
- **Query (exact):** `Move Function site:refactoring.com/catalog`
- **Date/time (local):** `2026-03-17 22:07 +0500`
- **Why this query is precise:** the surviving seam is logic that talks more to `state_service.py` and `DialogStateService` than to `decision.py`, so the implementation must move that decision power to the owner surface instead of wrapping it again.
- **Sources opened (from this query):**
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** when a function mostly uses another module's data and collaborators, move the decision logic to that module and leave the old callsite as a thin invocation.
- **Decision:** `reuse/integrate` — extend `state_service.py` with one owner-surface runtime contract for activation/preserve and timeout-boundary reuse, then reduce the frozen coordinator cluster in `decision.py` to that contract.
- **Rejected options:**
  - another `decision.py -> helper -> decision.py` chain
  - reopening `pending.py` work
  - broad pending lifecycle rewrite

## Root cause (mandatory)
- **Symptom:** pending-resume helper deletion is complete, but frozen `decision.py` still owns the coordinator decisions that determine whether pending-resume becomes active, whether session memory is preserved, and whether timeout degrade may reuse the same boundary contract.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:10627-10709`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:14960-15012`.
  3. inspect `truffles-api/app/services/state_service.py:687-776`.
  4. confirm zero helper-body matches remain in `truffles-api/app/routers/webhook/pending.py`.
- **Evidence:**
  - code scan from the required `sed` and `rg` commands above
  - existing owner-surface functions in `state_service.py`
  - existing endpoint/state-service deterministic tests
- **Five Whys (or equivalent):**
  1. Why is the pending-resume family still multi-owner? Because `decision.py` still decides activation/preserve/timeout reuse after the lower-level owner surfaces prepare the data.
  2. Why did Block R not finish this? Because it removed helper bodies, not the surviving coordinator.
  3. Why is another micro-helper cut not truthful? Because the surviving seam is one mixed coordinator cluster, not a missing primitive.
  4. Why is `state_service.py` the right owner? Because it already owns the pending-resume restore preparation and boundary payload derivation consumed by this cluster.
  5. Why must this be an implementation block? Because only a runtime deletion or unreachability change counts as progress from Block T.
- **Root cause statement:** the remaining old authority is a frozen coordinator seam in `decision.py` that still decides when owner-prepared pending-resume state becomes active, when session memory is preserved instead of reset, and when timeout degrade may reuse the same boundary contract.
- **Fix mechanism:** move those coordinator decisions into one non-frozen `state_service.py` owner surface that returns the activation/preserve/timeout-reuse contract, then reduce `decision.py` to bounded invocation and side-effect application only.

## Old authority seam to delete/reduce (mandatory)
- **FACT:** target seam in frozen `decision.py` is the activation/preserve coordinator at `truffles-api/app/routers/webhook/decision.py:10627-10709`.
- **FACT:** target seam in frozen `decision.py` also includes pending-timeout reuse eligibility at `truffles-api/app/routers/webhook/decision.py:14960-15012`.
- **FACT:** this block does **not** claim deletion of `_restore_resolved_handoff_resume_boundary(...)` or closure of the whole pending lifecycle.
- **INFERENCE:** the block is admissible only if those inline coordinator decisions become deleted or unreachable through a non-frozen owner-surface contract.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - existing pending-resume endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
  - existing pending-resume owner-surface coverage in `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - Martin Fowler `Move Function`
- **Why reuse wins here:** the repo already has the domain primitives and restore preparation. The missing work is to move the coordinator decision into the owner surface, not to build new semantics.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-pending-resume-activation-preserve`
- **Why this profile fits:** this is one bounded frozen-file rework with a single non-frozen owner-surface target and matching canon/test sync.

## Invariant
- no edits to `truffles-api/app/routers/webhook/booking.py`
- no semantic hardcode additions
- no claim of full pending-lifecycle closure
- pending-resume restore, preserve, and timeout-boundary behavior must remain contract-stable

## Scope
- add one non-frozen owner-surface runtime contract in `truffles-api/app/services/state_service.py`
- reduce the frozen activation/preserve and pending-timeout coordinator cluster in `truffles-api/app/routers/webhook/decision.py`
- add targeted deterministic coverage for the new owner-surface contract if needed
- sync canon/evidence after implementation

## Out of scope
- `booking.py`
- `pending.py`
- broader pending lifecycle rewrite
- semantic-owner work
- proof-path work

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one `state_service.py` owner-surface contract that resolves activation/restore/preserve and pending-timeout boundary reuse eligibility from the existing pending-resume primitives.
2. Replace the frozen `decision.py` coordinator cluster with bounded owner-surface invocation and keep only trace/meta/runtime side-effect application in the frozen file.
3. Record the scoped frozen-file waiver update in `docs/LEGACY_SUNSET.yaml`.
4. Prove the seam with targeted deterministic tests plus required governance checks.
5. Sync canon/session/state with FACT-only evidence.

## DoD
- frozen `decision.py` no longer decides `pending_resume_boundary_active`, preserve vs `handover` reset, or pending-timeout boundary reuse eligibility inline
- `truffles-api/app/services/state_service.py` owns that decision contract
- targeted pending-resume tests stay green
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
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume'`

## Evidence
- reduced frozen coordinator lines in `decision.py`
- new non-frozen owner-surface contract in `state_service.py`
- targeted deterministic test results
- updated canon/session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted pending-resume tests only
- **Stop condition:** if the change cannot make the old frozen coordinator deleted or unreachable, stop and record a `GAP` instead of keeping a wrapper-only cut
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with deterministic closure before any rollout
- **Go/no-go signals:**
  - old coordinator decisions are deleted or unreachable in `decision.py`
  - pending-resume targeted tests stay green
  - governance checks stay green
- **Rollback:** revert the state-service owner-surface addition, the frozen callsite reduction, and matching waiver lines, then rerun targeted checks
- **Post-release monitoring window:** first pending soft-pass and manager-resume conversations must preserve expected-reply, booking state, `session_memory_reset_skipped`, and timeout-boundary trace/meta evidence without reopening the old coordinator seam

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
- session-memory preserve logic and timeout reuse share the same boundary contract, so splitting the owner contract incorrectly can recreate the same coordinator in a new place
- frozen `decision.py` still owns trace/meta side effects, so the new owner contract must stay about decisions and context, not create a second live writer path

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `_restore_resolved_handoff_resume_boundary(...)` remains in frozen `decision.py`
  - broader pending lifecycle ownership remains outside this seam
  - frozen runtime still exists outside the targeted coordinator cluster
- **Why not in this block:**
  - this block is limited to the activation/preserve coordinator and its pending-timeout reuse branch
- **Risk if deferred:**
  - the team would keep the old coordinator authority alive while claiming the pending-resume owner path already exists
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-activation-preserve-post-waiver-audit-a922` (to be authored after runtime evidence)
- **Expiry/trigger to stop deferral:**
  - immediately after this bounded coordinator cut lands

## Next-block contract (mandatory)
- **Next block objective:** run one post-waiver audit to identify the next surviving pending-resume authority after the coordinator seam is deleted or becomes unreachable
- **First deterministic check command:** `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the implementation still leaves the same coordinator decisions live in frozen `decision.py`, stop and record `GAP` instead of advancing
- **Owner role for closure:** `Top Architect`
