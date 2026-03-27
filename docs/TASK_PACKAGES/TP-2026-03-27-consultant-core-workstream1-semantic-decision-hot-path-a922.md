# TP-2026-03-27-consultant-core-workstream1-semantic-decision-hot-path-a922

## Block identity
- `BLOCK_ID`: `WS1-F1-semantic-decision-hot-path`
- `PARENT_BLOCK_ID`: `none`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-target-decision-and-execution-program-a922.md`
- `UNLOCKS`: `WS1-F2-binding-boundary-read-only-cut`

## Название/цель
Внедрить первый bounded cut для Workstream 1: сделать `SemanticDecisionV1` единственным hot-path meaning artifact на активном runtime path, убрать concrete `tool_args` из owner output и добавить первый явный post-owner mutation guard для downstream compatibility carriers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/policy_tool_projector.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `contracts/runtime/policy_decision.v1.jsonschema`
- `Baseline commands`:
  - `rg -n "route_llm_policy_core|tool_args|semantic_frame|pending_question_contract|semantic_contract" truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py truffles-api/tests/test_turn_planner_expected_reply_validation.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - `route_llm_policy_core(...)` strips raw `tool_args` from LLM payload, then reintroduces projected `tool_args` into the returned success payload right before planner consumption; owner output is therefore not yet free of concrete binding args.
  - `TurnPlanner` still rebuilds `PendingQuestionContract`, `SemanticFrame`, and `meta.semantic_contract` from the post-owner payload and still carries `tool_args` in `PolicyDecision`.
  - `TurnExecutor` still reconstructs execution semantic and pending-question contracts from planner compatibility carriers instead of reading a single canonical owner artifact.
  - `ConsultantRuntime` still projects trace/meta semantic state from compatibility carriers (`semantic_frame`, `semantic_contract`, `pending_question_contract`) rather than from one canonical semantic owner object.
- `Detected drift (docs vs code)`: `present`
  - `docs/system_forensics/final/SEMANTIC_DECISION_V1.md` requires exactly one read-only meaning artifact with no concrete `tool_args`, but active code still reintroduces `tool_args` and rebuilds multiple compatibility meaning carriers after owner issuance.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev frozen pydantic model docs`
- **Date/time (local):** `2026-03-27 22:55, Asia/Almaty`
- **Why this query is precise:** We need one canonical semantic artifact that downstream code cannot casually mutate. The smallest external reuse candidate in this repo is a typed Pydantic model; the query targets the official immutability mechanism for that exact implementation choice.
- **Sources opened (from this query):**
  - `Pydantic ConfigDict / frozen`: `https://docs.pydantic.dev/2.0/api/config/`
- **Existing solutions found:** Official `ConfigDict(frozen=True)` gives a typed model with assignment blocking and schema generation, while still fitting the repo’s existing Pydantic-heavy runtime contracts.
- **Decision:** `integrate` — use a frozen Pydantic `SemanticDecisionV1` model plus explicit guard checks for derived compatibility carriers. This matches repo conventions and avoids inventing a parallel contract system.
- **Rejected options:**
  - Raw dict-only owner envelope: rejected because it does not create an enforceable typed contract or schema surface.
  - New external immutability library: rejected because the repo already standardizes on Pydantic runtime contracts.
- **Open questions:**
  - `frozen=True` is only faux immutability for nested containers, so the block still needs explicit guard logic for derived compatibility surfaces.

## Root cause (mandatory)
- **Symptom:** The active hot path still has split meaning authority after the owner call: owner output is not canonical, planner rebuilds meaning carriers, executor rehydrates meaning again, and runtime trace/meta read a compatibility mix instead of one semantic artifact.
- **Minimal reproduction:**
  - `rg -n "projected_payload\[\"tool_args\"\]|tool_args=self\._normalize_dict|_build_execution_semantic_contract|_project_runtime_semantic_contract" truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "tool_args or policy_core_preserves_pending_question_contract"`
- **Evidence to capture:**
  - runtime contract schemas
  - deterministic tests for route/planner/runtime contracts
  - exact code refs showing `tool_args` reinsertion and compatibility contract rebuilding
- **Five Whys (or equivalent):**
  1. Why is semantic ownership still split? Because the owner call does not emit a canonical semantic artifact that survives downstream intact.
  2. Why not? Because `route_llm_policy_core(...)` still returns a mixed payload (`semantic_frame` + projected binding data) instead of one typed semantic object.
  3. Why does that matter? Because planner and executor must then reconstruct `pending_question_contract`, `semantic_frame`, and `semantic_contract` from mixed payloads.
  4. Why is that dangerous? Because multiple downstream layers can silently change or reinterpret meaning fields after owner issuance.
  5. Why is the architecture still blocked? Because Workstream 1 requires one writer / read-only downstream meaning, and the current mixed payload prevents that cut.
- **Root cause statement:** The owner boundary still emits a mixed semantic-plus-binding payload, so planner/executor/runtime continue to rebuild and transport meaning through multiple compatibility carriers instead of reading one canonical semantic decision.
- **Fix mechanism:** Introduce a typed frozen `SemanticDecisionV1` on the hot path at the owner boundary, return binding data separately, derive planner compatibility carriers from `SemanticDecisionV1`, and add an explicit mutation guard that fails if those derived carriers diverge from the owner artifact.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse `LlmPolicyCoreOutput` validation in `truffles-api/app/schemas/intent.py`.
  - Reuse `PolicyToolProjection` / `project_policy_tool_binding(...)` as the temporary binding carrier.
  - Reuse existing `PolicyDecision`, `SemanticFrame`, and `PendingQuestionContract` as derived compatibility views.
- **External reuse:**
  - Official Pydantic `ConfigDict(frozen=True)` for the typed owner artifact.
- **Why not reinvent the wheel:** The repo already uses Pydantic for runtime contracts and JSON schema generation, so introducing a second contract mechanism would add surface area without removing authority.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** This is a code-first authority cut with limited contract/doc updates required to keep the repo truthful.

## Invariant
- Exactly one `SemanticDecisionV1` per canaried turn on the active runtime path.
- Owner output contains no concrete `tool_args`.
- Downstream layers may derive compatibility/binding views, but they may not become semantic co-owners.
- Failures remain explicit `deny/degrade/handoff`, not silent semantic rewrites.

## Scope
- Add a typed `SemanticDecisionV1` runtime contract in code and runtime schema.
- Make `route_llm_policy_core(...)` emit semantic payload + separate binding data.
- Make `TurnPlanner` derive compatibility carriers from `SemanticDecisionV1` and carry the canonical owner artifact on `PolicyDecision`.
- Add the first post-owner mutation guard for derived compatibility carriers on the active path.
- Make executor/runtime read the canonical owner artifact instead of rebuilding meaning from mixed compatibility payloads where feasible in this block.

## Out of scope
- Full `BindingPlanV1` extraction.
- `TurnJournalV1` / `ConversationProjectionV1` cutover.
- Legacy mesh strangling outside the active Workstream 1 spine.
- Deleting `booking_prompt_owner.py` in this block.

## Touch-list
- `truffles-api/app/core/semantic_decision.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `contracts/runtime/semantic_decision.v1.jsonschema`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-semantic-decision-hot-path-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add `SemanticDecisionV1` code contract and runtime schema, including helper methods for derived compatibility carriers and a mutation guard.
2. Change `route_llm_policy_core(...)` to emit canonical semantic payload plus separate binding output, with no concrete `tool_args` in semantic owner payload.
3. Change `TurnPlanner` to carry `semantic_decision` on `PolicyDecision`, derive compatibility carriers from it, and run the mutation guard.
4. Change executor/runtime reads to prefer `semantic_decision` over compatibility reconstruction where this family can remove authority without entering Workstreams 2-4.
5. Update deterministic tests and runtime contract schemas, then run the bounded checks.
6. Update `STATE.md` and `STRUCTURE.md` truthfully with removed authority and residual debt.

## DoD
- `route_llm_policy_core(...)` success payload is `SemanticDecisionV1` and contains no `tool_args`.
- `PolicyDecision` carries exactly one `semantic_decision` owner artifact on the hot path.
- Planner compatibility carriers are derived from `semantic_decision`, not from ad hoc raw payload rebuilding.
- The first explicit post-owner mutation guard exists and fails on divergence of derived compatibility meaning fields.
- Deterministic tests and runtime schema checks pass.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "tool_args or policy_core_preserves_pending_question_contract or response_format_is_strict"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- Code diff showing `SemanticDecisionV1` creation and `tool_args` removal from owner payload.
- Contract schema diff for `semantic_decision.v1` and updated `policy_decision.v1`.
- Deterministic test outputs.
- Truthful `STATE.md` entry naming exactly which authority was removed and what remains.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic-only in this family; no open-ended quality replay loop.
- **Stop condition:** if two code/test iterations fail without new authority reduction evidence, stop and reopen RCA.
- **Escalation path:** `Brain / Top Architect` for any extra long realism or acceptance runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local canary only in this worktree; no production rollout in this block.
- **Go/no-go signals:** owner payload has no `tool_args`; runtime schema tests pass; planner/runtime compatibility guard stays green.
- **Rollback:** revert the semantic-decision contract slice and restore prior payload shape in one commit.
- **Post-release monitoring window:** local deterministic regression pass for this block only.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `STRUCTURE.md`
  - this TP with implementation evidence
- `Drift closeout rule`:
  - update docs in this block; if a deeper state-writer guard remains open, record it explicitly as residual debt and next-block contract.

## Rollback
- Revert the `SemanticDecisionV1` introduction, policy-core return-shape change, and `PolicyDecision` schema/test updates together.

## No-go
- No new regex/phrase hardcoding in core for semantic routing.
- No reintroduction of `tool_args` into semantic owner payload.
- No hidden binding logic inside `SemanticDecisionV1` that changes capability meaning.
- No claiming state unification or binding extraction as complete in this block.

## Risks/Blockers
- Existing tests and runtime schemas pin the old mixed `PolicyDecision` shape, so contract updates must be kept synchronized.
- `frozen=True` does not deeply freeze nested dict/list payloads, so the explicit guard must cover the sensitive derived semantic fields.
- Some downstream code may still expect `tool_action` on the owner payload; that must be shifted to the separate binding result without widening scope.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: state-writer post-write guard is still partial; `BindingPlanV1` remains unextracted; `booking_prompt_owner.py` remains dormant second-lane debt.
- `Why not in this block`: this family is limited to hot-path owner artifact extraction and first mutation guard, not full binding/state/legacy workstreams.
- `Risk if deferred`: dialog-state and legacy compatibility surfaces can still drift later unless the next block extends the guard and removes more downstream compatibility authority.
- `Linked follow-up Task Package(s)`: `WS1-F2-binding-boundary-read-only-cut` (to be authored after this block lands).
- `Expiry/trigger to stop deferral`: if downstream code still needs to reconstruct semantic meaning outside `semantic_decision` after this block, the next block must target that seam directly before broader workstreams resume.

## Next-block contract (mandatory)
- `Next block objective`: separate binding from meaning by replacing temporary `binding_tool_action` carriage with the first `BindingPlanV1` read-only adapter on the active path.
- `First deterministic check command`: `rg -n "binding_tool_action|SemanticDecisionV1|tool_args" truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py`
- `Blocked-by conditions`: this block does not land a canonical `semantic_decision` field on `PolicyDecision`, or owner payload still carries concrete `tool_args`.
- `Owner role for closure`: `Brain / Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `no`
- `Start from`: `truffles-api/app/services/intent_service.py`
- `Do not touch`: `legacy webhook mesh outside the active Workstream 1 spine`
- `Open risks`: `runtime schema drift`, `old tests pinning mixed payload shape`, `state-writer guard still partial`
- `First command to verify`: `rg -n "projected_payload\[\"tool_args\"\]|semantic_decision" truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py`
