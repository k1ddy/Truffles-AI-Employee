# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the exact targeted frozen-waiver runtime cut for the surviving broader fact-guard family. The block is admissible only if the old mixed authority body at `truffles-api/app/routers/webhook/decision.py:9630-9718` becomes deleted or unreachable as a live authority, while the surviving `decision.py` callable stays only as thin owner-surface invocation into existing owner destinations.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md`
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
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p'`
  - `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
  - `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- `FACT findings`:
  - the old mixed authority body still lives at `truffles-api/app/routers/webhook/decision.py:9630-9718`.
  - the live direct frozen callsites still sit at `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768`.
  - frozen `decision.py` still injects the same callable into surviving consumers at `:19420`, `:20067`, `:20106`, `:20558`, `:21585`, and `:21867`.
  - frozen `booking.py` still only consumes the injected callable at `truffles-api/app/routers/webhook/booking.py:2442`; it is not the earliest blocker.
  - `truffles-api/app/services/policy_validation_boundary_service.py` already owns deterministic guard trace/meta/send-save orchestration, but not the broader fact-guard clarify-attempt / escalation orchestration yet.
  - `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`, `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`, and `truffles-api/app/core/dialog_state_service.py:2783-2817` already exist as reusable owner fragments.
  - live fallback into frozen ingress still remains at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`; this block does not claim to close that fallback.
- `Detected drift (docs vs code)`:
  - the targeted frozen-waiver decision correctly locked scope, but runtime progress has not started yet because the old mixed fact-guard body is still live.
  - the next truthful move is the implementation bundle itself; another doc-only block would not delete any seam.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the parent decision block; no second query is allowed or needed.
- **Existing solutions found:** move one live rooted authority slice onto an already-valid owner surface, keep the legacy caller as a thin shell only if the old mixed authority actually dies, and stop before widening into new hotspots.
- **Decision:** `reuse/integrate`
  - reuse `policy_validation_boundary_service.py` as the owner destination for deterministic fact-guard orchestration.
  - reuse `guards.py` and `DialogStateService` primitives for clarify-attempt and clarify-limit semantics.
  - keep the injected callable contract stable so `info.py` and frozen `booking.py` do not need widening.
- **Rejected options:**
  - second web query
  - new `fact_guard_service.py`
  - new compatibility wrapper/helper around the same mixed authority
  - widening into `booking.py`

## Root cause (mandatory)
- **Symptom:** the broader fact-guard family remains live because `_maybe_apply_fact_guard(...)` in frozen `decision.py` still owns clarify-attempt state mutation, trace/meta writes, clarify-limit escalation, send/save, and final `WebhookResponse` shaping.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:9630-9718` and confirm the mixed body still performs clarify-attempt read/write, escalation, trace/meta writes, send/save, and response shaping inline.
  2. inspect the frozen direct callsites at `truffles-api/app/routers/webhook/decision.py:19985`, `:21024`, `:21300`, and `:21768` and confirm they still execute the same legacy body.
  3. inspect the frozen injected callsites at `truffles-api/app/routers/webhook/decision.py:19420`, `:20067`, `:20106`, `:20558`, `:21585`, and `:21867` and confirm downstream consumers still receive that frozen callable.
  4. inspect `truffles-api/app/services/policy_validation_boundary_service.py:175-380` and confirm the existing owner destination already handles clarify-style trace/meta/send-save orchestration.
  5. inspect `truffles-api/app/routers/webhook/booking.py:2442` and confirm `booking.py` still only consumes the injected callable and does not force a wider edit by itself.
- **Evidence:**
  - exact rooted body range in frozen `decision.py`
  - exact direct and injected frozen callsites
  - existing owner fragments in `policy_validation_boundary_service.py`, `guards.py`, and `DialogStateService`
- **Five Whys:**
  1. Why is the family still open? Because the old mixed fact-guard body still lives in frozen `decision.py`.
  2. Why is that still a blocker after the earlier direct tool-reply seam deletion? Because the same callable is reused by broader info / intent-queue / followup contours and by injected downstream consumers.
  3. Why not solve this by editing consumers first? Because the earliest blocker is the frozen owner body itself; consumer-only changes would preserve the old authority.
  4. Why is `policy_validation_boundary_service.py` the truthful destination? Because it already owns deterministic guard orchestration patterns and can reuse existing clarify-attempt / escalation primitives without creating a new hotspot.
  5. Why can `booking.py` stay untouched? Because the callable contract can stay stable while the owner behind it changes.
- **Root cause statement:** the surviving broader fact-guard family is blocked by one old mixed authority body still rooted in frozen `decision.py`; progress is truthful only if that body loses state/trace/send/escalation ownership and becomes thin owner-surface invocation into the existing boundary/guard owner family.
- **Fix mechanism:**
  - extend `policy_validation_boundary_service.py` to own the fact-guard clarify / escalation orchestration using the existing guard/dialog-state primitives.
  - reduce `_maybe_apply_fact_guard(...)` in frozen `decision.py` to preflight plus owner invocation only.
  - keep direct and injected callsites on the same callable contract so `info.py`, `reasoning_core.py`, and frozen `booking.py` do not widen.

## Old authority seam to delete (mandatory)
- **Primary target seam:** the old mixed fact-guard body at `truffles-api/app/routers/webhook/decision.py:9630-9718`.
- **Success condition:** the old inline clarify-attempt / escalation / trace-meta / send-save / `WebhookResponse` shaping body is deleted or unreachable as a live authority, and the surviving frozen callable is only a thin owner-surface invocation into the existing non-frozen owner family.
- **Non-admissible outcomes:**
  - no old authority dies
  - a new wrapper/helper is introduced as the new mixed hotspot
  - `booking.py` or unrelated timeout/acceptance families are widened without a new decision block

## Invariant
- no new wrapper/helper counted as progress
- no widening into `truffles-api/app/routers/webhook/booking.py`
- no claim that live fallback `reasoning_core -> decision.py` is solved
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed
- no claim that green `L2` or final acceptance closure is proven

## Scope
- add the implementation TP and switch canon to it once the runtime result is truthful
- update the `decision.py` freeze waiver for the exact fact-guard implementation lines
- move fact-guard deterministic orchestration into `truffles-api/app/services/policy_validation_boundary_service.py`
- reduce `_maybe_apply_fact_guard(...)` in frozen `decision.py` to thin invocation only
- add focused regressions and sync canon/state/session only if the old seam really dies

## Out of scope
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/services/reasoning_core.py` runtime changes
- unrelated timeout, acceptance, or proof families
- a second web query
- claiming fallback ingress closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md`
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
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/app/routers/webhook/guards.py:_register_clarify_attempt(...)`
  - `truffles-api/app/routers/webhook/guards.py:_handle_clarify_limit_escalation(...)`
  - `truffles-api/app/core/dialog_state_service.py:2783-2817`
  - existing fact-guard endpoint regressions in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the owner fragments already exist; only the rooted mixed authority still has to die.

## Plan (1..N)
1. Author this implementation TP before runtime edits.
2. Update `docs/LEGACY_SUNSET.yaml` so the frozen `decision.py` waiver matches the exact new executable lines used by this block.
3. Extend `policy_validation_boundary_service.py` to own fact-guard clarify / escalation orchestration using existing hooks and primitives.
4. Reduce `_maybe_apply_fact_guard(...)` in frozen `decision.py` to gating plus owner invocation only.
5. Add focused regressions for the new owner surface and the preserved callback contract.
6. Run focused deterministic tests, then required packet/guard/architecture/session checks.
7. Sync canon/state/session with the truthful runtime result and name the next residual block without claiming broader closure.

## DoD
- the old mixed fact-guard body at `decision.py:9630-9718` is deleted or unreachable as live authority
- no new wrapper/helper or widened hotspot exists
- `legacy_freeze_guard.py` passes with the exact scoped waiver
- focused regressions pass
- required packet/guard/architecture/session checks pass
- canon/state/session truthfully name the dead seam and the next residual block

## Checks
- `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply_owner_execution or policy_validation_boundary'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'clarify_limit_escalates_after_two_attempts or llm_policy_core_provider_unavailable_escalates_after_clarify_limit or llm_policy_core_info_without_pack_refs_clarifies_instead_of_deriving_from_text or llm_policy_core_tool_reply_without_evidence_clarifies or multi_truth_reply_handles_hours_and_service_without_booking or multi_truth_reply_handles_hours_and_price_in_single_segment or intent_decomp_blocks_booking_and_drives_multi_truth'`
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
- diff showing the old mixed `decision.py` fact-guard body is gone or reduced to thin owner invocation only
- deterministic local reproduction that the excluded `llm_policy_core_direct_info_reply_without_evidence_clarifies` row currently resolves through populated booking-interrupt info metadata under repo truth rather than the rooted broader fact-guard family
- exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml`
- focused regression output for fact-guard and callback-contract behavior
- green required guards and architecture/session checks
- canon/session/state naming the deleted seam truthfully

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** `rg` + `py_compile`
- **Focused tests before required guards:** runtime contract subset + fact-guard endpoint subset
- **Stop condition:** if `booking.py` needs editing, if a new helper/wrapper becomes necessary, or if the old mixed body cannot actually die, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local exact-scope frozen-waiver implementation only
- **Go/no-go signals:**
  - the old mixed fact-guard body is gone or thin-only
  - `legacy_freeze_guard.py` passes with the exact waiver
  - focused regressions and required guards pass
- **Rollback:** revert `decision.py`, `policy_validation_boundary_service.py`, tests, and canon/docs for this block, then rerun focused checks
- **Post-release monitoring window:** none beyond this block's deterministic checks; do not claim acceptance proof

## Rollback
1. Revert this block's code and doc changes.
2. Rerun `py_compile`, focused tests, and required guards.
3. Restore canon/session/state to the previous decision block if the seam did not really die.

## No-go
- no second web query
- no new `fact_guard_service.py`
- no `booking.py` or `pending.py` widening
- no claim that live fallback `reasoning_core -> decision.py` is closed
- no claim that the broader fact-guard family is fully finished if the old mixed body still survives

## Risks / blockers
- `policy_validation_boundary_service.py` may require wider hook/input changes than expected; if that forces a new hotspot, stop.
- frozen `decision.py` additions must stay exactly listed in `docs/LEGACY_SUNSET.yaml` or the block is invalid.
- if any consumer requires a changed callback signature, the block must stop because that would widen beyond the declared family.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live fallback `truffles-api/app/services/reasoning_core.py:8075-8087` still remains.
  - the callback symbol `_maybe_apply_fact_guard(...)` may still survive as a thin invocation surface in frozen `decision.py`.
  - frozen `booking.py:2442` remains deferred debt.
- **Why not in this block:**
  - this block only deletes the old mixed authority body; it does not claim ingress-fallback or frozen-consumer closure.
- **Risk if deferred:**
  - the surviving thin callback and fallback ingress can still hide future drift if new logic is reintroduced there.
- **Linked follow-up Task Package(s):**
  - `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-POST-WAIVER-AUDIT-A922`
- **Expiry/trigger to stop deferral:**
  - stop if any new fact-guard behavior lands in frozen `decision.py` or `booking.py` after this block.

## Next-block contract (mandatory)
- **Next block objective:** run a post-waiver audit and prove whether the surviving frozen fact-guard callable and fallback ingress are thin-only residuals or another broader mixed family.
- **First deterministic check command:** `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p'`
- **Blocked-by conditions:**
  - the old mixed fact-guard body did not die
  - `legacy_freeze_guard.py` fails
  - `booking.py` or another unrelated family needs widening
- **Owner role for closure:** `Top Architect`
