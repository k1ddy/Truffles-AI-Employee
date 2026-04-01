# TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REWORK-PLAN-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-BROADER-REWORK-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-FROZEN-REWORK-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Author one broader rework plan around the surviving pending-resume continuity authority. This block must define one owner-capture path that converges pending-resume derivation, restore, activation, and snapshot semantics toward `DialogStateService` instead of continuing helper-by-helper micro-slices.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "capture_pending_resume_payload|restore_pending_resume_payload" truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py`
  - `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|pending_resume_boundary_payload|pending_resume_boundary_active|pending_handoff_resume_boundary" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_build_pending_resume_snapshot|_restore_pending_resume|pending_resume" truffles-api/app/routers/webhook/pending.py`
  - `sed -n '590,640p' truffles-api/app/services/state_service.py`
  - `sed -n '1097,1218p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '8558,8795p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10820,10930p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '111,180p' truffles-api/app/routers/webhook/pending.py`
- `FACT findings`:
  - `DialogStateService` already owns generic pending-resume payload capture and restore in `truffles-api/app/core/dialog_state_service.py:1097` and `truffles-api/app/core/dialog_state_service.py:1151`.
  - `state_service.py` already delegates generic pending-resume capture and restore to `DialogStateService` in `truffles-api/app/services/state_service.py:590` and `truffles-api/app/services/state_service.py:608`.
  - frozen `decision.py` still owns pending-resume boundary-specific derivation, restore, and activation semantics:
    - `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8558`
    - `_restore_pending_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8688`
    - `_restore_resolved_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8750`
    - activation/preserve flow at `truffles-api/app/routers/webhook/decision.py:10833`
  - frozen `pending.py` still owns direct pending snapshot/restore helpers in `truffles-api/app/routers/webhook/pending.py:111` and `truffles-api/app/routers/webhook/pending.py:137`.
  - existing tests already cover the target family across the new owner surfaces and the legacy callsites:
    - `truffles-api/tests/test_dialog_state_service.py`
    - `truffles-api/tests/test_state_service.py`
    - `truffles-api/tests/test_message_endpoint.py`
- `Detected drift (docs vs code)`:
  - the repo already has the beginnings of one continuity owner for pending-resume payloads, but the boundary-specific and frozen legacy callsites still keep the old multi-owner shape alive.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" pending resume rework plan`
- **Date/time (local):** `2026-03-17 20:40 +0500`
- **Why this query is precise:** the next block needs one migration plan for converging a legacy capability that is split across new and old owners without counting wrapper growth as progress.
- **Sources opened (from this query):**
  - `Parallel Change` — `https://martinfowler.com/bliki/ParallelChange.html`
- **Source quality:** primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** when the new side already owns part of the contract, the next truthful step is one explicit expand/migrate/contract plan that moves the remaining old callsites and then retires the legacy authority.
- **Decision:** `reuse/integrate` — use the existing `DialogStateService` and `state_service` pending-resume surfaces as the target owner, then plan one bounded frozen rework block that migrates the remaining legacy pending-resume callsites into those surfaces.
- **Rejected options:**
  - continue timeout-owner micro-slices after the timeout-owner family is already centralized
  - add another helper around legacy pending-resume functions without retiring the old callsites
  - reopen continuity micro-slice farming as if a new equally bounded non-frozen seam had appeared

## Root cause (mandatory)
- **Symptom:** after Block O, the live pending-resume authority remains split between new owner surfaces (`DialogStateService`, `state_service`) and frozen legacy helpers in `decision.py` and `pending.py`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/core/dialog_state_service.py:1097` and `truffles-api/app/core/dialog_state_service.py:1151` to confirm generic pending-resume payload capture/restore already exist in the target owner.
  2. inspect `truffles-api/app/services/state_service.py:590` and `truffles-api/app/services/state_service.py:608` to confirm non-frozen delegation already uses those owner methods.
  3. inspect `truffles-api/app/routers/webhook/decision.py:8558`, `truffles-api/app/routers/webhook/decision.py:8688`, `truffles-api/app/routers/webhook/decision.py:8750`, and `truffles-api/app/routers/webhook/decision.py:10833` to confirm boundary-specific pending-resume derivation/restore/activation still lives in frozen legacy.
  4. inspect `truffles-api/app/routers/webhook/pending.py:111` and `truffles-api/app/routers/webhook/pending.py:137` to confirm direct snapshot/restore helpers still live in frozen legacy as well.
  5. compare the surfaces: the new owner exists, but the old frozen callsites still remain reachable and authoritative.
- **Evidence to capture:**
  - existing owner methods in `DialogStateService`
  - existing non-frozen delegation in `state_service`
  - surviving frozen pending-resume callsites in `decision.py` and `pending.py`
  - planned owner-capture path that makes the old callsites deletable
- **Five Whys (or equivalent):**
  1. Why is the continuity owner still incomplete? Because pending-resume behavior still has multiple live writers/callers.
  2. Why did previous micro-slices stop helping? Because the remaining authority is an asset family across two frozen files, not one more isolated helper body.
  3. Why is there still a viable capture path? Because generic pending-resume payload handling already exists in `DialogStateService` and `state_service`.
  4. Why not implement directly from this block? Because the capture path needs one explicit plan covering derivation, restore, activation, and frozen callsite reduction together.
  5. Why is this still admissible? Because the next implementation block can target deletion/reduction of concrete old helper bodies in `decision.py` and `pending.py`, not just add another wrapper.
- **Root cause statement:** pending-resume continuity is no longer blocked by lack of a target owner; it is blocked by unfinished owner convergence. `DialogStateService` already owns generic pending-resume payload capture/restore, but frozen `decision.py` and `pending.py` still own boundary-specific derivation, restore, activation, and snapshot helpers, so the old continuity power shape remains live.
- **Fix mechanism:**
  - define one owner-capture asset around pending-resume continuity
  - reuse `DialogStateService` and `state_service` as the target owner surfaces
  - plan one bounded frozen rework implementation that reduces the remaining frozen helper bodies to service-owned calls

## Preferred capture path / rejected alternatives
- **FACT:** `DialogStateService` already owns generic pending-resume payload capture/restore.
- **FACT:** `state_service` already delegates to those owner methods.
- **FACT:** the live remaining legacy authority is now the boundary-specific pending-resume family in frozen `decision.py` plus direct snapshot/restore helpers in frozen `pending.py`.
- **INFERENCE:** preferred target is one pending-resume asset capture into `DialogStateService` plus `state_service`, because the new owner already exists and the old helper bodies can become deletable under one bounded frozen rework block.
- **INFERENCE:** rejected alternative `another timeout-owner micro-slice` is exhausted and would not touch the surviving continuity authority.
- **INFERENCE:** rejected alternative `wrap legacy pending helpers in another service` would add a bridge but leave multiple live writers.
- **INFERENCE:** rejected alternative `reopen tiny continuity micro-slices` would violate the earlier blocker truth that no equally bounded non-frozen seam exists anymore.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - existing pending-resume tests in `truffles-api/tests/test_dialog_state_service.py`
  - existing state-service tests in `truffles-api/tests/test_state_service.py`
  - existing endpoint continuity tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
- **Why not reinvent the wheel:** the target owner and partial delegation path already exist; the plan only needs to converge the remaining frozen callsites around them.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is one planning block that sets up the next real deletion block; runtime code stays unchanged here.

## Invariant
- no runtime code edits
- no claim that pending-resume authority is already converged
- no new helper family counted as progress by itself
- single continuity owner remains the target architecture

## Scope
- define one owner-capture path for pending-resume continuity
- identify the exact frozen helper bodies that the next implementation block must delete or reduce
- define the reuse path through `DialogStateService` and `state_service`
- sync canon/session artifacts and regenerate packet

## Out of scope
- runtime implementation
- direct edits to `decision.py` or `pending.py`
- semantic owner work
- proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with one exact web search, RCA, reuse-first section, residual debt, and next-block contract.
2. Record the owner-capture baseline: target owner already exists in `DialogStateService` / `state_service`, while frozen callsites remain in `decision.py` and `pending.py`.
3. Define the next implementation block as one bounded frozen rework around pending-resume helpers, not another micro-slice.
4. Update source-of-truth, active program, packet, session, and state.
5. Run governance checks.

## DoD
- the pending-resume rework plan TP exists at `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922.md`
- canon/packet/test all agree that Block Q is the active block
- the plan explicitly defines the target owner surfaces, the frozen helper bodies to remove/reduce, and the next implementation contract
- required checks are green

## Checks
- `rg -n "capture_pending_resume_payload|restore_pending_resume_payload" truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py`
- `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|pending_resume_boundary_payload|pending_resume_boundary_active|pending_handoff_resume_boundary" truffles-api/app/routers/webhook/decision.py`
- `rg -n "_build_pending_resume_snapshot|_restore_pending_resume|pending_resume" truffles-api/app/routers/webhook/pending.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP, canon, packet, session, and state
- seam scans for target owner and remaining frozen pending-resume helpers
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the next implementation block cannot reduce concrete frozen helper bodies in both files, stop and escalate instead of introducing another bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only planning block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the rework plan
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next block must target real frozen helper-body reduction in `decision.py` and `pending.py`

## Rollback
1. Revert the rework plan TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime implementation hidden in this planning block
- no continuation of timeout-owner micro-slice farming
- no wrapper-only helper growth counted as progress
- no claim that `pending.py` or `decision.py` authority is already deleted

## Risks / blockers
- the next implementation block spans two frozen files and therefore must stay tightly bounded to pending-resume helper-body reduction only
- pending-resume boundary behavior touches expected-reply, booking, session-memory, and re-entry semantics together, so split ownership can reappear if the next block is not kept asset-level

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `truffles-api/app/routers/webhook/decision.py` still owns pending-resume boundary derivation/restore/activation helpers
  - frozen `truffles-api/app/routers/webhook/pending.py` still owns direct snapshot/restore helpers
  - single continuity owner is still incomplete
- **Why not in this block:**
  - this block only defines the owner-capture path and next implementation contract
- **Risk if deferred:**
  - the team can drift back into fake progress through helper growth while the old continuity shape stays alive
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core continuity implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** author one bounded pending-resume frozen rework implementation TP that moves pending-resume derivation/restore/activation and snapshot helpers behind `DialogStateService` / `state_service` owned surfaces, while reducing the old helper bodies in `decision.py` and `pending.py` to bounded service invocation only
- **First deterministic check command:** `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|_build_pending_resume_snapshot|_restore_pending_resume" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
- **Blocked-by conditions:** if the implementation cannot reduce concrete frozen helper bodies in both files or if it reintroduces multiple live continuity writers, stop and escalate instead of authoring another bridge cut
- **Owner role for closure:** `Top Architect`
