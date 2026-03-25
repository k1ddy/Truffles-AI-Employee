# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-POST-WAIVER-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one broader fallback-ingress family decision after the post-waiver audit proved the surviving fact-guard callback is thin-only. This block must define the exact rooted `public_entrypoint_contract -> reasoning_core.handle_webhook_payload(...) -> decision_router._handle_webhook_payload(...)` family, lock the admissible owner destinations, keep deferred frozen debt explicit, and reject any next move that would hide the same mixed ingress authority inside a new wrapper/helper.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/routers/public_entrypoint_contract.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
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
  - `nl -ba truffles-api/app/routers/public_entrypoint_contract.py | sed -n '1,80p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '7296,7416p;7540,8098p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
  - `rg -n "handle_public_webhook_payload|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_expected_reply_context_sync_result|build_tool_reply_owner_cutover_payload|build_tool_reply_owner_execution|handle_policy_timeout_degrade_boundary|handle_policy_validation_boundary" truffles-api/app/routers/public_entrypoint_contract.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/services/policy_validation_boundary_service.py`
- `FACT findings`:
  - live fallback still remains explicit at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`, where `reasoning_core.handle_webhook_payload(...)` falls into frozen `truffles-api/app/routers/webhook/decision.py:_handle_webhook_payload(...)` at `:8889`.
  - the public entrypoint materialization contract already lives in non-frozen `truffles-api/app/routers/public_entrypoint_contract.py:29-50`, but it still delegates runtime processing into `reasoning_core.handle_webhook_payload(...)`.
  - the non-frozen ingress lane already owns payload normalization, secret-preflight bridge reuse, duplicate / tenant / sender prechecks, conversation snapshot loading, semantic override priming, runtime loader override priming, and the current safe direct-owner cutover chain before fallback.
  - once fallback enters frozen `decision.py`, the remaining live mixed residual families still include expected-reply/session-memory fallback at `truffles-api/app/routers/webhook/decision.py:1218-1320`, policy payload normalization / plan extraction at `:12478-12545`, timeout pending-question and active-name time-followup continuity/boundary handling at `:15659-15756`, and the surviving tool-reply / reschedule-guard family at `:19373-19456`.
  - existing non-frozen owner destinations already exist in `truffles-api/app/core/turn_planner.py:178`, `truffles-api/app/core/dialog_state_service.py:372`, `truffles-api/app/core/dialog_state_service.py:872`, `truffles-api/app/core/turn_executor.py:499`, `truffles-api/app/core/turn_executor.py:629`, `truffles-api/app/services/policy_timeout_degrade_boundary_service.py:102`, and `truffles-api/app/services/policy_validation_boundary_service.py:191`.
  - frozen `truffles-api/app/routers/webhook/booking.py:2442` remains explicit deferred debt, not the earliest blocker, because the live fallback reaches frozen `decision.py` first.
- `INFERENCE to verify in this block`:
  - continuing fact-guard work would now be fake progress; the next truthful move is a broader fallback-ingress family decision that treats `reasoning_core -> decision.py` as the surviving live mixed hotspot.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the parent fallback/fact-guard chain; no second query is allowed or needed.
- **Existing solutions found:** once the old local seam is dead, switch to the next broader live hotspot, define the rooted family explicitly, then continue only on a path that can make that old hotspot unreachable.
- **Decision:** `reuse/integrate`
  - reuse the existing public-entrypoint contract, `reasoning_core` owner lane, and downstream owner surfaces instead of inventing another ingress layer
  - publish an explicit broader fallback-ingress decision before any more runtime work
- **Rejected options:**
  - second web query
  - resuming fact-guard runtime edits
  - a new `fallback_ingress_service.py` or similar wrapper as a way around the mixed hotspot

## Root cause (mandatory)
- **Symptom:** the fact-guard family is no longer the live hotspot, but owners still remain partial because active ingress still falls from `reasoning_core` into the broader frozen webhook handler.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/public_entrypoint_contract.py:29-50` and confirm public entrypoints still delegate into `reasoning_core.handle_webhook_payload(...)`.
  2. inspect `truffles-api/app/services/reasoning_core.py:7540-8098` and confirm the non-frozen ingress lane still falls back at `:8075` and `:8087` into `decision_router._handle_webhook_payload(...)`.
  3. inspect `truffles-api/app/routers/webhook/decision.py:8889-9005` and confirm fallback still enters the full frozen webhook handler.
  4. inspect `truffles-api/app/routers/webhook/decision.py:1218-1320`, `:12478-12545`, `:15659-15756`, and `:19373-19456` and confirm the remaining mixed semantic / continuity / boundary families are still reachable only after that fallback.
  5. inspect the existing owner surfaces in `turn_planner`, `dialog_state_service`, `turn_executor`, `policy_timeout_degrade_boundary_service`, and `policy_validation_boundary_service` and confirm the downstream destinations already exist outside frozen `decision.py`.
- **Evidence:**
  - explicit `reasoning_core -> decision.py` fallback callsites
  - frozen `_handle_webhook_payload(...)` root still live
  - surviving mixed residual families inside frozen `decision.py`
  - existing non-frozen owner surfaces already materialized downstream
- **Five Whys (or equivalent):**
  1. Why are owners still partial after the fact-guard deletion? Because live ingress still reaches frozen `decision.py`.
  2. Why is the surviving hotspot broader than fact-guard? Because fallback enters the whole webhook handler, not just the thin fact-guard callback.
  3. Why is another narrow seam block dishonest now? Because it would measure local residue while ignoring the broader live ingress path.
  4. Why is a new helper/wrapper forbidden? Because it would re-house the same mixed ingress authority instead of making the old fallback unreachable.
  5. Why is a broader fallback-ingress decision the honest next step? Because repo truth already has enough evidence to define the family, lock the owner destinations, and reject invalid widening before runtime resumes.
- **Root cause statement:** the targeted fact-guard cut truthfully killed the old mixed fact-guard body, but active `/webhook` traffic still falls from the existing non-frozen `reasoning_core` ingress lane into the broader frozen `_handle_webhook_payload(...)` handler, so owner closure remains partial until a broader fallback-ingress move makes at least one of the remaining frozen residual families unreachable before fallback.
- **Fix mechanism:**
  - publish one broader fallback-ingress family decision block
  - lock the only admissible owner destinations to existing repo surfaces
  - keep `booking.py` as deferred debt unless a later block proves fallback bypass cannot preserve correctness without widening
  - reject any next move that needs a new wrapper/helper or reopens unrelated families

## Exact rooted broader fallback-ingress family
- `truffles-api/app/routers/public_entrypoint_contract.py:29-50` — public entrypoint materialization contract that still delegates runtime handling into `reasoning_core.handle_webhook_payload(...)`.
- `truffles-api/app/services/reasoning_core.py:7296-7416` — non-frozen payload normalization and secret-preflight bridge reuse ahead of the main ingress lane.
- `truffles-api/app/services/reasoning_core.py:7420-7523` — non-frozen runtime override priming for capabilities, truth, intent primitives, domain routing, controller routing, and policy-core routing.
- `truffles-api/app/services/reasoning_core.py:7540-8098` — broader ingress coordinator with prechecks, snapshot loading, semantic-owner cutovers, and the live fallback boundary.
- `truffles-api/app/services/reasoning_core.py:8075-8087` — exact surviving fallback seam into frozen `decision.py`.
- `truffles-api/app/routers/webhook/decision.py:8889-9005` — frozen webhook handler root reached by fallback.
- `truffles-api/app/routers/webhook/decision.py:1218-1320` — expected-reply/session-memory fallback continuity family still reachable after fallback.
- `truffles-api/app/routers/webhook/decision.py:12478-12545` — policy payload normalization / plan extraction / boundary projection family still reachable after fallback.
- `truffles-api/app/routers/webhook/decision.py:15659-15756` — timeout pending-question / active-name time-followup continuity-boundary family still reachable after fallback.
- `truffles-api/app/routers/webhook/decision.py:19373-19456` — surviving tool-reply / reschedule-guard family still reachable after fallback.

## Admissible owner destinations
- `truffles-api/app/routers/public_entrypoint_contract.py:29-50`
  - admissible only for the shared public-entrypoint response materialization contract; it is not the new mixed ingress owner.
- `truffles-api/app/services/reasoning_core.py:7540-8073`
  - admissible as the only broader ingress coordinator extension point before fallback.
- `truffles-api/app/core/turn_planner.py:178`
  - admissible only for typed tool-reply / policy decision construction.
- `truffles-api/app/core/dialog_state_service.py:372`
  - admissible only for typed tool-reply continuity state construction.
- `truffles-api/app/core/dialog_state_service.py:872`
  - admissible only for expected-reply/session-memory state-sync results.
- `truffles-api/app/core/turn_executor.py:499`
  - admissible only for typed owner cutover payload materialization.
- `truffles-api/app/core/turn_executor.py:629`
  - admissible only for the reusable owner-execution surface already in repo truth.
- `truffles-api/app/core/boundary_validator.py:40`
  - admissible only for typed boundary override/result contracts, not as a new ingress coordinator.
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py:102`
  - admissible only for timeout degrade / pending-question boundary orchestration already moved out of frozen `decision.py`.
- `truffles-api/app/services/policy_validation_boundary_service.py:191`
  - admissible only for validation/fact-guard boundary orchestration already moved out of frozen `decision.py`.
- **Explicitly not admissible:**
  - any new `fallback_ingress_service.py`, `webhook_delegate_service.py`, or similar wrapper/helper
  - moving the mixed `_handle_webhook_payload(...)` body wholesale into a new non-frozen hotspot
  - widening into frozen `truffles-api/app/routers/webhook/booking.py` or `truffles-api/app/routers/webhook/pending.py`
  - reopening proof-path, acceptance, or unrelated timeout/continuity families as a way around the fallback decision

## Frozen booking.py decision
- `truffles-api/app/routers/webhook/booking.py:2442` stays **explicit deferred debt** for the immediate next runtime block.
- Reason: current repo truth shows the earliest live blocker is the broader fallback into frozen `decision.py`; `booking.py` is only a downstream deferred consumer of the thin fact-guard callback.
- If the next runtime block proves `booking.py` must be edited to preserve correctness or kill an old fallback seam, stop and publish a new explicit waiver/decision block instead of widening silently.

## FACT vs INFERENCE verdict
- **FACT:** this block is doc-only; no old authority seam is deleted or made unreachable here.
- **FACT:** the surviving live mixed hotspot is now the broader fallback ingress rooted at `reasoning_core.handle_webhook_payload(...) -> decision_router._handle_webhook_payload(...)`.
- **FACT:** the remaining live residual families after fallback are still `decision.py:1218-1320`, `decision.py:12478-12545`, `decision.py:15659-15756`, and `decision.py:19373-19456`.
- **FACT:** existing admissible downstream owner surfaces already exist in non-frozen code.
- **FACT:** frozen `booking.py:2442` remains deferred debt, not the earliest blocker.
- **INFERENCE:** the next admissible move is one broader fallback-ingress implementation bundle that extends the existing non-frozen ingress owner lane and makes at least one old frozen residual family unreachable before fallback; if that cannot be done without helper growth or widening beyond this rooted family, stop and publish `GAP`.
- **Decision:** switch canon to this broader fallback-ingress family decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/public_entrypoint_contract.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - existing packet / arch / session guard flow
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the missing work is not another owner surface; it is making the remaining live fallback stop reaching frozen mixed authority.

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-heavy`
- **Why this profile fits:** this block defines the broader fallback-ingress family and the next admissible move without claiming runtime deletion.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no second web search
- no wrapper/helper growth counted as progress
- no silent widening into frozen `booking.py` or `pending.py`
- answer to `какой old authority seam стал deleted или unreachable после этого блока?` remains `никакой`

## Scope
- define the exact rooted broader fallback-ingress family
- define the admissible owner destinations for that family
- decide the immediate status of frozen `booking.py`
- switch canon/session artifacts to this decision block

## Out of scope
- runtime implementation in this block
- edits to `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- acceptance / `L2` / proof-path work
- any new web search
- claiming runtime seam deletion in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
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
1. Publish this broader fallback-ingress family decision TP with RCA and the exact rooted family map.
2. Lock the only admissible owner destinations to existing repo surfaces.
3. Keep frozen `booking.py:2442` explicit deferred debt for the immediate next runtime block.
4. Switch canon/session artifacts to this decision block.
5. Regenerate packet and rerun governance/session checks.

## DoD
- the broader fallback-ingress family decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
- canon / packet / architecture test all agree this is the active block
- the exact rooted fallback family and admissible owner destinations are explicit in repo truth
- frozen `booking.py` status is explicit rather than implicit
- the block states explicitly that seam-deletion count here is zero

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/routers/public_entrypoint_contract.py | sed -n '1,80p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '7296,7416p;7540,8098p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
- `rg -n "handle_public_webhook_payload|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_expected_reply_context_sync_result|build_tool_reply_owner_cutover_payload|build_tool_reply_owner_execution|handle_policy_timeout_degrade_boundary|handle_policy_validation_boundary" truffles-api/app/routers/public_entrypoint_contract.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/services/policy_validation_boundary_service.py`
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
- updated TP, canon, packet, session, and structure artifacts
- deterministic scan proving live ingress still falls from `reasoning_core` into frozen `decision.py`
- deterministic scan proving the remaining live residual families after fallback
- green governance/session checks after the doc sync

## Rollback
1. Revert this decision TP and matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only broader fallback-ingress decision; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the active decision block and the next move.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either implement the broader fallback-ingress family bundle or stop as `GAP`; it must not resume fact-guard seam farming or invent a new ingress wrapper.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic doc / governance checks only.
- **Stop condition:** if the next runtime bundle needs a new wrapper/helper, needs to widen beyond the rooted fallback family, needs to reopen frozen `booking.py` / `pending.py`, or cannot prove an old seam dies, stop and publish `GAP`.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits hidden inside this decision block
- no claim that another seam died here
- no second web search
- no new helper forest around `reasoning_core` or `decision.py`
- no silent widening into unrelated frozen files

## Risks / blockers
- the next broader runtime implementation may still prove that one of the surviving residual families needs an explicit frozen waiver; if so, stop and publish `GAP` instead of widening silently.
- the broader implementation must not create another mixed hotspot inside `reasoning_core`.
- current seam deletions remain valid evidence, but they do not by themselves close owner status while fallback still remains live.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/public_entrypoint_contract.py:29-50`
  - `truffles-api/app/services/reasoning_core.py:7296-7416`
  - `truffles-api/app/services/reasoning_core.py:7420-7523`
  - `truffles-api/app/services/reasoning_core.py:7540-8098`
  - `truffles-api/app/routers/webhook/decision.py:8889-9005`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `truffles-api/app/routers/webhook/decision.py:19373-19456`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `semantic_owner` remains partial
  - `continuity_owner` remains partial
  - `boundary_owner` remains partial
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:** this block is decision-only and cannot truthfully claim runtime deletion.
- **Risk if deferred:** continuing runtime work without this decision would mislabel the broader live fallback hotspot as another narrow seam story and could reopen frozen debt silently.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
- **Expiry/trigger to stop deferral:** stop if the next runtime block needs a new ingress wrapper/helper, widens into frozen `booking.py`/`pending.py`, or fails to delete or bypass an old seam from this rooted family.

## Next-block contract (mandatory)
- **Next block objective:** implement one broader fallback-ingress bundle that extends the existing non-frozen ingress owner lane and makes at least one old frozen residual family unreachable before fallback.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:**
  - need for a new wrapper/helper
  - need to widen beyond the declared fallback-ingress family
  - need to reopen frozen `booking.py`, frozen `pending.py`, proof-path, or acceptance work
  - need for a second web query
  - inability to prove that an old authority seam dies or becomes unreachable on the chosen contour
- **Owner role for closure:** `Top Architect`
