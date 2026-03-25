# TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-OWNER-REPLACEMENT-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish the stop-line decision for the broader owner-replacement runtime bundle after six admissible slices. This block must prove that the strongest residual inside frozen `decision.py:19373-19456` is not truthfully cuttable with the currently existing owner surfaces only, record the exact generic tool-reply owner-surface gap, and lock the next move to one broader owner-surface implementation in existing non-frozen owner files instead of continuing safe semantic slice farming.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md`
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
  - `rg -n "_maybe_apply_fact_guard|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_tool_reply_owner_cutover_payload|_finalize_turn_planner_owner_cutover|decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19169,19456p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2376,2460p;5779,5900p;6063,6180p;6253,6406p;6493,6642p;8001,8022p'`
  - `nl -ba docs/SOURCE_OF_TRUTH.yaml | sed -n '1,35p;61,90p;296,308p'`
- `FACT findings`:
  - live fallback still remains explicit at `truffles-api/app/services/reasoning_core.py:8010` and `truffles-api/app/services/reasoning_core.py:8022`.
  - the strongest surviving residual family is still the generic tool-reply owner construction / fact-guard / finalize block at `truffles-api/app/routers/webhook/decision.py:19373-19456`.
  - that residual depends on the nested `_maybe_apply_fact_guard(...)` authority at `truffles-api/app/routers/webhook/decision.py:9630-9718`, which still mutates clarify attempts, trace/meta, escalation, and send/finalize behavior from frozen scope.
  - the existing non-frozen owner lanes in `truffles-api/app/services/reasoning_core.py` are case-specific only: services-overview tool reply at `:5779-5900`, pending-slot guidance at `:6063-6180`, booking interrupt service info at `:6253-6406`, and master override at `:6493-6642`.
  - the only shared non-frozen surface currently available for those lanes is the finalizer `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)` at `:2376-2460`; there is no existing reusable generic owner surface for the residual build+guard sequence itself.
  - the active implementation TP already says to start with this strongest residual and publish `GAP` if it cannot be cut without helper growth or widening.
- `Detected drift (docs vs code)`:
  - the broader-owner implementation TP truthfully captured six admissible slices, but it still frames the next move as continued safe semantic contour expansion even though the current blocker is now a generic owner-surface gap rather than another safe semantic slice.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent final-ingress decision / implementation blocks; no second query is allowed or needed
- **Existing solutions found:**
  - first exhaust direct reuse, then stop when the old hotspot needs a broader owner-surface materialization rather than another local cut
- **Decision:** `reuse/integrate`
  - reuse the same architecture guidance and existing owner destinations already present in repo truth
- **Rejected options:**
  - a second web query
  - continued safe semantic slice farming after the strongest residual proved non-cuttable
  - a new wrapper/helper around frozen `decision.py`

## Root cause (mandatory)
- **Symptom:** the broader owner-replacement implementation landed six admissible slices, but the strongest residual in `decision.py:19373-19456` still remains live and owners stay partial.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/decision.py:19373-19456` and confirm frozen `decision.py` still builds the generic tool-reply decision/state/payload bundle and then calls `_maybe_apply_fact_guard(...)` before `_finalize_turn_planner_owner_cutover(...)`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:9630-9718` and confirm `_maybe_apply_fact_guard(...)` still owns clarify-attempt state, trace/meta writes, escalation fallback, and send/finalize behavior from frozen scope.
  3. Inspect `truffles-api/app/services/reasoning_core.py:5779-5900`, `:6063-6180`, `:6253-6406`, and `:6493-6642` and confirm the existing non-frozen owner lanes are specialized contours, not a reusable generic tool-reply owner surface.
  4. Inspect `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md:257-263` and confirm the current block must stop and publish `GAP` if this strongest residual needs a new helper/wrapper or widening.
- **Evidence:**
  - explicit fallback from `reasoning_core` into frozen `decision.py`
  - residual generic tool-reply owner construction / fact-guard / finalize authority still lives in frozen scope
  - existing owner lanes only solve specialized contours
  - active TP contract already fail-closes on helper growth / widening for this residual
- **Five Whys (or equivalent):**
  1. Why are owners still partial after six admissible slices? Because fallback still reaches the generic residual tool-reply family in frozen `decision.py`.
  2. Why did the six slices not finish that family? Because they were all specialized safe contours that could reuse current owner lanes directly.
  3. Why can the strongest residual not be cut the same way? Because it is not another specialized semantic contour; it is the generic build+guard+finalize block for tool replies.
  4. Why can that generic block not be moved with current owner surfaces only? Because `_maybe_apply_fact_guard(...)` and the generic tool-reply owner construction still live only inside frozen `decision.py`, while existing non-frozen lanes are embedded case-specific branches.
  5. Why does this require a new decision block? Because continuing under the current implementation TP would violate its own stop-line and mislabel another architectural problem as just one more safe slice.
- **Root cause statement:** the broader owner-replacement implementation has reached truthful saturation on safe semantic contours; the remaining live authority is now a generic tool-reply owner-construction plus fact-guard boundary embedded in frozen `decision.py`, and the repo does not yet have a reusable generic owner surface for that block outside `decision.py`.
- **Fix mechanism:**
  - stop the current broader-owner implementation block as `GAP`
  - switch canon to a generic tool-reply owner-surface decision block
  - lock the next move to one owner-surface implementation in existing non-frozen owner destinations (`reasoning_core.py`, `turn_executor.py`, `boundary_validator.py`, and only the already existing supporting owner contracts) without a wrapper/helper around frozen ingress

## FACT vs INFERENCE verdict
- **FACT:** six bounded broader-owner slices are valid seam-deletion evidence.
- **FACT:** the strongest residual in `decision.py:19373-19456` is still live.
- **FACT:** current non-frozen owner lanes do not provide a reusable generic owner surface for that residual.
- **INFERENCE:** the next honest progress unit is a generic tool-reply owner-surface decision and implementation, not another safe semantic slice report.
- **Decision:** switch canon from the broader-owner implementation block to this generic tool-reply owner-surface decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`
  - `truffles-api/app/core/turn_planner.py:build_tool_reply_owner_decision(...)`
  - `truffles-api/app/core/dialog_state_service.py:build_tool_reply_owner_state(...)`
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_cutover_payload(...)`
  - `truffles-api/app/core/boundary_validator.py`
  - the six already-landed broader-owner slices as evidence boundaries
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the missing piece is not another brand new subsystem; it is one reusable owner surface inside already-existing owner modules so the residual generic tool-reply family can leave frozen `decision.py`.

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-heavy`
- **Override token:** `final-ingress-coordinator-generic-tool-reply-owner-surface-decision`
- **Why this profile fits:** this block only changes trajectory/canon so the next runtime block can target the real generic owner-surface gap.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is `done`
- no claim that the six broader-owner slices were invalid
- no new wrapper/helper or helper forest counted as progress
- no reopening of `booking.py`, `pending.py`, proof-path, or acceptance work as the main story

## Scope
- record that the broader-owner implementation is now blocked on a generic tool-reply owner-surface gap
- explain why the strongest residual cannot truthfully be cut with current owner surfaces only
- lock the next runtime move to one generic tool-reply owner-surface implementation bundle in existing owner files
- switch canon/session/packet to this decision block

## Out of scope
- runtime implementation in this block
- edits to frozen files in this block
- new acceptance or dev reruns
- new web search
- unrelated consultant-core families outside final ingress/coordinator closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md`
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
1. Publish this generic tool-reply owner-surface decision TP with the exact saturation proof and next-block contract.
2. Record the factual state: six broader-owner slices are valid, but the strongest residual is blocked under the current implementation contract.
3. Switch canon so the next non-negotiable move is one generic tool-reply owner-surface implementation bundle.
4. Regenerate packet and rerun governance/session checks.

## Exact future generic owner-surface scope
- `truffles-api/app/services/reasoning_core.py`
  - the live fallback boundary rooted at `:8010-8022`
  - the shared finalizer surface rooted at `:2376-2460`
- `truffles-api/app/routers/webhook/decision.py`
  - the generic tool-reply owner construction / fact-guard / finalize family rooted at `:19373-19456`
  - the nested fact-guard authority rooted at `:9630-9718`
- bounded existing owner destinations only:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/boundary_validator.py`
  - focused tests under `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_message_endpoint.py`, `truffles-api/tests/test_consultant_core_runtime_contracts.py`, and `truffles-api/tests/architecture`
- **Not in scope:**
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - proof-path / acceptance work
  - unrelated `decision.py` families outside the rooted tool-reply / fact-guard block above unless a follow-up decision explicitly widens scope

## DoD
- this decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md`
- canon/packet/test all agree that this decision block is active
- repo truth states explicitly that no old seam died in this decision block
- the next move is no longer framed as another safe semantic slice inside the current broader-owner implementation TP
- required checks are green

## Checks
- `rg -n "_maybe_apply_fact_guard|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_tool_reply_owner_cutover_payload|_finalize_turn_planner_owner_cutover|decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19169,19456p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2376,2460p;5779,5900p;6063,6180p;6253,6406p;6493,6642p;8001,8022p'`
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
- deterministic line scans above
- synced canon docs / packet
- guard/session/architecture checks from this doc block
- explicit statement that the deleted seam count in this block is zero

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the future generic owner-surface implementation still cannot delete or bypass an old live seam without helper growth or widening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on the generic tool-reply owner-surface decision and next move
- **Rollback:** revert this TP and the matching canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next runtime block must target the generic tool-reply owner-surface implementation, not another safe semantic slice

## Rollback
- revert the new decision TP and the canon sync files to the prior broader-owner implementation block if this decision is judged untruthful

## No-go
- no runtime edits in this block
- no new helper/wrapper around frozen ingress
- no claim that the current broader-owner implementation block is complete
- no claim that owner closure or `L2` / final acceptance proof is done
- no second web search

## Risks / blockers
- the future implementation may still prove blocked if generic tool-reply owner construction cannot be materialized in existing owner files without duplicating `_maybe_apply_fact_guard(...)`
- if the future implementation needs to widen into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756`, that must be a new explicit decision rather than silent scope growth

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/services/reasoning_core.py:8010-8022`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `truffles-api/app/routers/webhook/decision.py:19373-19456`
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
- **Why not in this block:**
  - this is a decision-only stop-line block; it records that the current implementation contract is saturated and locks the next truthful move
- **Risk if deferred:**
  - owners remain partial while fallback still carries the generic tool-reply boundary authority
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next implementation still requires a wrapper/helper or wider frozen-family reopening, stop and escalate again rather than claiming another partial contraction

## Next-block contract (mandatory)
- **Next block objective:**
  - materialize the generic tool-reply owner surface in existing non-frozen owner files and delete or bypass the old live authority seam rooted at `decision.py:19373-19456`, or publish `GAP`
- **First deterministic check command:**
  - `rg -n "_maybe_apply_fact_guard|build_tool_reply_owner_decision|build_tool_reply_owner_state|build_tool_reply_owner_cutover_payload|_finalize_turn_planner_owner_cutover|decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19169,19456p' && nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2376,2460p;5779,5900p;6063,6180p;6253,6406p;6493,6642p;8001,8022p'`
- **Blocked-by conditions:**
  - need for a new wrapper/helper around frozen `decision.py`
  - need to widen into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756` without an explicit new decision
  - need to reopen `booking.py`, `pending.py`, proof-path, or acceptance work
  - need for a second web query
- **Owner role for closure:** `Top Architect`
