# TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-POLICY-PAYLOAD-INTERACTION-OWNER-FAMILY-PACKAGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-GUARD-SEND-TRACE-ORCHESTRATION-FAMILY-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-POLICY-PAYLOAD-INTERACTION-OWNER-CLOSURE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Delete or truthfully localize the next live frozen semantic authority on the same tool-reply ingress contour after guard/send/trace orchestration cutover. The target family is the remaining tool-reply policy-payload shaping and interaction-owner selection in frozen `decision.py`; the block is admissible only if that authority dies without a new wrapper/helper or a wider frozen hotspot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSION_INDEX.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19412p'`
  - `rg -n "tool_reply_policy_payload|tool_reply_interaction_owner|tool_reply_interaction_relation|build_from_policy_override" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py`
  - `sed -n '2588,2620p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '2788,2820p' truffles-api/app/services/reasoning_core.py`
  - `rg -n "tool_reply_without_evidence_clarifies|services_overview|pending_question_preserves_interaction_evidence|typed_tool_reply_owner_cutover_artifact" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - the old direct tool-reply guard/send/trace/meta orchestration authority is already dead; the contour now exits through non-frozen `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`.
  - the same frozen contour still shapes `tool_reply_policy_payload` from `policy_payload`, applies the `master_override_applied` semantic override, selects `tool_reply_interaction_owner` / `tool_reply_interaction_relation` from `pending_question_tool_followup`, `collect_service_info_interrupt_active`, and `master_override_applied`, and then drives `TurnPlanner().build_from_policy_override(...)` in `truffles-api/app/routers/webhook/decision.py:19319-19408`.
  - the same frozen contour still chooses whether the downstream continuity path is `DialogStateService().build_collect_owner_state(...)` or `DialogStateService().normalize(...)` based on `turn_outcome_expected_reply`.
  - non-frozen owner examples already exist in `truffles-api/app/services/reasoning_core.py` where planner-owner cutovers build override decisions with explicit `interaction_owner` / `interaction_relation` and finalize them through the shared owner-cutover path.
  - this block is about the semantic tool-reply payload / interaction-owner family only; it does not reopen broader route/rescue/payload extraction elsewhere in `decision.py`, timeout/degrade families, or acceptance proof-path work.
- `Detected drift (docs vs code)`:
  - repo truth already says the next admissible move is to author the tool-reply policy-payload / interaction-owner family package; canon must now switch from the executed guard/send/trace block to this narrower surviving semantic contour.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal primary architecture guidance
- **Reuse rule for this block:**
  - reused from the parent final-ingress closure line; no second query is needed before the next implementation block
- **Existing solutions found:**
  - move one live semantic coordinator slice at a time into the new interface, then contract the legacy coordinator authority on that exact contour
- **Decision:** `reuse/integrate`
  - reuse existing planner-owner patterns in `reasoning_core.py`, `turn_planner.py`, and `dialog_state_service.py`
- **Rejected options:**
  - second web query
  - new compatibility wrapper/helper around frozen `decision.py`
  - broad multi-family frozen move in one block

## Root cause (mandatory)
- **Symptom:** `boundary_owner` remains partial after direct tool-reply artifact and guard/send/trace cutovers because frozen `decision.py` still owns live semantic tool-reply payload shaping and interaction-owner selection on the same contour.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19319-19408`
  2. confirm `tool_reply_policy_payload` is still normalized inline from `policy_payload` and semantic fallbacks
  3. confirm `tool_reply_interaction_owner` / `tool_reply_interaction_relation` are still selected inline from `pending_question_tool_followup`, `collect_service_info_interrupt_active`, and `master_override_applied`
  4. confirm the resulting shaped payload still directly drives `TurnPlanner().build_from_policy_override(...)`, `DialogStateService().build_collect_owner_state(...)`, and `DialogStateService().normalize(...)`
  5. compare with non-frozen planner-owner examples in `truffles-api/app/services/reasoning_core.py:2797` and sibling safe-owner cutovers
- **Evidence:**
  - exact frozen contour `decision.py:19319-19408`
  - exact non-frozen planner-owner cutover examples in `reasoning_core.py`
  - focused endpoint/runtime-contract tests already covering services-overview, fact-guard clarify, and pending-question tool-reply contours
- **Five Whys:**
  1. Why does `boundary_owner` remain partial? Because frozen `decision.py` still performs semantic tool-reply shaping before the planner owner path.
  2. Why is that still live? Because the previous block deleted only orchestration authority after the artifact existed, not the upstream semantic shaping authority.
  3. Why is this the next admissible slice? Because it is the narrowest surviving semantic authority on the same rooted tool-reply contour.
  4. Why can this move still count as architectural progress? Because the target is live authority deletion inside final ingress, not a proof-path symptom fix.
  5. Why not widen into broader route/payload extraction now? Because that is a separate frozen family and would break package-level closure discipline.
- **Root cause statement:** the surviving frozen hotspot on this contour is now the semantic tool-reply payload / interaction-owner shaping that still lives directly in `decision.py` and decides how the planner-owner path is built.
- **Fix mechanism:**
  - reuse an existing non-frozen planner-owner pattern
  - move the tool-reply payload / interaction-owner shaping out of frozen `decision.py` without a new wrapper/helper
  - keep the block bounded to the same contour and stop if it expands into broader route/payload or timeout/degrade families

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the frozen tool-reply policy-payload / interaction-owner shaping authority in `truffles-api/app/routers/webhook/decision.py:19319-19408`.
- **FACT:** this includes live ownership of `intent` / `action` / `tool_action` fallback shaping, master-override semantic forcing, interaction-owner / relation selection, and the decision/dialog-state handoff that follows from those inline choices.
- **FACT:** this block does **not** claim deletion of broader route/rescue/payload extraction elsewhere in `decision.py` or timeout/degrade families.
- **INFERENCE:** the block is admissible only if that semantic authority becomes deleted/unreachable and does not reappear as a new mixed hotspot.

## Invariant
- no new wrapper/helper counted as progress
- no widening beyond the exact tool-reply policy-payload / interaction-owner contour plus bounded supporting owner/test code
- no reopening of proof-path, transport, observer, billing, or booking frozen work
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone

## Scope
- publish this narrow TP and switch canon to it
- next implementation block may touch only the exact tool-reply policy-payload / interaction-owner contour in `decision.py`
- next implementation block may reuse bounded non-frozen owner surfaces in `reasoning_core.py`, `turn_planner.py`, and `dialog_state_service.py`
- add/update bounded regressions for services-overview, fact-guard clarify, pending-question tool replies, and master-override tool replies

## Out of scope
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `ops/diagnose.py`
- broader policy-core route/rescue/payload extraction cutover outside the tool-reply contour
- timeout/degrade boundary family cutover
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922.md`
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
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_reasoning_core.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - planner-owner cutover patterns in `truffles-api/app/services/reasoning_core.py`
  - semantic override normalization in `truffles-api/app/core/turn_planner.py`
  - collect-vs-normalized continuity shaping in `truffles-api/app/core/dialog_state_service.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the next step is semantic owner reuse, not new abstraction growth

## Plan (1..N)
1. Publish this package TP and switch canon to it.
2. On the next implementation block, prove the exact semantic contour and choose the smallest existing non-frozen owner pattern that can absorb it.
3. Delete or bypass the frozen tool-reply payload / interaction-owner authority without adding a wrapper/helper.
4. Add/update bounded regressions.
5. Run deterministic checks and publish either truthful seam deletion or truthful `GAP`.

## DoD
- frozen tool-reply policy-payload / interaction-owner authority in `decision.py:19319-19408` is deleted/unreachable
- no new wrapper/helper or broadened frozen scope exists
- focused regressions pass
- `legacy_freeze_guard.py` passes under exact scope
- canon/session/state record exactly which semantic seam died and which residual family remains

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
- **Stop condition:** if the next implementation contour widens beyond `decision.py:19319-19408`, stop and publish `GAP`
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
- no widening from the tool-reply contour into broader route/payload or timeout/degrade families
- no acceptance/dev rerun substituting for architecture evidence

## Risks / blockers
- the truthful implementation may still require updating the exact frozen waiver record for this narrower semantic contour
- if no existing non-frozen owner pattern can absorb the contour without a new helper, the next block must stop as `GAP`
- if the contour actually depends on broader route/payload extraction than currently proven, the next block must stop as `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen tool-reply policy-payload / interaction-owner shaping still lives in `decision.py`
  - broader route/payload extraction still lives in `decision.py`
  - timeout/degrade boundary families still live in `decision.py`
- **Why not in this block:**
  - this block is TP publication only; implementation must stay bounded to the next rooted contour
- **Risk if deferred:**
  - `boundary_owner` remains partial and final ingress closure remains incomplete
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next block cannot delete this semantic seam without bridge growth, stop and publish `GAP`

## Next-block contract (mandatory)
- **Next block objective:** delete or truthfully localize the frozen tool-reply policy-payload / interaction-owner family on the same contour after guard/send/trace orchestration cutover
- **First deterministic check command:** `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19412p'`
- **Blocked-by conditions:**
  - any need to widen into broader route/payload extraction outside the tool-reply contour
  - any need to widen into timeout/degrade families
  - any new wrapper/helper seam
- **Owner role for closure:** `Top Architect`
