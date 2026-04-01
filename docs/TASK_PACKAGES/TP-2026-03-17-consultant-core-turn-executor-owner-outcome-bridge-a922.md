# TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-OWNER-OUTCOME-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-ARTIFACT-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-artifact-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-OWNER-FINALIZER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded owner-finalizer seam: `truffles-api/app/services/reasoning_core.py` больше не должен вручную делать `ResponseRealizer().realize(...)`, `TurnExecutor().assemble(...)` и `build_owner_cutover_turn_outcome(...)` для planner-owner cutover path. Typed owner reply/result/outcome assembly должен перейти в `truffles-api/app/core/turn_executor.py`, чтобы в `reasoning_core` остались orchestration, persistence и transport.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-artifact-bridge-a922.md`
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
  - `rg -n "ResponseRealizer\(\)\.realize\(|TurnExecutor\(\)\.assemble\(|build_owner_cutover_turn_outcome\(" truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_executor.py`
  - `sed -n '1360,1525p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,280p' truffles-api/app/core/turn_executor.py`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - bounded boundary artifact family already moved into `TurnExecutor`
  - the only remaining inline `ResponseRealizer/assemble/owner_outcome` authoring in `reasoning_core` belongs to planner-owner finalization
  - this seam is shared by all current safe owner-replacement cuts, so deleting it reduces orchestration ownership without widening semantics
- `Detected drift (docs vs code)`: `turn_executor` is already the typed result owner, but planner-owner finalizer still assembles its own reply/result/outcome inline in `reasoning_core`.

## One web search (mandatory before implementation)
- **Query (exact):** `Python typing Literal official docs`
- **Date/time (local):** `2026-03-17 16:28 +0500`
- **Why this query is precise:** this block may extend typed owner-outcome helper parameters, and any new action/status surface should stay on standard-library typing primitives instead of ad-hoc strings.
- **Sources opened (from this query):**
  - `typing — Support for type hints` — `https://docs.python.org/3/library/typing.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `typing.Literal` is the standard library way to keep a narrow, explicit value surface for helper parameters and return contracts.
- **Decision:** `reuse + integrate` — keep the owner-outcome bridge typed inside `TurnExecutor` with narrow parameter surfaces instead of adding untyped dict plumbing.
- **Rejected options:**
  - leaving owner reply/result/outcome assembly inline in `reasoning_core`
  - widening the block into planner semantics
  - touching frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** planner-owner cutovers still leave the final reply/result/outcome assembly inside `reasoning_core`, even though `TurnExecutor` already owns the typed runtime result contract.
- **Minimal reproduction:**
  1. Inspect `_finalize_turn_planner_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py`.
  2. Observe inline `ResponseRealizer().realize(...)`, `TurnExecutor().assemble(...)`, and `build_owner_cutover_turn_outcome(...)`.
  3. Compare with the previous boundary blocks where the same execution-shape responsibilities were moved into `TurnExecutor`.
- **Evidence to capture:**
  - `TurnExecutor` builds a typed owner artifact for planner-owner cutovers
  - reasoning-core owner-cutover regressions stay green without frozen-router edits
- **Five Whys (or equivalent):**
  1. Why is planner-owner finalization still split? Because previous execution cutovers stopped at bounded boundary families.
  2. Why does that matter? Because orchestration still owns the last typed reply/result/outcome assembly seam for direct owner replacement.
  3. Why is this bounded? Because it only rewires the shared owner-finalizer path and does not add any new semantic branch.
  4. Why not widen into booking/service semantics now? Because this block is purely about deleting execution ownership from `reasoning_core`.
  5. Why now? Because the remaining boundary micro-seams are effectively exhausted and this is the next real execution-owner seam.
- **Root cause statement:** planner-owner cutovers only partially migrated to core execution ownership; the final reply/result/outcome assembly remained inline in `reasoning_core` after typed contracts already moved into `TurnExecutor`.
- **Fix mechanism:**
  - add a typed owner artifact builder to `TurnExecutor`
  - route `_finalize_turn_planner_owner_cutover(...)` through it
  - add direct contract coverage and rerun owner-cutover regressions

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `TurnExecutor` boundary artifact pattern
  - existing owner-cutover finalizer in `reasoning_core`
  - existing owner-cutover reasoning-core regressions
- **External reuse:**
  - official Python `typing.Literal` documentation
- **Why not reinvent the wheel:** this block extends the existing execution owner instead of introducing a parallel helper family.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded execution-owner slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Planner-owner external behavior and metadata must stay contract-equivalent.
- No widening into new planner semantics or continuity logic.

## Scope
- Add a typed planner-owner artifact builder to `TurnExecutor`.
- Delegate planner-owner reply/result/outcome assembly in `reasoning_core.py` through it.
- Add focused runtime-contract coverage.
- Keep existing owner-cutover regressions green.
- Sync canon/session artifacts.

## Out of scope
- new semantic owner slices
- continuity work
- frozen legacy semantic files
- new ingress bridges
- broader boundary-owner work outside the planner-owner execution seam

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-owner-outcome-bridge-a922.md`
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
2. Extend `TurnExecutor` with a typed planner-owner artifact builder.
3. Replace inline owner reply/result/outcome assembly in `_finalize_turn_planner_owner_cutover(...)` with that builder.
4. Add focused runtime-contract coverage and rerun owner-cutover regressions.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `TurnExecutor` owns typed planner-owner artifact assembly.
- `reasoning_core.py` no longer manually realizes reply / assembles turn result / builds owner outcome for planner-owner cutovers.
- runtime-contract tests cover the new execution-owned helper.
- existing owner-cutover regressions stay green.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'pricing_collect_owner or duration_collect_owner or master_query_collect_owner or master_query_owner or booking_verification_owner or safe_service_query_owner or safe_catalog_owner or safe_info_owner'`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime-contract tests covering the execution-owned planner-owner artifact builder
- reasoning-core owner-cutover regressions proving parity for the shared finalizer path
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** runtime-contract + focused owner-cutover reasoning-core tests + architecture only
- **Stop condition:** if this deletes the last inline planner-owner execution seam from `reasoning_core`, the next block must move to richer owner replacement or broader boundary/continuity owner work
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded execution-owner cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** runtime-contract + focused owner-cutover regressions + architecture green; packet/session gates green
- **Rollback:** revert the new turn-executor owner artifact helper, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should return to richer owner replacement or broader owner work unless another equally bounded execution seam still exists

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the turn-executor owner-outcome bridge and generated packet output.

## Rollback
1. Revert the new turn-executor owner artifact helper, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no semantic owner widening
- no continuity detour
- no counting this block as done unless inline planner-owner reply/result/outcome assembly is deleted from `reasoning_core`

## Risks / blockers
- if owner metadata drifts, downstream evidence in `decision_meta/turn_outcome` could regress without visible text changes
- if transport reason propagation drifts, owner-cutover audit evidence could become incomplete

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the shared owner-finalizer seam
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the remaining shared execution seam in planner-owner finalization and must not widen into new semantic behavior
- **Risk if deferred:**
  - execution ownership would remain split between orchestration and core execution owners for every current safe owner cutover
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-next-slice-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block removes the last shared planner-owner execution seam, stop execution micro-cutovers and return to richer owner replacement or broader owner work

## Next-block contract (mandatory)
- **Next block objective:** audit whether any equally bounded execution seam remains after deleting planner-owner reply/result/outcome assembly; otherwise switch back to richer owner replacement or broader owner work
- **First deterministic check command:** `rg -n "ResponseRealizer\(\)\.realize\(|TurnExecutor\(\)\.assemble\(|build_owner_cutover_turn_outcome\(" truffles-api/app/services/reasoning_core.py truffles-api/app/core`
- **Blocked-by conditions:** if remaining matches belong only to broader planner orchestration or would require new semantic branch growth, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
