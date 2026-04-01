# TP-2026-03-27-consultant-core-workstream2-policy-decision-binding-contract-closeout-a922

- Title/goal: Enforce `binding_plan` as a required runtime contract whenever `PolicyDecision` is semantic-owner-backed or synthetic boundary-backed, and fix the duplicated JSON-schema `allOf` bug that currently drops one of those constraints.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md`
- Invariant: no semantic rewrite; this block only strengthens the typed binding contract and rejects invalid runtime payloads earlier.
- Scope: `PolicyDecision` model validation, `policy_decision.v1` schema, focused runtime contract tests, factual repo truth updates.
- Out of scope: state unification, legacy mesh, control plane, LLM quality acceptance.
- Touch-list:
  - `truffles-api/app/core/turn_planner.py`
  - `contracts/runtime/policy_decision.v1.jsonschema`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `json schema allOf official reference`
- Date/time: `2026-03-27 18:50:00 +05`
- Opened sources:
  - `https://json-schema.org/understanding-json-schema/reference/combining`
- Found reusable solutions:
  - official JSON Schema docs confirm `allOf` must hold all subschemas together, so the contract should use one combined `allOf` array rather than duplicated top-level keys that silently override each other in JSON parsers
- Reuse/integrate/build decision:
  - `integrate`
  - Reason: fix the schema by composing both binding-required and shadow-only constraints under one `allOf` array, and mirror the same invariant in the Pydantic model
- Rejected variants:
  - leave schema as-is and rely only on runtime guards: weak contract, allows invalid payloads to parse successfully

## Root cause (mandatory)
- Symptom:
  - `PolicyDecision` can still validate without `binding_plan` in some cases where typed binding should be mandatory.
- Minimal reproduction:
  - `contracts/runtime/policy_decision.v1.jsonschema` contains duplicate top-level `allOf` keys, so JSON parsing drops the earlier `binding_plan` requirement when `semantic_decision` exists.
- Evidence:
  - `contracts/runtime/policy_decision.v1.jsonschema`
  - `python3 - <<'PY' ... json.loads(...).keys()/allOf ... PY` showed only one surviving top-level `allOf`
- Five Whys:
  1. Why can invalid policy decisions still parse? Because schema composition was duplicated at the same JSON key.
  2. Why is that harmful? Because one of the contract invariants is silently disabled.
  3. Why does runtime still tolerate it? Because `PolicyDecision` Pydantic model also treats `binding_plan` as optional without contextual validation.
  4. Why is that a Workstream 2 problem? Because binding boundary is not fully enforced as the required executable artifact.
  5. Why fix now? Because this is the remaining low-level contract hole after executor/runtime moved to typed-binding-first reads.
- Root cause statement:
  - The `PolicyDecision` contract is under-enforced: duplicate JSON-schema keys drop the binding requirement, and the Pydantic model does not yet require `binding_plan` on semantic-owner or synthetic boundary decisions.
- Fix mechanism:
  - merge the schema constraints into one `allOf` array and add explicit model validation for `binding_plan` on semantic-owner-backed and synthetic decisions.

## Plan
1. Add `PolicyDecision` model validation for required `binding_plan` on semantic-owner-backed and synthetic decisions.
2. Merge the duplicated `allOf` clauses in `policy_decision.v1.jsonschema` and add the synthetic-decision binding requirement there too.
3. Add focused tests that reject invalid semantic-owner and synthetic decisions without `binding_plan`.
4. Run deterministic checks and record factual repo truth.

## DoD
- `PolicyDecision` model rejects semantic-owner-backed payloads without `binding_plan`
- `PolicyDecision` model rejects synthetic decisions without `binding_plan`
- `policy_decision.v1.jsonschema` enforces the same rules
- focused deterministic tests pass

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "policy_decision and binding_plan"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `git diff --check`

## Evidence
- focused runtime contract output
- exact files changed
- `STATE.md` update after checks

## Rollback
- revert this TP diff; `PolicyDecision` returns to the previous looser contract.

## No-go
- no semantic-field mutation
- no weakening of existing owner/binding guards
- no broad refactor outside the `PolicyDecision` contract

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - non-owner legacy compatibility decisions without `binding_plan` may still exist in tests/support helpers
  - compatibility fields still exist on `PolicyDecision`
- Why not in this block:
  - this block only closes the contract hole for runtime-valid decisions
- Risk if deferred:
  - invalid policy decisions keep slipping past schema/model validation and weaken Workstream 2 closure evidence
- Linked follow-up Task Package(s):
  - Workstream 2 closeout proof pass or remaining legacy support cleanup
- Expiry/trigger to stop deferral:
  - if any new semantic-owner or synthetic boundary decision is accepted without `binding_plan`, stop and finish contract closure first

## Next-block contract (mandatory)
- Next block objective:
  - close Workstream 2 with a proof pass, or explicitly isolate any remaining legacy support helper that still blocks closure
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or policy_decision or tool_execution_projection"`
- Blocked-by conditions:
  - `PolicyDecision` binding contract must be green first
- Owner role for closure:
  - Brain / Top Architect


## Implementation result
- Added `PolicyDecision` model validation that requires `binding_plan` for semantic-owner-backed and synthetic policy decisions.
- Fixed `contracts/runtime/policy_decision.v1.jsonschema` so the binding-required rule and the shadow-only semantic-carrier rule now coexist in one combined `allOf` array; added the synthetic-decision binding requirement there too.
- Updated test support to synthesize typed binding plans for synthetic policy decisions so contract tests exercise the same binding-first runtime path as app code.

## Checks run
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/tests/__init__.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "policy_decision and binding_plan"` -> `4 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `87 passed`
- `git diff --check` -> `pass`

## Authority removed
- Invalid semantic-owner and synthetic boundary decisions can no longer bypass the typed binding contract at schema/model-validation time.
- `policy_decision.v1` no longer silently drops one of its `allOf` invariants during JSON parsing.

## Residual debt after this block
- Compatibility `tool_action` / `outcome` fields still exist on `PolicyDecision` for legacy readers.
- Workstream 2 still needs an explicit closeout/proof pass to decide whether any remaining app-runtime path can mint a valid decision without typed binding.
