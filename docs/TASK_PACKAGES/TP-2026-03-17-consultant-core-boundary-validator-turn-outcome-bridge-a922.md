# TP-2026-03-17-consultant-core-boundary-validator-turn-outcome-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-VALIDATOR-TURN-OUTCOME-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-VALIDATOR-BLOCK-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-NEXT-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded boundary-authoring seam: `truffles-api/app/services/reasoning_core.py` больше не должен вручную собирать `TurnOutcome` для runtime-exception degrade и bounded preflight/ignore block artifact family. `BoundaryValidator` должен стать owner-ом typed turn-outcome contract для этих boundary artifacts.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py`
  - `sed -n '220,760p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,180p' truffles-api/app/core/boundary_validator.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'build_runtime_exception_artifact or build_empty_message_artifact or build_missing_remote_jid_artifact or build_missing_tenant_context_artifact or build_tenant_context_reject_artifact or build_remote_branch_phone_ignore_artifact or build_duplicate_message_artifact or build_sender_branch_ignore_artifact'`
- `FACT findings`:
  - `BoundaryValidator` already owns typed `block` and `degrade` override builders.
  - `reasoning_core.py` still manually authors `TurnOutcome` payloads for the same bounded boundary family.
  - The inline `TurnOutcome` authoring repeats the same boundary contract fields: `contract_status`, observability transport fields, `reason_code`, `boundary_decision`, `interaction_owner`, and path flags.
- `Detected drift (docs vs code)`: boundary owner cutover is truthful for override payloads, but boundary turn-outcome contract authoring still lives in `reasoning_core`, so boundary ownership remains mixed.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses.dataclass official docs`
- **Date/time (local):** `2026-03-17 08:55 +0500`
- **Why this query is precise:** this block needs a small typed internal contract for boundary turn-outcome authoring; the implementation should use a standard typed Python structure rather than ad-hoc dicts.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** standard-library typed structures are the correct reuse path for small immutable internal contracts; the block should keep boundary outcome authoring typed and centralized rather than extending ad-hoc dict assembly in `reasoning_core`.
- **Decision:** `reuse + integrate` — extend `BoundaryValidator` with typed turn-outcome builders and route existing boundary artifact helpers through them.
- **Rejected options:**
  - leaving `TurnOutcome` authoring inline in `reasoning_core`
  - widening into semantic planner ownership
  - touching frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** boundary cutover remains mixed because `reasoning_core.py` still manually assembles `TurnOutcome` payloads for bounded block/degrade artifacts even after `BoundaryValidator` took over typed override construction.
- **Minimal reproduction:**
  1. Inspect `_build_runtime_exception_artifact(...)` in `truffles-api/app/services/reasoning_core.py`.
  2. Inspect `_build_empty_message_artifact(...)`, `_build_missing_remote_jid_artifact(...)`, `_build_missing_tenant_context_artifact(...)`, `_build_sender_branch_ignore_artifact(...)`, `_build_tenant_context_reject_artifact(...)`, `_build_remote_branch_phone_ignore_artifact(...)`, and `_build_duplicate_message_artifact(...)`.
  3. Observe repeated inline `TurnOutcome(...)` / `TurnOutcomeObservability(...)` authoring in `reasoning_core`.
- **Evidence to capture:**
  - `BoundaryValidator` builds typed block and degrade turn outcomes.
  - existing reasoning-core artifact tests stay green without frozen-router edits.
- **Five Whys (or equivalent):**
  1. Why is boundary ownership still mixed? Because override authoring moved, but turn-outcome contract authoring for the same boundary family did not.
  2. Why does that matter? Because `reasoning_core` still owns boundary-specific contract details that should live behind `BoundaryValidator`.
  3. Why is this block bounded? Because it targets only the existing runtime-exception + preflight/ignore artifact family already controlled by new core.
  4. Why not widen further? Because planner semantics and broader runtime outcomes are separate owner-cutover seams.
  5. Why fix this now? Because it deletes another real boundary-authoring seam without any new bridge growth.
- **Root cause statement:** boundary cutover stopped at `BoundaryOverride`, leaving the bounded block/degrade `TurnOutcome` contract authored inline in `reasoning_core`, so boundary ownership is still split across layers.
- **Fix mechanism:**
  - add typed boundary turn-outcome builders to `BoundaryValidator`
  - route the existing bounded artifact helpers through those builders
  - verify parity with runtime-contract and reasoning-core regression tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `BoundaryValidator.build_block_override(...)`
  - existing `BoundaryValidator.build_degrade_override(...)`
  - existing reasoning-core artifact builders and tests
- **External reuse:**
  - official Python dataclasses documentation
- **Why not reinvent the wheel:** this block only centralizes an already duplicated bounded contract through the existing boundary owner.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded boundary-owner slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Boundary artifact behavior must stay contract-equivalent for runtime-exception and bounded preflight/ignore families.
- Unsafe semantic/stateful paths must remain outside this block.

## Scope
- Add typed boundary turn-outcome builders to `BoundaryValidator`.
- Delegate the bounded block/degrade artifact family in `reasoning_core.py` through those builders.
- Add focused runtime-contract tests.
- Keep existing reasoning-core regressions green.
- Sync canon/session artifacts.

## Out of scope
- planner semantic ownership
- booking/stateful owner cutovers
- trace/restore continuity work
- frozen legacy semantic files
- new ingress bridges

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-boundary-validator-turn-outcome-bridge-a922.md`
- `truffles-api/app/core/boundary_validator.py`
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
2. Extend `BoundaryValidator` with typed turn-outcome builders for bounded block and degrade artifacts.
3. Replace inline `TurnOutcome` authoring in the existing reasoning-core boundary artifact family with boundary-owned builders.
4. Add focused runtime-contract tests and rerun existing reasoning-core regressions.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `BoundaryValidator` owns typed turn-outcome authoring for the bounded runtime-exception + preflight/ignore artifact family.
- `reasoning_core.py` no longer manually authors `TurnOutcome` for that family.
- runtime-contract tests cover the new boundary-owned builders.
- existing reasoning-core artifact regressions stay green.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'build_runtime_exception_artifact or build_empty_message_artifact or build_missing_remote_jid_artifact or build_missing_tenant_context_artifact or build_tenant_context_reject_artifact or build_remote_branch_phone_ignore_artifact or build_duplicate_message_artifact or build_sender_branch_ignore_artifact'`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/boundary_validator.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime-contract tests covering boundary-owned block/degrade turn-outcome builders
- reasoning-core artifact regressions proving parity for the bounded family
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** runtime-contract + focused reasoning-core artifact tests + architecture only
- **Stop condition:** if the next remaining boundary seam widens into broader planner/stateful booking semantics, stop micro-cutovers and switch back to richer owner replacement
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded boundary-owner cutover only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** runtime-contract + reasoning-core artifact regressions + architecture green; packet/session gates green
- **Rollback:** revert boundary-validator turn-outcome builders, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should be another bounded boundary-owner seam only if it deletes real legacy-mixed ownership

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the boundary-validator turn-outcome bridge and generated packet output.

## Rollback
1. Revert the new boundary-validator turn-outcome builders, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no semantic owner widening
- no continuity micro-bridge detour
- no counting this block as done unless inline boundary `TurnOutcome` authoring is deleted from the bounded reasoning-core family

## Risks / blockers
- if turn-outcome meta parity drifts, observability-based evidence could regress even if the reply path still works
- if reject/ignore mapping drifts, preflight telemetry could mislabel blocked vs ignored paths

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains outside this bounded artifact family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the bounded block/degrade turn-outcome authoring seam and must not widen into planner semantics or stateful booking outcomes
- **Risk if deferred:**
  - boundary ownership would remain split across `BoundaryValidator` and `reasoning_core`, keeping the cutover only half true
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-boundary-owner-next-slice-a922` (to be authored only if another bounded boundary seam remains)
- **Expiry/trigger to stop deferral:**
  - if the next boundary candidate requires booking/stateful semantic ownership, stop micro-cutovers and switch block type

## Next-block contract (mandatory)
- **Next block objective:** determine whether another bounded boundary-owner seam remains after deleting the turn-outcome authoring family; otherwise switch back to richer owner replacement
- **First deterministic check command:** `rg -n "TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** if the remaining matches are outside the bounded boundary artifact family or require semantic/stateful booking ownership, do not force another boundary micro-cutover
- **Owner role for closure:** `Top Architect`
