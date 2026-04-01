# TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-TOOL-REPLY-TURN-OUTCOME-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-NEXT-RESIDUAL-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the first exact-scope frozen-waiver runtime cut inside final ingress/coordinator closure. Delete the old direct tool-reply `TurnOutcome` / `TurnOutcomeObservability` authority in frozen `decision.py` by routing that artifact assembly through existing non-frozen `TurnPlanner` + `TurnExecutor` owner surfaces, add bounded regressions, and stop if the slice grows beyond the rooted tool-reply outcome family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/turn_planner.py`
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
  - `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19313,19445p'`
  - `rg -n "build_owner_cutover_artifact|build_owner_cutover_turn_outcome|build_from_policy_override" truffles-api/app/core/turn_executor.py truffles-api/app/core/turn_planner.py`
  - `rg -n "tool reply without evidence|pending_question_preserves_interaction_evidence|active_time_duration_info_interrupt" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - frozen `decision.py` is still the only live runtime location that directly instantiates `TurnOutcome(...)` and `TurnOutcomeObservability(...)`, and that authority is confined to the LLM policy-core tool-reply path at `truffles-api/app/routers/webhook/decision.py:19322-19442`.
  - the old seam survives after `_maybe_apply_fact_guard(...)` returns `None`: the tool-reply path directly authors turn-outcome metadata twice (pre-send pending observability and post-send transport observability) inside frozen `decision.py`.
  - non-frozen owner surfaces already exist for the typed artifact itself: `truffles-api/app/core/turn_planner.py` can synthesize `PolicyDecision` from policy payloads, and `truffles-api/app/core/turn_executor.py` already owns typed boundary and owner-cutover artifact assembly.
  - this slice does **not** require moving `_maybe_apply_fact_guard(...)`, `_send_and_save(...)`, or the surrounding trace/metadata branches out of `decision.py` in the same block.
- `Detected drift (docs vs code)`:
  - the waiver-decision block truthfully locked four rooted frozen families, but the direct tool-reply turn-outcome authority is the narrowest live deletion slice because it is the only remaining direct `TurnOutcome` authoring in frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent waiver-decision block; no second query is allowed or needed
- **Existing solutions found:**
  - move a live slice to the new interface first, then contract the old coordinator authority
- **Decision:** `reuse/integrate`
  - reuse `TurnPlanner` and `TurnExecutor` as the new typed artifact owners for this slice
- **Rejected options:**
  - second web query
  - new compatibility wrapper/helper around `decision.py`
  - broad frozen family move in one step

## Root cause (mandatory)
- **Symptom:** `boundary_owner` remains partial because frozen `decision.py` still directly authors tool-reply `TurnOutcome` / transport observability on a live `/webhook` path.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:19322-19442` and confirm direct `TurnOutcome(...)` plus `TurnOutcomeObservability(...)` authoring.
  2. inspect `truffles-api/app/core/turn_executor.py` and confirm typed artifact assembly already exists for other owner-cutover and boundary paths.
  3. inspect `truffles-api/app/core/turn_planner.py` and confirm a synthetic `PolicyDecision` can be built from policy payloads.
  4. confirm `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py` returns only this frozen block.
- **Evidence:**
  - exact frozen block `decision.py:19322-19442`
  - exact non-frozen typed owner surfaces in `turn_executor.py` and `turn_planner.py`
  - nearby endpoint/runtime-contract tests already covering fact-guard, pending-question, and interrupt tool-reply contours
- **Five Whys:**
  1. Why does `boundary_owner` remain partial? Because a live tool-reply path still builds `TurnOutcome` directly in frozen `decision.py`.
  2. Why is that still live? Because earlier owner cutovers only removed planner/boundary families around it, not the final tool-reply artifact assembly itself.
  3. Why is this the narrowest admissible slice? Because it is the only direct `TurnOutcome` instantiation left in frozen `decision.py`.
  4. Why can this move proceed without a new wrapper/helper? Because `TurnPlanner` and `TurnExecutor` already provide the typed artifact seams; only the frozen callsite needs to route into them.
  5. Why not move the whole `19313-19445` family now? Because guard/send/trace branches would broaden the block beyond one deletable authority seam.
- **Root cause statement:** the surviving frozen boundary hotspot is the direct tool-reply turn-outcome authoring in `decision.py`; typed owners exist, but this live path has not yet been rewired to use them.
- **Fix mechanism:**
  - add one exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml` for the new `decision.py` additions
  - route the tool-reply artifact assembly through `TurnPlanner` + `TurnExecutor`
  - preserve the surrounding guard/send/trace flow in place for this block
  - add bounded regressions that prove the frozen direct `TurnOutcome` authority is gone while user-visible contract stays intact

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the direct frozen tool-reply `TurnOutcome` / `TurnOutcomeObservability` authoring in `truffles-api/app/routers/webhook/decision.py:19322-19442`.
- **FACT:** this block does **not** claim deletion of broader semantic route/payload, expected-reply fallback inference, or timeout/degrade authority in `decision.py`.
- **INFERENCE:** the block is admissible only if those direct frozen `TurnOutcome` constructor calls become unreachable without a new wrapper/helper seam.

## Invariant
- no new wrapper/helper counted as progress
- no scope expansion beyond the direct tool-reply turn-outcome authoring slice plus bounded supporting non-frozen owner code/tests
- no movement of `_maybe_apply_fact_guard(...)`, `_send_and_save(...)`, or the surrounding send/trace flow into a new hotspot in this block
- no reopening of proof-path work, transport, billing, or observer code
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone

## Scope
- add exact waiver lines for frozen `decision.py`
- route the tool-reply turn-outcome assembly in `decision.py:19322-19442` through `TurnPlanner` + `TurnExecutor`
- add bounded regressions in `truffles-api/tests/test_consultant_core_runtime_contracts.py` and `truffles-api/tests/test_message_endpoint.py`
- run deterministic guards/tests and sync canon/session/state with the truthful implementation result

## Out of scope
- edits to `truffles-api/app/routers/webhook/booking.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `ops/diagnose.py`
- moving `_maybe_apply_fact_guard(...)` itself out of `decision.py`
- moving `route_llm_policy_core(...)` out of `decision.py`
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/turn_planner.py`
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

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py::build_from_policy_override`
  - `truffles-api/app/core/turn_executor.py::build_owner_cutover_artifact`
  - existing typed runtime contract tests in `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - existing endpoint tests around fact-guard, booking interrupt, and pending-question tool replies
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the typed owner surfaces already exist; only the frozen tool-reply path still bypasses them

## Plan (1..N)
1. Publish this exact-scope implementation TP and switch canon to it.
2. Add the exact scoped `decision.py` waiver lines to `docs/LEGACY_SUNSET.yaml`.
3. Extend `TurnExecutor` / `TurnPlanner` only as needed to build the typed tool-reply artifact without changing existing owner-cutover behavior.
4. Replace the direct frozen `TurnOutcome` / `TurnOutcomeObservability` constructor path in `decision.py:19322-19442` with the typed artifact call.
5. Add bounded runtime-contract and endpoint regressions.
6. Run deterministic tests and required packet/guard/session checks.
7. Publish the truthful implementation result and the next residual family, if any.

## DoD
- the direct frozen `TurnOutcome` / `TurnOutcomeObservability` authoring at `decision.py:19322-19442` is deleted/unreachable
- no new wrapper/helper or broadened frozen scope exists
- the scoped waiver passes `legacy_freeze_guard.py`
- bounded regressions pass
- canon/session/state reflect exactly which old seam died and which residual family remains

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py truffles-api/app/core/turn_planner.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply or owner_cutover'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'tool_reply_without_evidence_clarifies or active_time_duration_info_interrupt_preserves_time_resume or list_slots_missing_slot_pending_question_preserves_interaction_evidence'`
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
- exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml`
- diff showing frozen `decision.py` no longer instantiates `TurnOutcome` directly
- diff showing typed owner surface additions in `turn_executor.py` / `turn_planner.py`
- focused test output
- canon/session/state naming the deleted seam and the next residual family

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** `py_compile` + focused pytest + freeze/arch/session guards
- **Stop condition:** if the slice requires moving guard/send logic, broad semantic routing, or any frozen family outside `decision.py:19322-19442`, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded local freeze-waived runtime change only; no acceptance/dev rerun in this block
- **Go/no-go signals:**
  - frozen `decision.py` no longer directly instantiates `TurnOutcome`
  - `legacy_freeze_guard.py` passes with the exact scoped waiver
  - focused runtime-contract and endpoint regressions pass
- **Rollback:** revert the `decision.py`, `turn_executor.py`, `turn_planner.py`, test, and `docs/LEGACY_SUNSET.yaml` changes, then rerun deterministic checks
- **Post-release monitoring window:** the next block must target the next residual frozen family, not reopen this seam

## Rollback
1. Revert this block's `decision.py`, owner-surface, test, and `docs/LEGACY_SUNSET.yaml` changes.
2. Re-run the deterministic checks.
3. Revert canon/session/state if the runtime result is rejected.

## No-go
- no helper wrapper counted as progress
- no widening of the frozen waiver beyond the direct tool-reply turn-outcome slice
- no acceptance/dev rerun substituting for seam deletion evidence
- no claim that the whole final ingress/coordinator family is dead after this block

## Risks / blockers
- the typed artifact may need one small `TurnExecutor` API extension; that is allowed only if it centralizes owner authority and does not create a compatibility shell
- `master_override_applied` may require explicit intent/action override in the synthetic policy decision; if that broadens into route/guard logic, stop
- if endpoint regressions reveal hidden dependence on the old inline `turn_outcome` write timing, stop and publish `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - expected-reply/session-memory fallback inference still lives in frozen `decision.py`
  - policy-core route/rescue/payload extraction still lives in frozen `decision.py`
  - timeout/degrade boundary continuity still lives in frozen `decision.py`
  - `_maybe_apply_fact_guard(...)` and tool-reply send/trace orchestration still live in frozen `decision.py`
- **Why not in this block:**
  - each remaining family is a separate live authority slice and would broaden the block past one deletable seam
- **Risk if deferred:**
  - `boundary_owner` remains partial after this block, and broader ingress closure is still incomplete
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- **Expiry/trigger to stop deferral:**
  - if the next block tries to use this new typed artifact as a bridge without killing another old live authority seam, stop and publish `GAP`

## Next-block contract (mandatory)
- **Next block objective:** delete or truthfully localize the next residual frozen ingress family after the direct tool-reply turn-outcome seam is gone
- **First deterministic check command:** `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py`
- **Blocked-by conditions:**
  - any need to move `_maybe_apply_fact_guard(...)` or `_send_and_save(...)` in the same block
  - any new frozen family outside `decision.py:19322-19442`
  - any new wrapper/helper seam
- **Owner role for closure:** `Top Architect`
