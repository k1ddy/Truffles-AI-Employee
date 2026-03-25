# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one explicit targeted frozen-waiver decision after proving that the non-frozen broader fact-guard implementation block is not admissible. This block must lock the exact frozen `decision.py` fact-guard scope that keeps the old `_maybe_apply_fact_guard(...)` authority live, keep `booking.py` as explicit deferred debt, and forbid any runtime move that only adds another delegate layer without killing the old rooted authority.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
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
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md`
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
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p'`
  - `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
  - `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- `FACT findings`:
  - the old rooted authority body still lives at `truffles-api/app/routers/webhook/decision.py:9630-9718`.
  - the old rooted authority is still called directly from frozen `decision.py` at `:19985`, `:21024`, `:21300`, and `:21768`.
  - frozen `decision.py` still injects the same callable into the current family at `:19420`, `:20106`, `:20558`, `:21585`, and `:21867`, so existing non-frozen consumers still depend on a frozen caller/injector.
  - frozen `decision.py` still injects the same callable into frozen booking flows at `:20067` and `:21585`, while frozen `booking.py` still consumes that injected callable at `truffles-api/app/routers/webhook/booking.py:2442`.
  - `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)` at `:2705-2765` remains only a consumer surface because frozen `decision.py:19420` still supplies `maybe_apply_fact_guard`.
  - live fallback into frozen ingress still remains at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`.
  - existing admissible destination fragments remain unchanged: `truffles-api/app/core/dialog_state_service.py:2783-2817`, `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`, `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`, and `truffles-api/app/services/policy_validation_boundary_service.py:175-280`.
- `Detected drift (docs vs code)`:
  - the active broader fact-guard family decision correctly locked scope, but the immediate non-frozen implementation move is not truthful because the old rooted authority still survives inside frozen `decision.py` itself.
  - continuing with a non-frozen-only implementation bundle would at best add another delegate layer while leaving the old frozen body live.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Why this query is reused here:** this is still a doc-only decision block inside the same active chain; no second query is allowed.
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** when the old authority remains rooted in a frozen caller that still injects the legacy callable into downstream consumers, stop the non-frozen bundle, publish an explicit waiver decision, and only continue with a scope that can actually kill the frozen seam.
- **Decision:** `reuse/integrate`
  - reuse the current broader family map and existing admissible owner destinations.
  - do not run a second query and do not invent a new owner layer.
- **Rejected options:**
  - a second web query
  - resuming the non-frozen implementation bundle anyway
  - introducing a runtime monkeypatch, wrapper, or new `fact_guard_service.py`

## Root cause (mandatory)
- **Symptom:** the next non-frozen broader fact-guard implementation move cannot truthfully delete or bypass the old rooted `_maybe_apply_fact_guard(...)` authority.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:9630-9718` and confirm the rooted body still owns clarify-attempt mutation, trace/meta writes, clarify-limit escalation, send/save, and `WebhookResponse` shaping.
  2. inspect frozen direct callsites at `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768` and confirm the old rooted body still stays live there.
  3. inspect frozen callback injection sites at `truffles-api/app/routers/webhook/decision.py:19420`, `:20067`, `:20106`, `:20558`, `:21585`, and `:21867` and confirm current family consumers still receive the legacy callable from frozen `decision.py`.
  4. inspect `truffles-api/app/services/reasoning_core.py:8075-8087` and confirm live runtime still falls through to frozen `decision.py`.
  5. inspect `truffles-api/app/routers/webhook/booking.py:2442` and confirm `booking.py` is still only a consumer of the injected callable, not the earliest blocker.
- **Evidence to capture:**
  - exact frozen `decision.py` scope that still keeps the rooted authority live
  - explicit verdict that the current non-frozen bundle is blocked
  - explicit deferred status for `booking.py`
  - explicit next move limited to a targeted frozen-waiver implementation
- **Five Whys (or equivalent):**
  1. Why is the non-frozen implementation bundle blocked? Because the old rooted `_maybe_apply_fact_guard(...)` body is still called and injected directly from frozen `decision.py`.
  2. Why can existing non-frozen owner destinations not close the family by themselves? Because frozen `decision.py` still decides when and where the legacy callable runs.
  3. Why would continuing the non-frozen bundle be untruthful? Because the old rooted authority would remain live even if downstream consumers changed.
  4. Why does `booking.py` stay deferred here? Because the blocker sits earlier in frozen `decision.py`, and `booking.py` is still only consuming the callable injected from there.
  5. Why is a waiver decision the honest next step? Because only an explicit frozen `decision.py` scope can authorize the edits required to make the old rooted authority die.
- **Root cause statement:** the broader fact-guard family is blocked before runtime implementation because the old authority is still rooted in frozen `truffles-api/app/routers/webhook/decision.py`, which both calls `_maybe_apply_fact_guard(...)` directly and injects that callable into downstream consumers; therefore a non-frozen-only bundle cannot make the old rooted seam deleted or unreachable.
- **Fix mechanism:**
  - publish one targeted frozen-waiver decision limited to the current fact-guard family inside frozen `decision.py`
  - keep admissible owner destinations unchanged
  - keep frozen `booking.py` deferred unless the later waiver implementation proves otherwise
  - reject any move that only adds delegation without deleting or bypassing the old rooted body

## Exact frozen waiver scope
- `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - rooted old authority body for fact-guard clarify / escalation / send-save / response shaping.
- `truffles-api/app/routers/webhook/decision.py:19420`
  - frozen consumer injection into `reasoning_core._finalize_tool_reply_owner_execution(...)`.
- `truffles-api/app/routers/webhook/decision.py:19985`
  - direct legacy fact-guard callsite on the info reply contour.
- `truffles-api/app/routers/webhook/decision.py:20067`
  - frozen callback injection into booking-interrupt handling.
- `truffles-api/app/routers/webhook/decision.py:20106`
  - frozen callback injection into non-frozen `info.py` flow handling.
- `truffles-api/app/routers/webhook/decision.py:20558`
  - frozen callback injection into the later booking-interrupt branch.
- `truffles-api/app/routers/webhook/decision.py:21024`
  - direct legacy fact-guard callsite on the intent-queue info reply contour.
- `truffles-api/app/routers/webhook/decision.py:21300`
  - direct legacy fact-guard callsite on the multi-intent info reply contour.
- `truffles-api/app/routers/webhook/decision.py:21585`
  - frozen callback injection into booking-flow handling.
- `truffles-api/app/routers/webhook/decision.py:21768`
  - direct legacy fact-guard callsite on the expected-reply followup reply contour.
- `truffles-api/app/routers/webhook/decision.py:21867`
  - frozen callback injection into the later non-frozen `info.py` flow handling.
- **Out of waiver scope for this decision:**
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - unrelated timeout / acceptance / proof families

## Admissible owner destinations
- `truffles-api/app/core/dialog_state_service.py:2783-2817`
  - admissible only for clarify-attempt read/write primitives.
- `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - admissible only for bounded clarify-attempt mutation reuse around the existing context-manager contract.
- `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - admissible only for bounded clarify-limit escalation / send-save reuse.
- `truffles-api/app/services/policy_validation_boundary_service.py:175-280`
  - admissible only for deterministic guard/boundary orchestration that already owns trace/meta/send-save patterns for clarify-style guard replies.
- `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)`
  - may remain a caller/consumer once frozen `decision.py` stops injecting the old callable, but it is not itself the new owner destination.
- **Explicitly not admissible:**
  - any new `fact_guard_service.py`
  - any runtime monkeypatch that reassigns `_maybe_apply_fact_guard` from outside frozen `decision.py`
  - any new wrapper/helper that only re-houses the same mixed authority
  - widening into unrelated timeout/offline/truth-gate families in this block

## Frozen booking.py decision
- `truffles-api/app/routers/webhook/booking.py:2442` stays **explicit deferred debt** in this decision block.
- Reason: the deterministic blocker sits earlier in frozen `decision.py`; this block does not prove that `booking.py` itself must be edited.
- If the later targeted frozen-waiver implementation proves `booking.py` must be edited for correctness or seam deletion, stop and publish a new explicit decision/waiver block instead of widening silently.

## FACT vs INFERENCE verdict
- **FACT:** this block is doc-only; no old authority seam is deleted or made unreachable here.
- **FACT:** the immediate non-frozen broader fact-guard implementation move is blocked.
- **FACT:** frozen `decision.py`, not `booking.py`, is the earliest live blocker for the current rooted family.
- **FACT:** `booking.py:2442` remains deferred debt in this block.
- **INFERENCE:** the next admissible move is one targeted frozen-waiver implementation bundle over the exact frozen `decision.py` scope above.
- **Decision:** switch canon from the broader fact-guard family decision block to this targeted frozen-waiver decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py:2783-2817`
  - `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - existing packet / arch / session guard flow
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the required owner fragments already exist in-repo
  - the missing step is frozen caller replacement, not a new ownership layer

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-heavy`
- **Why this profile fits:** this block only records the truthful blocker and exact frozen scope before any runtime edits.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no new wrapper/helper or runtime monkeypatch counted as progress
- no claim that frozen `booking.py` is already solved
- answer to "какой old authority seam стал deleted или unreachable после этого блока?" remains `никакой`

## Scope
- publish the truthful blocker verdict for the non-frozen broader fact-guard implementation move
- define the exact frozen `decision.py` waiver scope for the current broader fact-guard family
- keep `booking.py` explicitly deferred
- switch canon/session artifacts to this waiver decision block

## Out of scope
- runtime implementation
- editing `decision.py`, `info.py`, `booking.py`, `guards.py`, `reasoning_core.py`, `policy_validation_boundary_service.py`, or `dialog_state_service.py`
- reopening unrelated timeout, acceptance, or proof families
- a second web query
- claiming any runtime seam deletion in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md`
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
1. Publish this targeted frozen-waiver decision TP with the exact frozen `decision.py` scope.
2. Record the blocker truthfully: the non-frozen broader fact-guard implementation move is inadmissible because the old rooted authority still lives inside frozen `decision.py`.
3. Keep `booking.py` as explicit deferred debt instead of widening silently.
4. Switch canon/session artifacts to this decision block.
5. Regenerate packet and rerun governance/session checks.

## DoD
- the targeted frozen-waiver decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md`
- canon / packet / architecture test all agree this is the active block
- the current non-frozen implementation move is explicitly marked blocked
- the exact frozen `decision.py` scope is machine-readable in canon/session artifacts
- `booking.py` remains explicitly deferred rather than silently widened
- the block states explicitly that seam-deletion count here is zero

## Checks
- `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p'`
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
- deterministic scan proving the exact frozen `decision.py` blocker scope
- explicit statement that seam-deletion count in this block is zero
- green governance/session checks after the doc sync

## Rollback
1. Revert this decision TP and matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only blocker/waiver decision; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the active decision block and the next move.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either implement the exact targeted frozen-waiver bundle or stop as `GAP`; it must not resume the blocked non-frozen bundle.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic doc / governance checks only.
- **Stop condition:** if the next runtime bundle needs a new helper/wrapper, a runtime monkeypatch, a second web query, or silent widening into frozen `booking.py`, stop and publish `GAP` instead of continuing.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits hidden inside this decision block
- no second web search
- no helper/wrapper growth or runtime monkeypatch counted as progress
- no claim that `_maybe_apply_fact_guard(...)` is already deleted or unreachable in this block
- no silent widening into frozen `booking.py`
- no reopening unrelated continuity, timeout, acceptance, or proof families

## Risks / blockers
- the later targeted frozen-waiver implementation may still prove that some currently omitted frozen caller lies outside the exact rooted family; if so, stop and publish a new decision instead of widening silently.
- live fallback `truffles-api/app/services/reasoning_core.py:8075-8087` still remains and must not be miscounted as solved by this block.
- other rooted residual families at `decision.py:1218-1320`, `:12478-12545`, and `:15659-15756` remain open and are not solved by this decision.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9718`
  - `truffles-api/app/routers/webhook/decision.py:19420`
  - `truffles-api/app/routers/webhook/decision.py:19985`
  - `truffles-api/app/routers/webhook/decision.py:20067`
  - `truffles-api/app/routers/webhook/decision.py:20106`
  - `truffles-api/app/routers/webhook/decision.py:20558`
  - `truffles-api/app/routers/webhook/decision.py:21024`
  - `truffles-api/app/routers/webhook/decision.py:21300`
  - `truffles-api/app/routers/webhook/decision.py:21585`
  - `truffles-api/app/routers/webhook/decision.py:21768`
  - `truffles-api/app/routers/webhook/decision.py:21867`
  - `truffles-api/app/routers/webhook/info.py:813`
  - `truffles-api/app/routers/webhook/info.py:1176`
  - `truffles-api/app/routers/webhook/info.py:1282`
  - `truffles-api/app/routers/webhook/info.py:1411`
  - `truffles-api/app/routers/webhook/info.py:1725`
  - `truffles-api/app/routers/webhook/info.py:2136`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `truffles-api/app/services/reasoning_core.py:2705-2765`
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
  - this block only decides the truthful frozen blocker scope and next move; it does not execute runtime deletion.
- **Risk if deferred:**
  - the team could resume the blocked non-frozen bundle and miscount another delegate layer as progress.
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md` (to be authored or executed next)
- **Expiry/trigger to stop deferral:**
  - before any next runtime claim touching `_maybe_apply_fact_guard(...)`
  - immediately if anyone proposes a new helper/wrapper, a runtime monkeypatch, or silent `booking.py` widening

## Next-block contract (mandatory)
- **Next block objective:** implement the targeted frozen-waiver bundle so the old rooted `_maybe_apply_fact_guard(...)` authority at `truffles-api/app/routers/webhook/decision.py:9630-9718` becomes deleted or unreachable as live authority by replacing the exact frozen `decision.py` call/injection bundle above with the existing admissible owner destinations, while keeping frozen `booking.py` deferred unless a new explicit decision says otherwise.
- **First deterministic check command:** `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py && nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p' && nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p' && nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p' && nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- **Blocked-by conditions:**
  - if the runtime plan needs a new helper/wrapper or runtime monkeypatch to carry the broader fact-guard family
  - if the runtime plan cannot stay inside `DialogStateService`, `guards.py`, and `policy_validation_boundary_service.py` as the owner destinations
  - if the runtime plan needs to widen into frozen `booking.py` without a new explicit decision/waiver block
  - if the runtime plan reopens unrelated timeout, acceptance, or proof families
  - if the runtime plan needs a second web query
  - if the runtime plan cannot delete or bypass the old rooted authority and only adds another delegate layer
- **Owner role for closure:** `Top Architect`
