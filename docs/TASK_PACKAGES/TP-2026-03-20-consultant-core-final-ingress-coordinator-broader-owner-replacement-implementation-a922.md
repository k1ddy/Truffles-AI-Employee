# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-NEXT-RESIDUAL-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the broader owner-replacement bundle for the remaining final-ingress hotspot by extending the non-frozen `reasoning_core` owner lane before fallback. This block is admissible only if at least one old live authority seam becomes deleted or unreachable from the remaining `reasoning_core -> decision.py` final-ingress path without a new helper forest and without reopening unrelated frozen families.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Baseline commands`:
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '5538,6075p;7988,8020p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
  - `rg -n "build_tool_reply_owner_decision|build_tool_reply_owner_state|build_tool_reply_owner_cutover_payload|build_expected_reply_context_sync_result|handle_policy_timeout_degrade_boundary" truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `FACT findings`:
  - live fallback still remains explicit in `truffles-api/app/services/reasoning_core.py:8001` and `:8013`.
  - the remaining final-ingress hotspot is still rooted at `truffles-api/app/routers/webhook/decision.py:1218-1320`, `:12478-12545`, `:15659-15756`, and `:19373-19456`.
  - existing non-frozen owner surfaces already cover the current tool-reply semantic / dialog-state / artifact contract pieces through `TurnPlanner`, `DialogStateService`, `TurnExecutor`, and `_finalize_turn_planner_owner_cutover(...)`.
  - the broader owner lane now already absorbs the safe pending-question `calendar.list_slots` contour, the active-time service-info interrupt contour, the explicit master-override service-query contour, the safe non-booking semantic pricing and duration service-query contours, and the safe non-booking semantic services-overview service-query contour before fallback, while the remaining hotspot still sits in the declared residual families.
- `Detected drift (docs vs code)`:
  - canon and session summaries must stay synchronized as each broader-owner slice lands; stale fallback line refs or slice counts are not admissible repo truth.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent broader-owner-replacement decision block; no second query is allowed or needed
- **Existing solutions found:**
  - move a broader live authority slice onto the new owner path first, then contract legacy fallback only when the old slice actually becomes unreachable
- **Decision:** `reuse/integrate`
  - reuse the existing `reasoning_core` direct-owner lane and the existing `TurnPlanner` / `DialogStateService` / `TurnExecutor` contracts
  - do not invent a new ingress compatibility layer or helper forest
- **Rejected options:**
  - second web query
  - new wrapper/helper around frozen `decision.py`
  - widening into unrelated `booking.py`, `pending.py`, proof-path, or acceptance work

## Root cause (mandatory)
- **Symptom:** the new architecture exists, but the remaining final-ingress families still stay live because the last broader fallback seam still reaches frozen `decision.py`.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/reasoning_core.py:8001` and `:8013` and confirm fallback still enters frozen `decision.py`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:19373-19456` and confirm frozen `decision.py` still owns direct tool-reply decision/state/payload/finalizer authority on the surviving tool-reply contour.
  3. Inspect `truffles-api/app/services/reasoning_core.py:5538-6075` and confirm the non-frozen semantic-arbitration owner lane already absorbs the landed safe contours but still stops short of the remaining residual hotspot.
- **Evidence:**
  - explicit `reasoning_core -> decision.py` fallback
  - surviving frozen tool-reply finalizer contour
  - existing non-frozen owner surfaces already in repo truth
- **Five Whys (or equivalent):**
  1. Why are owners still partial? Because fallback still reaches frozen `decision.py`.
  2. Why does that still happen after previous seam deletions? Because those cuts removed local authority shards, not the broader fallback slice.
  3. Why is the broader slice still live? Because `reasoning_core` still stops before the surviving tool-reply contour.
  4. Why can the broader bundle continue through additional safe semantic service-query contours? Because those contours already reuse the current owner surfaces and can finalize before fallback without reopening the broader frozen extraction families.
  5. Why is that admissible? Because each such cut deletes a live fallback-owned authority seam from the broader hotspot instead of farming another frozen micro-cut.
- **Root cause statement:** the current hotspot remains live because the broader `reasoning_core` owner lane does not yet absorb the surviving safe semantic tool-reply contour, even though all required semantic / dialog-state / artifact owner surfaces already exist outside frozen `decision.py`.
- **Fix mechanism:**
  - continue the broader implementation TP
  - extend `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)` to absorb additional safe semantic service-query / tool-reply contours before fallback
  - prove each old frozen fallback-owned seam becomes bypassed from `reasoning_core`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py:_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)`
  - `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`
  - `truffles-api/app/core/turn_planner.py:build_tool_reply_owner_decision(...)`
  - `truffles-api/app/core/dialog_state_service.py:build_tool_reply_owner_state(...)`
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_cutover_payload(...)`
  - `truffles-api/app/services/booking_transition_owner.py:apply_tool_transition_owner(...)`
  - `truffles-api/app/services/expected_reply_contract.py:resolve_tool_expected_reply_contract(...)`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the owner contracts already exist; the missing work is cutover wiring, not a new semantic or continuity subsystem

## Execution profile
- **TP mode:** `implementation`
- **Doc touch budget (files):** `10`
- **Code dominance:** `runtime-heavy`
- **Override token:** `final-ingress-coordinator-broader-owner-replacement-implementation`
- **Why this profile fits:** this block executes the broader owner replacement by extending the non-frozen owner lane before the remaining fallback seam.

## Invariant
- no new wrapper/helper forest
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is `done`
- no claim that green `L2` or final acceptance closure is proven
- no widening into unrelated `decision.py` families beyond the declared broader-owner bundle
- no reopening `booking.py`, `pending.py`, proof-path, or acceptance work in this block

## Scope
- activate the broader owner-replacement implementation block in canon
- extend the `reasoning_core` semantic-arbitration owner lane before fallback
- continue targeting the surviving safe service-query / tool-reply contours that can still finalize before fallback without widening beyond the declared broader-owner hotspot
- prove at least one old live authority seam becomes deleted or unreachable from `reasoning_core`
- sync canon/session/packet/result docs after the runtime change

## Out of scope
- claiming full owner closure
- acceptance / `L2` / multi-pack proof work
- unrelated frozen `decision.py` families outside the declared remaining hotspot
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Plan (1..N)
1. Keep this implementation TP active and synchronized with repo truth as broader-owner slices land.
2. Continue extending the non-frozen semantic-arbitration owner lane in `reasoning_core` so additional safe service-query / tool-reply contours finalize before fallback.
3. Add focused regression coverage proving each added safe owner path bypasses frozen `decision.py` for its contour.
4. Regenerate packet, rerun required checks, and sync truthful result docs after each admissible slice.

## DoD
- the broader owner-replacement implementation TP exists and is active in canon
- at least one old authority seam from the broader final-ingress hotspot becomes deleted or unreachable
- the surviving `reasoning_core -> decision.py` fallback no longer owns the implemented contour
- required focused runtime checks and required canon/session checks are green
- docs truthfully record what seam died and what residual families still remain

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '5538,6075p;7988,8020p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
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
- broader implementation TP and canon/session sync
- runtime diff in `reasoning_core.py`
- focused regression coverage proving the implemented contour bypasses frozen fallback
- green guard / packet / architecture / session checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused runtime tests plus required guard/session checks only
- **Stop condition:** if the broader `reasoning_core` slice still cannot delete or bypass an old live authority seam on the chosen contour without new helper growth, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime cutover inside the non-frozen owner lane; no rollout claims
- **Go/no-go signals:** the chosen safe contour bypasses frozen fallback in focused regression coverage and required guard/session checks stay green
- **Rollback:** revert the `reasoning_core` / test / doc changes, regenerate packet, rerun required checks
- **Post-release monitoring window:** the next block must either delete another old broader-hotspot seam or publish `GAP`; it must not resume seam farming inside frozen `decision.py`

## Rollback
- revert `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
- revert canon/session/doc sync files
- revert `truffles-api/app/services/reasoning_core.py` and focused tests
- rerun packet / architecture / session checks

## No-go
- no new helper/wrapper layer around frozen ingress
- no broadened edit into `truffles-api/app/routers/webhook/decision.py`
- no claim that the broader owner-replacement bundle is complete if the old seam still lives
- no acceptance/proof reruns in this block

## Risks / blockers
- the next chosen safe contour may still depend on trace/meta state that only exists after frozen `decision.py` mutation; if so, stop and publish `GAP`
- if the direct owner path needs timeout / expected-reply / rescue families to move together, stop and publish `GAP` instead of widening silently

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - any untouched subset of `truffles-api/app/routers/webhook/decision.py:19373-19456`
- **Why not in this block:**
  - six bounded broader-owner slices are now landed, but finishing the entire hotspot in one step is still not yet proven
- **Risk if deferred:**
  - owners remain partial while fallback still carries remaining authority
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next broader-owner slice fails to delete an old seam, stop and escalate rather than continuing partial contractions

## Next-block contract (mandatory)
- **Next block objective:**
  - delete or bypass the next remaining broader final-ingress authority seam after the six landed slices, starting with the strongest residual inside `decision.py:19373-19456` if it can be cut without helper growth, or publish `GAP`
- **First deterministic check command:**
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py && nl -ba truffles-api/app/services/reasoning_core.py | sed -n '5538,5635p;7988,8020p' && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1218,1320p;12478,12545p;15659,15756p;19373,19456p'`
- **Blocked-by conditions:**
  - need for a new wrapper/helper
  - need to widen beyond the declared broader-owner hotspot
  - need to reopen `booking.py`, `pending.py`, proof-path, or acceptance work
- **Owner role for closure:** `Top Architect`
