# TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FROZEN-BOUNDARY-WAIVER-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-REWORK-PLAN-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-rework-plan-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TIMEOUT-OWNER-FROZEN-WAIVER-IMPLEMENTATION-A922`, `CONSULTANT-CORE-TIMEOUT-OWNER-BROADER-REWORK-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish the stop-the-line waiver decision for the frozen timeout-owner boundary seam. This block must prove whether a truthful non-frozen bypass can be authored from `reasoning_core` before the legacy fallback, and if not, switch canon to an explicit frozen-boundary waiver decision instead of pretending that a safe implementation TP already exists.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-rework-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "resolve_timeout_owner_boundary|matched_booking_followup_state|timeout_resume_contract_state|policy_core_timeout_degrade|pending_info_signal|intent_decomp_payload" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '288,302p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1609,1638p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1870,1888p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '11072,11100p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '14311,14658p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '15435,15766p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '230,339p' truffles-api/app/services/owner_resolver.py`
- `FACT findings`:
  - `reasoning_core.py` does not currently carry the timeout-owner input contract: zero matches there for `resolve_timeout_owner_boundary`, `matched_booking_followup_state`, `timeout_resume_contract_state`, `policy_core_timeout_degrade`, `pending_info_signal`, and `intent_decomp_payload`.
  - the non-frozen `ReasoningCoreConversationSnapshot` only projects `reply_slot`, `current_goal`, `booking_active`, `resume_reason`, `booking_time_token`, `booking_datetime_value`, and `service_referent` at `truffles-api/app/services/reasoning_core.py:289`.
  - the safe non-frozen booking helpers in `reasoning_core.py` call `route_llm_policy_core(...)` but return `None` when `policy_result.get("ok")` is false at `truffles-api/app/services/reasoning_core.py:1619`, `truffles-api/app/services/reasoning_core.py:1633`, `truffles-api/app/services/reasoning_core.py:1881`, and `truffles-api/app/services/reasoning_core.py:1886`; they do not surface timeout classification or derived timeout followup contracts.
  - frozen `decision.py` still derives the timeout-owner inputs from the expected-reply contract and timeout guard flow at `truffles-api/app/routers/webhook/decision.py:11072`, `truffles-api/app/routers/webhook/decision.py:15435`, and `truffles-api/app/routers/webhook/decision.py:15535`, then executes the live boundary state/meta/send authority at `truffles-api/app/routers/webhook/decision.py:15593` and `truffles-api/app/routers/webhook/decision.py:15610`.
  - `resolve_timeout_owner_boundary(...)` in `truffles-api/app/services/owner_resolver.py:302` is a pure resolver for pre-derived inputs only; it does not derive `matched_booking_followup_*`, `slot_fill_followup_*`, `resume_contract_*`, or timeout failure classification by itself.
- `Detected drift (docs vs code)`:
  - Block J still left open the possibility of authoring a truthful non-frozen timeout-owner bypass implementation next, but current code truth shows the necessary input contract is still produced only inside frozen `decision.py`; moving directly to an implementation TP would overstate what the non-frozen path can currently delete.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change"`
- **Date/time (local):** `2026-03-17 19:12 +0500`
- **Why this query is precise:** the next decision is whether the timeout-owner seam can move through safe expand/migrate/contract steps from a non-frozen entrypoint or whether the migration must stop and request an explicit freeze waiver.
- **Sources opened (from this query):**
  - `Parallel Change` — `https://martinfowler.com/bliki/ParallelChange.html`
- **Source quality:** primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** safe interface migration requires an explicit expand/migrate/contract plan; if the new side does not yet own the needed contract inputs, the migration must stop instead of pretending contract removal already has a safe path.
- **Decision:** `reuse/integrate` — apply the parallel-change rule as a stop condition here: do not author a bypass implementation TP until the non-frozen side can prove it owns the timeout-owner input contract.
- **Rejected options:**
  - author a timeout-owner bypass implementation TP before proving the non-frozen input contract exists
  - wrap frozen mutable helpers from `decision.py` and count that as deletion
  - clone broader timeout/expected-reply/intent-decomposition logic into `reasoning_core.py` without a bounded owner-deletion proof
- **Open questions:** whether Top Architect approves a bounded freeze waiver for the timeout-owner seam or requires a broader deletion/rework decision first.

## Root cause (mandatory)
- **Symptom:** the current next-step contract still suggests a timeout-owner bypass implementation TP may be the next admissible block, but the non-frozen path does not yet own the contract inputs that the frozen timeout-owner boundary consumes.
- **Minimal reproduction:**
  1. run `rg -n "resolve_timeout_owner_boundary|matched_booking_followup_state|timeout_resume_contract_state|policy_core_timeout_degrade|pending_info_signal|intent_decomp_payload" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`.
  2. confirm `reasoning_core.py` returns zero matches while `decision.py` carries those inputs and the timeout-owner branch.
  3. inspect `truffles-api/app/services/reasoning_core.py:289` and confirm the active snapshot only carries reply-slot / goal / booking / resume projections, not timeout-owner boundary inputs.
  4. inspect `truffles-api/app/services/reasoning_core.py:1619` plus `truffles-api/app/services/reasoning_core.py:1881` and confirm the current safe booking helpers only continue on `policy_result.get("ok")`; they drop timeout/error detail instead of surfacing a timeout-owner contract input.
  5. inspect `truffles-api/app/routers/webhook/decision.py:11072`, `truffles-api/app/routers/webhook/decision.py:15435`, and `truffles-api/app/routers/webhook/decision.py:15593` and confirm frozen `decision.py` still derives the matched followup / slot-fill followup / resume-contract inputs and then executes the boundary state/meta/send authority there.
  6. inspect `truffles-api/app/services/owner_resolver.py:302` and confirm the resolver itself only consumes already-derived inputs.
- **Evidence to capture:**
  - the zero-match scan in `reasoning_core.py`
  - the limited snapshot/input surface in `reasoning_core.py`
  - the current helper behavior on non-OK policy-core results
  - the frozen derivation + authority cluster in `decision.py`
- **Five Whys (or equivalent):**
  1. Why is the next implementation TP blocked? Because the non-frozen path does not expose the timeout-owner input contract.
  2. Why not derive that input from the current snapshot? Because the snapshot only carries reply-slot / goal / booking projections, not matched followup, timeout classification, pending-info, or intent-decomposition state.
  3. Why not call `resolve_timeout_owner_boundary(...)` directly from `reasoning_core`? Because that resolver requires pre-derived inputs that `reasoning_core` does not currently own.
  4. Why not port the missing derivation into `reasoning_core` right now? Because doing so would either wrap frozen mutable helpers or clone a broad semantic/boundary decision surface into new core without proof that the old authority becomes unreachable.
  5. Why switch to a waiver decision? Because the only repo-proven location with the full timeout-owner authority seam is frozen `decision.py`, so the truthful next block is an explicit waiver/deletion decision, not speculative implementation.
- **Root cause statement:** Block J stopped on the right surviving authority seam, but its next-step contract remained too optimistic: `reasoning_core` can intercept before fallback, yet it does not own the timeout-owner input contract that frozen `decision.py` still derives and executes, so a direct implementation TP would currently depend on wrapper growth or broad logic duplication rather than a proven owner deletion path.
- **Fix mechanism:**
  - publish the waiver decision as canon
  - record the exact non-frozen input-contract GAP
  - force the next block to choose explicitly between a bounded frozen-file waiver implementation and a broader deletion/rework decision

## Admissibility verdict
- **FACT:** no non-frozen file currently owns the timeout-owner boundary input contract.
- **FACT:** frozen `decision.py` still derives and executes the live timeout-owner state/meta/send branch.
- **FACT:** `owner_resolver.resolve_timeout_owner_boundary(...)` is necessary but insufficient for bypass, because the non-frozen path does not yet produce its required inputs.
- **INFERENCE:** authoring a timeout-owner bypass implementation TP right now would likely be fake progress, because the new block would either wrap frozen mutable helpers or recreate a broad legacy decision surface in `reasoning_core`.
- **Decision:** switch canon to a frozen-boundary waiver decision for the timeout-owner seam.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `app.services.owner_resolver.resolve_timeout_owner_boundary(...)` as the typed pure resolver
  - `DialogStateService` and `TurnExecutor` as the typed state/outcome surfaces already available if a waiver implementation is approved
  - the existing `reasoning_core` owner-cutover finalizer pattern
- **External reuse:**
  - Martin Fowler / Danilo Sato `Parallel Change`
- **Why not reinvent the wheel:** the repo already has the typed boundary/result/outcome surface; what is missing is a truthful migration seam for the timeout-owner inputs, not another custom wrapper.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `none`
- **Why this profile fits:** this is a governance/decision block that updates the architecture packet test and generated canon, so session gate still treats it as implementation-mode doc work.

## Invariant
- No runtime code edits.
- No frozen-router edits.
- No timeout-owner bypass implementation starts in this block.
- FACT vs INFERENCE separation stays explicit.

## Scope
- prove whether the timeout-owner boundary is currently bypassable from non-frozen code
- author the frozen-boundary waiver decision TP
- switch canon/session/packet to the waiver-decision block
- regenerate packet and rerun governance checks

## Out of scope
- runtime implementation
- frozen-file waiver execution
- edits to frozen `decision.py`
- semantic or continuity implementation beyond the waiver decision

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Record the exact non-frozen timeout-owner input-contract GAP.
3. Switch canon from Block J to the waiver-decision block so no speculative implementation TP is treated as admissible.
4. Regenerate packet and rerun governance checks.

## DoD
- the waiver decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-frozen-boundary-waiver-decision-a922.md`
- canon/packet/test all agree on the waiver-decision block and next move
- the TP explicitly records why the non-frozen bypass is not yet proven and what decision must happen next
- required checks are green

## Checks
- `rg -n "resolve_timeout_owner_boundary|matched_booking_followup_state|timeout_resume_contract_state|policy_core_timeout_degrade|pending_info_signal|intent_decomp_payload" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP, source of truth, active program, packet, session, and state
- zero-match timeout-owner input scan in `reasoning_core.py`
- green governance checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the non-frozen path still does not own the timeout-owner input contract, do not author an implementation TP in this block
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only governance block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree that the next move is a waiver decision rather than speculative implementation
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next block must choose explicit waiver or broader rework before any timeout-owner implementation begins

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
- `Drift closeout rule`:
  - active block metadata must match the waiver-decision verdict and generated packet output.

## Rollback
1. Revert the waiver decision TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no timeout-owner bypass implementation hidden inside this decision block
- no frozen-file edits under this TP
- no claim that a non-frozen bypass exists without proving the input contract also exists outside frozen `decision.py`
- no wrapper-only solution counted as deletion

## Risks / blockers
- a bounded freeze waiver may still be rejected, in which case a broader deletion/rework decision is required next
- the timeout-owner seam still shares territory with pending-resume and other timeout branches, so waiver scope must stay bounded
- the frozen tool-reply `TurnOutcome` path remains broader residual follow-up even if the timeout-owner waiver is approved later

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen `decision.py` still owns the timeout-owner authority seam
  - frozen pending-resume and tool-reply boundary authorities remain live
  - no non-frozen timeout-owner input contract exists yet
- **Why not in this block:**
  - this block is only the waiver decision; it does not implement the freeze-waived change or a broader rework
- **Risk if deferred:**
  - the next team may try to author a fake implementation TP that grows wrappers or duplicates legacy logic without deleting authority
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-timeout-owner-frozen-waiver-implementation-a922` (to be authored if waiver is approved)
  - `TP-2026-03-17-consultant-core-timeout-owner-broader-rework-decision-a922` (to be authored if waiver is denied)
- **Expiry/trigger to stop deferral:**
  - before any next consultant-core timeout-owner implementation block starts

## Next-block contract (mandatory)
- **Next block objective:** obtain the explicit Top Architect decision between a bounded frozen-file waiver for the timeout-owner boundary seam and a broader deletion/rework decision
- **First deterministic check command:** `rg -n "resolve_timeout_owner_boundary|matched_booking_followup_state|timeout_resume_contract_state|policy_core_timeout_degrade|pending_info_signal|intent_decomp_payload" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if waiver scope expands beyond the bounded timeout-owner seam or no owner decision is available, stop and escalate instead of authoring speculative implementation
- **Owner role for closure:** `Top Architect`
