# TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BROADER-RESIDUAL-FAMILY-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BUNDLE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BROADER-RESIDUAL-FAMILY-BUNDLE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one broader residual-family decision after the active terminal convergence bundle proved saturated. This block must record that the current bundle cannot truthfully kill the live `reasoning_core -> decision_router._handle_webhook_payload(...)` transport seam without widening into a larger frozen residual family, define that broader rooted family exactly, lock the admissible owner destinations, and stop runtime edits until the broader family is explicitly activated.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
- `truffles-api/app/services/policy_core_guard_orchestration_service.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n 'decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|"expected_reply_type": "time"' truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '14120,14480p;14860,15040p;15616,15756p;19373,19481p'`
  - `rg -n "handle_policy_validation_boundary|handle_policy_timeout_degrade_boundary|handle_policy_timeout_recovery_boundary|handle_policy_timeout_booking_specialist_boundary|handle_policy_timeout_booking_time_followup_boundary|handle_policy_core_guard_orchestration|resolve_and_apply_timeout_owner_boundary" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/*.py`
  - `python3 scripts/continuity_writer_guard.py`
  - `python3 scripts/arch_guard.py`
- `FACT findings`:
  - the live legacy transport seam still remains at `truffles-api/app/services/reasoning_core.py:12349` and `:12361`, where active `/webhook` traffic still falls into frozen `truffles-api/app/routers/webhook/decision.py:8889`.
  - the current terminal convergence bundle still carries continuity-guard drift at `truffles-api/app/services/reasoning_core.py:9482` (`expected_reply_type=reply_slot,`) and `truffles-api/app/services/reasoning_core.py:9693` (`"expected_reply_type": "time",`), so `python3 scripts/continuity_writer_guard.py` and `python3 scripts/arch_guard.py` remain red.
  - frozen residual family `truffles-api/app/routers/webhook/decision.py:1419-1875` still reaches `handle_policy_validation_boundary(...)`, `handle_policy_timeout_booking_specialist_boundary(...)`, `handle_policy_core_guard_orchestration(...)`, and `resolve_and_apply_timeout_owner_boundary(...)`.
  - frozen residual family `truffles-api/app/routers/webhook/decision.py:14866-15040` still reaches `handle_policy_timeout_recovery_boundary(...)` and `handle_policy_timeout_degrade_boundary(...)`.
  - frozen residual family `truffles-api/app/routers/webhook/decision.py:15616-15756` still reaches `handle_policy_timeout_degrade_boundary(...)`, `handle_policy_timeout_booking_time_followup_boundary(...)`, and `handle_policy_core_guard_orchestration(...)`.
  - frozen residual family `truffles-api/app/routers/webhook/decision.py:19373-19481` still remains the surviving tool-reply / reschedule-guard contour behind the same fallback.
  - those broader owner destinations already exist in non-frozen services, but they are outside the active terminal convergence bundle touch-list and outside the narrower admissible-owner set of the current bundle.
- `INFERENCE to verify in this block`:
  - the active terminal convergence bundle is truthfully saturated; the next admissible move is a broader residual-family decision, not more runtime edits under the current narrower bundle.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active terminal convergence chain; no second query is allowed or needed.
- **Existing solutions found:** when the current implementation bundle cannot retire the old seam without widening beyond its rooted family, stop runtime work, publish the broader family decision explicitly, and only then resume implementation on the larger rooted contour.
- **Decision:** `reuse/integrate`
  - reuse existing non-frozen owner surfaces already materialized in the timeout / guard / boundary services
  - do not invent a new transport wrapper inside `reasoning_core`
- **Rejected options:**
  - second web query
  - copying the frozen `decision.py` body into a new `reasoning_core` helper/wrapper
  - claiming progress from continuity-guard cleanup alone while the live transport seam still survives

## Root cause (mandatory)
- **Symptom:** the active terminal convergence bundle can inspect the live fallback seam and the continuity-guard drift, but it cannot truthfully retire the seam within its current rooted scope.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/reasoning_core.py:12336-12361` and confirm active traffic still reaches `decision_router._handle_webhook_payload(...)` when all current safe owner cutovers return `None`.
  2. inspect `truffles-api/app/services/reasoning_core.py:9423-9704` and confirm the current semantic-arbitration tail only covers the bounded timeout pending-slot-question / reschedule slices before returning `None`.
  3. inspect `truffles-api/app/routers/webhook/decision.py:14120-14480`, `:14866-15040`, `:15616-15756`, and `:19373-19481` and confirm the surviving fallback path still fronts broader residual families backed by existing timeout / guard / boundary owner services.
  4. compare those service destinations against the active bundle touch-list and admissible-owner set and confirm the current bundle would have to widen beyond its rooted family to keep moving.
  5. run `python3 scripts/continuity_writer_guard.py` and confirm the current implementation bundle also remains governance-red.
- **Evidence:**
  - explicit `reasoning_core -> decision.py` fallback callsites
  - bounded `semantic_arbitration_owner_cutover` returns `None` outside its current narrowed slices
  - broader frozen residual families still reachable behind fallback
  - current implementation bundle does not admit the broader timeout / recovery / guard family needed to replace that fallback truthfully
- **Five Whys (or equivalent):**
  1. Why is the old seam still live? Because the current safe owner lane still falls through to frozen `decision.py`.
  2. Why not just keep extending the current bundle? Because the next surviving work is no longer limited to the current narrowed family.
  3. Why is that widening real? Because the next live fallback path immediately reaches broader timeout-recovery, specialist-followup, timeout-owner, and guard-orchestration families in frozen `decision.py`.
  4. Why is copying those branches into `reasoning_core` invalid? Because that would create a new mixed compatibility hotspot instead of deleting the old one through existing owners.
  5. Why is a broader decision block required? Because repo truth must first lock the larger rooted family and admissible destinations before runtime work can resume honestly.
- **Root cause statement:** the active terminal convergence bundle is blocked because killing `truffles-api/app/services/reasoning_core.py:12349-12361` under the current rooted scope would require widening into a broader frozen residual family that fronts already-existing timeout / recovery / guard services outside the active bundle contract.
- **Fix mechanism:**
  - publish one broader residual-family decision block
  - lock the exact rooted broader family and admissible owner destinations
  - stop the current implementation bundle as `GAP` without runtime edits
  - only then activate a broader residual-family implementation bundle

## Exact rooted broader residual family
- `truffles-api/app/services/reasoning_core.py:12349-12361` — still-live default-path transport seam into frozen `decision.py`.
- `truffles-api/app/routers/webhook/decision.py:12478-12545` — frozen policy payload normalization / plan extraction still reachable behind fallback.
- `truffles-api/app/routers/webhook/decision.py:14120-14480` — frozen validation / invalid-schema specialist-followup / guard-orchestration / timeout-owner boundary cluster still reachable behind fallback.
- `truffles-api/app/routers/webhook/decision.py:14866-15040` — frozen timeout recovery and generic timeout-clarify cluster still reachable behind fallback.
- `truffles-api/app/routers/webhook/decision.py:15106-15349` — frozen timeout specialist-followup and master-info-interrupt cluster still reachable behind fallback.
- `truffles-api/app/routers/webhook/decision.py:15432-15756` — frozen booking-retry / pending-slot-question / active-name time-followup / degraded-collect cluster still reachable behind fallback.
- `truffles-api/app/routers/webhook/decision.py:19373-19481` — surviving frozen tool-reply / reschedule-guard cluster still reachable behind fallback.
- existing non-frozen owner destinations already materialized behind that broader family:
  - `truffles-api/app/services/policy_validation_boundary_service.py:191`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py:102`
  - `truffles-api/app/services/policy_timeout_recovery_boundary_service.py:49`
  - `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py:90`
  - `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py:72`
  - `truffles-api/app/services/policy_core_guard_orchestration_service.py:178`
  - `truffles-api/app/services/timeout_owner_boundary_service.py:276`

## Admissible owner destinations
- `truffles-api/app/services/reasoning_core.py`
  - admissible only as transport/preflight coordinator; it must not become a new copied compatibility wrapper.
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
- `truffles-api/app/services/policy_core_guard_orchestration_service.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- **Explicitly not admissible:**
  - any new transport wrapper/helper around `decision.py`
  - silent widening into frozen `truffles-api/app/routers/webhook/booking.py`
  - silent widening into frozen `truffles-api/app/routers/webhook/pending.py`
  - counting continuity-guard cleanup without old seam death as runtime progress

## FACT vs INFERENCE verdict
- **FACT:** this block is doc-only; no old authority seam is deleted or made unreachable here.
- **FACT:** the active terminal convergence bundle is blocked/saturated on current repo truth.
- **FACT:** the still-live fallback now fronts a broader residual family than the current bundle admits.
- **FACT:** the broader owner destinations already exist in non-frozen services; the current bundle simply does not admit that widening.
- **INFERENCE:** the next truthful move is one broader residual-family implementation bundle activated only after this decision sync, not more runtime edits under the current narrower bundle.
- **Decision:** switch canon to this broader residual-family decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
  - `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
  - `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
  - `truffles-api/app/services/policy_core_guard_orchestration_service.py`
  - `truffles-api/app/services/timeout_owner_boundary_service.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the missing work is not a new surface; it is admitting the truthful broader family already visible in repo code and routing it through existing owners.

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-only`
- **Why this profile fits:** the current implementation bundle is blocked by repo truth, so the only truthful next block is a broader-family decision.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no second web search
- no new wrapper/helper counted as progress
- answer to `какой old authority seam стал deleted или unreachable после этого блока?` remains `никакой`

## Scope
- record the truthful `GAP` on the active terminal convergence bundle
- define the exact broader residual family that blocks the current bundle
- define the admissible owner destinations for that broader family
- switch canon/session artifacts to this broader decision block

## Out of scope
- runtime edits in `truffles-api/app/services/reasoning_core.py`
- edits to frozen `truffles-api/app/routers/webhook/decision.py`
- edits to frozen `truffles-api/app/routers/webhook/booking.py`
- edits to frozen `truffles-api/app/routers/webhook/pending.py`
- acceptance / `L2` / proof-path work
- any second web search

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this broader residual-family decision TP.
2. Switch canon/session artifacts away from the blocked narrower implementation bundle.
3. Regenerate packet and rerun the decision-sync checks.
4. Preserve the active runtime result as `GAP`: no seam died in this block.

## DoD
- the broader residual-family decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922.md`
- canon / packet / architecture test all agree this is the active block
- the block states explicitly that seam-deletion count here is zero
- the block states explicitly why the current implementation bundle is blocked
- the next non-negotiable move becomes one broader residual-family implementation bundle

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|"expected_reply_type": "time"" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '14120,14480p;14860,15040p;15616,15756p;19373,19481p'`
- `rg -n "handle_policy_validation_boundary|handle_policy_timeout_degrade_boundary|handle_policy_timeout_recovery_boundary|handle_policy_timeout_booking_specialist_boundary|handle_policy_timeout_booking_time_followup_boundary|handle_policy_core_guard_orchestration|resolve_and_apply_timeout_owner_boundary" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/*.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- deterministic scans proving the current narrower implementation bundle is blocked by a broader residual family
- deterministic scans proving the live transport seam still remains
- deterministic scans proving continuity / architecture guards remain red on current repo truth
- updated canon/session artifacts for this broader decision block

## Rollback
1. Revert the doc changes from this decision block.
2. Regenerate the packet.
3. Re-run the checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only broader-family decision; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate agree the current narrower bundle is blocked and the broader decision is active.
- **Rollback:** revert the decision docs, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either implement the broader residual family or stop with a narrower truthful `GAP`; it must not resume the blocked narrower implementation bundle.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic scans plus doc/governance checks only.
- **Stop condition:** if the broader residual family still cannot be activated without frozen widening or helper growth, stop and publish `GAP` instead of claiming terminal progress.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits in this block
- no new wrapper/helper
- no claim that the live `reasoning_core -> decision.py` seam is already dead
- no claim that continuity-guard drift is resolved in this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- live `reasoning_core -> decision.py` transport seam at `truffles-api/app/services/reasoning_core.py:12349-12361`
- continuity-guard drift at `truffles-api/app/services/reasoning_core.py:9482` and `:9693`
- broader residual family in frozen `decision.py` at `:12478-12545`, `:14120-14480`, `:14866-15040`, `:15106-15349`, `:15432-15756`, and `:19373-19481`

### Why not in this block
- the current narrower implementation bundle is now proven saturated; runtime work would widen beyond its admitted rooted family.

### Risk if deferred
- owner statuses remain truthfully partial
- the live legacy transport seam remains active
- continuity / architecture governance remains red

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922.md`
- future implementation follow-up locked by this decision block

### Expiry/trigger to stop deferral
- stop deferral immediately if any runtime proposal tries to resume the narrower terminal bundle or copy frozen coordinator logic into a new `reasoning_core` helper/wrapper

## Next-block contract (mandatory)
### Next block objective
- activate one broader residual-family implementation bundle that can repair governance drift and make at least one old live authority seam unreachable inside the broader rooted family.

### First deterministic check command
- `rg -n "handle_policy_validation_boundary|handle_policy_timeout_degrade_boundary|handle_policy_timeout_recovery_boundary|handle_policy_timeout_booking_specialist_boundary|handle_policy_timeout_booking_time_followup_boundary|handle_policy_core_guard_orchestration|resolve_and_apply_timeout_owner_boundary" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/*.py`

### Blocked-by conditions
- need for a new wrapper/helper
- need to widen into frozen `truffles-api/app/routers/webhook/booking.py`
- need to widen into frozen `truffles-api/app/routers/webhook/pending.py`
- need for a second web query
- inability to make any old live authority seam unreachable inside the broader rooted family

### Owner role for closure
- `Top Architect`
