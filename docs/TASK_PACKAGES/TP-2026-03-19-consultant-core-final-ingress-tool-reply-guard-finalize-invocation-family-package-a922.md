# TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922

## Task metadata
- `TP_ID`: `TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922`
- `Program`: `Consultant Core Controlled Demolition`
- `Block`: `Final Ingress Tool Reply Guard Finalize Invocation Family Package`
- `Status`: `active`
- `Owner role`: `Brain / Top Architect`
- `Session`: `2026-03-15-consultant-core-governance-lock-a922`
- `Context integrity gate`: `required`
- `Block type`: `package-level family closure`
- `Primary seam family`: `final_ingress_tool_reply_guard_finalize_invocation`
- `Decision record`: `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `Master package`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-GUARD-FINALIZE-INVOCATION-FAMILY-PACKAGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-ARTIFACT-SIDECAR-PAYLOAD-FAMILY-PACKAGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-GUARD-FINALIZE-INVOCATION-CLOSURE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Delete or truthfully localize the next live frozen authority on the same tool-reply ingress contour after the artifact-sidecar payload cutover. The target family is the remaining direct finalizer invocation plus fact-guard wiring in frozen `decision.py`; the next implementation block is admissible only if that authority dies without a new wrapper/helper and without widening the frozen hotspot beyond this contour.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922.md`
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
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19357,19405p'`
  - `rg -n "_finalize_turn_planner_owner_cutover|_maybe_apply_fact_guard|guard_response_resolver|trace_payload_override|extra_trace_payloads|extra_meta_updates" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py`
  - `sed -n '2375,2465p' truffles-api/app/services/reasoning_core.py`
  - `rg -n "tool_reply_without_evidence_clarifies|services_overview|pending_question_preserves_interaction_evidence|master_signal_override" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - the old direct frozen tool-reply artifact / sidecar payload authority is already dead; that contour now exits through non-frozen `truffles-api/app/core/turn_executor.py:493`
  - the surviving frozen contour now starts at `truffles-api/app/routers/webhook/decision.py:19357` and still owns the direct `_finalize_turn_planner_owner_cutover(...)` invocation, `_maybe_apply_fact_guard(...)` resolver wiring, and the frozen argument bundle passed into the shared owner-finalize path
  - the same contour remains live because `decision.py` still decides when and how the shared finalizer is invoked on this tool-reply path
  - existing non-frozen owner surfaces already exist in `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`; this block is about deleting the frozen invocation authority, not rebuilding the downstream owner
  - this block is about the guard/finalize invocation family only; it does not reopen broader route/rescue/payload extraction elsewhere in `decision.py`, timeout/degrade families, or acceptance proof-path work
- `Detected drift (docs vs code)`:
  - repo truth now says the next admissible move is to author the tool-reply guard/finalize invocation family package; canon must switch from the executed artifact-sidecar block to this narrower surviving frozen contour

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com Parallel Change Strangler Fig Application legacy coordinator side effects`
- **Date/time (local):** `2026-03-19 20:30 +0500`
- **Sources opened (from this query):**
  - `https://www.martinfowler.com/articles/patterns-legacy-displacement/event-interception.html`
- **Source quality:**
  - high-signal primary architecture guidance
- **Reuse rule for this block:**
  - reused from the parent final-ingress line; no second query is needed before the next implementation block
- **Existing solutions found:**
  - keep displacing one live seam at a time through an existing integration point instead of widening legacy edits or introducing a new transitional shell
- **Decision:** `reuse/integrate`
  - reuse `reasoning_core._finalize_turn_planner_owner_cutover(...)` as the non-frozen destination surface for this contour
- **Rejected options:**
  - second web query
  - new compatibility wrapper/helper around frozen `decision.py`
  - broad multi-family frozen move in one block

## Root cause (mandatory)
- **Symptom:** `boundary_owner` remains partial after the artifact-sidecar cutover because frozen `decision.py` still owns the live guard/finalize invocation on the same tool-reply contour.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19357-19390`
  2. confirm `decision.py` still directly calls `reasoning_core._finalize_turn_planner_owner_cutover(...)`
  3. confirm `_maybe_apply_fact_guard(...)` is still wired inline there through `guard_response_resolver`
  4. confirm frozen `decision.py` still assembles the invocation bundle for `artifact`, `trace_payload_override`, `extra_trace_payloads`, and `extra_meta_updates`
  5. compare with the existing non-frozen owner finalizer in `truffles-api/app/services/reasoning_core.py:2375`
- **Evidence:**
  - exact frozen contour `decision.py:19357-19390`
  - existing non-frozen finalizer surface in `reasoning_core.py`
  - focused runtime-contract and endpoint regressions already covering this contour's tool-reply semantics
- **Five Whys:**
  1. Why does `boundary_owner` remain partial? Because frozen `decision.py` still owns the final invocation of the shared owner-finalize path on this contour.
  2. Why is that still live? Because the previous block deleted only the upstream artifact-sidecar shaping authority, not the direct frozen invocation authority.
  3. Why is this the next admissible slice? Because it is the narrowest surviving live authority on the same rooted tool-reply ingress contour.
  4. Why can this count as architectural progress? Because the target is live authority deletion inside final ingress, not a proof-path symptom fix.
  5. Why not widen into broader route/payload extraction or timeout/degrade now? Because those are separate frozen families and would break package-level closure discipline.
- **Root cause statement:** the surviving frozen hotspot on this contour is now the direct finalizer invocation and fact-guard wiring that still lives directly in `decision.py` and decides how the shared owner-finalize path is entered.
- **Fix mechanism:**
  - reuse existing non-frozen `reasoning_core._finalize_turn_planner_owner_cutover(...)`
  - move or bypass the direct tool-reply finalizer invocation and guard wiring out of frozen `decision.py` without a new wrapper/helper
  - keep the block bounded to the same contour and stop if it expands into broader route/payload or timeout/degrade families

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the frozen tool-reply guard/finalize invocation authority in `truffles-api/app/routers/webhook/decision.py:19357-19390`.
- **FACT:** this includes live ownership of the direct `_finalize_turn_planner_owner_cutover(...)` call, `_maybe_apply_fact_guard(...)` resolver wiring, and the exact frozen argument bundle passed into that call on this contour.
- **FACT:** this block does **not** claim deletion of broader route/rescue/payload extraction elsewhere in `decision.py` or timeout/degrade families.
- **INFERENCE:** the block is admissible only if that invocation authority becomes deleted/unreachable and does not reappear as a new mixed hotspot.

## Invariant
- no new wrapper/helper counted as progress
- no widening beyond the exact guard/finalize invocation contour plus bounded supporting owner/test code
- no reopening of proof-path, transport, observer, billing, or booking frozen work
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone

## Scope
- publish this narrow TP and switch canon to it
- next implementation block may touch only the exact tool-reply guard/finalize invocation contour in `decision.py`
- next implementation block may reuse bounded non-frozen owner surfaces in `reasoning_core.py` and `turn_executor.py`
- add/update bounded regressions for fact-guard clarify, services-overview, pending-question tool replies, and master-override tool replies if this contour changes their finalize/guard envelopes

## Out of scope
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `ops/diagnose.py`
- broader policy-core route/rescue/payload extraction cutover outside the tool-reply contour
- timeout/degrade boundary family cutover
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922.md`
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
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_reasoning_core.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `reasoning_core._finalize_turn_planner_owner_cutover(...)`
  - `TurnExecutor().build_tool_reply_owner_cutover_payload(...)`
- **External reuse:**
  - Fowler `Event Interception`
- **Why not reinvent the wheel:**
  - the next step is deleting the frozen invocation authority, not growing another integration shell

## Plan (1..N)
1. Publish this package TP and switch canon to it.
2. On the next implementation block, prove the exact guard/finalize invocation contour and choose the smallest existing non-frozen owner pattern that can absorb it.
3. Delete or bypass the frozen invocation authority without adding a wrapper/helper.
4. Add/update bounded regressions.
5. Run deterministic checks and publish either truthful seam deletion or truthful `GAP`.

## DoD
- frozen tool-reply guard/finalize invocation authority in `decision.py:19357-19390` is deleted/unreachable
- no new wrapper/helper or broadened frozen scope exists
- focused regressions pass
- `legacy_freeze_guard.py` passes under exact scope
- canon/session/state record exactly which invocation seam died and which residual family remains

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
- **Stop condition:** if the next implementation contour widens beyond `decision.py:19357-19390`, stop and publish `GAP`
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
- the truthful implementation may still require updating the exact frozen waiver record for this narrower invocation contour
- if no existing non-frozen owner pattern can absorb the contour without a new helper, the next block must stop as `GAP`
- if the contour actually depends on broader route/payload extraction than currently proven, the next block must stop as `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen tool-reply guard/finalize invocation still lives in `decision.py`
  - broader route/payload extraction still lives in `decision.py`
  - timeout/degrade boundary families still live in `decision.py`
- **Why not in this block:**
  - this block is TP publication only; implementation must stay bounded to the next rooted contour
- **Risk if deferred:**
  - `boundary_owner` remains partial and final ingress closure remains incomplete
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next block cannot delete this invocation seam without bridge growth, stop and publish `GAP`

## Next-block contract (mandatory)
- **Next block objective:**
  - `implement_consultant_core_final_ingress_tool_reply_guard_finalize_invocation_family_closure_bundle`
- **First deterministic check command:**
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19357,19405p'`
- **Blocked-by conditions:**
  - need for a new wrapper/helper
  - need to widen beyond `decision.py:19357-19390`
  - need to reopen broader route/payload extraction or timeout/degrade families
- **Owner role for closure:**
  - `Top Architect / Brain`
