# TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-BROADER-REWORK-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-TIMEOUT-BOUNDARY-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-REWORK-PLAN-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one broader rework decision after the timeout-owner micro-slice line is exhausted. This block must decide truthfully that the surviving live authority is no longer another cheap timeout-owner helper cut, but a broader pending-resume continuity family spanning derivation, restore, and activation across frozen legacy surfaces.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|pending_resume_boundary_payload|pending_resume_boundary_active|pending_handoff_resume_boundary" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_build_pending_resume_snapshot|_restore_pending_resume|pending_resume" truffles-api/app/routers/webhook/pending.py`
  - `sed -n '8558,8795p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10820,10930p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15155,15245p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15585,15655p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1,240p' truffles-api/app/services/timeout_owner_boundary_service.py`
- `FACT findings`:
  - both timeout-owner apply/send branches now exit through `apply_timeout_owner_boundary_resolution(...)` in `truffles-api/app/routers/webhook/decision.py:15192` and `truffles-api/app/routers/webhook/decision.py:15540`.
  - the surviving live authority in frozen `decision.py` is now the pending-resume derivation/restore/activation cluster, not another timeout-owner apply/send body:
    - `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8558`
    - `_restore_pending_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8688`
    - `_restore_resolved_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8750`
    - activation/preserve path at `truffles-api/app/routers/webhook/decision.py:10833`
  - `_derive_pending_booking_resume_boundary_payload(...)` is reused at multiple live callsites in `decision.py`, including restore flow and the pending-timeout branch, so there is no next cheap single-callsite deletion left.
  - frozen `truffles-api/app/routers/webhook/pending.py` still owns direct pending-resume snapshot/restore helpers via `_build_pending_resume_snapshot(...)` and `_restore_pending_resume(...)`.
- `Detected drift (docs vs code)`:
  - after Block O, continuing the same micro-slice style would overstate progress; the remaining authority is now a broader pending-resume continuity asset, not another bounded timeout-owner helper seam.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "StranglerFigApplication"`
- **Date/time (local):** `2026-03-17 20:32 +0500`
- **Why this query is precise:** the next decision is whether to keep carving tiny helper slices or to acknowledge that the remaining legacy authority must be captured as one broader asset.
- **Sources opened (from this query):**
  - `Strangler Fig Application` — `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** when a legacy capability remains shared across multiple live entrypoints and restore paths, it should be captured as one bounded asset instead of farming narrow cuts that leave the same authority shape alive.
- **Decision:** `reuse/integrate` — use the strangler-fig rule as the truth gate here: switch from timeout-owner micro-slices to one broader pending-resume rework decision around the surviving continuity asset.
- **Rejected options:**
  - continue authoring timeout-owner micro-slices after apply/send authority already moved
  - count another helper wrapper around pending-resume derivation as equivalent to authority deletion
  - reopen continuity micro-slice farming without proving a new bounded non-frozen seam

## Root cause (mandatory)
- **Symptom:** Block O deleted the pending-timeout inline apply/send body, but the remaining live legacy authority is still spread across pending-resume derivation, restore, and activation logic in frozen `decision.py` plus direct snapshot/restore helpers in frozen `pending.py`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:15192` and `truffles-api/app/routers/webhook/decision.py:15540` to confirm both timeout-owner apply/send branches are already helper-owned.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8558`, `truffles-api/app/routers/webhook/decision.py:8688`, `truffles-api/app/routers/webhook/decision.py:8750`, and `truffles-api/app/routers/webhook/decision.py:10833` to confirm the live pending-resume derivation/restore/activation cluster remains inline in frozen legacy.
  3. inspect `truffles-api/app/routers/webhook/pending.py:111` and `truffles-api/app/routers/webhook/pending.py:137` to confirm pending snapshot/restore authority still lives in frozen `pending.py`.
  4. compare the callsite spread for `_derive_pending_booking_resume_boundary_payload(...)`; it is reused across restore and pending-timeout paths, so deleting one callsite no longer deletes the authority family.
- **Evidence to capture:**
  - helper-owned timeout-owner callsites
  - pending-resume derivation/restore/activation cluster in `decision.py`
  - direct snapshot/restore helpers in `pending.py`
  - updated canon moving away from another micro-slice
- **Five Whys (or equivalent):**
  1. Why is another timeout-owner micro-slice no longer truthful? Because the apply/send authority that defined that family has already moved.
  2. Why does progress stop there? Because the remaining live authority is now shared derivation/restore behavior, not one more isolated send branch.
  3. Why is that broader? Because the same pending-resume contract is produced, restored, and activated in multiple legacy entrypoints.
  4. Why not keep cutting one helper at a time? Because helper growth would leave the same multi-writer continuity shape alive.
  5. Why move to a rework decision now? Because repo truth shows the next honest seam is an asset-level pending-resume rework, not another cheap timeout-owner deletion.
- **Root cause statement:** timeout-owner micro-slices were valid only while inline apply/send authority bodies were still alive. After Block O, the surviving authority is a broader pending-resume continuity family fragmented across derivation, restore, activation, and snapshot helpers in frozen `decision.py` and `pending.py`, so continuing micro-slices would no longer delete the old power shape.
- **Fix mechanism:**
  - publish a broader pending-resume rework decision in canon
  - stop further timeout-owner micro-slice farming
  - force the next block to plan pending-resume authority capture as one bounded asset

## FACT vs INFERENCE verdict
- **FACT:** timeout-owner apply/send ownership now lives in `truffles-api/app/services/timeout_owner_boundary_service.py`.
- **FACT:** surviving pending-resume authority remains in frozen `decision.py` derivation/restore/activation helpers plus frozen `pending.py` snapshot/restore helpers.
- **FACT:** `_derive_pending_booking_resume_boundary_payload(...)` is reused across multiple live callsites, so there is no remaining one-callsite timeout-owner deletion seam of the same class as Block L or Block O.
- **INFERENCE:** the next admissible block is a broader pending-resume rework plan, not another timeout-owner implementation micro-slice.
- **Decision:** switch canon to a broader pending-resume rework decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py` as the target continuity owner surface
  - `truffles-api/app/services/timeout_owner_boundary_service.py` as proof that the apply/send side is already centralized
  - existing continuity guards and packet flow
  - existing frozen pending-resume helpers as the authority inventory to capture, not to duplicate
- **External reuse:**
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the repo already contains the new continuity owner surface and the exact legacy authority inventory; what is missing is one truthful capture plan, not another custom helper family.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is one decision block to reset the next-step contract after the runtime seam scan; runtime code stays unchanged in this block.

## Invariant
- no runtime code edits
- no new timeout-owner micro-slice TP
- no deletion claim for `pending.py` in this block
- FACT vs INFERENCE separation stays explicit

## Scope
- classify the surviving post-Block-O authority shape
- record the broader pending-resume rework decision in canon
- switch the machine-readable next move away from timeout-owner micro-slices
- regenerate packet/session artifacts and rerun governance checks

## Out of scope
- runtime implementation
- frozen-file waiver execution
- direct `decision.py` or `pending.py` edits
- broader proof-path or semantic work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with one exact web search, RCA, reuse-first reasoning, and next-block contract.
2. Record the factual post-Block-O verdict: timeout-owner micro-slices are exhausted.
3. Switch canon to the broader pending-resume rework decision.
4. Regenerate packet and rerun governance checks.

## DoD
- the broader rework decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-broader-rework-decision-a922.md`
- canon/packet/test all agree the current block is the broader pending-resume rework decision
- timeout-owner micro-slice continuation is no longer the machine-readable next move
- required checks are green

## Checks
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
- seam scan proving timeout-owner apply/send is already centralized
- seam scan proving pending-resume authority remains broader and fragmented
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the rework decision cannot point to a concrete surviving authority cluster, stop and mark the GAP explicitly instead of inventing the next seam
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the new broader rework decision
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next block must be authored from the broader pending-resume rework decision, not from another timeout-owner micro-slice

## Rollback
1. Revert the broader rework decision TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no new timeout-owner implementation TP in this block
- no runtime code hidden inside the decision block
- no claim that pending-resume authority is already converged
- no wrapper-only helper growth counted as progress

## Risks / blockers
- the broader pending-resume asset spans two frozen files, so the next plan may require an explicit freeze-waiver decision or a larger owner-capture block than prior micro-slices
- `DialogStateService` is the natural target owner, but the exact convergence path is still to be planned, not assumed

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `truffles-api/app/routers/webhook/decision.py` still owns pending-resume derivation/restore/activation authority
  - frozen `truffles-api/app/routers/webhook/pending.py` still owns pending snapshot/restore helpers
  - single continuity owner is still not closed
- **Why not in this block:**
  - this block only resets the next-step contract after Block O; it does not implement the broader capture
- **Risk if deferred:**
  - the team may keep farming micro-slices that no longer delete the old continuity power shape
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core continuity or timeout-owner implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** author one pending-resume rework plan that defines how derivation, restore, activation, and snapshot authority converge to one continuity owner without reopening micro-slice farming
- **First deterministic check command:** `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|_build_pending_resume_snapshot|_restore_pending_resume" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
- **Blocked-by conditions:** if the plan cannot identify one owner-capture path that makes part of the old pending-resume authority deleted or unreachable, stop and escalate instead of authoring another helper cut
- **Owner role for closure:** `Top Architect`
