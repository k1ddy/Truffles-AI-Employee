# TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-NEXT-RESIDUAL-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the generic tool-reply owner-surface bundle for the surviving final-ingress hotspot. This block is admissible only if the old direct generic tool-reply decision/state/payload authority in frozen `decision.py` becomes deleted or unreachable by materializing one reusable owner surface inside existing non-frozen owner files, without reopening broader semantic / continuity families and without moving `_maybe_apply_fact_guard(...)` into a new mixed hotspot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
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
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "build_tool_reply_owner_decision\(|build_tool_reply_owner_state\(|build_tool_reply_owner_cutover_payload\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19373,19456p'`
  - `nl -ba truffles-api/app/core/turn_executor.py | sed -n '98,140p;433,621p'`
  - `rg -n "tool_reply_owner" truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - live fallback still remains explicit at `truffles-api/app/services/reasoning_core.py:8010` and `:8022`.
  - frozen `decision.py:19377-19419` still directly builds `TurnPlanner().build_tool_reply_owner_decision(...)`, `DialogStateService().build_tool_reply_owner_state(...)`, and `TurnExecutor().build_tool_reply_owner_cutover_payload(...)` inline before fact guard / finalizer execution.
  - `truffles-api/app/core/turn_executor.py` already owns the typed tool-reply artifact contract, but it does not yet own the generic decision/state/payload assembly as one reusable owner surface.
  - current tests already cover the three split tool-reply owner surfaces independently.
- `Detected drift (docs vs code)`:
  - after the generic owner-surface decision block, the active next move must be runtime implementation; leaving canon on the decision TP while changing code would be repo-truth drift.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent decision blocks; no second query is allowed or needed
- **Existing solutions found:**
  - materialize the missing reusable new-path surface, then contract the duplicated legacy authority until it becomes unreachable
- **Decision:** `reuse/integrate`
  - reuse existing `TurnPlanner`, `DialogStateService`, `TurnExecutor`, and the already-landed owner cutover finalizer
- **Rejected options:**
  - second web query
  - another safe semantic slice instead of generic owner-surface work
  - moving `_maybe_apply_fact_guard(...)` into a brand new helper layer in this block

## Root cause (mandatory)
- **Symptom:** six admissible broader-owner slices landed, but frozen `decision.py` still owns the generic tool-reply decision/state/payload assembly on the strongest residual contour.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/decision.py:19377-19419` and confirm the direct generic tool-reply owner assembly still lives there.
  2. Inspect `truffles-api/app/core/turn_executor.py:493-621` and confirm the owner module still starts only after decision/state are already built.
  3. Inspect `truffles-api/app/services/reasoning_core.py:5779-5900`, `:6063-6180`, `:6253-6406`, and `:6493-6642` and confirm the owner path is repeated across specialized lanes.
- **Evidence:**
  - direct frozen tool-reply decision/state/payload assembly still present
  - typed owner payload builder already exists in non-frozen code
  - specialized owner lanes repeat the same build pattern outside frozen scope
- **Five Whys (or equivalent):**
  1. Why does the residual family still stay live? Because frozen `decision.py` still owns the generic tool-reply decision/state/payload construction.
  2. Why do specialized owner lanes not solve that? Because they are contour-specific and do not expose one reusable generic surface.
  3. Why is that a blocker now? Because the current strongest residual is generic tool-reply owner construction, not another safe semantic contour.
  4. Why is one generic owner surface the next truthful move? Because it deletes duplicated authority in frozen scope without reopening broader extraction families.
  5. Why keep fact guard out of this exact block if possible? Because moving `_maybe_apply_fact_guard(...)` now would widen into a separate nested boundary authority and risks reintroducing a mixed hotspot before the generic owner surface is proven.
- **Root cause statement:** the remaining residual persists because the repo has typed tool-reply artifact ownership but not yet one reusable generic owner surface for tool-reply decision/state/payload assembly, so frozen `decision.py` still performs that assembly inline.
- **Fix mechanism:**
  - materialize one generic tool-reply owner execution surface inside `truffles-api/app/core/turn_executor.py`
  - route frozen `decision.py:19377-19419` through it
  - leave `_maybe_apply_fact_guard(...)` and broader residual families untouched in this exact block unless they are required for correctness and still bounded

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py:build_tool_reply_owner_decision(...)`
  - `truffles-api/app/core/dialog_state_service.py:build_tool_reply_owner_state(...)`
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_cutover_payload(...)`
  - `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the repo already has the three split owner surfaces; this block only materializes their missing generic composition surface inside an existing owner file

## Invariant
- no widening into `decision.py:1218-1320`, `decision.py:12478-12545`, or `decision.py:15659-15756`
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is `done`
- no new wrapper/helper around frozen ingress counted as progress
- no proof-path / acceptance / unrelated frozen family work

## Scope
- activate the runtime implementation TP for the generic tool-reply owner surface
- add one reusable generic tool-reply owner execution surface in `truffles-api/app/core/turn_executor.py`
- reroute the frozen residual tool-reply decision/state/payload contour through that owner surface
- add focused runtime-contract coverage for the new owner surface
- sync canon / waiver / packet / session truthfully

## Out of scope
- moving `_maybe_apply_fact_guard(...)` out of `decision.py` in this block unless required for correctness and still bounded
- changing the remaining residual families at `decision.py:1218-1320`, `:12478-12545`, `:15659-15756`
- acceptance or `L2` reruns
- `booking.py` / `pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
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
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## Plan (1..N)
1. Publish this implementation TP and sync active canon / waiver to it.
2. Add one generic tool-reply owner execution surface in `TurnExecutor` using existing owner contracts.
3. Replace the direct generic tool-reply decision/state/payload assembly in frozen `decision.py` with that owner surface.
4. Add focused runtime-contract coverage and rerun focused + mandatory checks.
5. Sync docs/session truthfully with the exact seam deletion or `GAP`.

## DoD
- active canon points to this implementation TP
- frozen `decision.py` no longer directly calls `build_tool_reply_owner_decision(...)`, `build_tool_reply_owner_state(...)`, and `build_tool_reply_owner_cutover_payload(...)` on the targeted residual contour
- the new owner surface lives in existing non-frozen owner code only
- focused runtime-contract and endpoint checks stay green
- mandatory guard/session checks stay green
- docs truthfully state exactly which old seam died, or publish `GAP`

## Checks
- `rg -n "build_tool_reply_owner_decision\(|build_tool_reply_owner_state\(|build_tool_reply_owner_cutover_payload\(|build_tool_reply_owner_execution\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply_owner'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'tool_reply_without_evidence_clarifies or list_slots_missing_slot_pending_question_preserves_interaction_evidence or llm_policy_core_catalog_service_reply_applies_master_signal_override'`
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
- diff showing the direct frozen generic tool-reply assembly is gone
- focused test outputs above
- packet / guard / architecture / session checks
- synced canon + waiver docs

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused runtime-contract + endpoint + mandatory guards only
- **Stop condition:** if the generic owner surface still cannot delete an old live seam without widening into nested fact-guard or broader residual families, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** exact-scope runtime cut under the frozen waiver with focused regressions first, then mandatory guards
- **Go/no-go signals:** targeted seam deleted or unreachable, focused tests green, legacy freeze guard green, no widening beyond declared contour
- **Rollback:** revert the implementation TP/canon sync plus the code diff, regenerate packet, rerun guards
- **Post-release monitoring window:** the next residual after this block must be the remaining fact-guard/finalize authority or a truthful `GAP`, not another safe semantic slice

## Rollback
1. Revert the new implementation TP / canon / waiver sync.
2. Revert the code changes in `truffles-api/app/core/turn_executor.py`, `truffles-api/app/routers/webhook/decision.py`, and focused tests.
3. Regenerate packet and rerun the mandatory checks.

## No-go
- no new helper/wrapper around frozen ingress outside existing owner files
- no widening into the broader residual families
- no hidden semantic logic move into regex/phrase branches
- no claim of owner completion from this block alone
- no second web search

## Risks / blockers
- if the generic owner surface still needs frozen `_maybe_apply_fact_guard(...)` internals to build the owner execution itself, this block may still stop as `GAP`
- if `legacy_freeze_guard.py` rejects the needed frozen callsite change under the current waiver, sync the waiver truthfully or stop

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - any untouched subset of `truffles-api/app/routers/webhook/decision.py:19373-19456`
- **Why not in this block:**
  - this block only targets the generic tool-reply decision/state/payload assembly seam
- **Risk if deferred:**
  - owners remain partial while the remaining fact-guard / finalizer family stays live
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - if this block fails to delete an old live seam, stop and escalate instead of continuing partial contractions

## Next-block contract (mandatory)
- **Next block objective:**
  - delete or bypass the next remaining generic tool-reply residual after this exact owner-surface cut, expected to be the nested fact-guard / finalize authority inside `decision.py:19373-19456`, or publish `GAP`
- **First deterministic check command:**
  - `rg -n "build_tool_reply_owner_decision\(|build_tool_reply_owner_state\(|build_tool_reply_owner_cutover_payload\(|build_tool_reply_owner_execution\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19373,19456p' && nl -ba truffles-api/app/core/turn_executor.py | sed -n '98,140p;433,700p'`
- **Blocked-by conditions:**
  - need to widen into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756`
  - need to move `_maybe_apply_fact_guard(...)` into a new mixed helper layer
  - need to reopen `booking.py`, `pending.py`, proof-path, or acceptance work
  - need for a second web query
- **Owner role for closure:** `Top Architect`
