# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-POST-IMPLEMENTATION-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the post-implementation truth audit for the broader fallback-ingress family after the latest admissible runtime cut. This block must record which old fallback-owned contour actually died, which broader fallback residual families still remain live, and whether runtime work can continue under the same rooted family without widening or wrapper growth.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before audit closure)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
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
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '634,706p;4634,4688p;8250,8270p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19481p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '347,384p;5882,6015p;10781,10904p'`
- `FACT findings`:
  - the latest runtime block truthfully killed one old fallback-owned contour: the mixed `session_memory_expected_reply_fallback` authority at `truffles-api/app/routers/webhook/decision.py:1243-1288` is now unreachable on the active-booking short booking-reply path because active ingress restores the session-memory expected reply earlier through `truffles-api/app/services/reasoning_core.py:634-704` and then exits through the existing booking-prompt owner lane at `truffles-api/app/services/reasoning_core.py:4634-4811`.
  - the regression evidence at `truffles-api/tests/test_reasoning_core.py:347-384` and `truffles-api/tests/test_reasoning_core.py:10781-10904` proves that contour no longer reaches `decision_router._handle_webhook_payload(...)` and instead finalizes through the non-frozen owner lane before fallback.
  - `truffles-api/tests/test_reasoning_core.py:5882-6015` now isolates the owner-local richer-envelope boundary and proves the new cut stays bounded: direct booking requests are excluded from `expected_reply_shortcircuit` at `truffles-api/app/services/reasoning_core.py:4640-4666`, so broader generic/richer collect contours are not silently swallowed by the new short-reply restore.
  - deterministic follow-up audit proves the explicit-human-request bypass subcontour inside the same old `expected_reply_contract` family is already unreachable on the bounded human-request path: the frozen branch at `truffles-api/app/routers/webhook/decision.py:1306-1359` is preempted by `detect_policy_core_route_snapshot(...)` in `truffles-api/app/core/intent_routing.py:284-338` plus the existing explicit-handoff owner lane at `truffles-api/app/services/reasoning_core.py:12114-12125` and `truffles-api/app/services/reasoning_core.py:2919-3170`, and focused regression evidence stands at `truffles-api/tests/test_reasoning_core.py:1550-1688` and `truffles-api/tests/test_reasoning_core.py:1700-1837`.
  - deterministic follow-up audit proves the booking-verification bypass subcontour inside that same old family is already unreachable on bounded collect-reference paths: the frozen branch at `truffles-api/app/routers/webhook/decision.py:1362-1418` is preempted by `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:8681-8900`, and focused regression evidence stands at `truffles-api/tests/test_reasoning_core.py:7221-7380` and `truffles-api/tests/test_reasoning_core.py:7381-7510`.
  - the surviving live authority inside the older `decision.py:1218-1875` expected-reply family is therefore no longer the already-dead subcontours at `:1243-1288`, `:1306-1359`, or `:1362-1418`; it is concentrated in the remaining interpreter / slot-validation body at `truffles-api/app/routers/webhook/decision.py:1419-1875`.
  - the earlier broader fallback-ingress cuts that killed `timeout_degraded_collect_reschedule_handoff` at `truffles-api/app/routers/webhook/decision.py:15725-15743` and `policy_reschedule_guard_handoff` at `truffles-api/app/routers/webhook/decision.py:19385-19481` remain landed evidence, but they are not the seam deleted by this doc-only block.
  - one speculative timeout pending-slot-question cut was intentionally reverted during follow-up inspection because the tested bounded path still exited earlier through the existing booking-prompt owner lane, so this audit does not count any new runtime seam deletion beyond the already-landed contours above.
  - this latest deletion is contour-bounded; it does not claim the whole `decision.py:1218-1320` family is gone.
  - live broader fallback ingress still remains at `truffles-api/app/services/reasoning_core.py:8254` and `:8266`, where traffic still falls into frozen `truffles-api/app/routers/webhook/decision.py:8889` when no earlier owner lane resolves the turn.
  - surviving rooted residual families still remain at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`.
  - frozen `truffles-api/app/routers/webhook/booking.py:2442` remains explicit deferred debt, not the earliest blocker, because live fallback still sits earlier in `reasoning_core`.
  - existing downstream owner destinations remain the same non-frozen surfaces already locked in the broader fallback-ingress decision and implementation TPs; no new owner layer is justified by repo truth.
- `INFERENCE to verify in this block`:
  - the broader fallback-ingress family remains admissible for another runtime move inside the same rooted family, but this audit must prevent over-claiming closure from the bounded `session_memory_expected_reply_fallback` contour deletion.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active broader fallback-ingress implementation; no second query is allowed or needed.
- **Existing solutions found:** after each bounded runtime cut, publish one audit that confirms the old contour really died and only then continue within the same rooted family.
- **Decision:** `reuse/integrate`
  - reuse the existing `reasoning_core` owner lane and the already-landed regression evidence
  - do not create a new ingress helper or a new runtime layer
- **Rejected options:**
  - second web query
  - runtime edits in this audit block
  - new wrapper/helper around `reasoning_core` fallback

## Root cause (mandatory)
- **Symptom:** one broader fallback-ingress contour has died, but the family still has live fallback entry and multiple rooted residual families; without audit, the program could overstate closure or resume seam farming blindly.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/reasoning_core.py:634-704` and confirm the active conversation snapshot now restores a bounded session-memory expected reply for short booking replies before fallback.
  2. inspect `truffles-api/app/services/reasoning_core.py:4634-4811` and confirm the existing booking-prompt owner lane finalizes that bounded reply contour without delegating into frozen `decision.py`.
  3. inspect `truffles-api/app/services/reasoning_core.py:4640-4666` and confirm direct booking requests are explicitly excluded from the new `expected_reply_shortcircuit`, so broader generic/richer collect contours remain outside the deleted seam.
  4. inspect `truffles-api/app/core/intent_routing.py:284-338` plus `truffles-api/app/services/reasoning_core.py:12114-12125` and `:2919-3170` and confirm explicit human-request turns are intercepted before the frozen bypass branch at `truffles-api/app/routers/webhook/decision.py:1306-1359`.
  5. inspect `truffles-api/app/services/reasoning_core.py:8681-8900` and confirm booking-verification collect-reference turns are intercepted before the frozen bypass branch at `truffles-api/app/routers/webhook/decision.py:1362-1418`.
  6. inspect `truffles-api/app/services/reasoning_core.py:8254-8266` and confirm live fallback still enters frozen `decision.py` when no earlier owner lane resolves the turn.
  7. inspect `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481` and confirm broader residual families still remain live after fallback.
- **Evidence:**
  - earlier owner exit in `reasoning_core`
  - deterministic early explicit-handoff interception for human-request turns
  - deterministic early `check_booking_prompt` interception for bounded booking-verification turns
  - surviving fallback callsites into frozen `decision.py`
  - surviving rooted residual families after fallback
  - focused regression proving the exact deleted contour no longer reaches the frozen delegate
- **Five Whys (or equivalent):**
  1. Why is another immediate runtime claim risky? Because only one bounded contour has died since the last audit sync.
  2. Why is that insufficient for closure? Because broader fallback still remains and multiple rooted residual families still sit behind it.
  3. Why is a doc-only audit required now? Because the program must record the exact seam deletion count for this runtime block before continuing.
  4. Why is helper growth forbidden here? Because it would only relocate the same fallback authority instead of deleting another old seam.
  5. Why can runtime still continue after this audit? Because the rooted broader fallback-ingress family and admissible owner destinations remain unchanged.
- **Root cause statement:** the latest broader fallback-ingress runtime cut truthfully deleted one old contour, but the broader family is still live through `reasoning_core -> decision_router._handle_webhook_payload(...)`; the next truthful move depends on auditing that partial result before resuming runtime work.
- **Fix mechanism:**
  - publish this post-implementation audit as a doc-only block
  - record which adjacent subcontours inside the older expected-reply family are already dead on bounded paths so the next runtime move does not re-target them
  - keep the seam-deletion count in this audit at zero
  - lock the next non-negotiable move back to the existing broader fallback-ingress implementation bundle only if the broader family remains admissible without widening

## Old authority seams under audit (mandatory)
- **FACT:** the old mixed `session_memory_expected_reply_fallback` contour in `truffles-api/app/routers/webhook/decision.py:1243-1288` is already dead on the active-booking short booking-reply path and therefore is not the next live seam.
- **FACT:** the old explicit-human-request bypass contour in `truffles-api/app/routers/webhook/decision.py:1306-1359` is already unreachable on the bounded explicit-human-request path because active ingress now exits earlier through `detect_policy_core_route_snapshot(...)` plus the existing explicit-handoff owner lane in `truffles-api/app/services/reasoning_core.py`.
- **FACT:** the old booking-verification bypass contour in `truffles-api/app/routers/webhook/decision.py:1362-1418` is already unreachable on bounded booking-verification collect-reference paths because active ingress now exits earlier through `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py`.
- **FACT:** the older mixed `timeout_degraded_collect_reschedule_handoff` contour in `truffles-api/app/routers/webhook/decision.py:15725-15743` and `policy_reschedule_guard_handoff` in `truffles-api/app/routers/webhook/decision.py:19385-19481` remain landed evidence, not the seam deleted by this doc-only block.
- **FACT:** live broader fallback ingress still remains at `truffles-api/app/services/reasoning_core.py:8254-8266` into frozen `truffles-api/app/routers/webhook/decision.py:8889`.
- **FACT:** surviving rooted residual families still remain at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`.
- **FACT:** frozen `truffles-api/app/routers/webhook/booking.py:2442` remains deferred debt, not the earliest blocker.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py:_build_conversation_snapshot(...)`
  - `truffles-api/app/services/reasoning_core.py:_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`
  - existing broader fallback-ingress owner destinations in `truffles-api/app/core/turn_planner.py`, `truffles-api/app/core/dialog_state_service.py`, `truffles-api/app/core/turn_executor.py`, `truffles-api/app/core/boundary_validator.py`, `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`, and `truffles-api/app/services/policy_validation_boundary_service.py`
  - existing regression evidence in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_message_endpoint.py`, and `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the repo already contains the rooted family map, the owner destinations, and the exact runtime evidence needed for the audit.

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-only`
- **Why this profile fits:** this block records the result of the latest broader fallback-ingress runtime cut and locks the next move without changing runtime code.

## Invariant
- no runtime edits in this block
- no claim that another old authority seam dies in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is fully closed
- no widening into frozen `truffles-api/app/routers/webhook/booking.py` or `truffles-api/app/routers/webhook/pending.py`
- no second web search

## Scope
- record the exact contour that died in the latest implementation block
- classify the surviving broader fallback-ingress residual families
- switch canon/session artifacts to this post-implementation audit block
- lock whether runtime work can continue under the same broader fallback-ingress family

## Out of scope
- runtime edits in `reasoning_core.py`, `decision.py`, `booking.py`, or `pending.py`
- new helper/wrapper creation
- acceptance or `L2` work
- any second web search

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
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
1. Run the deterministic post-implementation audit checks.
2. Record the exact contour that died in the latest broader fallback-ingress runtime cut.
3. Classify the surviving rooted residual families and whether the broader family remains admissible.
4. Switch canon/session artifacts to this audit block with one machine-readable next move.

## DoD
- the post-implementation audit TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
- canon / packet / architecture test all agree this is the active block
- the block states explicitly that seam-deletion count here is zero
- the block states explicitly which old contour already died in the previous runtime block
- the next non-negotiable move is either the same broader fallback-ingress implementation bundle or `GAP`; no hidden third option

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '634,706p;4634,4688p;8250,8270p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1218,1320p;12478,12545p;15659,15756p;19373,19481p'`
- `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '347,384p;5882,6015p;10781,10904p'`
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
- deterministic scan proving the dead contour now exits before fallback
- deterministic scan proving live broader fallback still remains
- existing focused runtime evidence from the latest broader fallback-ingress cut
- updated canon/session artifacts for the audit block
- green governance/session checks after the doc sync

## Rollback
1. Revert this audit TP and canon/session updates.
2. Regenerate the packet.
3. Re-run the governance/session checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only post-implementation audit; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the active audit block and the next move.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either resume the broader fallback-ingress implementation bundle and delete another old seam or stop as `GAP`; it must not reopen seam farming outside this rooted family.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic audit scans plus governance/session checks only.
- **Stop condition:** if the audit cannot justify another runtime move inside the same broader fallback-ingress family without helper growth or frozen downstream widening, stop and publish `GAP` instead of resuming runtime work.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits in this block
- no new helper/wrapper
- no claim that the whole `decision.py:15659-15756` family is gone
- no claim that broader fallback ingress is closed
- no acceptance / proof-path work in this block

## Risks / blockers
- the surviving residual families may require a broader runtime move than the exact deleted contour; if that move widens beyond the rooted fallback family, stop and publish `GAP`.
- the next admissible runtime contour may still need proof that it dies before fallback rather than after entering frozen `decision.py`; if that proof is missing, stop and publish `GAP`.
- frozen `booking.py:2442` stays deferred only while earlier fallback remains the real blocker.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/services/reasoning_core.py:8254-8266`
  - `truffles-api/app/routers/webhook/decision.py:8889-9005`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `truffles-api/app/routers/webhook/decision.py:19373-19481`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `semantic_owner` remains partial
  - `continuity_owner` remains partial
  - `boundary_owner` remains partial
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:** this is an audit-only block; it records one landed contour deletion and classifies what still remains.
- **Risk if deferred:** the program could misread one bounded seam deletion as broader fallback-family closure.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md`
- **Expiry/trigger to stop deferral:** stop if the next runtime contour needs a new helper, a second web query, or widening into frozen downstream files.

## Next-block contract (mandatory)
- **Next block objective:** resume the broader fallback-ingress implementation bundle and delete another old fallback-owned seam inside the same rooted family without helper growth.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:**
  - no old fallback-owned seam can be deleted or made unreachable before fallback on the chosen contour
  - need for a new wrapper/helper
  - need to widen beyond the declared broader fallback-ingress family
  - need to reopen frozen `booking.py`, frozen `pending.py`, proof-path, or acceptance work
  - need for a second web query
- **Owner role for closure:** `Top Architect`
