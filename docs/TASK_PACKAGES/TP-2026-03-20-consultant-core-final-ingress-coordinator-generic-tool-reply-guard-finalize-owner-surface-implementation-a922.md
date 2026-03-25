# TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-GUARD-FINALIZE-OWNER-SURFACE-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-OWNER-SURFACE-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-GENERIC-TOOL-REPLY-GUARD-FINALIZE-POST-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Delete the next surviving generic tool-reply guard/finalize entry authority on the final-ingress hotspot. This block is admissible only if frozen `decision.py` stops directly invoking `_maybe_apply_fact_guard(...)` and `_finalize_turn_planner_owner_cutover(...)` on the rooted generic tool-reply contour by routing that contour through one bounded owner surface in existing non-frozen `reasoning_core.py`, without moving the nested `_maybe_apply_fact_guard(...)` body itself and without widening into the broader semantic / continuity families.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md`
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
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "build_tool_reply_owner_execution\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_executor.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19373,19442p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2376,2505p'`
  - `rg -n "tool_reply_owner|tool_reply_without_evidence_clarifies|list_slots_missing_slot_pending_question_preserves_interaction_evidence|llm_policy_core_catalog_service_reply_applies_master_signal_override" truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - live fallback still remains explicit at `truffles-api/app/services/reasoning_core.py:8010` and `:8022`
  - frozen `decision.py:19406-19442` still directly invokes `_maybe_apply_fact_guard(...)` and then `_finalize_turn_planner_owner_cutover(...)` on the surviving generic tool-reply contour
  - `truffles-api/app/core/turn_executor.py:629` now owns the generic tool-reply decision/state/payload execution bundle, but there is still no reusable non-frozen entry surface for the remaining generic guard/finalize step
  - nested `_maybe_apply_fact_guard(...)` authority itself remains frozen at `truffles-api/app/routers/webhook/decision.py:9630-9718` and is explicitly out of scope for body migration in this block
- `Detected drift (docs vs code)`:
  - after the first generic owner-surface cut landed, leaving canon on the old implementation TP while adding the next guard/finalize owner surface would be repo-truth drift

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent generic owner-surface block; no second query is allowed or needed
- **Existing solutions found:**
  - materialize the missing reusable new-path surface, then contract the duplicated legacy authority until it becomes unreachable
- **Decision:** `reuse/integrate`
  - reuse the existing generic `ToolReplyOwnerExecution` bundle in `TurnExecutor` and the existing `_finalize_turn_planner_owner_cutover(...)` surface in `reasoning_core.py`
- **Rejected options:**
  - second web query
  - widening into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756`
  - moving the nested `_maybe_apply_fact_guard(...)` body itself in this block

## Root cause (mandatory)
- **Symptom:** after the generic tool-reply decision/state/payload owner-surface cut landed, frozen `decision.py` still owns the direct generic tool-reply fact-guard / finalizer entry on the same rooted contour.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/decision.py:19377-19442`.
  2. Confirm the contour already uses `TurnExecutor().build_tool_reply_owner_execution(...)`.
  3. Confirm the same contour still directly invokes `_maybe_apply_fact_guard(...)` and `_finalize_turn_planner_owner_cutover(...)`.
  4. Confirm `truffles-api/app/services/reasoning_core.py` has the downstream finalizer but not yet one generic tool-reply entry surface for that step.
- **Evidence:**
  - direct frozen guard/finalize entry still present on the rooted generic tool-reply contour
  - generic decision/state/payload owner execution already exists in non-frozen `TurnExecutor`
  - specialized reasoning-core safe lanes are not a generic replacement for all tool replies
- **Five Whys (or equivalent):**
  1. Why does the residual family stay live? Because frozen `decision.py` still decides when/how the generic tool-reply guard/finalize step is entered.
  2. Why did the previous block not close that? Because it only deleted the direct decision/state/payload authority.
  3. Why can the current owner surfaces not fully replace this contour yet? Because there is no reusable generic entry surface for the guard/finalize step.
  4. Why is `reasoning_core.py` the right destination? Because it already owns `_finalize_turn_planner_owner_cutover(...)` and the downstream owner-cutover transport/orchestration contract.
  5. Why keep `_maybe_apply_fact_guard(...)` body frozen in this block? Because migrating that nested body would widen into a broader fact-guard family instead of deleting the exact entry seam.
- **Root cause statement:** the surviving residual persists because the repo has a reusable generic tool-reply execution bundle and a reusable downstream finalizer, but it does not yet have one reusable non-frozen owner surface for the generic guard/finalize entry step; frozen `decision.py` still performs that entry inline.
- **Fix mechanism:**
  - add one bounded generic tool-reply guard/finalize owner surface in existing `truffles-api/app/services/reasoning_core.py`
  - route frozen `decision.py:19406-19442` through it
  - leave the nested `_maybe_apply_fact_guard(...)` body at `decision.py:9630-9718` untouched in this exact block

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_executor.py:build_tool_reply_owner_execution(...)`
  - `truffles-api/app/services/reasoning_core.py:_finalize_turn_planner_owner_cutover(...)`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the repo already has the upstream generic execution surface and the downstream finalizer; this block only materializes the missing generic entry surface between them

## Invariant
- no widening into `decision.py:1218-1320`, `decision.py:12478-12545`, or `decision.py:15659-15756`
- no moving the nested `_maybe_apply_fact_guard(...)` body out of `decision.py:9630-9718`
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is `done`
- no proof-path / acceptance / unrelated frozen family work

## Scope
- publish and activate this exact-scope implementation TP
- add one bounded generic tool-reply guard/finalize owner surface in `truffles-api/app/services/reasoning_core.py`
- reroute frozen `decision.py:19406-19442` through that owner surface
- add focused runtime-contract coverage for the new reasoning-core owner surface
- sync canon / waiver / packet / session truthfully

## Out of scope
- moving `_maybe_apply_fact_guard(...)` body itself out of `decision.py`
- changing the remaining residual families at `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756`
- acceptance or `L2` reruns
- `booking.py` / `pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md`
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
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## Plan (1..N)
1. Publish this implementation TP and switch canon / waiver to it.
2. Add one bounded generic tool-reply guard/finalize owner surface in `reasoning_core.py`.
3. Replace the direct frozen guard/finalize entry in `decision.py` with that owner surface.
4. Add focused runtime-contract coverage and rerun focused + mandatory checks.
5. Sync docs/session truthfully with the exact seam deletion or `GAP`.

## DoD
- active canon points to this implementation TP
- frozen `decision.py` no longer directly invokes `_maybe_apply_fact_guard(...)` or `_finalize_turn_planner_owner_cutover(...)` on the targeted generic tool-reply contour
- the new owner surface lives in existing non-frozen owner code only
- focused runtime-contract and endpoint checks stay green
- mandatory guard/session checks stay green
- docs truthfully state exactly which old seam died, or publish `GAP`

## Checks
- `rg -n "_finalize_tool_reply_owner_execution|build_tool_reply_owner_execution\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
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
- diff showing the direct frozen generic tool-reply guard/finalize entry is gone
- focused test outputs above
- packet / guard / architecture / session checks
- synced canon + waiver docs

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused runtime-contract + endpoint + mandatory guards only
- **Stop condition:** if the generic guard/finalize owner surface still cannot delete an old live seam without widening into the nested fact-guard body or broader residual families, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** exact-scope runtime cut under the frozen waiver with focused regressions first, then mandatory guards
- **Go/no-go signals:** targeted seam deleted or unreachable, focused tests green, legacy freeze guard green, no widening beyond declared contour
- **Rollback:** revert the TP/canon sync plus the code diff, regenerate packet, rerun guards
- **Post-release monitoring window:** the next residual after this block must be either the nested fact-guard body / broader residual audit or a truthful `GAP`, not another safe semantic slice

## Rollback
1. Revert this implementation TP / canon / waiver sync.
2. Revert the code changes in `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/routers/webhook/decision.py`, and focused tests.
3. Regenerate packet and rerun the mandatory checks.

## No-go
- no widening into the broader residual families
- no moving `_maybe_apply_fact_guard(...)` body itself in this block
- no hidden semantic logic move into regex/phrase branches
- no claim of owner completion from this block alone
- no second web search

## Risks / blockers
- if the new `reasoning_core.py` surface is only a thin wrapper while leaving the old frozen authority effectively intact, this block is not progress
- if `legacy_freeze_guard.py` rejects the needed frozen callsite change under the current waiver, sync the waiver truthfully or stop
- if the nested fact-guard body becomes required for correctness changes beyond simple delegation, stop and publish `GAP`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - any untouched subset of `truffles-api/app/routers/webhook/decision.py:19373-19442`
- **Why not in this block:**
  - this block only targets the generic tool-reply guard/finalize entry seam
- **Risk if deferred:**
  - owners remain partial while the remaining nested fact-guard / broader final-ingress families stay live
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - if this block fails to delete an old live seam, stop and escalate instead of continuing partial contractions

## Next-block contract (mandatory)
- **Next block objective:**
  - delete or truthfully localize the next remaining residual after this exact guard/finalize owner-surface cut, expected to be the nested fact-guard body family at `decision.py:9630-9718` or a truthful post-cut residual audit
- **First deterministic check command:**
  - `rg -n "_finalize_tool_reply_owner_execution|build_tool_reply_owner_execution\(|_maybe_apply_fact_guard|_finalize_turn_planner_owner_cutover" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_executor.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '19373,19442p;9630,9718p' && nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2376,2765p'`
- **Blocked-by conditions:**
  - need to widen into `decision.py:1218-1320`, `:12478-12545`, or `:15659-15756`
  - need to move `_maybe_apply_fact_guard(...)` body itself in this block
  - need to reopen `booking.py`, `pending.py`, proof-path, or acceptance work
  - need for a second web query
- **Owner role for closure:** `Top Architect`
