# TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-BROADER-FALLBACK-INGRESS-FAMILY-POST-IMPLEMENTATION-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BUNDLE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one terminal convergence decision for Consultant Core. This block must stop the current micro-cut story from being mistaken for full closure, choose the end-state explicitly, define the exact transport seam that still keeps `semantic_owner`, `continuity_owner`, and `boundary_owner` truthfully partial, and lock the next runtime move to one terminal convergence bundle instead of another open-ended series of residual micro-cuts.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before decision closure)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
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
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1419,1875p;12478,12545p;15659,15756p;19373,19481p'`
  - `rg -n "semantic_owner:|continuity_owner:|boundary_owner:|current_nonnegotiable_next_move" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md`
- `FACT findings`:
  - the live legacy transport seam is still `truffles-api/app/services/reasoning_core.py:12349` and `truffles-api/app/services/reasoning_core.py:12361`, where active `/webhook` traffic still calls `decision_router._handle_webhook_payload(...)`.
  - frozen ingress authority still begins at `truffles-api/app/routers/webhook/decision.py:8889`.
  - the surviving rooted residual families behind that transport seam are still concentrated at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `truffles-api/app/routers/webhook/decision.py:12478-12545`, `truffles-api/app/routers/webhook/decision.py:15659-15756`, and `truffles-api/app/routers/webhook/decision.py:19373-19481`.
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial in `docs/SOURCE_OF_TRUTH.yaml`; repo truth does not justify claiming full closure.
  - the mandatory governance rerun is still red: `python3 scripts/continuity_writer_guard.py` flags `truffles-api/app/services/reasoning_core.py:9482` (`expected_reply_type=reply_slot,`) and `truffles-api/app/services/reasoning_core.py:9693` (`"expected_reply_type": "time",`), and `python3 scripts/arch_guard.py` fails transitively for the same reason.
  - the current canon still points to another fallback-family micro-cut, but that trajectory does not by itself answer whether the program is finishing as full replacement or stabilizing as hybrid compatibility.
- `INFERENCE to verify in this block`:
  - the next truthful move should be a terminal convergence bundle under explicit `finish_mode`, not an unbounded continuation of micro-cut narrative.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active final-ingress chain; no second query is allowed or needed.
- **Existing solutions found:** stop counting bridge growth or local cuts as closure; choose the end-state explicitly, then route the last live traffic through the target owner lane and retire the legacy ingress seam.
- **Decision:** `reuse/integrate`
  - reuse existing target owners in `turn_planner`, `dialog_state_service`, `boundary_validator`, and `turn_executor`
  - do not introduce a new compatibility wrapper around `decision.py`
- **Rejected options:**
  - second web query
  - declaring hybrid completion without explicit decision
  - another doc block that still leaves the end-state ambiguous

## Root cause (mandatory)
- **Symptom:** many old seams have died, but `semantic_owner`, `continuity_owner`, and `boundary_owner` still remain truthfully partial and the program cannot honestly claim full architectural migration.
- **Minimal reproduction:**
  1. inspect `docs/SOURCE_OF_TRUTH.yaml` and confirm `semantic_owner`, `continuity_owner`, and `boundary_owner` still mark live legacy surfaces as current primary.
  2. inspect `truffles-api/app/services/reasoning_core.py:12349-12361` and confirm active `/webhook` traffic still falls through to `decision_router._handle_webhook_payload(...)`.
  3. inspect `truffles-api/app/routers/webhook/decision.py:8889-9005` and confirm frozen `decision.py` still remains the legacy ingress handler.
  4. inspect `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481` and confirm broader live mixed authority families still remain behind that transport seam.
  5. inspect `truffles-api/app/services/reasoning_core.py:9482` and `:9693` and confirm current governance red still blocks clean closure claims.
- **Evidence:**
  - live `reasoning_core -> decision.py` transport fallback
  - surviving mixed residual families in frozen `decision.py`
  - partial owner statuses in `docs/SOURCE_OF_TRUTH.yaml`
  - red `continuity_writer_guard` / `arch_guard`
- **Five Whys (or equivalent):**
  1. Why do owner statuses stay partial? Because active ingress still reaches frozen `decision.py`.
  2. Why does that matter? Because the surviving semantic, continuity, and boundary residuals still live behind that transport seam.
  3. Why are seam-by-seam local wins not enough anymore? Because they reduce the surface, but they do not by themselves define whether the program is finishing as full replacement or intentionally retaining a hybrid island.
  4. Why is a terminal decision required now? Because repo truth must stop implying that more micro-cuts automatically equal full closure.
  5. Why is governance repair part of the terminal story? Because clean closure cannot be claimed while the continuity guard and `arch_guard` are red on current repo truth.
- **Root cause statement:** the remaining blocker is no longer lack of local seam deletions; it is absence of one explicit terminal convergence decision around the still-live `reasoning_core -> decision_router._handle_webhook_payload(...)` transport seam plus unresolved governance drift that keeps clean closure claims invalid.
- **Fix mechanism:**
  - publish one terminal convergence decision block
  - choose `finish_mode` as the active target
  - define the exact terminal seam, residual family, and closure criteria
  - lock the next move to one terminal convergence bundle that must both repair governance drift truthfully and kill or bypass the final live transport seam without new helper growth

## End-state decision (mandatory)
- **Option A — `finish_mode`:** the program completes only when active `/webhook` traffic no longer reaches `decision_router._handle_webhook_payload(...)` on the default path, the remaining residual authority families are rehomed or unreachable through existing target owners, governance guards are clean, and owner statuses can move beyond `partial` with evidence.
- **Option B — `hybrid_mode`:** the program stops as a stable mixed architecture with an intentional retained legacy compatibility island; `partial` then becomes accepted steady-state instead of temporary migration debt.
- **FACT:** current canon objective still says full replacement: `replace multi-owner runtime with one semantic core, one continuity store, and a black-box proof path`.
- **Decision:** select `finish_mode`.
- **Reason:** repo truth does not support claiming the architecture is already fully migrated, and it also does not document intentional retention of the legacy transport seam as permanent product design.

## Terminal closure criteria (mandatory)
- `semantic_owner` cannot move beyond `partial` while active `/webhook` traffic still reaches `truffles-api/app/routers/webhook/decision.py` through `truffles-api/app/services/reasoning_core.py:12349` or `truffles-api/app/services/reasoning_core.py:12361`.
- `continuity_owner` cannot move beyond `partial` while `python3 scripts/continuity_writer_guard.py` still fails on `truffles-api/app/services/reasoning_core.py:9482` and `truffles-api/app/services/reasoning_core.py:9693`.
- `boundary_owner` cannot move beyond `partial` while the residual families at `truffles-api/app/routers/webhook/decision.py:15659-15756` and `truffles-api/app/routers/webhook/decision.py:19373-19481` still remain live behind the fallback seam.
- final closure is admissible only if repo truth shows:
  - no default-path call from `reasoning_core` into `decision_router._handle_webhook_payload(...)`
  - no new helper/wrapper used as a substitute for killing that seam
  - governance guards green
  - acceptance closure proven separately; this decision block does not claim it yet

## Rooted terminal family (mandatory)
- `truffles-api/app/services/reasoning_core.py:12349-12361`
- `truffles-api/app/routers/webhook/decision.py:8889-9005`
- `truffles-api/app/routers/webhook/decision.py:1419-1875`
- `truffles-api/app/routers/webhook/decision.py:12478-12545`
- `truffles-api/app/routers/webhook/decision.py:15659-15756`
- `truffles-api/app/routers/webhook/decision.py:19373-19481`
- governance repair blocker family:
  - `truffles-api/app/services/reasoning_core.py:9482`
  - `truffles-api/app/services/reasoning_core.py:9693`

## Admissible owner destinations (mandatory)
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py` as transport/preflight coordinator only, not as a new semantic/continuity compatibility wrapper
- existing supporting non-frozen services already used in this family:
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/app/services/policy_validation_boundary_service.py`

## FACT vs INFERENCE verdict
- **FACT:** this block is doc-only; no old authority seam is deleted or made unreachable here.
- **FACT:** the live legacy transport seam is still `reasoning_core -> decision_router._handle_webhook_payload(...)` at `truffles-api/app/services/reasoning_core.py:12349` and `:12361`.
- **FACT:** surviving rooted residual families still remain in frozen `decision.py` at `:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`.
- **FACT:** governance is still red on `truffles-api/app/services/reasoning_core.py:9482` and `:9693`.
- **INFERENCE:** the next truthful move is one terminal convergence bundle under `finish_mode`, not another open-ended fallback-family micro-cut narrative.
- **Decision:** switch canon to this terminal convergence decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - existing non-frozen owner-cutover patterns in `truffles-api/app/services/reasoning_core.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the target owner surfaces already exist; the missing artifact is explicit terminal convergence criteria and one bounded bundle that makes the last live transport seam unreachable.

## Execution profile
- **TP mode:** `decision`
- **Doc touch budget (files):** `10`
- **Code dominance:** `doc-only`
- **Why this profile fits:** this block changes program trajectory and closure criteria, but it does not claim runtime deletion.

## Invariant
- no runtime code edits in this block
- no claim that any old authority seam dies in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is done
- no claim that green `L2` or final acceptance closure is proven
- no second web search
- no new wrapper/helper counted as progress
- answer to `какой old authority seam стал deleted или unreachable после этого блока?` remains `никакой`

## Scope
- choose the explicit end-state for the consultant-core demolition program
- define the exact terminal transport seam and residual family
- define terminal closure criteria and admissible owner destinations
- switch canon/session artifacts to this decision block

## Out of scope
- runtime implementation in this block
- editing `truffles-api/app/services/reasoning_core.py` or frozen router files
- acceptance / `L2` work
- any second web search
- claiming runtime seam deletion in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
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
1. Publish this terminal convergence decision TP.
2. Switch canon/session artifacts from fallback-family audit mode to explicit `finish_mode` terminal convergence.
3. Regenerate packet and rerun the doc/governance checks.
4. Record the resulting next non-negotiable move as one terminal convergence bundle.

## DoD
- the terminal convergence decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md`
- canon / packet / architecture test all agree this is the active block
- the block explicitly selects `finish_mode`
- the block explicitly says seam-deletion count here is zero
- the next non-negotiable move is one terminal convergence bundle, not an ambiguous continuation of micro-cutting

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9475,9490p;9688,9696p;12336,12370p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '8889,9005p;1419,1875p;12478,12545p;15659,15756p;19373,19481p'`
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
- deterministic scans showing the still-live transport seam and residual family
- deterministic scans showing the still-red continuity guard lines
- updated canon/session artifacts for the terminal convergence decision block
- packet/test/session evidence after doc sync

## Rollback
1. Revert this TP and canon/session updates.
2. Regenerate packet.
3. Re-run the checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only terminal decision; no runtime rollout.
- **Go/no-go signals:** source-of-truth, packet, architecture test, and session gate all agree on `finish_mode` and the next terminal bundle.
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks.
- **Post-release monitoring window:** the next block must either land the terminal convergence bundle or stop with `GAP`; it must not drift back into indefinite micro-cut narrative.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic scans plus doc/governance checks only.
- **Stop condition:** if the next bundle cannot repair governance drift and kill or bypass the final transport seam without helper growth or widening beyond the rooted family, stop and publish `GAP` instead of claiming terminal progress.
- **Escalation path:** `Top Architect`

## No-go
- no runtime edits in this block
- no new helper/wrapper
- no claim that final transport seam is already dead
- no claim that partial owner statuses are already closed
- no switch to `hybrid_mode` without an explicit future decision

## Risks / blockers
- the terminal convergence bundle may still require a frozen-waiver decision if one residual family cannot be bypassed through existing non-frozen owner surfaces.
- governance repair may reveal that one or both continuity-guard lines belong in an allowed writer instead of `reasoning_core`; if so, that rehouse must be explicit and tested.
- frozen `truffles-api/app/routers/webhook/booking.py:2442` remains deferred debt and must not silently widen back into the main path.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live transport seam at `truffles-api/app/services/reasoning_core.py:12349-12361`
  - frozen residual families at `truffles-api/app/routers/webhook/decision.py:1419-1875`, `:12478-12545`, `:15659-15756`, and `:19373-19481`
  - continuity-guard drift at `truffles-api/app/services/reasoning_core.py:9482` and `:9693`
  - `semantic_owner` remains partial
  - `continuity_owner` remains partial
  - `boundary_owner` remains partial
  - green `L2` is not proven
  - final acceptance closure is not proven
- **Why not in this block:** this is a decision-only block.
- **Risk if deferred:** the program can keep accumulating local seam wins without ever making the final closure criteria explicit.
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922` (to be authored if the next runtime bundle remains admissible)
- **Expiry/trigger to stop deferral:** before any next consultant-core runtime cut is counted as architectural progress.

## Next-block contract (mandatory)
- **Next block objective:** implement one terminal convergence bundle that truthfully repairs the current continuity-guard drift and kills or bypasses the live `reasoning_core -> decision_router._handle_webhook_payload(...)` transport seam on the remaining rooted family without adding a new compatibility wrapper.
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|expected_reply_type=reply_slot,|\"expected_reply_type\": \"time\"" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the bundle requires a new helper/wrapper, widens into frozen `booking.py` or `pending.py`, needs a second web query, or cannot make an old live authority seam unreachable, stop and publish `GAP` instead of claiming progress.
- **Owner role for closure:** `Top Architect`
