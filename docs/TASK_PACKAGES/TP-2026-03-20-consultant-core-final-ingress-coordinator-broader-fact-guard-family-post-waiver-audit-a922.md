# TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-POST-WAIVER-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FACT-GUARD-FAMILY-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-DECISION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the post-waiver truth audit for the broader fact-guard family after the targeted frozen-waiver implementation. This block must prove whether the surviving frozen `_maybe_apply_fact_guard(...)` callback is still a live mixed authority or only a thin compatibility shell, and it must identify the next real mixed hotspot without resuming runtime edits.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before audit closure)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md`
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
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,8925p'`
- `FACT findings`:
  - the old mixed fact-guard authority body in frozen `decision.py` is gone; `_maybe_apply_fact_guard(...)` at `truffles-api/app/routers/webhook/decision.py:9630-9670` now performs only feature gating, minimal metadata extraction, and one owner invocation into `handle_policy_validation_boundary(...)`.
  - direct and injected consumers in `decision.py`, `info.py`, `booking.py`, and `reasoning_core.py` still depend on the callback symbol, but they no longer re-enter the deleted mixed body.
  - `truffles-api/app/services/policy_validation_boundary_service.py:196-273` now owns the broader fact-guard clarify / escalation / trace-meta / send-save orchestration.
  - `truffles-api/app/services/reasoning_core.py:2728-2763` still uses the callback contract in `_finalize_tool_reply_owner_execution(...)`, but it only consumes the thin callback and does not recreate the deleted mixed authority.
  - the remaining live broad ingress fallback still sits at `truffles-api/app/services/reasoning_core.py:8075` and `:8087`, where traffic falls back into frozen `truffles-api/app/routers/webhook/decision.py:8889`.
  - frozen `truffles-api/app/routers/webhook/booking.py:2442` remains explicit deferred debt, but it is not the earliest mixed hotspot because the live fallback sits earlier in `reasoning_core`.
- `INFERENCE to verify in this block`:
  - continuing the broader fact-guard runtime ladder would now be seam farming against a thin compatibility shell; the next truthful move is a broader fallback-ingress decision block.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the parent fact-guard blocks; no second query is allowed or needed.
- **Existing solutions found:** after a bounded runtime cut, audit whether the old path is truly thin-only; if the next remaining live hotspot is broader, switch to a broader decision block before more edits.
- **Decision:** `reuse/integrate`
  - reuse the already-landed owner move into `policy_validation_boundary_service.py`
  - audit the surviving callback and fallback topology before any further runtime work
- **Rejected options:**
  - second web query
  - another runtime edit inside the same fact-guard family without audit
  - widening into `booking.py`

## Root cause (mandatory)
- **Symptom:** the targeted frozen-waiver implementation deleted the old mixed fact-guard body, but the program still needs one truthful next target; without audit, the next move can mistake a thin callback shell for a live mixed seam.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:9630-9670` and confirm the old mixed body no longer lives there.
  2. inspect the direct and injected callsites in `decision.py`, `info.py`, `booking.py`, and `reasoning_core.py` and confirm they still consume the callback symbol.
  3. inspect `truffles-api/app/services/policy_validation_boundary_service.py:196-273` and confirm the broader fact-guard orchestration now lives there.
  4. inspect `truffles-api/app/services/reasoning_core.py:8075-8087` and `truffles-api/app/routers/webhook/decision.py:8889` and confirm live ingress still falls back into frozen `decision.py` through the broader webhook handler.
- **Evidence:**
  - thin callback shell in frozen `decision.py`
  - broader owner body in non-frozen `policy_validation_boundary_service.py`
  - surviving compatibility consumers in `info.py`, `booking.py`, and `_finalize_tool_reply_owner_execution(...)`
  - surviving broad fallback ingress at `reasoning_core -> decision_router._handle_webhook_payload(...)`
- **Five Whys (or equivalent):**
  1. Why is the old fact-guard body no longer the next target? Because its clarify / escalation / trace-meta / send-save ownership has already moved out of frozen `decision.py`.
  2. Why is the callback still present? Because direct and injected consumers still need the compatibility contract.
  3. Why is another fact-guard runtime edit risky now? Because it would either edit a thin shell or widen silently into deferred consumers.
  4. Why is the next real hotspot broader? Because live ingress still falls from `reasoning_core` into the full frozen webhook handler.
  5. Why is a decision block required next? Because the broader fallback family exceeds the just-closed fact-guard scope and must be defined before runtime work resumes.
- **Root cause statement:** the targeted frozen-waiver implementation truthfully deleted the old mixed fact-guard body, leaving only a thin compatibility callback; the next live mixed hotspot is the broader `reasoning_core -> decision_router._handle_webhook_payload(...)` fallback ingress family, so continuing inside the fact-guard family would be fake progress.
- **Fix mechanism:**
  - publish a post-waiver audit that records the callback as thin-only residual
  - switch canon to a broader fallback-ingress decision block for the next move
  - keep `booking.py` as deferred debt until that broader fallback family is classified

## Old authority seams under audit (mandatory)
- **FACT:** the old mixed fact-guard authority body at `truffles-api/app/routers/webhook/decision.py:9630-9718` is already dead and therefore is not the next audit target.
- **FACT:** the surviving `_maybe_apply_fact_guard(...)` callback at `truffles-api/app/routers/webhook/decision.py:9630-9670` is a thin compatibility shell only.
- **FACT:** the next live mixed hotspot is the broader fallback ingress at `truffles-api/app/services/reasoning_core.py:8075-8087` into `truffles-api/app/routers/webhook/decision.py:8889`.
- **FACT:** frozen `truffles-api/app/routers/webhook/booking.py:2442` remains deferred consumer debt, not the earliest blocker.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/app/services/reasoning_core.py:_finalize_tool_reply_owner_execution(...)`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - existing architecture guard packet flow
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the fact-guard owner move is already landed; this block only needs to classify the new topology and lock the next broader decision.

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `9`
- **Code dominance:** `doc-only`
- **Why this profile fits:** this block is a pure audit/sync step; no runtime edit is admissible here.

## Invariant
- no runtime code edits in this block
- no claim that any old authority seam dies in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is fully closed
- no widening into `booking.py`, `pending.py`, or acceptance families
- no second web search

## Scope
- classify the surviving fact-guard callback as thin-only or mixed
- classify the next live mixed hotspot after the implementation block
- switch canon/session artifacts to the post-waiver audit block
- lock the next move to a broader fallback-ingress decision block

## Out of scope
- runtime edits in `reasoning_core.py`, `decision.py`, `info.py`, or `booking.py`
- new wrapper/helper creation
- acceptance or `L2` work
- any second web search

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md`
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
1. Run the deterministic post-waiver audit checks.
2. Record whether the surviving callback is thin-only or still mixed.
3. Identify the next live mixed hotspot if the callback is thin-only.
4. Switch canon/session artifacts to this audit block with one machine-readable next move.

## DoD
- the post-waiver audit TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md`
- canon / packet / architecture test all agree this is the active block
- the block states explicitly that seam-deletion count here is zero
- the next non-negotiable move is no longer another fact-guard runtime edit
- required checks are green

## Checks
- `rg -n "_maybe_apply_fact_guard|maybe_apply_fact_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/booking.py truffles-api/app/services/reasoning_core.py`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '9630,9718p;19416,19422p;19980,20076p;20096,20110p;20552,20559p;21020,21040p;21294,21310p;21580,21586p;21762,21778p;21860,21868p'`
- `nl -ba truffles-api/app/routers/webhook/info.py | sed -n '780,828p;1168,1188p;1274,1292p;1404,1418p;1718,1732p;2130,2142p'`
- `nl -ba truffles-api/app/routers/webhook/booking.py | sed -n '2436,2450p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '2705,2765p;8075,8087p'`
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
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
- deterministic scan proving `_maybe_apply_fact_guard(...)` is now thin-only
- deterministic scan proving live ingress fallback still remains at `reasoning_core -> decision_router._handle_webhook_payload(...)`
- updated canon/session artifacts for the new audit block
- green governance/session checks after the doc sync

## Rollback
1. Revert this audit TP and canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only post-waiver audit; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the active audit block and the next move.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either publish the broader fallback-ingress decision or stop as `GAP`; it must not resume fact-guard runtime edits.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic doc / governance checks only.
- **Stop condition:** if the audit still finds mixed authority inside `_maybe_apply_fact_guard(...)`, stop and reopen runtime work; if the next move would require `booking.py` edits or a second web query, stop and publish `GAP`.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits in this block
- no second web search
- no wrapper/helper growth counted as progress
- no claim that fallback ingress is already deleted here
- no silent widening into frozen `booking.py`

## Risks / blockers
- the next broader fallback-ingress decision may prove that the live residual exceeds a single reusable owner surface.
- live fallback at `truffles-api/app/services/reasoning_core.py:8075-8087` still remains and must not be miscounted as solved by this block.
- other rooted residual families at `truffles-api/app/routers/webhook/decision.py:1218-1320`, `:12478-12545`, and `:15659-15756` remain open and are not solved by this audit.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `truffles-api/app/routers/webhook/decision.py:9630-9670` thin callback shell
  - `truffles-api/app/routers/webhook/info.py:813`
  - `truffles-api/app/routers/webhook/info.py:1176`
  - `truffles-api/app/routers/webhook/info.py:1282`
  - `truffles-api/app/routers/webhook/info.py:1411`
  - `truffles-api/app/routers/webhook/info.py:1725`
  - `truffles-api/app/routers/webhook/info.py:2136`
  - `truffles-api/app/routers/webhook/booking.py:2442`
  - `truffles-api/app/services/reasoning_core.py:2705-2765`
  - `truffles-api/app/services/reasoning_core.py:8075-8087`
  - `truffles-api/app/routers/webhook/decision.py:8889-8925`
  - `truffles-api/app/routers/webhook/decision.py:1218-1320`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `semantic_owner` remains partial
  - `continuity_owner` remains partial
  - `boundary_owner` remains partial
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:** this block is audit-only and cannot truthfully widen beyond the just-closed fact-guard family.
- **Risk if deferred:** continuing runtime work without this audit would misclassify thin callback residue as live progress and blur the broader fallback hotspot.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md`
- **Expiry/trigger to stop deferral:** stop if any new logic lands inside frozen `_maybe_apply_fact_guard(...)` or if deferred `booking.py` starts blocking before the fallback family is classified.

## Next-block contract (mandatory)
- **Next block objective:** publish the broader fallback-ingress decision that defines the exact rooted `reasoning_core -> decision_router._handle_webhook_payload(...)` family, admissible owner destinations, and blocked-by conditions before runtime work resumes.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:**
  - the surviving `_maybe_apply_fact_guard(...)` callback proves mixed again instead of thin-only
  - the broader fallback family cannot be defined without reopening unrelated continuity, timeout, acceptance, or frozen-booking scope
  - a second web query would be required
- **Owner role for closure:** `Top Architect`
