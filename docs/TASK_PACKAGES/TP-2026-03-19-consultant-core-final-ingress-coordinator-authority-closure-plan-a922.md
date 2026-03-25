# TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-AUTHORITY-CLOSURE-PLAN-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-PREFLIGHT-CLEAR-STATE-CONTAMINATION-FAMILY-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-AUTHORITY-CLOSURE-IMPLEMENTATION-A922`, `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Author the final ingress/coordinator closure plan around the real surviving live authority: `/webhook` still falls through `reasoning_core` into frozen `decision.py`, so `semantic_owner`, `continuity_owner`, and `boundary_owner` cannot truthfully become `done`. This block must switch the primary story from proof-path residual laddering to structural owner closure.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md`
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
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '6860,6915p' truffles-api/app/services/reasoning_core.py`
  - `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
  - `sed -n '19310,19445p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15590,15650p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "semantic_owner:|continuity_owner:|boundary_owner:|current_primary_files:|target_primary_files:" docs/SOURCE_OF_TRUTH.yaml`
- `FACT findings`:
  - `reasoning_core.py` still delegates unmatched live `/webhook` traffic into frozen legacy at `truffles-api/app/services/reasoning_core.py:6887` and `truffles-api/app/services/reasoning_core.py:6899` by calling `decision_router._handle_webhook_payload(...)`.
  - frozen `decision.py` remains the live ingress/coordinator handler at `truffles-api/app/routers/webhook/decision.py:8887`.
  - frozen `decision.py` still authors boundary/result artifacts directly via `TurnOutcome(...)` and `TurnOutcomeObservability(...)` at `truffles-api/app/routers/webhook/decision.py:19322`, `truffles-api/app/routers/webhook/decision.py:19336`, and `truffles-api/app/routers/webhook/decision.py:19432`.
  - frozen `decision.py` still retains timeout/boundary override authority around `truffles-api/app/routers/webhook/decision.py:15593` and `truffles-api/app/routers/webhook/decision.py:15610`.
  - `docs/SOURCE_OF_TRUTH.yaml` still marks `semantic_owner`, `continuity_owner`, and `boundary_owner` as partial because `truffles-api/app/routers/webhook/decision.py` remains current primary on live ingress, while target owners are `truffles-api/app/core/turn_planner.py`, `truffles-api/app/core/dialog_state_service.py`, and `truffles-api/app/core/boundary_validator.py` / `truffles-api/app/core/turn_executor.py`.
  - `ops/diagnose.py` is only a proof-path surface in `docs/SOURCE_OF_TRUTH.yaml`; fixing proof residuals there cannot by itself finish owner closure.
- `Detected drift (docs vs code)`:
  - the current primary story is still acceptance-preflight proof-path blocker handling, but the code truth says the structural blocker is surviving ingress/coordinator authority behind frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Why this query is precise:** the repo already has downstream target owners; the remaining question is how to replace a surviving live coordinator without counting bridge growth or proof-path residual handling as architectural closure.
- **Sources opened (from this query):**
  - `Parallel Change` - `https://martinfowler.com/bliki/ParallelChange.html`
  - `Strangler Fig Application` - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** use an expand/migrate/contract plan to route live traffic through the new interface first, then contract the old coordinator until it becomes transport-only or unreachable.
- **Decision:** `reuse/integrate` - prefer one ingress/coordinator closure plan that routes remaining live authority through existing target owners (`turn_planner`, `dialog_state_service`, `boundary_validator`, `turn_executor`) over more proof-path residual or helper-driven work.
- **Rejected options:**
  - continue `ops/diagnose.py` residual laddering as the primary story
  - add another compatibility wrapper/helper around frozen `decision.py`
  - weaken owner status claims without making the live coordinator unreachable
- **Open questions:** whether the final closure can make `decision.py` unreachable from `reasoning_core` without touching frozen `decision.py`, or whether the truthful path requires an explicit targeted frozen waiver.

## Root cause (mandatory)
- **Symptom:** repeated acceptance-preflight residuals keep surfacing, while `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial.
- **Minimal reproduction:**
  1. Inspect `docs/SOURCE_OF_TRUTH.yaml` and confirm that `semantic_owner`, `continuity_owner`, and `boundary_owner` still list `truffles-api/app/routers/webhook/decision.py` or legacy ingress surfaces as current primary files.
  2. Inspect `truffles-api/app/services/reasoning_core.py:6887` and `truffles-api/app/services/reasoning_core.py:6899` and confirm unmatched live traffic still falls through to `decision_router._handle_webhook_payload(...)`.
  3. Inspect `truffles-api/app/routers/webhook/decision.py:19322`, `truffles-api/app/routers/webhook/decision.py:19336`, and `truffles-api/app/routers/webhook/decision.py:19432` and confirm frozen legacy still authors boundary/result artifacts.
  4. Inspect `docs/SOURCE_OF_TRUTH.yaml` proof-path section and confirm `ops/diagnose.py` is not an owner surface.
  5. Compare this with `r24`: proof-path residuals can move, but owner status does not close while the ingress/coordinator remains live.
- **Evidence to capture:**
  - current-primary vs target-primary owner map from `docs/SOURCE_OF_TRUTH.yaml`
  - live fallback from `reasoning_core` into `decision.py`
  - surviving `TurnOutcome` / boundary authority in `decision.py`
  - explicit reclassification of `r24` residuals as evidence-only, not the primary architectural story
- **Five Whys (or equivalent):**
  1. Why do owner statuses stay partial? Because live `/webhook` ingress still reaches legacy `decision.py`.
  2. Why does that matter? Because `decision.py` still makes semantic/boundary/coordinator decisions and emits runtime artifacts on live paths.
  3. Why do proof-path fixes not close this? Because `ops/diagnose.py` is observer/proof-only and not the runtime owner.
  4. Why did the program drift into proof-path blocker laddering? Because acceptance-preflight failures were cheaper to observe than the broader ingress closure, and each rerun exposed only the next surviving seam.
  5. Why is the broader ingress closure still missing? Because the program has not yet published one plan that treats `reasoning_core -> decision.py` fallback as the primary structural blocker and defines the contract for making it unreachable.
- **Root cause statement:** the remaining architectural blocker is live ingress/coordinator authority split across `truffles-api/app/services/reasoning_core.py` and frozen `truffles-api/app/routers/webhook/decision.py`; until that live path is retired or reduced to a transport-only shell, downstream owner cutovers cannot truthfully finish.
- **Fix mechanism:** publish one final ingress/coordinator closure plan, then execute one bounded implementation bundle that routes remaining live authority through `turn_planner`, `dialog_state_service`, `boundary_validator`, `turn_executor`, and `state_service`; if this cannot be done without frozen `decision.py` edits, escalate to one targeted frozen-waiver decision instead of another proof-path residual block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - existing owner-cutover interception patterns in `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/state_service.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the target owners and typed runtime contracts already exist; the missing artifact is one explicit ingress/coordinator closure plan that migrates the surviving live path and then contracts the old coordinator.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this block is a planning/canon switch, but it changes the program's primary implementation story and therefore must flow through packet/test/session guards.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is already `done`
- no proof-path residual counted as architectural closure by itself
- no new wrapper/helper counted as progress

## Scope
- define the structural blocker as live ingress/coordinator authority
- reclassify `r24` proof-path residuals as evidence-only, not the primary story
- map the target owner surfaces for final closure
- define the exact next implementation contract and the waiver decision point
- sync canon/session artifacts and regenerate packet

## Out of scope
- runtime implementation
- new `ops/diagnose.py` bugfix work
- acceptance or dev reruns
- transport, billing, or observer reopening as the primary story

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md`
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
1. Publish this TP with RCA, one exact web search, reuse-first reasoning, residual debt, and next-block contract.
2. Record the live ingress/coordinator seams that keep owner status partial.
3. Reclassify `r24` proof-path residuals as evidence-only and switch the primary story to final ingress/coordinator closure.
4. Update source-of-truth, active program, session, state, structure, and generated packet.
5. Run governance checks.

## DoD
- the final ingress/coordinator closure plan exists at `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md`
- canon/packet/test all agree that this plan is the active block
- the plan explicitly names the live ingress seams, target owner surfaces, and waiver decision point
- required checks are green

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
- `rg -n "semantic_owner:|continuity_owner:|boundary_owner:|current_primary_files:|target_primary_files:" docs/SOURCE_OF_TRUTH.yaml`
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
- updated TP, source of truth, active program, structure, packet, session, and state
- seam scans showing live `reasoning_core -> decision.py` fallback and surviving `TurnOutcome` authority in `decision.py`
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the next block cannot make the live ingress/coordinator authority unreachable without introducing a new compatibility seam, stop and escalate to one targeted frozen-waiver decision instead of coding around proof-path symptoms
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only planning block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the new primary story and next implementation contract
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next block must target live ingress/coordinator authority, not another proof-path micro residual

## Rollback
1. Revert the final ingress/coordinator closure plan TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime implementation hidden inside this planning block
- no continuation of proof-path residual laddering as the primary story
- no wrapper-only bridge growth around `decision.py`
- no claim of owner completion without deleting or bypassing a live ingress authority seam

## Risks / blockers
- the truthful next implementation may require frozen `truffles-api/app/routers/webhook/decision.py` edits and therefore an explicit waiver decision
- one implementation bundle may still need to split into bounded package-level families if the live coordinator is broader than this plan can safely close at once
- proof-path residuals such as `r24` may remain open until the structural ingress closure lands

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live `/webhook` ingress still falls through `reasoning_core` into frozen `decision.py`
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial
  - `r24` proof-path fallback-JID `None` dereference remains unresolved as evidence-only residue
- **Why not in this block:**
  - this block only switches the program to the correct structural closure plan
- **Risk if deferred:**
  - the program will keep spending expensive runs on downstream residue while the main owner closure remains incomplete
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-implementation-a922` (to be authored if bounded implementation is admissible)
  - `TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922` (to be authored if exact closure requires frozen `decision.py` edits)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core proof-path or acceptance-preflight residual block starts

## Next-block contract (mandatory)
- **Next block objective:** implement one bounded final ingress/coordinator closure bundle that makes the surviving live `reasoning_core -> decision.py` authority unreachable on the chosen family contour and converges the remaining semantic/continuity/boundary ingress through target owners; if the exact closure proves frozen-bound, stop and author the targeted waiver decision package instead of continuing proof-path symptom work
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the implementation path requires a new wrapper/helper, broadens scope beyond the declared owner surfaces, or cannot make an old ingress authority seam unreachable, stop and escalate instead of claiming progress
- **Owner role for closure:** `Top Architect`
