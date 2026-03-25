# TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922

## Task metadata
- `TP_ID`: `TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922`
- `Program`: `Consultant Core Controlled Demolition`
- `Block`: `Final Ingress Tool Reply Artifact Sidecar Payload Family Package`
- `Status`: `active`
- `Owner role`: `Brain / Top Architect`
- `Session`: `2026-03-15-consultant-core-governance-lock-a922`
- `Context integrity gate`: `required`
- `Block type`: `package-level family closure`
- `Primary seam family`: `final_ingress_tool_reply_artifact_sidecar_payload`
- `Decision record`: `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `Master package`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-ARTIFACT-SIDECAR-PAYLOAD-FAMILY-PACKAGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-POLICY-PAYLOAD-INTERACTION-OWNER-FAMILY-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-ARTIFACT-SIDECAR-PAYLOAD-CLOSURE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Delete or truthfully localize the next live frozen authority on the same tool-reply ingress contour after the policy-payload / interaction-owner cutover. The target family is the remaining artifact-sidecar payload shaping in frozen `decision.py`; the next implementation block is admissible only if that authority dies without a new wrapper/helper and without widening the frozen hotspot beyond this contour.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md`
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
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19470p'`
  - `rg -n "tool_reply_contract_status|build_owner_cutover_artifact|tool_reply_extra_trace_payloads|tool_reply_extra_meta_updates|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py`
  - `sed -n '2375,2675p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '426,470p' truffles-api/app/core/turn_executor.py`
  - `rg -n "typed_tool_reply_owner_cutover_artifact|tool_reply_owner_decision|tool_reply_owner_state|services_overview|pending_question_preserves_interaction_evidence|master_signal_override" truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - the old direct frozen tool-reply policy-payload / interaction-owner semantic authority is already dead; that contour now exits through non-frozen `truffles-api/app/core/turn_planner.py:178` and `truffles-api/app/core/dialog_state_service.py:372`
  - the surviving frozen contour now starts at `truffles-api/app/routers/webhook/decision.py:19313` and still owns `tool_reply_contract_status`, `TurnExecutor().build_owner_cutover_artifact(...)` input shaping, auxiliary trace sidecars, auxiliary metadata sidecars, and the argument bundle passed into `reasoning_core._finalize_turn_planner_owner_cutover(...)`
  - the same contour remains live because `decision.py` still computes the owner-cutover artifact sidecar payloads directly before returning through `_finalize_turn_planner_owner_cutover(...)`
  - existing non-frozen owner surfaces already exist for the downstream artifact and finalization path in `truffles-api/app/core/turn_executor.py` and `truffles-api/app/services/reasoning_core.py`
  - this block is about the artifact / sidecar payload family only; it does not reopen broader route/rescue/payload extraction elsewhere in `decision.py`, timeout/degrade families, or acceptance proof-path work
- `Detected drift (docs vs code)`:
  - repo truth now says the next admissible move is to author the tool-reply artifact-sidecar payload family package; canon must switch from the executed policy-payload / interaction-owner block to this narrower surviving frozen contour

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com Parallel Change Strangler Fig Application legacy coordinator side effects`
- **Date/time (local):** `2026-03-19 20:30 +0500`
- **Sources opened (from this query):**
  - `https://www.martinfowler.com/articles/patterns-legacy-displacement/event-interception.html`
- **Source quality:**
  - high-signal primary architecture guidance
- **Existing solutions found:**
  - keep displacing one live seam at a time through an existing integration point instead of widening legacy edits or introducing a new transitional shell
- **Decision:** `reuse/integrate`
  - reuse `TurnExecutor().build_owner_cutover_artifact(...)` and `reasoning_core._finalize_turn_planner_owner_cutover(...)` as the non-frozen destination surfaces for this contour
- **Rejected options:**
  - second web query
  - new compatibility wrapper/helper around frozen `decision.py`
  - broad multi-family frozen move in one block

## Root cause (mandatory)
- **Symptom:** `boundary_owner` remains partial after the policy-payload / interaction-owner cutover because frozen `decision.py` still owns live artifact-sidecar payload shaping on the same tool-reply contour.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19313-19465`
  2. confirm `tool_reply_contract_status` is still computed inline in frozen `decision.py`
  3. confirm `TurnExecutor().build_owner_cutover_artifact(...)` is still parameterized inline from frozen locals there
  4. confirm `tool_reply_extra_trace_payloads` and `tool_reply_extra_meta_updates` are still constructed inline there
  5. confirm the contour still returns through `reasoning_core._finalize_turn_planner_owner_cutover(...)` with that frozen sidecar payload bundle
- **Evidence:**
  - exact frozen contour `decision.py:19313-19465`
  - existing non-frozen artifact/finalize owner surfaces in `turn_executor.py` and `reasoning_core.py`
  - focused runtime-contract and endpoint regressions that already cover this contour's semantic preconditions
- **Five Whys:**
  1. Why does `boundary_owner` remain partial? Because frozen `decision.py` still shapes live artifact-sidecar payloads before the shared owner-finalize path.
  2. Why is that still live? Because the previous block deleted only the upstream semantic payload / interaction-owner authority, not the downstream artifact-sidecar shaping authority.
  3. Why is this the next admissible slice? Because it is the narrowest surviving live authority on the same rooted tool-reply ingress contour.
  4. Why can this count as architectural progress? Because the target is live authority deletion inside final ingress, not a proof-path symptom fix.
  5. Why not widen into broader route/payload extraction or timeout/degrade now? Because those are separate frozen families and would break package-level closure discipline.
- **Root cause statement:** the surviving frozen hotspot on this contour is now the artifact/sidecar payload assembly that still lives directly in `decision.py` and decides the contract/meta/trace bundle handed to the shared owner-finalize path.
- **Fix mechanism:**
  - reuse existing non-frozen `TurnExecutor` and `reasoning_core` owner surfaces
  - move the tool-reply artifact/sidecar payload shaping out of frozen `decision.py` without a new wrapper/helper
  - keep the block bounded to the same contour and stop if it expands into broader route/payload or timeout/degrade families

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the frozen tool-reply artifact-sidecar payload authority in `truffles-api/app/routers/webhook/decision.py:19313-19465`.
- **FACT:** this includes live ownership of `tool_reply_contract_status`, owner-cutover artifact assembly inputs, auxiliary trace payload shaping, auxiliary metadata payload shaping, and the frozen argument bundle passed into `reasoning_core._finalize_turn_planner_owner_cutover(...)` on this contour.
- **FACT:** this block does **not** claim deletion of broader route/rescue/payload extraction elsewhere in `decision.py` or timeout/degrade families.
- **INFERENCE:** the block is admissible only if that artifact-sidecar authority becomes deleted/unreachable and does not reappear as a new mixed hotspot.

## Invariant
- no new wrapper/helper counted as progress
- no widening beyond the exact artifact-sidecar payload contour plus bounded supporting owner/test code
- no reopening of proof-path, transport, observer, billing, or booking frozen work
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone

## Scope
- publish this narrow TP and switch canon to it
- next implementation block may touch only the exact tool-reply artifact-sidecar payload contour in `decision.py`
- next implementation block may reuse bounded non-frozen owner surfaces in `reasoning_core.py`, `turn_executor.py`, `turn_planner.py`, and `dialog_state_service.py`
- add/update bounded regressions for services-overview, fact-guard clarify, pending-question tool replies, and master-override tool replies if the contour changes their artifact/meta envelopes

## Out of scope
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `ops/diagnose.py`
- broader policy-core route/rescue/payload extraction cutover outside the tool-reply contour
- timeout/degrade boundary family cutover
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md`
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
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_reasoning_core.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `TurnExecutor().build_owner_cutover_artifact(...)`
  - `reasoning_core._finalize_turn_planner_owner_cutover(...)`
  - existing tool-reply owner decision/state builders in `turn_planner.py` and `dialog_state_service.py`
- **External reuse:**
  - Fowler `Event Interception`
- **Why not reinvent the wheel:**
  - the next step is owner-surface reuse, not new abstraction growth

## Plan (1..N)
1. Publish this package TP and switch canon to it.
2. On the next implementation block, prove the exact artifact-sidecar contour and choose the smallest existing non-frozen owner pattern that can absorb it.
3. Delete or bypass the frozen artifact-sidecar authority without adding a wrapper/helper.
4. Add/update bounded regressions.
5. Run deterministic checks and publish either truthful seam deletion or truthful `GAP`.

## DoD
- frozen tool-reply artifact-sidecar payload authority in `decision.py:19313-19465` is deleted/unreachable
- no new wrapper/helper or broadened frozen scope exists
- focused regressions pass
- `legacy_freeze_guard.py` passes under exact scope
- canon/session/state record exactly which artifact-sidecar seam died and which residual family remains

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
- **Stop condition:** if the next implementation contour widens beyond `decision.py:19313-19465`, stop and publish `GAP`
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
- the truthful implementation may still require updating the exact frozen waiver record for this narrower artifact-sidecar contour
- if no existing non-frozen owner pattern can absorb the contour without a new helper, the next block must stop as `GAP`
- if the contour actually depends on broader route/payload extraction than currently proven, the next block must stop as `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen tool-reply artifact-sidecar payload shaping still lives in `decision.py`
  - broader route/payload extraction still lives in `decision.py`
  - timeout/degrade boundary families still live in `decision.py`
- **Why not in this block:**
  - this block is TP publication only; implementation must stay bounded to the next rooted contour
- **Risk if deferred:**
  - `boundary_owner` remains partial and final ingress closure remains incomplete
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next block cannot delete this artifact-sidecar seam without bridge growth, stop and publish `GAP`

## Next-block contract (mandatory)
- **Next block objective:**
  - `implement_consultant_core_final_ingress_tool_reply_artifact_sidecar_payload_family_closure_bundle`
- **First deterministic check command:**
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19470p'`
- **Blocked-by conditions:**
  - need for a new wrapper/helper
  - need to widen beyond `decision.py:19313-19465`
  - need to reopen broader route/payload extraction or timeout/degrade families
- **Owner role for closure:**
  - `Top Architect / Brain`
