# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-POST-IMPLEMENTATION-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one broader fallback-ingress runtime bundle over the surviving `public_entrypoint_contract -> reasoning_core.handle_webhook_payload(...) -> decision_router._handle_webhook_payload(...)` hotspot. This block is admissible only if at least one old live fallback-owned authority seam becomes deleted or unreachable before fallback without a new wrapper/helper and without widening into frozen `booking.py` or `pending.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/public_entrypoint_contract.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/routers/public_entrypoint_contract.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Baseline commands`:
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/routers/public_entrypoint_contract.py | sed -n '1,80p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '7296,7416p;7540,8098p;5327,6075p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
  - `rg -n "handle_public_webhook_payload|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_expected_reply_context_sync_result|build_tool_reply_owner_cutover_payload|build_tool_reply_owner_execution|handle_policy_timeout_degrade_boundary|handle_policy_validation_boundary" truffles-api/app/routers/public_entrypoint_contract.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/services/policy_validation_boundary_service.py`
- `FACT findings`:
  - live fallback still remains explicit at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`, where the broader non-frozen ingress lane still falls into frozen `truffles-api/app/routers/webhook/decision.py:_handle_webhook_payload(...)` at `:8889`.
  - the shared public-entrypoint materialization contract already exists at `truffles-api/app/routers/public_entrypoint_contract.py:29-50`, but runtime handling still delegates into `reasoning_core.handle_webhook_payload(...)`.
  - the broader non-frozen ingress lane already owns payload normalization, secret-preflight bridge reuse, duplicate / tenant / sender prechecks, conversation snapshot loading, semantic override priming, runtime loader override priming, and the current safe direct-owner cutover chain before fallback.
  - the current frozen residual hotspot still includes expected-reply/session-memory fallback at `truffles-api/app/routers/webhook/decision.py:1218-1320`, policy payload normalization / plan extraction at `:12478-12545`, timeout pending-question and active-name time-followup continuity/boundary handling at `:15659-15756`, and the surviving tool-reply / reschedule-guard family at `:19373-19456`.
  - existing downstream owner surfaces already exist in `turn_planner`, `dialog_state_service`, `turn_executor`, `boundary_validator`, `policy_timeout_degrade_boundary_service`, and `policy_validation_boundary_service`; no new owner layer is required by repo truth.
  - frozen `truffles-api/app/routers/webhook/booking.py:2442` remains explicit deferred debt, not the earliest blocker.
- `Detected drift (docs vs code)`:
  - the broader fallback-ingress decision is now the active canon block; runtime work must proceed under this rooted family only and cannot reopen the older fact-guard story.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active fallback-ingress decision; no second query is allowed or needed.
- **Existing solutions found:** extend the new path before fallback, then count progress only when the old fallback-owned authority becomes unreachable on the chosen contour.
- **Decision:** `reuse/integrate`
  - reuse the existing `reasoning_core` ingress lane and downstream owner surfaces
  - do not invent a new ingress compatibility layer or helper forest
- **Rejected options:**
  - second web query
  - another doc-only decision block instead of runtime work
  - new `fallback_ingress_service.py`, `webhook_delegate_service.py`, or similar helper layer

## Root cause (mandatory)
- **Symptom:** owner closure remains partial because active ingress still falls from the non-frozen coordinator into the broader frozen webhook handler.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/reasoning_core.py:7540-8098` and confirm the broader non-frozen ingress lane still falls back at `:8075` and `:8087`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8889-9005` and confirm fallback still enters the full frozen webhook handler.
  3. inspect `truffles-api/app/routers/webhook/decision.py:1218-1320`, `:12478-12545`, `:15659-15756`, and `:19373-19456` and confirm the remaining mixed semantic / continuity / boundary families are still reachable after fallback.
  4. inspect `truffles-api/app/services/reasoning_core.py:5327-6075` and confirm the current safe semantic owner lane already absorbs multiple contours before fallback through existing downstream owner surfaces.
- **Evidence:**
  - explicit `reasoning_core -> decision.py` fallback callsites
  - frozen `_handle_webhook_payload(...)` root still live
  - surviving frozen residual families still reachable after fallback
  - existing non-frozen downstream owner surfaces already present
- **Five Whys (or equivalent):**
  1. Why are owners still partial? Because fallback still reaches frozen `decision.py`.
  2. Why is this still true after the fact-guard deletion? Because the broader ingress lane still stops before the remaining frozen residual families.
  3. Why is another narrow seam block dishonest now? Because the surviving hotspot is the broader fallback path, not an isolated local helper.
  4. Why is a new wrapper/helper forbidden? Because it would re-house the same mixed ingress authority instead of making the old fallback-owned seam unreachable.
  5. Why is this implementation block admissible? Because repo truth already has an existing non-frozen ingress lane and existing downstream owner surfaces that can still bypass at least one old frozen residual family before fallback.
- **Root cause statement:** the current hotspot remains live because `reasoning_core.handle_webhook_payload(...)` still falls through to frozen `_handle_webhook_payload(...)`, even though the non-frozen ingress lane and downstream owner surfaces already exist; the next truthful runtime move is to extend that existing lane so at least one old fallback-owned frozen residual family becomes unreachable before fallback.
- **Fix mechanism:**
  - keep this implementation TP active in canon
  - extend the existing non-frozen ingress owner lane before fallback
  - add focused regression coverage proving the chosen contour no longer reaches frozen `decision.py`
  - stop and publish `GAP` if the chosen contour needs a new helper, frozen `booking.py`/`pending.py`, or cannot delete an old seam

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/public_entrypoint_contract.py`
  - `truffles-api/app/services/reasoning_core.py:handle_webhook_payload(...)`
  - `truffles-api/app/services/reasoning_core.py:_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)`
  - `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`
  - `truffles-api/app/core/turn_planner.py:build_tool_reply_owner_decision(...)`
  - `truffles-api/app/core/dialog_state_service.py:build_tool_reply_owner_state(...)`
  - `truffles-api/app/core/dialog_state_service.py:build_expected_reply_context_sync_result(...)`
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_cutover_payload(...)`
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_execution(...)`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - repo truth already contains the needed owner surfaces; the missing work is cutover wiring before fallback, not a new subsystem.

## Execution profile
- **TP mode:** `implementation`
- **Doc touch budget (files):** `10`
- **Code dominance:** `runtime-heavy`
- **Why this profile fits:** this block is the first runtime bundle over the broader fallback-ingress family and must be accepted only if an old fallback-owned seam actually dies.

## Invariant
- no new wrapper/helper forest
- no second web search
- no silent widening into frozen `truffles-api/app/routers/webhook/booking.py` or `truffles-api/app/routers/webhook/pending.py`
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no runtime edits that only reshuffle the same mixed authority into another hotspot

## Scope
- activate the broader fallback-ingress implementation TP in canon
- extend the existing non-frozen ingress owner lane before fallback
- target at least one old fallback-owned frozen residual family so it becomes deleted or unreachable on the chosen contour
- add focused regression coverage proving the chosen contour bypasses frozen `decision.py`
- sync canon/session artifacts after the runtime result

## Out of scope
- claiming full owner closure
- acceptance / `L2` / proof-path work
- edits to frozen `truffles-api/app/routers/webhook/booking.py`
- edits to frozen `truffles-api/app/routers/webhook/pending.py`
- new web search

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/routers/public_entrypoint_contract.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Plan (1..N)
1. Keep this implementation TP active and synchronized with repo truth.
2. Extend the existing non-frozen ingress owner lane in `reasoning_core` so one admissible broader fallback contour finalizes before `decision_router._handle_webhook_payload(...)`.
3. Add focused regression coverage proving the chosen contour bypasses frozen fallback.
4. Regenerate packet, rerun required checks, and sync truthful runtime-result docs.

## DoD
- the broader fallback-ingress implementation TP exists and is active in canon
- at least one old fallback-owned authority seam from the rooted family becomes deleted or unreachable
- the chosen contour no longer reaches frozen `truffles-api/app/routers/webhook/decision.py` through fallback
- focused runtime checks and required canon/session checks are green
- docs truthfully record which old seam died and which rooted residual families still remain

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/routers/public_entrypoint_contract.py | sed -n '1,80p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '7296,7416p;7540,8098p;5327,6075p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'semantic_tool_reply_pending_question or semantic_service_info_interrupt or semantic_master_override or semantic_duration_service_query or semantic_pricing_service_query or semantic_services_overview_service_query'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'collect_service_info_interrupt_routes_to_catalog_service_query or list_slots_missing_slot_pending_question_preserves_interaction_evidence or tool_reply_without_evidence_clarifies'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply_owner_decision or tool_reply_owner_state or tool_reply_owner_cutover_payload'`
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
- active implementation TP plus synced canon/session artifacts
- runtime diff proving the chosen contour now exits before fallback
- focused regression coverage proving frozen `decision.py` is bypassed on that contour
- green packet / guard / architecture / session checks

## Rollback
1. Revert this implementation TP and matching canon/session updates.
2. Revert any runtime/test changes from the implementation bundle.
3. Regenerate packet and rerun required checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime cutover inside the existing non-frozen ingress lane; no rollout claims.
- **Go/no-go signals:** the chosen contour bypasses frozen fallback in focused coverage and required guard/session checks stay green.
- **Rollback:** revert runtime/test/doc changes, regenerate packet, rerun required checks.
- **Post-release monitoring window:** the next block must either publish a post-implementation audit that proves which old fallback-owned seam died or stop as `GAP`; it must not resume seam farming outside this rooted family.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused runtime tests plus required packet/guard/session checks only.
- **Stop condition:** if the chosen contour cannot delete or bypass an old fallback-owned seam without a new helper, a second web query, or widening into frozen `booking.py` / `pending.py`, stop and publish `GAP`.
- **Escalation path:** `Top Architect`

## No-go
- no new helper/wrapper layer around `reasoning_core` or `decision.py`
- no broadened edit into frozen `truffles-api/app/routers/webhook/decision.py` counted as this block's primary progress path
- no widening into frozen `truffles-api/app/routers/webhook/booking.py` or `truffles-api/app/routers/webhook/pending.py`
- no claim that progress happened if the old fallback-owned seam still lives on the chosen contour
- no acceptance or proof-path reruns in this block

## Risks / blockers
- the chosen contour may still depend on trace/state mutations that only exist after fallback enters frozen `decision.py`; if so, stop and publish `GAP`.
- the chosen contour may require multiple residual families to move together; if that widens beyond this rooted family or needs frozen `booking.py` / `pending.py`, stop and publish `GAP`.
- the broader implementation must not create another mixed hotspot inside `reasoning_core`.

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
- **Why not in this block:** this bundle can only count truthful progress when one old fallback-owned seam actually dies; full closure of every residual family is not yet proven.
- **Risk if deferred:** owners remain partial while live ingress still reaches frozen mixed authority.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
- **Expiry/trigger to stop deferral:** stop if runtime work on this bundle cannot delete an old seam from the rooted family without helper growth or frozen downstream widening.

## Next-block contract (mandatory)
- **Next block objective:** publish the post-implementation audit that proves which old fallback-owned seam died, which rooted residual families still remain, and whether a further broader fallback move is admissible or blocked.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:**
  - no old fallback-owned seam dies or becomes unreachable on the chosen contour
  - need for a new wrapper/helper
  - need to widen beyond the declared broader fallback-ingress family
  - need to reopen frozen `booking.py`, frozen `pending.py`, proof-path, or acceptance work
  - need for a second web query
- **Owner role for closure:** `Top Architect`
