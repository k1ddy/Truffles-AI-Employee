# TP-2026-03-17-consultant-core-boundary-rework-plan-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-REWORK-PLAN-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOUNDED-REWORK-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-bounded-rework-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-BYPASS-IMPLEMENTATION-A922`, `CONSULTANT-CORE-FROZEN-BOUNDARY-WAIVER-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Author the broader boundary rework plan around the real surviving legacy authority. This block must identify which frozen boundary cluster is the next admissible target, what non-frozen bypass can make it unreachable, and whether a frozen-file waiver is required instead of pretending another `reasoning_core` micro-slice still exists.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-bounded-rework-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-rework-plan-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `sed -n '5520,6095p' truffles-api/app/services/reasoning_core.py`
  - `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|resolve_timeout_owner_boundary|timeout_owner_boundary_resolution|TurnOutcome\\(|TurnOutcomeObservability\\(" truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8670,8788p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10805,11055p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15593,15760p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '20970,21130p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "build_block_boundary_artifact_from_request|build_degrade_boundary_artifact_from_request|build_owner_cutover_artifact" truffles-api/app/core/turn_executor.py`
- `FACT findings`:
  - `reasoning_core.py` already intercepts preflight boundary conditions and many safe owner-cutover paths before the final fallback to `decision_router._handle_webhook_payload(...)`, but unmatched paths still flow into frozen legacy at `truffles-api/app/services/reasoning_core.py:6072`.
  - frozen `decision.py` still manually authors tool-reply `TurnOutcome` and transport observability in the policy-core tool reply path at `truffles-api/app/routers/webhook/decision.py:20991`.
  - frozen `decision.py` still owns pending-resume boundary derivation and restore helpers at `truffles-api/app/routers/webhook/decision.py:8553`, `truffles-api/app/routers/webhook/decision.py:8683`, and `truffles-api/app/routers/webhook/decision.py:8745`, and those helpers are invoked in the main legacy flow around `truffles-api/app/routers/webhook/decision.py:10828` and `truffles-api/app/routers/webhook/decision.py:11039`.
  - frozen `decision.py` still owns timeout owner boundary resolution and the subsequent context/expected-reply writes at `truffles-api/app/routers/webhook/decision.py:15593` and `truffles-api/app/routers/webhook/decision.py:15610`.
  - `TurnExecutor` and `BoundaryValidator` already own the typed block/degrade artifact/result/outcome builders for non-frozen paths, so the next boundary progress must come from bypassing or deleting one of the frozen legacy clusters, not from more helper extraction.
- `Detected drift (docs vs code)`:
  - the surviving boundary authority is now broader and more coupled than the earlier queued micro-slice inventory; the next block must explicitly choose between a non-frozen bypass strategy and a frozen-file waiver instead of assuming another narrow `reasoning_core` seam exists.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Strangler Fig Application"`
- **Date/time (local):** `2026-03-17 18:56 +0500`
- **Why this query is precise:** the next boundary step needs a migration pattern for making frozen legacy authority unreachable via a new path instead of continuing helper-by-helper abstraction churn.
- **Sources opened (from this query):**
  - `Strangler Fig Application` — `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** primary architecture guidance from Martin Fowler.
- **Existing solutions found:** the new implementation should grow around the old one and gradually make the old path unused/unreachable, rather than repeatedly polishing abstraction layers without retiring the surviving legacy authority.
- **Decision:** `reuse/integrate` — prefer a broader boundary bypass plan that makes one frozen authority cluster unreachable from `reasoning_core` over another helper extraction block.
- **Rejected options:**
  - continue helper-level boundary farming in non-frozen files
  - treat wrapper cleanup as equivalent to removing a live frozen authority
  - start implementation before choosing whether bypass or waiver is required
- **Open questions:** whether the timeout owner boundary can be bypassed entirely from a non-frozen intercept in `reasoning_core`, or whether it immediately requires a frozen-file waiver.

## Root cause (mandatory)
- **Symptom:** after the bounded rework decision stopped the stale non-frozen boundary queue, the program still lacks one explicit plan for how to make the remaining frozen boundary authority unreachable.
- **Minimal reproduction:**
  1. Inspect `reasoning_core.py` and confirm the final unmatched path still falls back into `decision_router._handle_webhook_payload(...)`.
  2. Inspect the frozen tool-reply `TurnOutcome` path at `truffles-api/app/routers/webhook/decision.py:20991`.
  3. Inspect the frozen pending-resume boundary derive/restore cluster at `truffles-api/app/routers/webhook/decision.py:8553`, `truffles-api/app/routers/webhook/decision.py:8683`, and `truffles-api/app/routers/webhook/decision.py:8745`, plus its runtime invocation points around `truffles-api/app/routers/webhook/decision.py:10828` and `truffles-api/app/routers/webhook/decision.py:11039`.
  4. Inspect the frozen timeout owner boundary cluster at `truffles-api/app/routers/webhook/decision.py:15593` and `truffles-api/app/routers/webhook/decision.py:15610`.
  5. Confirm that `TurnExecutor` / `BoundaryValidator` already own the available non-frozen typed builders, so no new helper extraction can delete these frozen authorities by itself.
- **Evidence to capture:**
  - the exact frozen boundary clusters that still own live decisions
  - the last non-frozen intercept point before legacy fallback in `reasoning_core.py`
  - the preferred rework candidate and explicit rejection of non-admissible alternatives
  - whether a freeze waiver is required or avoidable
- **Five Whys (or equivalent):**
  1. Why did the old boundary queue become invalid? Because the non-frozen helper seams it targeted are already centralized.
  2. Why is boundary ownership still incomplete? Because the live remaining authority is frozen and coupled to legacy context/state writes.
  3. Why is that a different problem? Because progress now requires bypassing a legacy cluster, not moving another helper.
  4. Why not pick any frozen helper at random? Because only a path that makes the old authority unreachable counts as progress; narrow extraction without bypass would fail the contract.
  5. Why plan first? Because the rework must choose between a broader non-frozen bypass and an explicit freeze-waiver decision before implementation starts.
- **Root cause statement:** the remaining boundary work shifted from helper extraction to legacy authority bypass: frozen `decision.py` still owns tool-reply outcome authoring plus pending-resume/timeout boundary state transitions, while `reasoning_core.py` still falls back into that legacy path whenever no safe cutover matches.
- **Fix mechanism:**
  - classify the surviving frozen boundary clusters by admissibility
  - choose one broader rework target with a concrete non-frozen intercept/bypass path
  - record whether a freeze waiver is required if bypass cannot make the old path unreachable

## Preferred target / rejected alternatives
- **FACT:** timeout owner boundary still lives in frozen `decision.py` at `truffles-api/app/routers/webhook/decision.py:15593` and `truffles-api/app/routers/webhook/decision.py:15610`, where it rewrites booking state, expected-reply context, canonical interaction owner, policy-guard override, trace/meta evidence, and final transport/send flow.
- **FACT:** pending-resume boundary derive/restore still lives in frozen `decision.py` at `truffles-api/app/routers/webhook/decision.py:8553`, `truffles-api/app/routers/webhook/decision.py:8683`, and `truffles-api/app/routers/webhook/decision.py:8745`, and is invoked from the main flow around `truffles-api/app/routers/webhook/decision.py:10828` and `truffles-api/app/routers/webhook/decision.py:11039`.
- **FACT:** tool-reply `TurnOutcome` authoring still lives in frozen `decision.py` at `truffles-api/app/routers/webhook/decision.py:20991`, but that path is behavior-rich and sits deep inside the policy-core tool reply branch.
- **INFERENCE:** preferred next implementation target is the timeout owner boundary cluster, because it is the clearest surviving boundary authority surface: it actively overrides the policy guard into `collect`, rewrites state/owner fields, and emits its own boundary trace/meta contract.
- **INFERENCE:** rejected immediate target `pending-resume derive/restore` is real surviving authority but remains continuity-heavy; by itself it does not cover the wider timeout-boundary override power shape that still controls guard recovery.
- **INFERENCE:** rejected immediate target `tool-reply TurnOutcome` is real authority but too broad for the immediate next implementation block; it should follow only after a successful timeout-boundary bypass or a separate waiver decision.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `reasoning_core.py` preflight and owner-cutover interception pattern
  - `TurnExecutor` boundary and owner artifact builders
  - `BoundaryValidator` typed outcome builders
  - current source-of-truth and packet flow
- **External reuse:**
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the repo already has the typed core execution surface; the missing piece is a plan for routing around the surviving frozen authority.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is still a planning/governance correction block, but it updates the architecture packet test, so session gate must treat it as an implementation-mode doc-led block.

## Invariant
- No runtime code edits.
- No frozen-router edits.
- No new boundary implementation starts before this rework plan chooses the admissible target.
- FACT vs INFERENCE separation must stay explicit.

## Scope
- classify the surviving frozen boundary clusters
- identify the real non-frozen intercept point before fallback
- choose the preferred broader rework target
- explicitly reject non-admissible alternatives
- sync canon/session artifacts and regenerate packet

## Out of scope
- runtime implementation
- frozen-file edits or waiver execution
- semantic owner work
- continuity owner work outside the boundary clusters
- proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-rework-plan-a922.md`
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
2. Record the surviving frozen boundary clusters and the last non-frozen intercept point before fallback.
3. Choose the preferred broader rework target and reject the non-admissible alternatives.
4. Update source-of-truth, active program, packet, session, and state so the new active block is boundary rework planning.
5. Run governance checks.

## DoD
- one broader boundary rework plan TP exists at `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-rework-plan-a922.md`
- canon/packet/test all agree on the new active block and next move
- the plan explicitly names the preferred target, the rejected alternatives, and the freeze-waiver/bypass decision point
- required checks are green

## Checks
- `sed -n '5520,6095p' truffles-api/app/services/reasoning_core.py`
- `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|resolve_timeout_owner_boundary|timeout_owner_boundary_resolution|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP, source of truth, active program, packet, session, and state
- frozen boundary cluster scan in `decision.py`
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if no bypass path can make a frozen cluster unreachable, record that a freeze waiver is required and stop instead of inventing another micro-slice
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only planning block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the preferred rework target
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next implementation block must follow this plan and target one real frozen boundary authority cluster

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
  - active block metadata must match the boundary rework plan and generated packet output.

## Rollback
1. Revert the boundary rework plan TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime implementation hidden inside this planning block
- no continuation of stale non-frozen boundary micro-slices
- no frozen-file edits under this TP
- no claim of progress unless the next implementation block can delete or bypass a real frozen authority seam

## Risks / blockers
- the preferred timeout-owner rework target may still require a freeze waiver if no non-frozen bypass can make it unreachable
- the tool-reply path is behavior-rich and remains broader follow-up scope
- the pending-resume boundary cluster still remains as residual follow-up authority even if timeout-owner is handled first

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `decision.py` still owns live boundary authority
  - continuity, proof path, and multi-pack closure remain incomplete
  - the exact first implementation candidate is still unexecuted
- **Why not in this block:**
  - this block only chooses the admissible target and bypass/waiver decision point
- **Risk if deferred:**
  - boundary work can drift back into fake progress or ad-hoc waiver requests
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-boundary-bypass-implementation-a922` (to be authored if bypass is feasible)
  - `TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922` (to be authored if bypass is not feasible)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core boundary implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** author the implementation TP that either bypasses the timeout owner boundary cluster from `reasoning_core` before legacy fallback or formally escalates to a frozen-file waiver decision
- **First deterministic check command:** `rg -n "resolve_timeout_owner_boundary|timeout_owner_boundary_resolution|_apply_policy_guard_override|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the chosen target cannot be made unreachable from a non-frozen intercept path and no waiver decision is approved, stop and escalate to `Top Architect`
- **Owner role for closure:** `Top Architect`
