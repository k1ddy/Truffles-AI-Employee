# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish the broader owner-replacement decision for final ingress/coordinator closure. This block must prove that the targeted frozen-waiver micro-implementation has produced admissible seam deletions but is no longer the right primary progress unit for finishing `semantic_owner`, `continuity_owner`, and `boundary_owner`, record why the new architecture is built-but-not-exclusive, and lock the next move to one broader owner-replacement bundle instead of continued seam farming.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
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
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1208,1325p;12470,12545p;15659,15756p;19373,19456p'`
  - `nl -ba docs/SOURCE_OF_TRUTH.yaml | sed -n '1,35p;255,265p'`
- `FACT findings`:
  - live fallback still remains explicit in `truffles-api/app/services/reasoning_core.py:6983` and `truffles-api/app/services/reasoning_core.py:6995`.
  - the target owner surfaces already exist in non-frozen code: `truffles-api/app/core/turn_planner.py:178`, `truffles-api/app/core/dialog_state_service.py:372`, `truffles-api/app/core/dialog_state_service.py:872`, `truffles-api/app/core/turn_executor.py:493`, and `truffles-api/app/services/policy_timeout_degrade_boundary_service.py:102`.
  - the targeted frozen-waiver implementation has already deleted three old live seams:
    - degraded-collect booking-state mutation at `truffles-api/app/routers/webhook/decision.py:15575-15600`
    - expected-reply context wrapper at `truffles-api/app/routers/webhook/decision.py:15603-15610`
    - tool-reply guard/finalize lambda-wiring at `truffles-api/app/routers/webhook/decision.py:19381-19406`
  - despite those deletions, the remaining live families are still rooted at `truffles-api/app/routers/webhook/decision.py:1216-1320`, `truffles-api/app/routers/webhook/decision.py:12478-12545`, `truffles-api/app/routers/webhook/decision.py:15659-15756`, and `truffles-api/app/routers/webhook/decision.py:19373-19456`.
  - `docs/SOURCE_OF_TRUTH.yaml` still lists `truffles-api/app/routers/webhook/decision.py` as a current primary file for `semantic_owner` and `boundary_owner` and still reflects non-exclusive continuity ownership.
- `Detected drift (docs vs code)`:
  - the targeted frozen-waiver implementation is truthful as seam-deletion evidence, but it is no longer the right main architecture story because finishing owner closure now requires one broader owner-replacement move instead of another isolated seam report.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent final-ingress waiver blocks; no second query is allowed or needed for this decision block
- **Existing solutions found:**
  - first build the new path, then contract the old coordinator until it becomes transport-only or unreachable
- **Decision:** `reuse/integrate`
  - reuse existing owner surfaces and the existing direct-owner cutover chain in `reasoning_core`
  - switch the active question from `which next seam dies` to `how the remaining live families become unreachable together`
- **Rejected options:**
  - a second web query: rejected by the active TP rule and unnecessary
  - continued micro seam farming as the primary architecture story: rejected because it can keep owners partial indefinitely
  - a new helper forest around `decision.py`: rejected because it would create another mixed hotspot instead of finishing replacement

## Root cause (mandatory)
- **Symptom:** `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial even though the new owner architecture already exists and several exact legacy seams have been deleted.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/reasoning_core.py:6983` and `:6995` and confirm live traffic still falls through to `decision_router._handle_webhook_payload(...)`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:1218`, `:12478`, `:15659`, and `:19377` and confirm the remaining semantic / continuity / boundary families are still live.
  3. Inspect `docs/SOURCE_OF_TRUTH.yaml:9-14`, `:18-25`, and `:29-33` and confirm target owners are defined but not yet exclusive runtime owners.
  4. Inspect the existing owner surfaces and confirm the architecture is materialized downstream.
- **Evidence:**
  - explicit fallback from `reasoning_core` into frozen `decision.py`
  - surviving rooted families in frozen `decision.py`
  - existing non-frozen owner surfaces already present
  - current source-of-truth still marks owners partial
- **Five Whys (or equivalent):**
  1. Why are owners still partial? Because live ingress still reaches frozen `decision.py`.
  2. Why does that remain true after several admissible seam deletions? Because the deleted seams were local contractions, not the final broader replacement of the remaining hotspot.
  3. Why is the new architecture not enough by itself? Because it exists downstream, but no fully wired broader entrypoint currently makes the remaining families unreachable together.
  4. Why is another micro cut the wrong main move now? Because it keeps measuring progress by local seam death rather than by exclusive runtime ownership.
  5. Why is a broader owner-replacement block now the honest next step? Because only one broader replacement can change the runtime topology from `built-but-downstream` to `exclusive owner path before fallback`.
- **Root cause statement:** the program has reached expand-without-contract saturation on final ingress/coordinator closure: the new architecture is built, but the remaining live mixed hotspot still sits on the `reasoning_core -> decision.py` fallback path, so owner status cannot close until a broader owner-replacement path makes those families transport-only or unreachable together.
- **Fix mechanism:**
  - stop treating further seam farming as the primary architecture story
  - switch canon to one broader owner-replacement decision block
  - lock the next runtime move to a broader owner-replacement bundle over the remaining final-ingress families plus the fallback boundary in `reasoning_core`

## FACT vs INFERENCE verdict
- **FACT:** the new owner architecture exists in non-frozen code.
- **FACT:** live runtime still falls through `reasoning_core` into frozen `decision.py`.
- **FACT:** three exact seams have died, but owners remain partial.
- **INFERENCE:** the next honest progress unit is one broader owner-replacement bundle, not another isolated seam report.
- **Decision:** switch canon from the targeted frozen-waiver implementation block to a broader owner-replacement decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - existing direct-owner interception chain in `truffles-api/app/services/reasoning_core.py`
  - evidence from the targeted frozen-waiver implementation block
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the missing piece is not another target owner surface; it is finishing the cutover topology so the remaining hotspot stops being live

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-heavy`
- **Override token:** `final-ingress-coordinator-broader-owner-replacement-decision`
- **Why this profile fits:** this block only changes trajectory/canon so the next runtime block can target owner closure directly.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is already `done`
- no claim that the targeted frozen-waiver implementation was invalid; it remains truthful seam-deletion evidence
- no new wrapper/helper or helper forest counted as progress
- no reopening of `booking.py`, `pending.py`, proof-path, or acceptance work as the main story

## Scope
- record that the new architecture is built but still not runtime-exclusive
- explain why continued seam farming is no longer the right primary progress unit
- lock the broader owner-replacement implementation scope for the remaining final-ingress families
- switch canon/session/packet to this decision block

## Out of scope
- runtime implementation in this block
- edits to frozen files in this block
- new acceptance or dev reruns
- new web search
- unrelated consultant-core families outside final ingress/coordinator closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
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
1. Publish this broader owner-replacement decision TP with RCA and exact next-block contract.
2. Record the factual state: targeted frozen-waiver implementation has produced valid seam deletions, but owner closure still remains incomplete.
3. Switch canon so the next non-negotiable move is one broader owner-replacement bundle.
4. Regenerate packet and rerun governance/session checks.

## Exact future broader replacement scope
- `truffles-api/app/services/reasoning_core.py`
  - the live fallback boundary rooted at `:6970-6995`
- `truffles-api/app/routers/webhook/decision.py`
  - expected-reply/session-memory fallback family rooted at `:1216-1320`
  - policy-core route/rescue/payload extraction family rooted at `:12478-12545`
  - timeout/pending-slot-question continuity + boundary family rooted at `:15659-15756`
  - tool-reply decision/state/payload + guard/finalize family rooted at `:19373-19456`
- bounded supporting non-frozen surfaces only:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - focused tests under `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_dialog_state_service.py`, `truffles-api/tests/test_message_endpoint.py`, and `truffles-api/tests/architecture`
- **Not in scope:**
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `ops/diagnose.py`
  - acceptance/l2 work
  - unrelated `decision.py` branches outside the rooted families above

## DoD
- the broader owner-replacement decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
- canon/packet/test all agree that this decision block is active
- the next move is no longer another targeted seam inside the old block
- required checks are green
- docs truthfully state that no old seam died in this decision block

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1208,1325p;12470,12545p;15659,15756p;19373,19456p'`
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
- updated TP, canon, packet, session, and structure
- deterministic scan proving the live fallback still reaches frozen `decision.py`
- deterministic scan proving the remaining final-ingress families are still live there
- green governance/session checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the future broader replacement scope still cannot make an old authority seam unreachable on the chosen contour, stop and publish `GAP` instead of inventing another seam ladder
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the broader owner-replacement decision and next move
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next runtime block must target broader owner replacement, not a new seam-farming branch

## Rollback
1. Revert this decision TP and the matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime edits hidden inside this decision block
- no claim that another seam died here
- no more targeted seam farming counted as the primary architecture story
- no new helper forest around `reasoning_core` or `decision.py`
- no silent widening into unrelated frozen files

## Risks / blockers
- the broader runtime implementation may still prove that one of the remaining families needs exact frozen work; if so, stop and publish `GAP` instead of silently re-entering seam farming
- the broader bundle must not create another mixed hotspot inside `reasoning_core`
- current historical seam deletions remain valid evidence, but they do not by themselves close owner status

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live `/webhook` ingress still falls through `reasoning_core` into frozen `decision.py`
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial
  - green `L2` is still unproven
  - final acceptance closure is still unproven
- **Why not in this block:**
  - this block only changes trajectory and canon; it does not execute the broader runtime replacement
- **Risk if deferred:**
  - the program can keep producing local seam evidence without ever reaching exclusive owner closure
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md` (to be authored or executed next)
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md` (historical evidence only)
- **Expiry/trigger to stop deferral:**
  - before any new final-ingress micro seam is proposed
  - immediately if the next block stops targeting broader owner replacement

## Next-block contract (mandatory)
- **Next block objective:** implement one broader owner-replacement bundle that wires a non-frozen final-ingress path in `reasoning_core` for the remaining semantic / continuity / boundary families and makes the old `reasoning_core -> decision.py` authority seam transport-only or unreachable on the chosen contour
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|_apply_expected_reply_contract|route_llm_policy_core|handle_policy_timeout_degrade_boundary|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_tool_reply_owner_cutover_payload" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- **Blocked-by conditions:** if the implementation requires a new helper forest, widens beyond the declared broader replacement scope, or still cannot make an old authority seam unreachable, stop and escalate instead of claiming progress
- **Owner role for closure:** `Top Architect`
