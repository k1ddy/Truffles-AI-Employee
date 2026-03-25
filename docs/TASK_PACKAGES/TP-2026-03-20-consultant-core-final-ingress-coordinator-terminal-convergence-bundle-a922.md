# TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BUNDLE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-POST-IMPLEMENTATION-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one terminal convergence bundle under `finish_mode`. This block must truthfully repair the current continuity-guard drift and make the live `reasoning_core -> decision_router._handle_webhook_payload(...)` transport seam deleted or unreachable on the default path without adding a new compatibility wrapper and without widening into frozen `decision.py`, `booking.py`, or `pending.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|\"expected_reply_type\": \"time\"" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1419,1875p;12478,12545p;15659,15756p;19373,19481p'`
  - `python3 scripts/continuity_writer_guard.py`
  - `python3 scripts/arch_guard.py`
- `FACT findings`:
  - active `/webhook` traffic still reaches frozen legacy through `truffles-api/app/services/reasoning_core.py:12349` and `truffles-api/app/services/reasoning_core.py:12361`.
  - frozen ingress authority still begins at `truffles-api/app/routers/webhook/decision.py:8889`.
  - the surviving rooted residual families remain concentrated at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`.
  - mandatory governance rerun is red because `python3 scripts/continuity_writer_guard.py` flags `truffles-api/app/services/reasoning_core.py:9482` (`expected_reply_type=reply_slot,`) and `truffles-api/app/services/reasoning_core.py:9693` (`"expected_reply_type": "time",`); `python3 scripts/arch_guard.py` fails transitively.
  - current canon truth does not permit claiming full migration while that transport seam and those governance violations remain live.
- `INFERENCE to verify in this block`:
  - one bounded runtime bundle may still be admissible if the continuity writes are truthfully rehoused or deleted and the live fallback seam becomes unreachable before traffic reaches frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active terminal convergence chain; no second query is allowed or needed.
- **Existing solutions found:** use one explicit expand/migrate/contract bundle that routes the remaining live traffic through the target owner lane first, then contracts the legacy coordinator so the old seam becomes unreachable.
- **Decision:** `reuse/integrate`
  - reuse existing target owners in `turn_planner`, `dialog_state_service`, `boundary_validator`, and `turn_executor`
  - reuse existing non-frozen boundary services already carrying adjacent residual slices
  - do not create a new transport wrapper around `decision.py`
- **Rejected options:**
  - second web query
  - another micro-cut that leaves the default-path transport seam alive
  - helper-only compatibility growth

## Root cause (mandatory)
- **Symptom:** the program has landed many local seam deletions, but the final live transport fallback and continuity-guard drift still block truthful closure claims.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/reasoning_core.py:12349-12361` and confirm active `/webhook` traffic still falls through to `decision_router._handle_webhook_payload(...)`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8889-9005` and confirm frozen `decision.py` still remains the live downstream ingress handler.
  3. inspect `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481` and confirm broader mixed authority remains behind that transport seam.
  4. run `python3 scripts/continuity_writer_guard.py` and confirm the current repo drift at `truffles-api/app/services/reasoning_core.py:9482` and `:9693`.
- **Evidence:**
  - active `reasoning_core -> decision.py` fallback
  - surviving mixed residual families in frozen `decision.py`
  - red continuity / architecture guards on current repo truth
- **Five Whys (or equivalent):**
  1. Why is the migration still incomplete? Because active ingress still reaches frozen `decision.py`.
  2. Why is that the decisive blocker? Because the remaining semantic/continuity/boundary residual authority still lives behind that path.
  3. Why are the current red guards relevant? Because clean closure claims are invalid while continuity writes remain in a non-allowed writer surface.
  4. Why is another micro-cut insufficient? Because it can reduce one branch while leaving the same default-path transport seam alive.
  5. Why is one terminal bundle required? Because only a bundle that both repairs governance drift and kills the final transport seam can move the program out of truthfully partial status.
- **Root cause statement:** the remaining blocker is the combination of one still-live transport seam from `reasoning_core` into frozen `decision.py` and unresolved continuity writes in `reasoning_core`; until both are removed or rehoused through existing owners, the architecture remains truthfully partial.
- **Fix mechanism:**
  - remove or rehouse the two continuity-token writes from `reasoning_core` into canonically allowed owner surfaces or non-guarded transport-safe forms
  - extend the existing non-frozen owner lane so the remaining rooted residual family resolves before fallback
  - prove the old default-path `reasoning_core -> decision_router._handle_webhook_payload(...)` seam is deleted or unreachable

## Old authority seam targeted in this block (mandatory)
- **Primary old seam to kill:** `truffles-api/app/services/reasoning_core.py:12349-12361` -> `decision_router._handle_webhook_payload(...)` default-path transport fallback.
- **Governance blockers to repair as part of the same bundle:**
  - `truffles-api/app/services/reasoning_core.py:9482`
  - `truffles-api/app/services/reasoning_core.py:9693`
- **Residual families that must not silently widen:**
  - `truffles-api/app/routers/webhook/decision.py:1419-1875`
  - `truffles-api/app/routers/webhook/decision.py:12478-12545`
  - `truffles-api/app/routers/webhook/decision.py:15659-15756`
  - `truffles-api/app/routers/webhook/decision.py:19373-19481`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
  - existing owner-cutover lanes already landed in `truffles-api/app/services/reasoning_core.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the target owners and adjacent family exits already exist; this block must finish the transport retirement instead of inventing another compatibility layer.

## Execution profile
- **TP mode:** `implementation`
- **Doc touch budget (files):** `10`
- **Code dominance:** `runtime-heavy`
- **Why this profile fits:** this block is expected to make a real runtime seam unreachable and clean up governance drift.

## Invariant
- no edits to frozen `truffles-api/app/routers/webhook/decision.py`
- no edits to frozen `truffles-api/app/routers/webhook/booking.py`
- no edits to frozen `truffles-api/app/routers/webhook/pending.py`
- no new wrapper/helper as a way around the block
- no second web search
- no claim that green `L2` or final acceptance closure is proven

## Scope
- repair the current continuity-guard drift in `reasoning_core`
- kill or bypass the live `reasoning_core -> decision_router._handle_webhook_payload(...)` transport seam on the default path
- keep work inside the rooted terminal family and existing owner destinations
- add focused runtime evidence and sync canon/session artifacts with the truthful result

## Out of scope
- changes to frozen router files
- unrelated proof-path or acceptance work
- reopening unrelated continuity or timeout families outside the rooted terminal family
- any second web search

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Run the deterministic seam and continuity-guard scans.
2. Remove or rehouse the continuity-token writes currently blocking `continuity_writer_guard.py`.
3. Extend the existing non-frozen owner lane so the rooted residual family resolves before `decision_router._handle_webhook_payload(...)` on the default path.
4. Add focused regression evidence for transport-seam death and guard closure.
5. Sync canon/session artifacts with the truthful runtime result, or stop and publish `GAP` if seam death cannot be proven.

## DoD
- the old default-path transport seam at `truffles-api/app/services/reasoning_core.py:12349-12361` is deleted or unreachable
- `python3 scripts/continuity_writer_guard.py` is green
- `python3 scripts/arch_guard.py` is green
- no new helper/wrapper was introduced as the escape hatch
- focused runtime tests prove the old seam no longer reaches frozen `decision.py`
- if the seam cannot be killed truthfully, the block stops as `GAP` and does not claim progress

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|\"expected_reply_type\": \"time\"" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1419,1875p;12478,12545p;15659,15756p;19373,19481p'`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py truffles-api/app/services/state_service.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'expected_reply or booking_prompt_owner or explicit_handoff_owner or check_booking_prompt_owner or timeout_pending_slot_question'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'tool_reply_without_evidence_clarifies or list_slots_missing_slot_pending_question_preserves_interaction_evidence or collect_service_info_interrupt_routes_to_catalog_service_query'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply or policy_timeout or owner_cutover'`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'booking_payload or expected_reply'`
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
- deterministic scans proving the old transport seam no longer remains live
- green continuity and architecture guards
- focused regression proving default-path traffic no longer falls into frozen `decision.py`
- updated canon/session artifacts for the truthful seam result

## Rollback
1. Revert the runtime/code/doc changes from this bundle.
2. Regenerate the packet.
3. Re-run the checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded runtime bundle in non-frozen owner surfaces only.
- **Go/no-go signals:** continuity guard, architecture guard, focused runtime tests, architecture tests, and session gate are green; repo truth proves the old transport seam is dead.
- **Rollback:** revert the bundle, regenerate packet, rerun guards/tests.
- **Post-release monitoring window:** the immediate next block must be a post-implementation audit or `GAP`, not another unrelated micro-cut.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic scans plus focused unit/contract suites only.
- **Stop condition:** if the continuity drift cannot be repaired truthfully or the live transport seam cannot be killed without helper growth or frozen widening, stop and publish `GAP` instead of claiming terminal progress.
- **Escalation path:** `Top Architect`

## No-go
- no frozen-file edits
- no new helper/wrapper counted as progress
- no claim that final acceptance closure is done
- no doc-only block counted as runtime seam deletion

## Risks / blockers
- one or more residual families may still require a targeted frozen-waiver decision if they cannot be bypassed through the existing non-frozen owner lane.
- the continuity-guard drift may indicate missing owner extraction rather than a simple line deletion; if so, rehouse it only to allowed writer surfaces.
- if the default-path transport seam survives even after governance repair, this block must stop as `GAP`.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - frozen residual families at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`
  - frozen deferred debt at `truffles-api/app/routers/webhook/booking.py:2442`
  - `semantic_owner` remains partial until seam death is proven
  - `continuity_owner` remains partial until guard closure and seam death are proven
  - `boundary_owner` remains partial until seam death is proven
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:** this block only targets the terminal transport seam and governance drift, not acceptance closure.
- **Risk if deferred:** the program keeps a live legacy transport seam and red governance status while appearing further along than repo truth allows.
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-post-implementation-audit-a922` (to be authored only if this bundle lands a real seam death)
- **Expiry/trigger to stop deferral:** stop deferral before any new consultant-core block is counted as meaningful progress.

## Next-block contract (mandatory)
- **Next block objective:** publish one post-implementation audit only if this bundle truthfully kills the old `reasoning_core -> decision_router._handle_webhook_payload(...)` seam; otherwise publish `GAP` or an explicit frozen-waiver decision.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|\"expected_reply_type\": \"time\"" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if seam death requires a new wrapper/helper, frozen-file widening, a second web query, or cannot be proven with focused runtime evidence, stop and publish `GAP`.
- **Owner role for closure:** `Top Architect`
