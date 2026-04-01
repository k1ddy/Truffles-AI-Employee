# TP-2026-03-17-consultant-core-turn-executor-boundary-turn-result-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-TURN-RESULT-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-OWNER-OUTCOME-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-NEXT-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded boundary/runtime-contract seam: preflight/degrade artifact family в `truffles-api/app/services/reasoning_core.py` больше не должна вручную собирать typed `TurnResult` через `TurnExecutor().assemble(...)`. Typed boundary turn-result contract должен перейти в `truffles-api/app/core/turn_executor.py`, чтобы `reasoning_core` остался orchestration layer, а boundary-family runtime output assembly жил в core execution owner.

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
  - `rg -n "TurnExecutor\(\)\.assemble|boundary_override=|build_degrade_turn_outcome|build_block_turn_outcome" truffles-api/app/services/reasoning_core.py`
  - `sed -n '200,650p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,180p' truffles-api/app/core/turn_executor.py`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - bounded boundary outcome ownership already moved out of `reasoning_core`
  - bounded boundary `TurnResult` assembly still lives inline in the preflight/degrade artifact builders
  - the remaining inline `TurnExecutor().assemble(...)` outside planner finalization belongs only to this boundary family
- `Detected drift (docs vs code)`: execution ownership is partially true, but bounded boundary turn-result assembly still lives in `reasoning_core` instead of the execution owner.

## One web search (mandatory before implementation)
- **Query (exact):** `Python keyword-only arguments official docs`
- **Date/time (local):** `2026-03-17 15:10 +0500`
- **Why this query is precise:** this block adds another small typed execution helper with several similarly typed contract fields, so the helper must stay keyword-only and misuse-resistant.
- **Sources opened (from this query):**
  - `More on Defining Functions — Special parameters` — `https://docs.python.org/3/tutorial/controlflow.html#special-parameters`
  - `Python glossary — keyword-only` — `https://docs.python.org/3/glossary.html#term-keyword-only`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python keyword-only parameters are the standard way to keep helper calls explicit when many string/status arguments share the same type shape.
- **Decision:** `reuse + integrate` — extend `TurnExecutor` with keyword-only boundary turn-result builders and route the existing reasoning-core boundary family through them.
- **Rejected options:**
  - leaving bounded boundary turn-result assembly inline in `reasoning_core`
  - moving this seam into frozen router files
  - widening the block into richer semantic cutover
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `reasoning_core` still manually assembles typed `TurnResult` for the bounded boundary/preflight family even after boundary override and boundary outcome ownership moved into core owners.
- **Minimal reproduction:**
  1. Inspect `_build_runtime_exception_artifact(...)` and `_build_*_artifact(...)` preflight helpers in `truffles-api/app/services/reasoning_core.py`.
  2. Observe repeated inline `TurnExecutor().assemble(...)` calls with bounded `blocked` / `degraded` contract semantics.
  3. Compare with `TurnExecutor`, which already owns the same runtime result schema and owner-cutover outcome helpers.
- **Evidence to capture:**
  - `TurnExecutor` builds bounded boundary `TurnResult` contracts
  - reasoning-core boundary/preflight tests stay green without frozen-router edits
- **Five Whys (or equivalent):**
  1. Why is execution ownership still split? Because boundary overrides/outcomes moved to core owners, but the paired boundary `TurnResult` assembly stayed inline in `reasoning_core`.
  2. Why does that matter? Because orchestration code still owns typed runtime contract details for the boundary family.
  3. Why is this block bounded? Because it targets only the shared preflight/degrade artifact family and does not widen into planner semantics.
  4. Why not do richer semantic work here? Because this block is only deleting the remaining bounded boundary turn-result seam.
  5. Why now? Because it removes another real contract-authoring seam without new bridge growth.
- **Root cause statement:** bounded boundary runtime contract assembly was only partially migrated: override and outcome ownership moved into core helpers, but the matching `TurnResult` assembly remained inline in `reasoning_core`, leaving execution ownership split.
- **Fix mechanism:**
  - add keyword-only boundary `TurnResult` builders to `TurnExecutor`
  - route the bounded preflight/degrade artifact family through them
  - cover the builders in runtime-contract tests and rerun reasoning-core regressions

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `TurnExecutor.assemble(...)`
  - existing `BoundaryValidator` builders
  - existing reasoning-core boundary artifact tests
- **External reuse:**
  - official Python keyword-only parameter documentation
- **Why not reinvent the wheel:** this block extends the existing execution owner instead of introducing another sidecar helper.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded execution-owner slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Boundary/preflight behavior and metadata must stay contract-equivalent.
- No widening into planner semantics or continuity logic.

## Scope
- Add typed boundary `TurnResult` builders to `TurnExecutor`.
- Delegate the bounded boundary/preflight artifact family in `reasoning_core.py` through them.
- Add focused runtime-contract coverage.
- Keep existing reasoning-core boundary regressions green.
- Sync canon/session artifacts.

## Out of scope
- richer semantic owner cutovers
- continuity work
- frozen legacy semantic files
- new ingress bridges
- broader boundary validation semantics outside the bounded preflight/degrade family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-turn-result-bridge-a922.md`
- `truffles-api/app/core/turn_executor.py`
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
2. Extend `TurnExecutor` with keyword-only typed boundary turn-result builders for `blocked` and `degraded` paths.
3. Replace inline boundary-family `TurnExecutor().assemble(...)` calls in `reasoning_core.py` with those builders.
4. Add focused runtime-contract coverage and rerun boundary reasoning-core regressions.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `TurnExecutor` owns typed boundary-family `TurnResult` assembly.
- `reasoning_core.py` no longer manually assembles the bounded boundary/preflight `TurnResult` family inline.
- runtime-contract tests cover the new execution-owned builders.
- existing reasoning-core boundary regressions stay green.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'build_runtime_exception_artifact or build_empty_message_artifact or build_missing_remote_jid_artifact or build_missing_tenant_context_artifact or build_tenant_context_reject_artifact or build_remote_branch_phone_ignore_artifact or build_duplicate_message_artifact or build_sender_branch_ignore_artifact'`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime-contract tests covering the execution-owned boundary turn-result builders
- reasoning-core boundary regressions proving parity for the shared bounded family
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** runtime-contract + focused boundary reasoning-core tests + architecture only
- **Stop condition:** if the next remaining seam widens into richer planner or restore semantics, stop micro-cutovers and return to larger owner replacement
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded execution-owner cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** runtime-contract + focused boundary regressions + architecture green; packet/session gates green
- **Rollback:** revert the new turn-executor helpers, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should return to richer owner replacement or remaining boundary-owner completion unless another equally bounded contract seam remains

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the turn-executor boundary turn-result bridge and generated packet output.

## Rollback
1. Revert the new turn-executor boundary turn-result helpers, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no semantic owner widening
- no continuity detour
- no counting this block as done unless inline bounded boundary `TurnResult` assembly is deleted from `reasoning_core`

## Risks / blockers
- if boundary stage metadata drifts, preflight/degrade evidence could regress even with identical external behavior
- if blocked/degraded contract status drifts, downstream runtime-contract assertions could fail

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the bounded boundary turn-result seam and must not widen into richer planner logic
- **Risk if deferred:**
  - execution ownership would remain split between core execution primitives and orchestration code for the boundary family
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-next-slice-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if no equally bounded boundary/output seam remains, stop micro-cutovers and return to richer owner replacement or broader boundary owner completion

## Next-block contract (mandatory)
- **Next block objective:** determine whether any equally bounded boundary/output seam remains after deleting bounded boundary turn-result assembly; otherwise switch back to richer owner replacement
- **First deterministic check command:** `rg -n "TurnExecutor\(\)\.assemble|build_.*turn_result" truffles-api/app/services/reasoning_core.py truffles-api/app/core`
- **Blocked-by conditions:** if remaining matches belong only to planner owner finalization or schema/model definitions, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
