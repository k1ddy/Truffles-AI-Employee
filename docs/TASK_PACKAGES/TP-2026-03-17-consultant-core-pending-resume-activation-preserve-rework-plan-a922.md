# TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-REWORK-PLAN-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-BROADER-REWORK-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-broader-rework-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-ACTIVATION-PRESERVE-FROZEN-REWORK-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Author one broader owner-capture plan for the surviving pending-resume activation/preserve cluster in frozen `decision.py`. The goal is to define one future owner surface, one bounded deletion target, and one implementation path that removes coordinator authority instead of wrapping it again.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-broader-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before planning)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '10620,10720p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '14950,15020p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_prepare_pending_handoff_resume_boundary_restore|_prepare_resolved_handoff_resume_boundary_restore|_restore_pending_resume_payload|_derive_pending_booking_resume_boundary_payload" truffles-api/app/services/state_service.py`
- `FACT findings`:
  - Block R already deleted the frozen `pending.py` helper family and moved pending-resume derivation plus restore preparation into `DialogStateService` and `state_service`.
  - The surviving live authority is the inline coordinator cluster in frozen `truffles-api/app/routers/webhook/decision.py:10627-10709` and `truffles-api/app/routers/webhook/decision.py:14960-15012`.
  - That cluster still decides whether the pending-resume boundary is active, whether soft-pass restore runs, whether session memory is preserved instead of reset, and whether timeout fallback may reuse the boundary contract.
  - `truffles-api/app/services/state_service.py` already owns the lower-level restore preparation needed by that cluster, and `truffles-api/app/services/timeout_owner_boundary_service.py` already owns the timeout-owner apply/send path.

## One web search (mandatory before implementation)
- **Query (exact):** `Branch By Abstraction site:martinfowler.com/bliki`
- **Date/time (local):** `2026-03-17 21:47 +0500`
- **Why this query is precise:** the remaining seam is a mixed coordinator cluster after partial extraction, so the right plan is to converge on one owner surface without claiming progress from another wrapper.
- **Sources opened (from this query):**
  - `Branch By Abstraction` — `https://martinfowler.com/bliki/BranchByAbstraction.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** gradual migration is valid only when one abstraction becomes the sole interaction point and the old supplier can later be deleted; if both implementations stay live behind coordinator code, the migration is not complete.
- **Decision:** `reuse/integrate` — plan the next block around existing `state_service` and `timeout_owner_boundary_service` owner surfaces instead of inventing another legacy-facing helper family.
- **Rejected options:**
  - extracting the coordinator cluster into a new wrapper while leaving the same authority shape alive
  - reopening `pending.py` helper-family work
  - broad pending-lifecycle rewrite without a bounded deletion target

## Root cause (mandatory)
- **Symptom:** after Block R, pending-resume helper bodies are gone, but frozen `decision.py` still coordinates activation, restore/preserve behavior, and timeout-boundary reuse.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:10627-10709` to see activation, optional restore, and session-memory preserve/reset decisions.
  2. inspect `truffles-api/app/routers/webhook/decision.py:14960-15012` to see pending-timeout reuse of the same boundary contract.
  3. inspect `truffles-api/app/services/state_service.py:664-767` to confirm the lower-level restore preparation already exists outside frozen files.
  4. confirm zero frozen helper bodies remain in `truffles-api/app/routers/webhook/pending.py`.
- **Evidence:**
  - direct code scan of the residual cluster in `decision.py`
  - owner-surface functions already present in `state_service.py`
  - zero-match proof for deleted `pending.py` helper bodies
- **Five Whys (or equivalent):**
  1. Why is pending-resume not converged yet? Because `decision.py` still decides whether the owner-prepared boundary contract is activated and preserved.
  2. Why didn't Block R finish this? Because Block R only deleted helper bodies, not the remaining coordinator.
  3. Why can't we continue with another tiny helper cut? Because the remaining code spans restore, preserve/reset, and timeout reuse together.
  4. Why is that risky? Because moving those lines without naming one owner would just recreate the same authority in another file.
  5. Why is a rework plan required before code? Because the next implementation must delete one coordinator seam, not add another bridge.
- **Root cause statement:** the remaining old authority is no longer helper logic; it is a frozen coordinator cluster in `decision.py` that still decides when owner-prepared pending-resume state becomes active, when session memory is preserved, and when timeout fallback can reuse the same contract.
- **Fix mechanism:** define one owner-capture plan that routes activation/preserve decisions through non-frozen owner surfaces and reduces the frozen coordinator cluster to bounded invocation or deletion.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/state_service.py` for pending-resume restore preparation and boundary payload derivation
  - `truffles-api/app/core/dialog_state_service.py` for dialog-state projections and pending-resume reason derivation
  - `truffles-api/app/services/timeout_owner_boundary_service.py` for timeout-owner apply/send ownership
  - existing endpoint coverage in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Branch By Abstraction`
- **Why reuse wins here:** the missing behavior is coordinator ownership, not missing domain primitives. The plan should converge on the owner surfaces that already exist.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only planning block; no runtime rollout in this TP.
- **Go/no-go signals:** go only if canon and guard suite stay aligned; no production behavior may change from this block.
- **Rollback:** revert this TP and canon sync if a later scan disproves the planned deletion target.
- **Post-release monitoring window:** not applicable for this doc-only planning block.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Why:** this block is limited to governance and deterministic guard reruns.

## Execution profile (mandatory)
- `TP mode`: `doc_only`
- `Doc touch budget (files)`: `12`
- `Code dominance`: `docs_only`
- `Override token`: `pending-resume-activation-preserve-plan`
- `Why this profile fits`: this block only defines the next admissible deletion path and must not touch runtime code.

## Invariant
- no runtime behavior changes in this block
- no claim that pending-resume convergence is complete
- no new wrapper counted as progress
- no expansion into broader pending lifecycle beyond the residual cluster

## Scope
- define the future owner surface for the activation/preserve cluster
- define the exact residual lines/seams the next implementation block must delete or reduce
- sync canon to that plan

## Out of scope
- runtime implementation
- `booking.py`
- proof-path work
- semantic-owner work
- multi-pack closure work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-activation-preserve-rework-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Reconfirm the exact coordinator lines that remain live in frozen `decision.py`.
2. Name the future owner surfaces that can absorb activation/preserve logic without widening scope.
3. Define the bounded deletion target for the next implementation block.
4. Sync canon and rerun governance checks.

## DoD
- one future owner surface is named
- one bounded deletion target is named
- one implementation follow-up TP is implied by the next-block contract
- canon, packet, and architecture guard stay consistent

## Checks
- `sed -n '10620,10720p' truffles-api/app/routers/webhook/decision.py`
- `sed -n '14950,15020p' truffles-api/app/routers/webhook/decision.py`
- `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated rework-plan TP
- updated canon / agent packet / session entries
- deterministic guard pass

## Rollback
- revert the plan TP and canon sync if a later implementation scan proves the owner choice or deletion target is wrong

## No-go
- do not write runtime code in this block
- do not claim deletion of the whole pending lifecycle
- do not choose a plan that keeps coordinator power split across multiple new owners

## Risks / blockers
- the cluster mixes continuity and boundary concerns, so the future implementation can regress into wrapper-growth if owner boundaries stay blurry
- if the future plan cannot reduce the frozen coordinator to bounded invocation or deletion, the correct state remains blocked

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`:
  - frozen `decision.py` still owns activation/preserve coordination and pending-timeout boundary reuse
  - thin restore wrappers still remain in frozen `decision.py`
- `Why not in this block`:
  - this block only plans the next deletion path
  - runtime edits belong to the follow-up implementation block
- `Risk if deferred`:
  - the team may keep counting coordinator extraction as real progress
- `Linked follow-up Task Package(s)`:
  - `TP-2026-03-17-consultant-core-pending-resume-activation-preserve-frozen-rework-implementation-a922` (to be authored only if this plan stands)
- `Expiry/trigger to stop deferral`:
  - stop deferral if the next implementation proposal cannot name the exact old coordinator seam that becomes deleted or unreachable

## Next-block contract (mandatory)
- `Next block objective`: implement one bounded owner-capture cut that deletes or reduces the frozen `decision.py` activation/preserve coordinator cluster to owner-surface invocation
- `First deterministic check command`: `rg -n "pending_resume_boundary_active|pending_resume_boundary_payload|pending_resume_boundary_restored|session_memory_reset_skipped|pending_timeout_resume_boundary_payload" truffles-api/app/routers/webhook/decision.py`
- `Blocked-by conditions`:
  - if the implementation cannot route activation/preserve decisions through one non-frozen owner surface
  - if the implementation still leaves the same coordinator authority live in frozen `decision.py`
  - if the change widens into full pending lifecycle rewrite
- `Owner role for closure`: `Top Architect`
