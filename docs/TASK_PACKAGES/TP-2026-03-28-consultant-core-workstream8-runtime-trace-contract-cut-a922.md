# TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922

## Title / Goal
Introduce the first typed `Workstream 8` trace contract so the active runtime path records one versioned evidence object covering `owner -> binding -> action -> state` transitions instead of relying only on flattened ad hoc `decision_trace` / `decision_meta` fields.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 8 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 8 — Observability, Proof, and Release Gates`
- `AGENTS.md` — one-web-search / root-cause / evidence gates

## One Web Search (mandatory before implementation)
- Query: `OpenTelemetry span events attributes semantic conventions official docs`
- Date/time: `2026-03-28T22:23:00+05:00`
- Opened sources:
  - `https://opentelemetry.io/docs/concepts/signals/traces/`
- High-signal source quality:
  - Official OpenTelemetry documentation describing traces as structured spans with attributes/events and semantic conventions, which is directly relevant for designing a typed runtime trace contract instead of a flat debug payload.
- Found reusable idea:
  - Keep the trace evidence structured and versioned, with one canonical object that can hold stage-specific attributes while still remaining exportable to broader observability tooling later.
- Reuse / integrate / build decision:
  - `integrate + build`
- Why:
  - Reuse the existing runtime decision-trace surfaces and integrate a typed versioned contract inside them; build a repo-local contract object because the runtime persists JSON evidence in `decision_trace` / `decision_meta`, not raw OpenTelemetry spans.
- Rejected options:
  - emit only more flat `decision_meta` keys: rejected because that preserves the current proof debt.
  - replace repo-local trace evidence with direct OpenTelemetry-only spans: rejected because current acceptance/proof tooling reads persisted runtime JSON artifacts.

## Root Cause (mandatory)
### Symptom
`Workstream 8` is still open because the runtime has no single versioned trace artifact proving the `owner -> binding -> action -> state` transition on each active turn.

### Minimal Reproduction
1. Inspect `truffles-api/app/core/consultant_runtime.py::_record_turn_trace(...)`.
2. Observe that it writes a flattened `trace_event` plus merged `decision_meta` fields such as `semantic_contract`, `pending_question_contract`, `reason_code`, and `tool_execution_projection`.
3. Run `rg -n "runtime_trace_contract|trace_contract_version|owner_transition|binding_transition" truffles-api/app truffles-api/tests contracts/runtime -S` and observe no typed runtime trace contract exists.

### Evidence
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `contracts/runtime/turn_result.v1.jsonschema`
- `rg -n "runtime_trace_contract|trace_contract_version|owner_transition|binding_transition" truffles-api/app truffles-api/tests contracts/runtime -S`

### Five Whys
1. Why is `Workstream 8` still open?
   - Because trace evidence is still stored as flat bags and stage-specific keys.
2. Why is that a problem?
   - Because there is no single canonical object proving how owner meaning, binding, execution, and canonical state relate on a turn.
3. Why do flat keys fail the objective?
   - Because proof depends on narrative interpretation of many fields instead of one machine-checkable contract.
4. Why not wait for later release-gate work?
   - Because `trace contract covers owner/binding/action/state transitions` is the first explicit completion criterion of `Workstream 8`.
5. Why is runtime the right boundary?
   - Because runtime already has all four ingredients available after state write: owner decision, binding plan, execution result, and canonical runtime projection/journal.

### Root Cause Statement
The active runtime path still emits observability evidence as ad hoc flattened `decision_trace` / `decision_meta` payloads, so there is no versioned machine-checkable contract that binds semantic owner output, binding output, execution outcome, and canonical state transition into one canonical trace artifact.

### Fix Mechanism
Add a typed `RuntimeTraceContractV1` artifact and schema, build it inside `ConsultantRuntime._record_turn_trace(...)` from `PolicyDecision`, `BindingPlanV1`, `RuntimeExecutionResult`, `ConversationProjectionV1`, and `TurnJournalV1`, then persist it into runtime trace/meta surfaces while preserving the existing flattened compatibility fields.

## Invariant
- No semantic/runtime control-path behavior changes.
- Existing flattened `decision_trace` / `decision_meta` keys remain for compatibility.
- No weakening of existing trace retention or mutation guards.

## Scope
- Typed runtime trace contract for the active runtime path.
- Focused deterministic tests for trace contract emission and schema validity.
- Repo truth update for this W8 family only.

## Out of Scope
- Shadow diff scoring.
- Canary/go-no-go/rollback standardization.
- Broad refactors in legacy webhook trace helpers.
- Reworking reminder/health-service trace emitters.

## Touch-list
- `contracts/runtime/runtime_trace_contract.v1.jsonschema`
- `contracts/runtime/turn_result.v1.jsonschema`
- `truffles-api/app/core/runtime_trace_contract.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922.md`

## Plan
1. Add `RuntimeTraceContractV1` model + JSON schema.
2. Emit the contract from `_record_turn_trace(...)` using owner, binding, execution, and canonical runtime state.
3. Attach the typed contract to `TurnTrace` and persisted runtime `decision_trace` / `decision_meta` without removing compatibility fields.
4. Add focused deterministic tests and schema validation.
5. Update repo truth if the focused envelope stays green.

## DoD
- `RuntimeTraceContractV1` exists as a typed runtime artifact and schema.
- Active runtime path emits a populated `runtime_trace_contract` covering owner/binding/action/state transitions.
- `turn_result.v1` schema accepts the new trace field.
- Focused deterministic envelope is green.
- `STATE.md` / `STRUCTURE.md` updated truthfully.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/runtime_trace_contract.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "runtime_trace_contract or record_turn_trace or turn_result_trace"`
- `git diff --check`

## Evidence
- New runtime trace contract model + schema
- Focused runtime trace tests
- Updated `STATE.md` entry for this W8 family

## Release Safety
- Local worktree only
- No deploy / no rollout in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No control-path behavior changes.
- No removal of existing flat trace/meta fields in this block.
- No W8 shadow diff or release-gate scope growth.

## Risks / Blockers
- Existing consumers read flat `decision_meta`; the new contract must be additive.
- Direct unit tests call `_record_turn_trace(...)` with minimal fake conversations, so the contract builder must tolerate absent runtime payloads and derive state evidence from available dialog state.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Shadow diff scoring still does not exist.
- Canary/go-no-go/rollback evidence is still not standardized.
- Legacy trace writers outside runtime core still emit non-canonical trace payloads.

### Why not in this block
- This block only closes the first W8 completion criterion: the canonical trace contract.

### Risk if deferred
- Proof remains fragmented and later W8 work will still depend on narrative stitching across flat trace keys.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream8-shadow-diff-scoring-cut-a922.md` (planned)
- `TP-2026-03-28-consultant-core-workstream8-release-gates-standardization-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral immediately if new proof tooling starts depending on more ad hoc trace/meta keys instead of the typed runtime contract.

## Next-block Contract (mandatory)
### Next block objective
Add shadow-diff scoring over the new runtime trace contract so owner/binding/action/state regressions can be measured without narrative inspection.

### First deterministic check command
`rg -n "runtime_trace_contract|shadow diff|diff score|decision_trace" truffles-api/app truffles-api/tests ops scripts -S`

### Blocked-by conditions
- This trace-contract block must be green and repo truthfully updated.

### Owner role for closure
- Brain / Top Architect
