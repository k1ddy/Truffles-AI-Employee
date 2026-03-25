# TP-2026-03-17-consultant-core-turn-executor-boundary-artifact-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-ARTIFACT-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-TURN-RESULT-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-turn-result-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-ARTIFACT-OWNER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded boundary-artifact seam: `truffles-api/app/services/reasoning_core.py` больше не должен вручную делать boundary `validate(...)`, `ResponseRealizer().realize(...)` и финальную сборку bounded preflight/degrade artifact pair. Typed boundary artifact assembly должен перейти в `truffles-api/app/core/turn_executor.py`, чтобы `reasoning_core` остался orchestration layer, а bounded boundary execution pair жила в core execution owner.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-turn-result-bridge-a922.md`
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
  - `rg -n "boundary\.validate\(|ResponseRealizer\(\)\.realize\(" truffles-api/app/services/reasoning_core.py`
  - `sed -n '220,610p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,220p' truffles-api/app/core/turn_executor.py`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - bounded boundary turn-result ownership already moved into `TurnExecutor`
  - bounded boundary outcome ownership already moved into `BoundaryValidator`
  - the same bounded reasoning-core family still performs inline boundary validation + reply realization before wrapping the artifact
- `Detected drift (docs vs code)`: execution ownership is closer, but bounded boundary artifact assembly is still split between `reasoning_core`, `BoundaryValidator`, and `TurnExecutor`.

## One web search (mandatory before implementation)
- **Query (exact):** `Python typing NamedTuple official docs`
- **Date/time (local):** `2026-03-17 15:40 +0500`
- **Why this query is precise:** this block likely needs one tiny typed return carrier for a paired `turn_result` + `turn_outcome`, and the implementation should use a standard typed tuple shape instead of ad-hoc dicts.
- **Sources opened (from this query):**
  - `typing — Support for type hints` — `https://docs.python.org/3/library/typing.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `typing.NamedTuple` is the standard library way to expose a small immutable typed pair with named fields and no extra schema churn.
- **Decision:** `reuse + integrate` — add a tiny typed artifact carrier in `TurnExecutor` and route the bounded boundary artifact family through execution-owned helpers.
- **Rejected options:**
  - leaving boundary artifact assembly inline in `reasoning_core`
  - returning untyped dicts/tuples
  - touching frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `reasoning_core` still manually validates boundary decisions, realizes boundary replies, and assembles the bounded preflight/degrade artifact pair even after boundary turn-result and boundary turn-outcome ownership moved into core helpers.
- **Minimal reproduction:**
  1. Inspect `_build_runtime_exception_artifact(...)` and `_build_*_artifact(...)` preflight helpers in `truffles-api/app/services/reasoning_core.py`.
  2. Observe repeated inline `boundary.validate(...)` and `ResponseRealizer().realize(...)` calls before wrapping the artifact.
  3. Compare with `TurnExecutor`, which already owns the paired `TurnResult` schema and can safely own the remaining bounded artifact pair assembly.
- **Evidence to capture:**
  - `TurnExecutor` builds a typed bounded boundary artifact pair
  - reasoning-core boundary/preflight regressions stay green without frozen-router edits
- **Five Whys (or equivalent):**
  1. Why is bounded boundary execution still split? Because override, turn-result, and turn-outcome ownership moved out, but validation/reply realization stayed inline in `reasoning_core`.
  2. Why does that matter? Because orchestration code still owns the last execution-shape details for the same bounded family.
  3. Why is this bounded? Because it targets only the runtime-exception plus preflight/ignore artifact family already behind new core.
  4. Why not widen into richer planner work? Because this block is only deleting the final bounded boundary artifact assembly seam.
  5. Why now? Because the previous audit showed this is the next real boundary seam left before micro-cutovers stop making sense.
- **Root cause statement:** bounded boundary artifact assembly was only partially migrated: `reasoning_core` still owns boundary validation and reply realization for the same preflight/degrade family whose typed contracts are already in core owners.
- **Fix mechanism:**
  - add typed boundary artifact builders to `TurnExecutor`
  - route the bounded preflight/degrade artifact family through them
  - cover the new helpers in runtime-contract tests and rerun reasoning-core regressions

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `BoundaryValidator` builders
  - existing `TurnExecutor` boundary turn-result builders
  - existing reasoning-core boundary artifact tests
- **External reuse:**
  - official Python `typing.NamedTuple` documentation
- **Why not reinvent the wheel:** this block extends the existing execution owner instead of adding a new sidecar helper or untyped return shape.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded execution-owner slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Bounded boundary/preflight behavior and metadata must stay contract-equivalent.
- No widening into planner semantics or continuity logic.

## Scope
- Add typed bounded boundary artifact builders to `TurnExecutor`.
- Delegate the bounded runtime-exception plus preflight/ignore artifact family in `reasoning_core.py` through them.
- Add focused runtime-contract coverage.
- Keep existing reasoning-core boundary regressions green.
- Sync canon/session artifacts.

## Out of scope
- richer semantic owner cutovers
- continuity work
- frozen legacy semantic files
- new ingress bridges
- broader boundary-owner work beyond the bounded artifact family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-artifact-bridge-a922.md`
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
2. Extend `TurnExecutor` with typed bounded boundary artifact builders.
3. Replace inline boundary validation + reply realization + artifact assembly in `reasoning_core.py` with those builders.
4. Add focused runtime-contract coverage and rerun boundary reasoning-core regressions.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `TurnExecutor` owns typed bounded boundary artifact assembly.
- `reasoning_core.py` no longer manually validates + realizes + assembles the bounded runtime-exception/preflight artifact family inline.
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
- runtime-contract tests covering the execution-owned bounded boundary artifact builders
- reasoning-core boundary regressions proving parity for the shared bounded family
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** runtime-contract + focused boundary reasoning-core tests + architecture only
- **Stop condition:** if no equally bounded boundary/output seam remains after this block, stop micro-cutovers and return to richer owner replacement or broader boundary owner work
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded execution-owner cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** runtime-contract + focused boundary regressions + architecture green; packet/session gates green
- **Rollback:** revert the new turn-executor artifact helpers, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should return to richer owner replacement or a broader boundary-owner slice unless another equally bounded contract seam still exists

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the turn-executor boundary artifact bridge and generated packet output.

## Rollback
1. Revert the new turn-executor boundary artifact helpers, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no semantic owner widening
- no continuity detour
- no counting this block as done unless inline bounded boundary validation + reply realization + artifact assembly is deleted from `reasoning_core`

## Risks / blockers
- if artifact metadata drifts, preflight/degrade evidence could regress even with identical external behavior
- if blocked/degraded transport or reason-code propagation drifts, runtime-contract assertions could fail

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded artifact family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the last clearly bounded boundary artifact seam and must not widen into richer planner logic
- **Risk if deferred:**
  - execution ownership would remain split across orchestration code and core owners for the same boundary family
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-next-slice-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if no equally bounded boundary/output seam remains after this block, stop micro-cutovers and return to richer owner replacement or broader boundary-owner work

## Next-block contract (mandatory)
- **Next block objective:** determine whether any equally bounded boundary/output seam remains after deleting bounded boundary artifact assembly; otherwise switch back to richer owner replacement
- **First deterministic check command:** `rg -n "boundary\.validate\(|ResponseRealizer\(\)\.realize\(" truffles-api/app/services/reasoning_core.py truffles-api/app/core`
- **Blocked-by conditions:** if remaining matches belong only to planner owner finalization or are not part of the bounded boundary family, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
