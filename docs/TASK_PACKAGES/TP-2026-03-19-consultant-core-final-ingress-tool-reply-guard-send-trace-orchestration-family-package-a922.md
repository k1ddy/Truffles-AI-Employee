# TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-GUARD-SEND-TRACE-ORCHESTRATION-FAMILY-PACKAGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-TURN-OUTCOME-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-NEXT-RESIDUAL-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Delete or truthfully localize the next live frozen authority on the same tool-reply contour after typed turn-outcome cutover. The target family is the remaining guard/send/trace/meta orchestration in frozen `decision.py`; the block is admissible only if that authority dies without creating a new wrapper/helper or mixed hotspot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19528p'`
  - `rg -n "_maybe_apply_fact_guard\(|_record_decision_trace\(|_record_message_decision_meta\(|_update_message_decision_metadata\(|_send_and_save\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/trace.py truffles-api/app/services/reasoning_core.py`
  - `sed -n '2550,2605p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '2870,2925p' truffles-api/app/services/reasoning_core.py`
  - `rg -n "tool_reply_without_evidence_clarifies|services_overview|pending_question_preserves_interaction_evidence" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - the old direct tool-reply `TurnOutcome` / `TurnOutcomeObservability` authority is already dead; constructor hits now live only in non-frozen `truffles-api/app/core/turn_executor.py`.
  - the same frozen contour still owns `_maybe_apply_fact_guard(...)`, pre-send metadata writes, trace writes, message-decision writes, `_send_and_save(...)`, and post-send transport observability mutation in `truffles-api/app/routers/webhook/decision.py:19313-19528`.
  - non-frozen owner examples already exist in `truffles-api/app/services/reasoning_core.py` where owner-cutover slices build artifacts, write `consultant_core_runtime`, and commit reply transport results without routing final authority back through frozen `decision.py`.
  - this block is about orchestration authority only; it does not reopen broader route/payload extraction, timeout/degrade, or acceptance proof-path work.
- `Detected drift (docs vs code)`:
  - repo truth already says the next residual family is the surrounding tool-reply guard/send/trace orchestration; the active block must now switch from executed turn-outcome deletion to this narrower live residual.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal primary architecture guidance
- **Reuse rule for this block:**
  - reused from the parent ingress cutover block; no second query is needed before implementation
- **Existing solutions found:**
  - move one live coordinator slice at a time into the new interface, then contract the legacy coordinator authority
- **Decision:** `reuse/integrate`
  - reuse existing non-frozen reply/orchestration patterns from `reasoning_core.py`, `trace.py`, and `turn_executor.py`
- **Rejected options:**
  - second web query
  - new compatibility wrapper/helper around frozen `decision.py`
  - broad multi-family frozen move in one block

## Root cause (mandatory)
- **Symptom:** `boundary_owner` remains partial after typed turn-outcome cutover because frozen `decision.py` still owns live tool-reply orchestration authority on the same contour.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19313-19528`
  2. confirm `_maybe_apply_fact_guard(...)`, `_record_decision_trace(...)`, `_record_message_decision_meta(...)`, `_update_message_decision_metadata(...)`, and `_send_and_save(...)` still execute directly on that contour
  3. compare with non-frozen owner-cutover patterns in `truffles-api/app/services/reasoning_core.py:2574-2595` and `truffles-api/app/services/reasoning_core.py:2875-2914`
- **Evidence:**
  - exact frozen contour `decision.py:19313-19528`
  - exact non-frozen orchestration examples in `reasoning_core.py`
  - focused endpoint tests already cover the contour families that would regress if orchestration semantics change
- **Five Whys:**
  1. Why does `boundary_owner` remain partial? Because frozen `decision.py` still performs live tool-reply orchestration after typed artifact assembly.
  2. Why is that still live? Because the previous block deleted only the direct artifact constructor authority, not the surrounding orchestration authority.
  3. Why is this the next admissible slice? Because it is the narrowest remaining live authority on the same rooted contour.
  4. Why can this move be package-level closure work instead of another symptom fix? Because the target is still authority deletion inside live ingress, not proof-path residue.
  5. Why not move broader routing now? Because route/payload extraction and timeout/degrade are separate live families and would widen the block beyond one rooted contour.
- **Root cause statement:** the surviving frozen hotspot is no longer artifact construction itself; it is the remaining tool-reply guard/send/trace/meta orchestration authority that still lives directly in `decision.py` on the same live contour.
- **Fix mechanism:**
  - reuse an existing non-frozen orchestration owner pattern
  - route the tool-reply contour through that owner without a new wrapper/helper
  - keep the block bounded to the same contour and stop if it expands into route/payload or timeout/degrade families

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the frozen tool-reply orchestration authority in `truffles-api/app/routers/webhook/decision.py:19313-19528`.
- **FACT:** this includes live ownership of fact-guard result handling, trace/meta persistence, reply send/transport update, and final webhook response shaping on the tool-reply contour.
- **FACT:** this block does **not** claim deletion of broader policy-core route/payload extraction or timeout/degrade authority in `decision.py`.
- **INFERENCE:** the block is admissible only if that orchestration authority becomes deleted/unreachable and does not reappear as a new mixed hotspot.

## Invariant
- no new wrapper/helper counted as progress
- no widening beyond the exact tool-reply orchestration contour plus bounded supporting owner/test code
- no reopening of proof-path, transport, observer, billing, or booking frozen work
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone

## Scope
- publish this narrow TP and switch canon to it
- next implementation block may touch only the exact tool-reply orchestration contour in `decision.py`
- next implementation block may reuse bounded non-frozen owner surfaces in `reasoning_core.py`, `trace.py`, and `turn_executor.py`
- add/update bounded regressions for services-overview, fact-guard clarify, and missing-slot pending-question tool replies

## Out of scope
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `ops/diagnose.py`
- broader policy-core route/rescue/payload extraction cutover
- timeout/degrade boundary family cutover
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- runtime/tests for the next implementation block:
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - non-frozen owner-cutover orchestration in `truffles-api/app/services/reasoning_core.py`
  - decision-meta/trace primitives in `truffles-api/app/routers/webhook/trace.py`
  - typed artifact assembly in `truffles-api/app/core/turn_executor.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the next step is orchestration-owner reuse, not new abstraction growth

## Plan (1..N)
1. Publish this package TP and switch canon to it.
2. On the next implementation block, prove the exact orchestration contour and choose the smallest existing non-frozen owner pattern that can absorb it.
3. Delete or bypass the frozen orchestration authority without adding a wrapper/helper.
4. Add/update bounded regressions.
5. Run deterministic checks and publish either truthful seam deletion or truthful `GAP`.

## DoD
- frozen tool-reply orchestration authority in `decision.py:19313-19528` is deleted/unreachable
- no new wrapper/helper or broadened frozen scope exists
- focused regressions pass
- `legacy_freeze_guard.py` passes under exact scope
- canon/session/state record exactly which orchestration seam died and which residual family remains

## Checks
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
- exact TP and canon switch
- exact frozen contour reference in `decision.py`
- exact current next move for implementation
- mandatory packet/guard/session check outputs

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** packet / guard / architecture / session checks only
- **Stop condition:** if the next implementation contour widens beyond `decision.py:19313-19528`, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** this TP block is doc-only; no runtime rollout happens here
- **Go/no-go signals:**
  - canon points to the exact next contour
  - packet/guard/session checks pass
- **Rollback:** revert this TP/canon sync and rebuild the agent packet
- **Post-release monitoring window:** next block only; no production change in this step

## Rollback
1. Revert this TP/canon sync.
2. Rebuild agent packet.
3. Re-run deterministic doc guards.

## No-go
- no implementation in this TP block
- no new helper shell to hide frozen authority
- no widening from the tool-reply contour into route/payload or timeout/degrade families
- no acceptance/dev rerun substituting for architecture evidence

## Risks / blockers
- the truthful implementation may still be frozen-bound and require another exact waiver line update in `docs/LEGACY_SUNSET.yaml`
- if no existing non-frozen owner pattern can absorb the contour without a new helper, the next block must stop as `GAP`
- if the contour actually depends on broader policy payload shaping than currently proven, the next block must stop as `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen tool-reply guard/send/trace/meta orchestration still lives in `decision.py`
  - broader route/payload extraction still lives in `decision.py`
  - timeout/degrade boundary families still live in `decision.py`
- **Why not in this block:**
  - this block is TP publication only; implementation must stay bounded to the next rooted contour
- **Risk if deferred:**
  - `boundary_owner` remains partial and ingress closure remains incomplete
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next block cannot delete this orchestration seam without bridge growth, stop and publish `GAP`

## Next-block contract (mandatory)
- **Next block objective:** delete or truthfully localize the frozen tool-reply guard/send/trace orchestration family on the same contour after typed turn-outcome cutover
- **First deterministic check command:** `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19528p'`
- **Blocked-by conditions:**
  - any need to widen into broader route/payload extraction
  - any need to widen into timeout/degrade families
  - any new wrapper/helper seam
- **Owner role for closure:** `Top Architect`
