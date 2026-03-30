# TP-2026-03-27-consultant-core-workstream1-closeout-proof-pass-a922

## Block identity
- `BLOCK_ID`: `WS1-closeout-proof-pass`
- `PARENT_BLOCK_ID`: `WS1-closeout-decision-final-legacy-residue`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-decision-final-legacy-residue-closeout-a922.md`
- `UNLOCKS`: `Workstream 1 close decision`

## Название/цель
Провести честный closure-only proof pass по критериям `Workstream 1` и определить, можно ли закрыть `Semantic Owner Extraction` без narrative claims.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## FACT pre-check (before closure)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `Baseline commands`:
  - `sed -n '19,43p' docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
  - `rg -n "from \\. import _legacy as legacy|from app\\.routers\\.webhook\\._legacy import|from app\\.routers\\.webhook import _legacy as legacy|legacy\\." truffles-api/app | sed -n '1,120p'`
- `FACT findings`:
  - completion criterion 4 now has direct import-graph evidence after the final `decision.py` residue cut.
  - criteria 1-3 already have targeted deterministic coverage across planner/runtime/intent tests, but they have not yet been replayed together as one closeout envelope.

## One web search (mandatory before implementation)
- `Not required`: closure-only proof block; no new implementation family is opened here.

## Root cause (mandatory)
- **Symptom:** Workstream 1 has many completed authority cuts but is still marked `open` because no final proof pass has mapped all four completion criteria to current evidence.
- **Minimal reproduction:**
  - `STATE.md` shows multiple completed Workstream 1 cuts while still declaring the workstream open.
- **Evidence to capture:**
  - one deterministic proof envelope covering all four completion criteria
  - explicit close decision: `done` or `open`
- **Five Whys (or equivalent):**
  1. Why is Workstream 1 not yet closed? Because the code changed incrementally, but a final criterion-by-criterion proof pass has not been recorded.
  2. Why does that matter? Because closure must be evidence-backed, not inferred from a series of patches.
  3. Why not assume it is done? Because criteria 1-3 require current replay evidence, and criterion 4 requires current import-graph evidence.
  4. Why run a combined deterministic envelope now? Because it is the smallest honest proof artifact before any done/open decision.
  5. Why keep it closure-only? Because the goal is assessment, not another implementation family.
- **Root cause statement:** Workstream 1 lacks a final machine-checkable closure pass tying current code to the program-level completion criteria.
- **Fix mechanism:** run the combined deterministic proof envelope, map each result to a criterion, and update repo truth with the close decision.

## Reuse-first plan (mandatory)
- **Internal reuse:** reuse the existing deterministic suites and architecture guards created by the earlier Workstream 1 cuts.
- **External reuse:** none.
- **Why not reinvent the wheel:** closure should use existing contract evidence, not new bespoke checks.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `closure`
- **Doc touch budget (files):** `3`
- **Code dominance:** `forbidden unless proof reveals a blocker`
- **Override token:** `none`

## Invariant
- no new implementation unless the proof pass reveals a concrete blocker.
- no downgrade of Workstream 1 completion criteria.

## Scope
- run one combined deterministic proof envelope for criteria 1-4
- update repo truth with the explicit close decision

## Out of scope
- new feature work
- Workstream 2+
- any acceptance/llm-quality claim

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-closeout-proof-pass-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Map each Workstream 1 criterion to an existing deterministic check.
2. Run the combined proof envelope.
3. Update repo truth with a close decision backed by the results.

## DoD
- every Workstream 1 criterion has current deterministic evidence recorded
- repo truth states explicitly whether Workstream 1 is `done` or remains `open`

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "route_llm_policy_core or semantic_decision or tool_args_sanitized"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment or semantic_decision_post_owner_mutation or semantic_decision_required"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `rg -n "from \\. import _legacy as legacy|from app\\.routers\\.webhook\\._legacy import|from app\\.routers\\.webhook import _legacy as legacy|legacy\\." truffles-api/app | sed -n '1,120p'`
- `git diff --check`

## Evidence
- criterion-by-criterion mapping to current passing checks
- explicit close decision in repo truth

## Rollback
- none for closure-only pass; if a blocker appears, open a new implementation TP instead of patching inside this block.

## No-go
- no new implementation unless a blocker is proven
- no marking Workstream 1 `done` without explicit evidence for all four criteria

## Risks/Blockers
- one or more criteria may still lack sufficient proof, forcing Workstream 1 to remain `open`.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: none beyond whatever the proof pass surfaces.
- `Why not in this block`: this block is assessment-only.
- `Risk if deferred`: Workstream 1 status remains narrative rather than evidence-backed.
- `Linked follow-up Task Package(s)`: if blocked, open a new implementation TP from the surfaced criterion.
- `Expiry/trigger to stop deferral`: n/a

## Next-block contract (mandatory)
- `Next block objective`: either mark Workstream 1 done with evidence or open the exact remaining implementation TP for the surfaced blocker.
- `First deterministic check command`: `sed -n '19,43p' docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `Blocked-by conditions`: any criterion lacks current evidence or fails replay.
- `Owner role for closure`: `Brain / Top Architect`

## Implementation result
- `Status`: `done`
- `Criterion map`:
  - `criterion 1` (`exactly one SemanticDecisionV1 per canaried turn`) -> `test_turn_planner_expected_reply_validation.py` (`8 passed`) + `test_consultant_core_runtime_contracts.py -k semantic_decision...` (`8 passed`)
  - `criterion 2` (`no downstream mutation of semantic owner fields`) -> runtime/dialog-state semantic subsets (`8 passed` + `7 passed`)
  - `criterion 3` (`owner output contains no concrete tool_args`) -> `test_intent.py -k route_llm_policy_core or semantic_decision or tool_args_sanitized` (`2 passed`)
  - `criterion 4` (`legacy owner-adjacent paths are shadow-only or deleted`) -> `test_legacy_freeze_guard.py` (`12 passed`) + app-runtime import grep shows no `_legacy.py` imports/calls
- `Deterministic checks`:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "route_llm_policy_core or semantic_decision or tool_args_sanitized"` -> `2 passed, 76 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py` -> `8 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment or semantic_decision_post_owner_mutation or semantic_decision_required"` -> `8 passed, 66 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment"` -> `7 passed, 73 deselected`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py` -> `12 passed`
  - `rg -n "from \. import _legacy as legacy|from app\.routers\.webhook\._legacy import|from app\.routers\.webhook import _legacy as legacy|legacy\." truffles-api/app | sed -n '1,120p'` -> no app-runtime `_legacy.py` imports/calls remain
  - `git diff --check` -> `pass`
- `Close decision`:
  - `Workstream 1`: `done`
  - `Program`: `open`
- `Realistic/local behavior checks`:
  - no new realism/llm-quality run in this closure-only pass
- `Next block`:
  - `Workstream 2 — Binding Boundary Extraction`
