# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-GUARD-FINALIZE-POST-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one exact broader fact-guard family decision after the truthful post-audit stopped the old generic tool-reply ladder. This block must define the rooted broader `_maybe_apply_fact_guard(...)` family, lock the admissible owner destinations, decide the status of frozen `booking.py`, and reject any next move that would restart seam farming or hide the same mixed authority inside a new helper.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
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
  - `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19980,20076p;21020,21040p;21294,21310p;21762,21778p'`
  - `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
  - `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- `FACT findings`:
  - the surviving old authority is no longer the reduced generic tool-reply contour; it is the broader `_maybe_apply_fact_guard(...)` family rooted at `truffles-api/app/routers/webhook/decision.py:9630-9718`.
  - the rooted body still owns clarify-attempt state mutation, low-confidence reset, trace/meta writes, clarify-limit escalation, reply send/save, and final `WebhookResponse` shaping.
  - the rooted body is still called directly from frozen `decision.py` at `:19985`, `:21024`, `:21300`, and `:21768`.
  - the same authority is still injected into non-frozen `info.py` at `:813`, `:1176`, `:1282`, `:1411`, `:1725`, and `:2136`.
  - the same authority is still injected into frozen `booking.py` at `:2442`.
  - `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)` at `:2705-2765` remains an entry owner surface that still depends on `maybe_apply_fact_guard`, while live fallback into frozen ingress still remains at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`.
  - existing relevant non-frozen fragments already exist in `truffles-api/app/routers/webhook/guards.py`, `truffles-api/app/services/policy_validation_boundary_service.py`, and `truffles-api/app/core/dialog_state_service.py:2783-2817`.
- `Detected drift (docs vs code)`:
  - the post-audit correctly stopped the exact tool-reply ladder, but repo truth still needed one decision block to say where the broader fact-guard family may go next.
  - continuing the old generic tool-reply implementation TP would silently widen into mixed ingress families and would no longer be truthful.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Why this query is reused here:** the same migration rule governs this decision block: only a move that deletes or bypasses the old live authority counts as progress.
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** after a truthful post-cut audit proves the remaining authority is broader than the original contour, stop, publish an explicit decision block, and only continue with a new rooted family package that can still kill the old live seam.
- **Decision:** `reuse/integrate`
  - reuse the parent migration rule and the existing in-repo owner surfaces instead of inventing a new fact-guard layer.
- **Rejected options:**
  - a second web query
  - resuming the old exact tool-reply TP
  - introducing a new `fact_guard_service.py` or similar wrapper layer as a way around the broader family decision

## Root cause (mandatory)
- **Symptom:** the exact generic tool-reply ladder stopped truthfully, but owners still remain partial because `_maybe_apply_fact_guard(...)` is broader than that reduced contour.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:9630-9718` and confirm the body still owns clarify-attempt state mutation, trace/meta writes, escalation, send/save, and `WebhookResponse` shaping.
  2. inspect `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768` and confirm the same body is still called directly from frozen legacy paths.
  3. inspect `truffles-api/app/routers/webhook/info.py:813`, `:1176`, `:1282`, `:1411`, `:1725`, `:2136`, and `truffles-api/app/routers/webhook/booking.py:2442` and confirm the same callable is still injected into broader ingress flows.
  4. inspect `truffles-api/app/routers/webhook/guards.py`, `truffles-api/app/services/policy_validation_boundary_service.py`, and `truffles-api/app/core/dialog_state_service.py:2783-2817` and confirm existing owner fragments already cover the bounded destination primitives for this family.
- **Evidence to capture:**
  - exact rooted broader fact-guard family map
  - exact admissible owner destinations
  - decision on frozen `booking.py`
  - proof that no old authority seam dies in this doc-only block
- **Five Whys (or equivalent):**
  1. Why did the old exact TP saturate? Because `_finalize_tool_reply_owner_execution(...)` deleted only the entry seam, not the broader `_maybe_apply_fact_guard(...)` authority.
  2. Why is `_maybe_apply_fact_guard(...)` broader than the reduced contour? Because the same body still serves direct `decision.py` callsites plus injected `info.py` and `booking.py` flows.
  3. Why can this not be treated as another exact residual? Because that would widen scope silently while pretending the family is still only generic tool-reply.
  4. Why is a new helper/wrapper forbidden here? Because it would move the same mixed authority into a new hotspot instead of deleting it.
  5. Why is a decision block the honest next step? Because repo truth already has enough evidence to lock one rooted broader family and one bounded next move without claiming runtime deletion.
- **Root cause statement:** the old direct tool-reply guard/finalize entry seam is already dead, but the surviving `_maybe_apply_fact_guard(...)` body is a broader mixed fact-guard family shared across frozen and non-frozen ingress paths; without a new rooted family decision, any next runtime move would mislabel wider family work as another exact tool-reply slice.
- **Fix mechanism:**
  - publish one broader fact-guard family decision block
  - lock the only admissible owner destinations to existing repo surfaces
  - mark frozen `booking.py` explicitly as deferred debt unless the next runtime block proves it must widen
  - reject any next move that relies on a new wrapper/helper or reopens unrelated families

## Exact rooted broader fact-guard family
- `truffles-api/app/routers/webhook/decision.py:9630-9718` — rooted old authority body for fact-guard clarify / escalation / send-save / response shaping.
- `truffles-api/app/routers/webhook/decision.py:19985` — direct legacy fact-guard callsite on the info reply contour.
- `truffles-api/app/routers/webhook/decision.py:21024` — direct legacy fact-guard callsite on the intent-queue info reply contour.
- `truffles-api/app/routers/webhook/decision.py:21300` — direct legacy fact-guard callsite on the multi-intent info reply contour.
- `truffles-api/app/routers/webhook/decision.py:21768` — direct legacy fact-guard callsite on the expected-reply followup reply contour.
- `truffles-api/app/routers/webhook/info.py:813` — injected non-frozen fact-guard use on `multi_truth`.
- `truffles-api/app/routers/webhook/info.py:1176` — injected non-frozen fact-guard use on bundled info replies.
- `truffles-api/app/routers/webhook/info.py:1282` — injected non-frozen fact-guard use on `guest_policy`.
- `truffles-api/app/routers/webhook/info.py:1411` — injected non-frozen fact-guard use on service matcher replies.
- `truffles-api/app/routers/webhook/info.py:1725` — injected non-frozen fact-guard use on truth-gate replies.
- `truffles-api/app/routers/webhook/info.py:2136` — injected non-frozen fact-guard use on alternate info bundle replies.
- `truffles-api/app/routers/webhook/booking.py:2442` — injected frozen fact-guard use on booking-interrupt info replies.
- `truffles-api/app/services/reasoning_core.py:2705-2765` — existing non-frozen entry owner surface that still depends on the fact-guard family.
- `truffles-api/app/services/reasoning_core.py:8075-8087` — live fallback that still keeps frozen ingress reachable overall.

## Admissible owner destinations
- `truffles-api/app/core/dialog_state_service.py:2783-2817`
  - admissible only for clarify-attempt read/write primitives (`get_clarify_attempt_state(...)` / `set_clarify_attempt_state(...)`).
- `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - admissible only for bounded clarify-attempt mutation reuse around the existing context-manager contract.
- `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - admissible only for bounded clarify-limit escalation / send-save reuse.
- `truffles-api/app/services/policy_validation_boundary_service.py`
  - admissible only for deterministic guard/boundary orchestration that already owns trace/meta/send-save patterns for clarify-style guard replies.
- `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)`
  - may remain a caller/consumer of the broader fact-guard owner surface, but is not itself the new family owner destination.
- **Explicitly not admissible:**
  - any new `fact_guard_service.py`
  - any new wrapper/helper that only re-houses the same mixed authority
  - shifting the broader fact-guard family into `state_service.py`, `turn_planner.py`, or `boundary_validator.py` without proving those surfaces can own clarify-attempt state plus escalation plus transport semantics as one bounded family

## Frozen booking.py decision
- `truffles-api/app/routers/webhook/booking.py:2442` becomes **explicit deferred debt** for the immediate next runtime block.
- Reason: `booking.py` currently consumes an injected `maybe_apply_fact_guard` callable, so the next runtime block must first prove the old rooted authority can die while preserving that injected contract and without editing frozen `booking.py`.
- If the next runtime block proves `booking.py` must be edited for correctness or deletion, stop and publish a new explicit waiver/decision block instead of widening silently.

## FACT vs INFERENCE verdict
- **FACT:** this block is doc-only; no old authority seam is deleted or made unreachable here.
- **FACT:** `_maybe_apply_fact_guard(...)` is a broader mixed fact-guard family, not the next exact tool-reply residual.
- **FACT:** existing admissible owner fragments already exist in `DialogStateService`, `guards.py`, and `policy_validation_boundary_service.py`.
- **FACT:** frozen `booking.py:2442` is now explicit deferred debt for the immediate next runtime block.
- **INFERENCE:** the next admissible move is one broader fact-guard family runtime bundle that kills or bypasses the old rooted authority without new helper growth and without widening into `booking.py` unless a new explicit decision says so.
- **Decision:** switch canon to this broader fact-guard family decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/app/core/dialog_state_service.py:2783-2817`
  - existing packet / arch / session guard flow
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the bounded destination fragments already exist in-repo
  - the only truthful work left is deleting or bypassing the old family, not inventing another coordinator layer

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-heavy`
- **Why this profile fits:** this is a doc-only decision block that defines the truthful next runtime move without claiming runtime deletion.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no new wrapper/helper counted as progress
- no claim that frozen `booking.py` is already solved
- answer to "какой old authority seam стал deleted или unreachable после этого блока?" remains `никакой`

## Scope
- define the exact rooted broader fact-guard family
- define the admissible owner destinations for that family
- define the `booking.py` status for the immediate next runtime block
- switch canon/session artifacts to this decision block

## Out of scope
- runtime implementation
- editing `decision.py`, `info.py`, `booking.py`, `guards.py`, `reasoning_core.py`, `policy_validation_boundary_service.py`, or `dialog_state_service.py`
- reopening unrelated continuity, timeout, acceptance, or proof families
- a second web query
- claiming any runtime seam deletion in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
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
1. Publish this broader fact-guard family decision TP with the exact rooted family map.
2. Lock the only admissible owner destinations to existing repo surfaces.
3. Mark frozen `booking.py:2442` as deferred debt for the immediate next runtime block.
4. Switch canon/session artifacts to this decision block.
5. Regenerate packet and rerun governance/session checks.

## DoD
- the broader fact-guard family decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
- canon / packet / architecture test all agree this is the active block
- the exact rooted broader family and admissible owner destinations are machine-readable in canon/session artifacts
- frozen `booking.py` status is explicit rather than implicit
- the block states explicitly that seam-deletion count here is zero

## Checks
- `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19980,20076p;21020,21040p;21294,21310p;21762,21778p'`
- `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
- `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
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
- updated TP, canon, packet, session, and state artifacts
- deterministic scan proving the exact rooted broader fact-guard family
- explicit statement that seam-deletion count in this block is zero
- green governance/session checks after the doc sync

## Rollback
1. Revert this decision TP and matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only broader-family decision; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the active decision block and the next move.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either implement the broader fact-guard family bundle under this decision or stop as `GAP`; it must not resume the old exact tool-reply ladder.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic doc / governance checks only.
- **Stop condition:** if the next runtime bundle needs a new helper/wrapper, a second web query, or a silent widening into frozen `booking.py`, stop and publish `GAP` instead of continuing.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits hidden inside this decision block
- no second web search
- no helper/wrapper growth counted as progress
- no claim that `_maybe_apply_fact_guard(...)` is already deleted or unreachable in this block
- no silent widening into frozen `booking.py`
- no reopening unrelated continuity, timeout, acceptance, or proof families

## Risks / blockers
- the next runtime bundle may prove that the existing destination fragments are still insufficient, which would require a new explicit decision instead of silent widening.
- live fallback `truffles-api/app/services/reasoning_core.py:8075-8087` still remains and must not be miscounted as solved by this block.
- other rooted residual families at `decision.py:1218-1320`, `:12478-12545`, and `:15659-15756` remain open and are not solved by this decision.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - `truffles-api/app/routers/webhook/decision.py:19985`
  - `truffles-api/app/routers/webhook/decision.py:21024`
  - `truffles-api/app/routers/webhook/decision.py:21300`
  - `truffles-api/app/routers/webhook/decision.py:21768`
  - `truffles-api/app/routers/webhook/info.py:813`
  - `truffles-api/app/routers/webhook/info.py:1176`
  - `truffles-api/app/routers/webhook/info.py:1282`
  - `truffles-api/app/routers/webhook/info.py:1411`
  - `truffles-api/app/routers/webhook/info.py:1725`
  - `truffles-api/app/routers/webhook/info.py:2136`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `truffles-api/app/services/reasoning_core.py:8075-8087`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `semantic_owner` remains partial
  - `continuity_owner` remains partial
  - `boundary_owner` remains partial
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:**
  - this block only decides the truthful broader fact-guard family scope and next move; it does not execute runtime deletion.
- **Risk if deferred:**
  - the team could resume seam farming under the dead exact TP or silently widen into frozen `booking.py` without a new decision.
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-implementation-a922.md` (to be authored or executed next)
- **Expiry/trigger to stop deferral:**
  - before any next runtime claim touching `_maybe_apply_fact_guard(...)`
  - immediately if anyone proposes a new helper/wrapper or a silent `booking.py` widening

## Next-block contract (mandatory)
- **Next block objective:** implement the broader fact-guard family bundle so the old rooted `_maybe_apply_fact_guard(...)` authority at `truffles-api/app/routers/webhook/decision.py:9630-9718` becomes deleted or unreachable as live authority, while staying inside the admissible owner destinations above and leaving frozen `booking.py` deferred unless a new explicit decision says otherwise.
- **First deterministic check command:** `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19980,20076p;21020,21040p;21294,21310p;21762,21778p' && nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p' && nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p' && nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- **Blocked-by conditions:**
  - if the runtime plan needs a new helper/wrapper to carry the broader fact-guard family
  - if the runtime plan cannot stay inside `DialogStateService`, `guards.py`, and `policy_validation_boundary_service.py` as the owner destinations
  - if the runtime plan needs to widen into frozen `booking.py` without a new explicit decision/waiver block
  - if the runtime plan needs a second web query
  - if the runtime plan reopens unrelated continuity, timeout, acceptance, or proof families
  - if the runtime plan cannot delete or bypass the old rooted authority and only adds another delegate layer
- **Owner role for closure:** `Top Architect`
