# TP-2026-03-17-consultant-core-bounded-rework-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOUNDED-REWORK-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ARCHITECTURE-TRUTH-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-architecture-truth-audit-before-further-cutovers-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-REWORK-PLAN-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Stop the stale queued boundary micro-slice plan before any more boundary implementation. This block must publish a bounded rework decision based on current code truth: either identify one real surviving boundary authority seam, or truthfully mark the queued boundary TP chain as exhausted/stale and force the next block to re-scope around the actual surviving mixed boundary authority.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-architecture-truth-audit-before-further-cutovers-a922.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-validator-turn-outcome-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-turn-result-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-artifact-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-decision-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-bounded-rework-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "build_controlled_degrade|build_preflight_reject|build_block_override|build_degrade_override|build_blocked_state|build_degraded_state|TurnOutcome\\(|TurnOutcomeObservability\\(" truffles-api/app/services/reasoning_core.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
  - `rg -n "TurnOutcome\\(|TurnOutcomeObservability\\(|ResponseRealizer\\(\\)\\.realize\\(|TurnExecutor\\(\\)\\.assemble\\(|build_owner_cutover_turn_outcome\\(|build_preflight_reject\\(|build_controlled_degrade\\(|build_block_override\\(|build_degrade_override\\(|build_blocked_state\\(|build_degraded_state\\(" truffles-api/app/services/reasoning_core.py`
  - `rg -n "build_block_boundary_artifact_from_request|build_degrade_boundary_artifact_from_request|build_owner_cutover_artifact|build_block_turn_outcome|build_degrade_turn_outcome|build_block_boundary_turn_result|build_degrade_boundary_turn_result" truffles-api/app/core/turn_executor.py truffles-api/app/core/boundary_validator.py`
  - `rg -n "TurnOutcome\\(|TurnOutcomeObservability\\(" truffles-api/app/routers/webhook/decision.py`
  - `sed -n '317,511p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '202,415p' truffles-api/app/core/turn_executor.py`
  - `sed -n '102,184p' truffles-api/app/core/boundary_validator.py`
  - `sed -n '20991,21109p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - `BoundaryValidator` already owns typed block/degrade `TurnOutcome` builders in `truffles-api/app/core/boundary_validator.py`.
  - `TurnExecutor` already owns typed block/degrade boundary artifact assembly and shared owner artifact assembly in `truffles-api/app/core/turn_executor.py`.
  - The inline boundary/result/outcome builders claimed by the queued boundary micro-slice TP chain are absent from `truffles-api/app/services/reasoning_core.py`; the remaining matches there are request-shaping calls into `TurnExecutor` plus thin owner-artifact invocation.
  - A real surviving mixed boundary authority still exists in frozen `truffles-api/app/routers/webhook/decision.py`, which still manually authors `TurnOutcome` and transport observability for the tool reply path.
- `Detected drift (docs vs code)`:
  - the queued boundary micro-slice TP chain now describes already-centralized ownership or only thin wrappers, so continuing it would narrate progress against stale code reality instead of deleting a live authority seam.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Branch by Abstraction"`
- **Date/time (local):** `2026-03-17 18:44 +0500`
- **Why this query is precise:** this block must decide whether the remaining boundary work is still a real migration seam or only stale abstraction churn after ownership has already moved.
- **Sources opened (from this query):**
  - `Branch by Abstraction` - `https://martinfowler.com/bliki/BranchByAbstraction.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** abstraction is a transition technique, not the end state; once the abstraction already owns the behavior, more wrapper churn does not count as meaningful migration unless an old implementation is actually retired.
- **Decision:** `reuse/integrate` - use the branch-by-abstraction rule as a truth gate: if the old boundary assembly already moved into `TurnExecutor` / `BoundaryValidator`, the queued micro-slice chain is stale and must not be executed as progress.
- **Rejected options:**
  - continue the queued boundary TP chain without revalidating it against code truth
  - count thin wrapper cleanup as equivalent to deleting a live authority seam
  - skip the rework decision and continue on narrative momentum
- **Open questions:** whether the next broader boundary block requires a frozen-file waiver or a new non-frozen bypass path.

## Root cause (mandatory)
- **Symptom:** after the architecture-truth audit said the next track was `boundary-owner audit`, the queued boundary TP chain still pointed to non-frozen micro-slices in `reasoning_core.py`, but the code scan now shows those micro-slices are already centralized in `TurnExecutor` / `BoundaryValidator` or reduced to thin wrappers.
- **Minimal reproduction:**
  1. Run the boundary seam scan against `reasoning_core.py`, `boundary_validator.py`, and `turn_executor.py`.
  2. Confirm that `reasoning_core.py` has no inline `TurnOutcome`, `TurnResult`, `ResponseRealizer().realize(...)`, or `TurnExecutor().assemble(...)` ownership for the queued boundary family.
  3. Confirm that `turn_executor.py` and `boundary_validator.py` already own those typed artifact/result/outcome helpers.
  4. Compare that with the queued boundary TPs, which still describe deleting those same seams from `reasoning_core.py`.
  5. Confirm that the broader live mixed boundary authority now sits mainly in frozen `decision.py` tool reply handling, not in the queued non-frozen micro-slices.
- **Evidence to capture:**
  - zero-match scan in `reasoning_core.py` for the queued inline boundary/result/outcome builders
  - positive matches in `turn_executor.py` / `boundary_validator.py` for the already-centralized helpers
  - positive matches in frozen `decision.py` for surviving manual `TurnOutcome` authoring
  - updated canon showing the next move changed from the stale queue to bounded rework decision
- **Five Whys (or equivalent):**
  1. Why is the queued boundary plan no longer trustworthy? Because it was not revalidated after recent cutovers landed in code.
  2. Why does that matter? Because it now points at already-deleted seams or thin wrappers rather than live authority.
  3. Why is that dangerous? Because it would count fake progress and keep the same old mixed boundary authority alive elsewhere.
  4. Why is the surviving authority harder now? Because the broader mixed boundary path is largely in frozen `decision.py` tool reply logic, not in a neat non-frozen helper seam.
  5. Why act now? Because continuing a stale micro-slice queue would violate the program rule that progress requires real old-authority deletion or unreachability.
- **Root cause statement:** the queued boundary micro-slice inventory drifted from actual code truth: `TurnExecutor` / `BoundaryValidator` already own the bounded boundary artifact/result/outcome assembly those TPs still claim to migrate, while the surviving mixed boundary authority is broader and partly frozen in `decision.py`.
- **Fix mechanism:**
  - stop the stale queued boundary micro-slice chain
  - publish a bounded rework decision in canon
  - force the next block to re-scope around the actual surviving boundary authority instead of already-finished abstractions

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing boundary seam scan commands
  - existing architecture-truth audit report
  - existing `TurnExecutor` / `BoundaryValidator` typed helpers
  - existing architecture packet/guard flow
- **External reuse:**
  - Martin Fowler `Branch by Abstraction`
- **Why not reinvent the wheel:** this block uses the repo's current typed core owners and only resets the plan to match code truth; it does not create a new migration mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is a stop-the-line planning correction block; runtime code stays unchanged.

## Invariant
- No runtime code edits.
- No frozen-router edits.
- No queued boundary micro-slice implementation may start before this rework decision is recorded.
- FACT vs INFERENCE separation must stay explicit.

## Scope
- audit the queued boundary TP chain against current code truth
- classify already-deleted seams vs thin wrappers vs surviving live authority
- publish the bounded rework decision in canon
- switch the machine-readable next move away from the stale boundary queue
- regenerate packet/session artifacts and rerun governance checks

## Out of scope
- runtime implementation
- frozen-file waiver or edits
- new boundary-owner implementation
- semantic owner work
- continuity work
- proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-bounded-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Record the factual boundary scan verdict: queued non-frozen micro-slices are stale/exhausted against current code.
3. Classify the surviving boundary authority as frozen/broader vs thin wrapper.
4. Update `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, packet, session, and `STATE.md` so the next move becomes bounded rework decision.
5. Run governance checks.

## DoD
- one bounded rework decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-bounded-rework-decision-a922.md`
- canon no longer points to `boundary_owner_audit_after_architecture_truth_audit` as the current non-negotiable next move
- packet/test/canon all agree that the boundary micro-slice queue is stale and the program is in bounded rework decision mode
- required checks are green

## Checks
- `rg -n "build_controlled_degrade|build_preflight_reject|build_block_override|build_degrade_override|build_blocked_state|build_degraded_state|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
- `rg -n "TurnOutcome\(|TurnOutcomeObservability\(|ResponseRealizer\(\)\.realize\(|TurnExecutor\(\)\.assemble\(|build_owner_cutover_turn_outcome\(|build_preflight_reject\(|build_controlled_degrade\(|build_block_override\(|build_degrade_override\(|build_blocked_state\(|build_degraded_state\(" truffles-api/app/services/reasoning_core.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP, canon, and packet
- zero-match reasoning-core boundary ownership scan
- positive-match frozen `decision.py` boundary authority scan
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the scan cannot distinguish thin wrappers from live authority, mark the gap explicitly and stop instead of guessing
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only stop-the-line decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gates agree on the new next move
- **Rollback:** revert the new TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next implementation block must be authored from the new bounded rework decision, not from the stale queued boundary TP chain

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Drift closeout rule`:
  - active block metadata must match the bounded rework decision and the generated packet output.

## Rollback
1. Revert the bounded rework decision TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime implementation hidden inside this decision block
- no claim that queued boundary micro-slices are still valid without code evidence
- no new bridge counted as progress
- no frozen-file edits under this TP

## Risks / blockers
- the actual surviving boundary seam may require either a frozen-file waiver or a broader bypass strategy, so the next implementation block may be wider than the old queued micro-slices
- some prior draft TPs remain in the repo and can mislead future agents unless the generated packet/source of truth are kept authoritative

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader boundary ownership is still incomplete
  - frozen `truffles-api/app/routers/webhook/decision.py` still owns real tool-reply boundary authoring
  - continuity, proof path, and multi-pack closure remain incomplete
- **Why not in this block:**
  - this block only resets the next-step contract to match current code truth; it does not implement the broader boundary deletion
- **Risk if deferred:**
  - the team may spend more cycles on stale micro-slices while the real mixed boundary authority remains alive
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-boundary-rework-plan-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core boundary implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** author a broader boundary rework plan around the real surviving mixed boundary authority, with explicit treatment of frozen `decision.py` tool-reply ownership and any required bypass/freeze-waiver decision
- **First deterministic check command:** `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if frozen-file policy cannot be relaxed and no broader non-frozen bypass can make the old boundary authority unreachable, stop and escalate to `Top Architect` instead of farming another micro-slice
- **Owner role for closure:** `Top Architect`
