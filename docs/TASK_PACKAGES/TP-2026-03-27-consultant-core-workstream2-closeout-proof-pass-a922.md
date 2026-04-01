# TP-2026-03-27-consultant-core-workstream2-closeout-proof-pass-a922

- Title/goal: Run the deterministic closeout proof for Workstream 2 and freeze the remaining binding-boundary creation surface.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md`
- Invariant: no new executable authority may bypass typed binding.
- Scope: architecture proof, deterministic contract replay, repo truth updates.
- Out of scope: new behavior changes, Workstream 3 state unification, legacy mesh, LLM quality acceptance.
- Touch-list:
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: closure

## Root cause (mandatory)
- Symptom:
  - Workstream 2 is heavily cut, but it is not yet frozen/proven closed at the repo boundary.
- Minimal reproduction:
  - without an architecture guard, a future app-runtime file could directly instantiate `PolicyDecision` or call `PolicyDecision.model_validate(...)` outside `TurnPlanner`/`BoundaryValidator` and silently reopen compatibility-only binding paths.
- Evidence:
  - app-runtime search shows construction is currently concentrated in `truffles-api/app/core/turn_planner.py` and normalization in `truffles-api/app/core/boundary_validator.py`
- Five Whys:
  1. Why isn't W2 closure explicit yet? Because the current evidence is distributed across several implementation families.
  2. Why is that risky? Because there is no single freeze guard for the remaining creation surface.
  3. Why does that matter? Because binding-boundary authority could quietly spread again.
  4. Why is that a Workstream 2 concern? Because Workstream 2 is about one binding boundary, not just local patches.
  5. Why fix now? Because the runtime contract and schema are already in place; only closure proof remains.
- Root cause statement:
  - Workstream 2 lacks one explicit closure proof that freezes `PolicyDecision` creation/validation to the governed core boundary.
- Fix mechanism:
  - add an architecture guard for direct `PolicyDecision` creation/model validation in app-runtime code and replay the deterministic contract envelope.

## Plan
1. Add an architecture guard that only `turn_planner.py` may construct `PolicyDecision` and only `turn_planner.py` / `boundary_validator.py` may call `PolicyDecision.model_validate(...)`.
2. Run runtime contract replay and architecture suite.
3. Update repo truth and decide whether Workstream 2 is `done`.

## DoD
- architecture guard is green
- runtime contract suite is green
- repo truth clearly states whether Workstream 2 is done or still open

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `git diff --check`

## Evidence
- test output
- exact files changed
- `STATE.md` closeout entry

## Rollback
- revert this TP diff; Workstream 2 stays open without a frozen closure guard.

## No-go
- no new binding behavior
- no closure claim without deterministic proof

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - compatibility `tool_action` / `outcome` fields still remain on `PolicyDecision`
- Why not in this block:
  - closeout only proves boundary ownership; it does not remove every compatibility field yet
- Risk if deferred:
  - Workstream 2 remains narratively open despite code-level closure
- Linked follow-up Task Package(s):
  - Workstream 3 entry TP
- Expiry/trigger to stop deferral:
  - if architecture guard or runtime replay fails, Workstream 2 cannot be marked done

## Next-block contract (mandatory)
- Next block objective:
  - start Workstream 3 only after Workstream 2 closeout is explicit
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- Blocked-by conditions:
  - Workstream 2 closure evidence must be green
- Owner role for closure:
  - Brain / Top Architect


## Implementation result
- Added an architecture guard that freezes `PolicyDecision` creation to `turn_planner.py` and `PolicyDecision.model_validate(...)` calls to `turn_planner.py` / `boundary_validator.py`.
- Replayed the deterministic Workstream 2 runtime contract envelope and the architecture freeze guard.
- Workstream 2 is now implementation-complete in this worktree: typed binding is the governed executable boundary for semantic-owner and synthetic boundary decisions, and app-runtime creation/validation is frozen to the governed core surface.

## Checks run
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `87 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `13 passed`
- `git diff --check` -> `pass`

## Authority removed
- App-runtime code can no longer silently spread `PolicyDecision` creation/model validation beyond the governed core boundary without tripping architecture proof.

## Residual debt after this block
- Compatibility `tool_action` / `outcome` fields still remain on `PolicyDecision`, but they are no longer the required executable authority when typed binding is present.
- Workstream 3 now owns canonical-state unification; W2 no longer blocks on binding-boundary extraction.
