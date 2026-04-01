# TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOUNDARY-VALIDATOR-BLOCK-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-PRICING-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-pricing-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOUNDARY-OWNER-NEXT-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Начать реальный `boundary owner cutover` без frozen-router edits: перенести authoring bounded `block` boundary overrides из `truffles-api/app/services/reasoning_core.py` в `truffles-api/app/core/boundary_validator.py`, чтобы preflight/ignore artifact family больше не формировала boundary contract локально в `reasoning_core`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-pricing-collect-owner-cutover-a922.md`
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
  - `sed -n '1,220p' truffles-api/app/core/boundary_validator.py`
  - `sed -n '260,830p' truffles-api/app/services/reasoning_core.py`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - `BoundaryValidator` currently owns only `build_degrade_override(...)`; bounded `block` overrides are still authored manually inside `reasoning_core`.
  - `reasoning_core` repeats the same `BoundaryOverride(decision="block", preserve_fields=[...])` contract for empty-message, missing-remote-jid, missing-tenant-context, sender-branch-ignore, tenant-context reject, remote-branch-phone-ignore, and duplicate-message artifact builders.
  - Those paths are already new-core controlled and do not require frozen-router edits, so they are the next safe boundary-owner slice once bounded semantic owner seams flatten out.
- `Detected drift (docs vs code)`: boundary ownership is still marked legacy-mixed, and this repeated block-override authoring inside `reasoning_core` is part of that remaining debt.

## One web search (mandatory before implementation)
- **Query (exact):** `Pydantic BaseModel methods official docs`
- **Date/time (local):** `2026-03-16 23:36 +0500`
- **Why this query is precise:** the block centralizes typed override construction in `BoundaryValidator`; it must keep override creation model-driven instead of open-coded dict assembly.
- **Sources opened (from this query):**
  - `Models - Pydantic` — `https://docs.pydantic.dev/latest/concepts/models/`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** typed `BaseModel` construction is the intended contract-preserving way to centralize override creation without widening mutation semantics.
- **Decision:** `reuse + integrate` — add a typed block-override builder inside `BoundaryValidator` and reuse it from existing preflight/ignore artifact builders.
- **Rejected options:**
  - leaving repeated `BoundaryOverride(...)` authoring in `reasoning_core`
  - touching frozen `decision.py` / `booking.py` / `pending.py`
  - widening immediately into broader policy-timeout legacy boundary logic
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** bounded boundary contract authoring for block/ignore paths is still duplicated in `reasoning_core` instead of living under the typed boundary owner.
- **Minimal reproduction:**
  1. Inspect `_build_empty_message_artifact(...)`, `_build_missing_remote_jid_artifact(...)`, `_build_missing_tenant_context_artifact(...)`, `_build_sender_branch_ignore_artifact(...)`, `_build_tenant_context_reject_artifact(...)`, `_build_remote_branch_phone_ignore_artifact(...)`, and `_build_duplicate_message_artifact(...)`.
  2. Observe the repeated inline `BoundaryOverride(decision="block", ...)` payload with the same preserve-field contract.
- **Evidence to capture:**
  - new `BoundaryValidator.build_block_override(...)` produces schema-valid typed payloads
  - representative reasoning-core artifact builders now delegate to the typed boundary owner
- **Five Whys (or equivalent):**
  1. Why is boundary owner still incomplete? Because `reasoning_core` still authors part of the block boundary contract itself.
  2. Why is that a problem? Because typed boundary ownership remains split across the target owner and orchestration layer.
  3. Why not tackle the larger legacy timeout/handoff boundary logic now? Because that still lives behind frozen legacy and is not a safe bounded slice.
  4. Why is this block safe? Because it only centralizes already-identical block override construction for paths already owned by new core.
  5. Why do this now? Because the next safe semantic seam inventory is thinning, and the strategy lock explicitly allows switching to boundary owner cutover.
- **Root cause statement:** the boundary owner target exists, but repeated `block` override creation still lives in `reasoning_core`, so boundary contract ownership remains unnecessarily fragmented.
- **Fix mechanism:**
  - add a typed `build_block_override(...)` seam in `BoundaryValidator`
  - route the existing preflight/ignore artifact family through that seam
  - add contract coverage for the new typed builder

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `BoundaryOverride`
  - `BoundaryValidator`
  - existing preflight/ignore artifact builders in `reasoning_core`
- **External reuse:**
  - official Pydantic model construction docs
- **Why not reinvent the wheel:** this block only centralizes already-existing boundary payloads under the typed boundary owner.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded boundary-owner bridge plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No semantic behavior widening.
- Only bounded block override authoring moves from `reasoning_core` to `BoundaryValidator`.

## Scope
- Add a typed `build_block_override(...)` helper in `BoundaryValidator`.
- Route the existing reasoning-core preflight/ignore artifact family through it.
- Add focused contract/regression coverage and sync canon/session artifacts.

## Out of scope
- legacy timeout/handoff boundary logic in frozen `decision.py`
- semantic owner cutovers
- broader request-replan boundary flows
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-boundary-validator-block-override-bridge-a922.md`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`
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
2. Add a typed block-override builder in `BoundaryValidator`.
3. Route the existing reasoning-core preflight/ignore artifact family through that seam.
4. Add focused contract/regression coverage.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `BoundaryValidator` owns typed block-override construction
- bounded reasoning-core preflight/ignore artifact builders no longer author `BoundaryOverride(decision="block", ...)` inline
- runtime contracts and reasoning-core regression coverage stay green
- no new bridge family is introduced

## Checks
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'missing_remote_jid_artifact or pricing_collect_owner or master_query_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/boundary_validator.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime contract test for typed block override
- reasoning-core regression showing representative artifact still yields the same boundary contract
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** contracts + reasoning-core + architecture only for this bounded block
- **Stop condition:** if the block starts pulling in frozen legacy timeout/handoff semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded boundary-owner bridge only; no new entrypoints or semantic bridges
- **Go/no-go signals:** contracts + reasoning-core + architecture suites green; continuity and semantic bridge guards green
- **Rollback:** revert the new boundary-validator helper, reasoning-core delegation, tests, and doc sync
- **Post-release monitoring window:** next block should either extend another bounded boundary-owner seam or return to a larger planner/outcome cutover without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the boundary-validator block-override bridge and generated packet output.

## Rollback
1. Revert the boundary-validator helper, reasoning-core delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into legacy timeout/handoff boundary logic
- no counting this block as done unless `BoundaryValidator` becomes the typed owner for the bounded block-override family

## Risks / blockers
- if another reasoning-core path still relies on custom inline block overrides outside this bounded family, boundary ownership would remain partial
- if the helper broadens preserve-field semantics, the contract could drift

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader boundary logic still remains legacy-mixed behind frozen `decision.py`
  - proof path is still not fully black-box
  - semantic owner cutover is still incomplete
- **Why not in this block:**
  - this block only centralizes one bounded block-override family already owned by new core
- **Risk if deferred:**
  - boundary ownership would stay split and continue to encourage orchestration-layer contract authoring
- **Linked follow-up Task Package(s):**
  - next bounded boundary-owner bridge, or richer planner/outcome cutover if that becomes the better deletion candidate
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate needs frozen legacy timeout/handoff edits or semantic bridge growth

## Next-block contract (mandatory)
- **Next block objective:** next bounded boundary-owner or richer owner-replacement seam that deletes another legacy-mixed authority without new bridge growth
- **First deterministic check command:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'boundary'`
- **Blocked-by conditions:** any candidate that needs frozen-router edits, timeout/handoff legacy widening, or new ingress bridge families
- **Owner role for closure:** `Top Architect`
