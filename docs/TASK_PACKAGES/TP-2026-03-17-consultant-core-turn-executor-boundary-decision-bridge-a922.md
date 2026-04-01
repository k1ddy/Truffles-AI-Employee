# TP-2026-03-17-consultant-core-turn-executor-boundary-decision-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-DECISION-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-OWNER-OUTCOME-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded boundary-authoring seam: `truffles-api/app/services/reasoning_core.py` больше не должен вручную строить `PolicyDecision`, `BoundaryOverride` и blocked/degraded `DialogState` для runtime-exception + preflight/ignore family. Typed boundary decision/override/state assembly должен перейти в `truffles-api/app/core/turn_executor.py`, чтобы в `reasoning_core` для этого family остались только thin wrappers и transport/persistence orchestration.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "build_preflight_reject|build_controlled_degrade|build_block_override|build_degrade_override|build_blocked_state|build_degraded_state" truffles-api/app/services/reasoning_core.py`
  - `sed -n '200,560p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,260p' truffles-api/app/core/turn_executor.py`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - boundary artifact/result/outcome assembly already moved into `TurnExecutor`
  - the remaining repeated authoring seam in `reasoning_core` is the bounded construction of boundary decision + override + dialog state for runtime-exception and preflight/ignore helpers
  - deleting this seam reduces boundary-authoring ownership in `reasoning_core` without widening semantics or touching frozen routers
- `Detected drift (docs vs code)`: execution/boundary contracts are typed in core, but `reasoning_core` still authors the same bounded boundary inputs inline across multiple helpers.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses official docs`
- **Date/time (local):** `2026-03-17 09:45 +0500`
- **Why this query is precise:** this block benefits from a small typed request carrier for repeated boundary-family inputs, and the carrier should stay on standard-library data structures instead of ad-hoc dict plumbing.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** standard-library `@dataclass` is the correct narrow way to model immutable typed request payloads without introducing new runtime validation frameworks into an internal core seam.
- **Decision:** `reuse + integrate` — use standard-library dataclasses for bounded boundary request carriers inside `TurnExecutor`.
- **Rejected options:**
  - leave boundary decision/override/state assembly inline in `reasoning_core`
  - widen the block into new semantic behavior
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** runtime-exception and preflight/ignore helpers in `reasoning_core` still repeat inline construction of `PolicyDecision`, `BoundaryOverride` and blocked/degraded `DialogState`, even after boundary artifact/result/outcome assembly moved into core executors.
- **Minimal reproduction:**
  1. Inspect `_build_runtime_exception_artifact(...)` and the adjacent `_build_*_artifact(...)` helpers in `truffles-api/app/services/reasoning_core.py`.
  2. Observe repeated `TurnPlanner()`, `BoundaryValidator()`, `DialogStateService()` setup and inline calls to `build_controlled_degrade`, `build_preflight_reject`, `build_*_override`, and `build_*_state`.
  3. Compare with the already-centralized `TurnExecutor` artifact builders that still need those inputs passed in from `reasoning_core`.
- **Evidence to capture:**
  - `TurnExecutor` builds typed boundary decision artifacts from request carriers
  - reasoning-core preflight/degrade regressions stay green without frozen-router edits
- **Five Whys (or equivalent):**
  1. Why is boundary ownership still split? Because earlier execution cutovers centralized only artifact/result/outcome assembly.
  2. Why does that matter? Because `reasoning_core` still authors the same bounded boundary contracts repeatedly.
  3. Why is this safe to cut over now? Because the family is deterministic and already contract-shaped; the block does not add new semantic branches.
  4. Why not widen into richer planner semantics? Because this block is about deleting remaining boundary-authoring duplication, not expanding semantic ownership.
  5. Why now? Because bounded boundary micro-seams in `reasoning_core` are nearly exhausted, and this is the next real owner deletion.
- **Root cause statement:** boundary execution moved to core incrementally, leaving the repeated construction of boundary decision/override/dialog-state inputs behind in `reasoning_core` for the bounded runtime-exception + preflight/ignore family.
- **Fix mechanism:**
  - add typed boundary request carriers and high-level builders to `TurnExecutor`
  - delegate the repeated reasoning-core boundary helpers through those builders
  - add direct contract coverage and rerun focused regressions

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `TurnExecutor` boundary artifact pattern
  - existing `TurnPlanner`, `BoundaryValidator`, `DialogStateService` typed builders
  - existing reasoning-core preflight/degrade regressions
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** this block extends the existing core execution owner instead of creating another helper family in `reasoning_core`.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded boundary-owner deletion plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Boundary external behavior and reason-code evidence must stay contract-equivalent.
- No widening into new planner semantics or continuity logic.

## Scope
- Add typed boundary request carriers/builders to `TurnExecutor`.
- Delegate bounded runtime-exception + preflight/ignore helpers in `reasoning_core.py` through them.
- Add focused runtime-contract coverage.
- Keep existing preflight/degrade regressions green.
- Sync canon/session artifacts.

## Out of scope
- new semantic owner slices
- continuity work
- frozen legacy semantic files
- new ingress bridges
- broader boundary-owner work outside the bounded runtime-exception + preflight/ignore family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-decision-bridge-a922.md`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Extend `TurnExecutor` with typed bounded boundary request carriers and high-level builders.
3. Replace repeated boundary decision/override/dialog-state authoring in `reasoning_core.py` with those builders.
4. Add focused runtime-contract coverage and rerun preflight/degrade regressions.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `TurnExecutor` owns typed bounded boundary decision/override/dialog-state assembly for runtime-exception + preflight/ignore family.
- `reasoning_core.py` no longer manually calls `build_controlled_degrade`, `build_preflight_reject`, `build_block_override`, `build_degrade_override`, `build_blocked_state`, or `build_degraded_state` for that bounded family.
- runtime-contract tests cover the new high-level builders.
- existing preflight/degrade regressions stay green.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'build_runtime_exception_artifact or build_empty_message_artifact or build_missing_remote_jid_artifact or build_missing_tenant_context_artifact or build_tenant_context_reject_artifact or build_remote_branch_phone_ignore_artifact or build_duplicate_message_artifact or build_sender_branch_ignore_artifact'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/core/__init__.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime-contract tests covering the execution-owned boundary request carriers/builders
- reasoning-core preflight/degrade regressions proving parity for the bounded boundary family
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** runtime-contract + focused reasoning-core preflight/degrade tests + architecture only
- **Stop condition:** if this deletes the last repeated bounded boundary decision seam from `reasoning_core`, the next block must move to richer owner replacement or a broader owner cutover
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded boundary-authoring cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** runtime-contract + focused reasoning-core preflight/degrade regressions + architecture green; packet/session gates green
- **Rollback:** revert the new turn-executor boundary builders, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should return to richer owner replacement or broader owner work unless another equally bounded boundary seam still exists

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the turn-executor boundary decision bridge and generated packet output.

## Rollback
1. Revert the new turn-executor boundary request carriers/builders, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no semantic owner widening
- no continuity detour
- no counting this block as done unless repeated boundary decision/override/dialog-state authoring is deleted from `reasoning_core` for this bounded family

## Risks / blockers
- if reason-code propagation drifts, preflight/degrade evidence in `turn_outcome.meta` can silently regress
- if tool-action or ignored-path metadata drifts, blocked inbound observability may change without visible reply changes

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded runtime-exception + preflight/ignore family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the remaining repeated boundary-authoring seam in `reasoning_core` and must not widen into new semantic behavior
- **Risk if deferred:**
  - boundary ownership remains split between orchestration and core execution owners for every runtime-exception + preflight/ignore turn
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-boundary-owner-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block removes the last repeated bounded boundary decision seam, stop boundary micro-cutovers and return to richer owner replacement or broader owner work

## Next-block contract (mandatory)
- **Next block objective:** audit whether any equally bounded boundary seam remains after deleting repeated boundary decision/override/dialog-state authoring; otherwise switch back to richer owner replacement or broader owner work
- **First deterministic check command:** `rg -n "build_controlled_degrade|build_preflight_reject|build_block_override|build_degrade_override|build_blocked_state|build_degraded_state" truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** if remaining matches belong only to broader orchestration or would require new semantic branch growth, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
