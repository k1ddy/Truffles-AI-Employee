# TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-AUTHORITY-CLOSURE-PLAN-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish the stop-the-line targeted frozen-waiver decision for final ingress/coordinator closure. This block must prove that truthful closure of the remaining live `/webhook` authority now requires exact frozen `decision.py` scope, record why non-frozen owner surfaces are insufficient by themselves, and lock the narrowest admissible future waiver scope.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
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
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1208,1325p;12470,12545p;15590,15625p;19310,19445p'`
  - `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py`
- `FACT findings`:
  - live fallback remains explicit and unconditional when direct-owner cutovers return `None`: `truffles-api/app/services/reasoning_core.py:6980` and `truffles-api/app/services/reasoning_core.py:6992` still call `decision_router._handle_webhook_payload(...)`.
  - the fallback target remains the frozen live ingress handler at `truffles-api/app/routers/webhook/decision.py:8887`.
  - frozen `decision.py` still owns semantic policy routing and payload extraction through `route_llm_policy_core(...)` at `truffles-api/app/routers/webhook/decision.py:12478`, `truffles-api/app/routers/webhook/decision.py:12510`, and `truffles-api/app/routers/webhook/decision.py:12534`.
  - frozen `decision.py` still owns continuity authority in `_apply_expected_reply_contract(...)` at `truffles-api/app/routers/webhook/decision.py:1216`, `truffles-api/app/routers/webhook/decision.py:1234`, `truffles-api/app/routers/webhook/decision.py:1273`, `truffles-api/app/routers/webhook/decision.py:1314`, and `truffles-api/app/routers/webhook/decision.py:1320`.
  - frozen `decision.py` still writes continuity plus timeout/degrade boundary state in the live flow at `truffles-api/app/routers/webhook/decision.py:15590` through `truffles-api/app/routers/webhook/decision.py:15625`.
  - frozen `decision.py` still owns fact-guard and tool-reply boundary/result assembly at `truffles-api/app/routers/webhook/decision.py:19313` through `truffles-api/app/routers/webhook/decision.py:19445`, including direct `TurnOutcome(...)` / `TurnOutcomeObservability(...)` authoring.
  - non-frozen owner surfaces already exist (`turn_planner`, `dialog_state_service`, `boundary_validator`, `turn_executor`, `state_service`), but no fully wired non-frozen entrypoint currently makes these remaining live families unreachable.
  - `ops/diagnose.py` remains proof-only; `r24` fallback-JID `None` dereference does not change runtime owner truth.
- `Detected drift (docs vs code)`:
  - the final-ingress closure plan correctly identified the structural blocker, but its next move still left open whether a bounded non-frozen implementation was admissible; deterministic scan now disproves that and forces the next move to a targeted frozen-waiver decision.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent final-ingress closure plan; no second query is allowed or needed for this stop-line decision block
- **Existing solutions found:**
  - use expand/migrate/contract to route live traffic through the new interface first, then contract the old coordinator until it becomes transport-only or unreachable
- **Decision:** `reuse/integrate`
  - keep the target owners (`turn_planner`, `dialog_state_service`, `boundary_validator`, `turn_executor`, `state_service`) unchanged
  - move the question from non-frozen implementation feasibility to exact frozen-waiver admissibility
- **Rejected options:**
  - a second web search: rejected by the block rule and unnecessary
  - adding a new compatibility wrapper/helper around `decision.py`: rejected because it preserves the live authority split
  - continuing proof-path residual work: rejected because it does not close runtime owner authority

## Root cause (mandatory)
- **Symptom:** `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial even after many downstream cutovers, and the final-ingress closure plan cannot proceed as a non-frozen implementation bundle.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/reasoning_core.py:6980` and `truffles-api/app/services/reasoning_core.py:6992` and confirm unmatched live traffic still falls through to `decision_router._handle_webhook_payload(...)`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:12478`, `:12510`, and `:12534` and confirm semantic policy routing + payload extraction still live in frozen ingress.
  3. Inspect `truffles-api/app/routers/webhook/decision.py:1216-1320` and confirm expected-reply/session-memory continuity writes still live in frozen ingress.
  4. Inspect `truffles-api/app/routers/webhook/decision.py:15590-15625` and `:19313-19445` and confirm boundary/result assembly still lives there.
  5. Compare with the non-frozen owner surfaces and confirm no fully wired non-frozen entrypoint currently replaces these remaining live families.
- **Evidence to capture:**
  - the explicit fallback from `reasoning_core` into `decision.py`
  - the surviving semantic, continuity, and boundary clusters inside frozen `decision.py`
  - the absence of a fully wired non-frozen replacement path for those clusters
  - reclassification of `r24` proof-path residue as evidence-only
- **Five Whys (or equivalent):**
  1. Why do owner statuses remain partial? Because live `/webhook` ingress still reaches frozen `decision.py`.
  2. Why can't current non-frozen owner surfaces close this by themselves? Because the remaining live authority families still have no fully wired non-frozen entrypoint before fallback.
  3. Why isn't another `reasoning_core` cut enough? Because that would require inventing a new bypass path or wrapper around still-live frozen families.
  4. Why is `ops/diagnose.py` not the answer? Because it is proof-only and does not own runtime authority.
  5. Why is a targeted frozen waiver now the honest next step? Because the blocker is no longer “find the right owner”; it is governance over exact frozen `decision.py` families that still hold live authority.
- **Root cause statement:** the remaining architectural blocker is governance-bound frozen ingress authority in `truffles-api/app/routers/webhook/decision.py`; the surviving semantic, continuity, and boundary families still sit on the live fallback path, and no fully wired non-frozen replacement path currently makes them unreachable.
- **Fix mechanism:**
  - publish the targeted frozen-waiver decision as the active canon block
  - lock the exact future frozen scope to the remaining ingress/coordinator families in `decision.py`
  - reject any broader frozen expansion, new compatibility seam, or proof-path detour

## FACT vs INFERENCE verdict
- **FACT:** live `/webhook` fallback still reaches frozen `decision.py`.
- **FACT:** the remaining live families are not limited to proof-path residue; they include semantic route/payload authority, continuity contract writes, and boundary/result assembly in frozen `decision.py`.
- **FACT:** current non-frozen owner surfaces are insufficient to make those families unreachable without wiring a new path that does not yet exist.
- **INFERENCE:** a narrow targeted frozen waiver is now the only honest path to further structural progress on this closure story.
- **Decision:** switch canon from the final-ingress closure plan TP to one targeted frozen-waiver decision block.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/state_service.py`
  - existing owner-cutover interception patterns in `truffles-api/app/services/reasoning_core.py`
  - the parent closure plan TP and its deterministic scans
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the target owners already exist; only exact frozen governance is missing

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `doc-heavy`
- **Override token:** `final-ingress-coordinator-targeted-frozen-waiver-decision`
- **Why this profile fits:** this is a governance/decision block that updates canon and locks the exact next move without touching runtime code.

## Invariant
- no runtime code edits in this block
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` is already `done`
- no claim that `r24` proof-path residue is the primary blocker
- no new wrapper/helper or compatibility seam counted as progress
- no reopening of transport / billing / observer as the main story

## Scope
- prove that final ingress/coordinator closure is now blocked by exact frozen ingress authority
- record why a non-frozen implementation bundle is not admissible
- lock the narrowest future waiver scope
- switch canon/session/packet to the waiver-decision block

## Out of scope
- runtime implementation
- edits to frozen files in this block
- acceptance or dev reruns
- new `ops/diagnose.py` work
- broad redesign beyond the exact future waiver scope

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
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
1. Publish this targeted frozen-waiver decision TP with exact scope, RCA, and next-block contract.
2. Record the factual blocked state: the final-ingress implementation cannot truthfully proceed as non-frozen work.
3. Lock the exact future waiver scope to the surviving ingress/coordinator families in frozen `decision.py` only.
4. Switch canon so the next nonnegotiable move is the runtime implementation under that targeted waiver.
5. Regenerate packet and rerun governance/session checks.

## Exact future waiver scope
- `truffles-api/app/routers/webhook/decision.py`
  - `_apply_expected_reply_contract(...)` continuity family rooted at `:1216` only for expected-reply/session-memory fallback and human-request bypass writes
  - policy-core route/rescue/payload extraction family rooted at `:12478`, `:12510`, and `:12534`
  - timeout/degrade boundary continuity family rooted at `:15590` through `:15625`
  - fact-guard + tool-reply `TurnOutcome` / transport-observability family rooted at `:19313` through `:19445`
- bounded supporting non-frozen surfaces only:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - focused tests under `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_dialog_state_service.py`, `truffles-api/tests/test_message_endpoint.py`, and `truffles-api/tests/architecture`
- **Not in waiver scope:**
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `ops/diagnose.py`
  - transport / billing / observer code
  - unrelated `decision.py` branches outside the exact rooted families above

## DoD
- the targeted frozen-waiver decision TP exists at `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- canon/packet/test all agree that this decision block is now active
- the exact future waiver scope is machine-readable in canon/session artifacts
- the next move is no longer the stale non-frozen implementation bundle
- required checks are green

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1208,1325p;12470,12545p;15590,15625p;19310,19445p'`
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
- updated TP, canon, packet, session, state, and structure
- deterministic scan proving the live fallback still reaches frozen `decision.py`
- deterministic scan proving the surviving semantic / continuity / boundary clusters still live there
- green governance/session checks

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** doc/canon/guard checks only
- **Stop condition:** if the future waiver scope cannot stay exact and rooted to the declared families, stop and publish `GAP` instead of widening the freeze
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only decision block; no runtime rollout
- **Go/no-go signals:** source-of-truth, packet, architecture tests, and session gate all agree on the targeted frozen-waiver decision and next move
- **Rollback:** revert the TP and canon/session updates, regenerate packet, rerun checks
- **Post-release monitoring window:** the next runtime block must stay inside the exact future waiver scope defined here

## Rollback
1. Revert this decision TP and the matching canon/session updates.
2. Regenerate packet.
3. Re-run governance/session checks.

## No-go
- no runtime edits hidden inside this decision block
- no continued proof-path residual laddering counted as structural progress
- no new wrapper/helper around `decision.py`
- no blanket frozen-file waiver beyond the exact future scope listed above
- no claim that the old ingress/coordinator family is already dead

## Risks / blockers
- the runtime implementation may prove that one of the rooted families is still broader than this decision scope; if so, stop and reopen the waiver decision instead of widening silently
- the future runtime block must avoid moving transport logic into `state_service.py` or another new hotspot
- `docs/LEGACY_SUNSET.yaml` will need exact scoped updates in the runtime block if the waiver is exercised

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live `/webhook` ingress still falls through `reasoning_core` into frozen `decision.py`
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial
  - `r24` proof-path fallback-JID `None` dereference remains unresolved as evidence-only residue
- **Why not in this block:**
  - this block only decides the truthful waiver scope and next move; it does not execute runtime changes
- **Risk if deferred:**
  - the program can stall on the freeze boundary or drift back into proof-path symptom work while the main live authority remains untouched
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md` (to be authored or executed next)
- **Expiry/trigger to stop deferral:**
  - before any next ingress/coordinator runtime implementation starts
  - immediately if anyone proposes another proof-path residual block as the primary story

## Next-block contract (mandatory)
- **Next block objective:** implement one exact-scope targeted frozen-waiver bundle that reduces the surviving live ingress/coordinator families in `decision.py` to target-owner invocation only and makes the old `reasoning_core -> decision.py` authority seam unreachable on the chosen contour
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the implementation requires a new wrapper/helper, broadens beyond the exact future waiver scope, or still cannot make an old authority seam unreachable, stop and escalate instead of claiming progress
- **Owner role for closure:** `Top Architect`
