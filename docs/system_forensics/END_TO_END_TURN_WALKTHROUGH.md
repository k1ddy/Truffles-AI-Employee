# End-To-End Turn Walkthrough

## Purpose
Give outside researchers one concrete runtime scenario that can be read without repo or runtime access.
This walkthrough uses one real turn from the current practical truth to map the current building blocks, authority seams, and remaining debt.

## Scenario chosen
Replay: `a922-practical-proof-20260330-r35f`
Dialog: `6`
Turn: `1`
User message: `Есть ли у вас парковка?`

Why this turn was chosen:
- it is a real current-truth turn, not a synthetic example;
- it touches the fact-side path, which is the biggest current structural gap;
- it also shows why the packet distinguishes semantic owner truth from downstream fact composition debt.

## Visible result
Visible bot reply on `r35f`:
- the parking fact is present again;
- but the final reply still over-composes adjacent branch facts (`address + hours + parking`), which is why the run stays human-semantic amber.

That makes this scenario representative in the right way:
- the semantic-owner family is improved,
- the fact-side architecture gap is still visible.

## Runtime skeleton used by this turn
The live path is:
1. public entrypoint wrapper
2. `consultant_core_v2`
3. `consultant_runtime`
4. `turn_planner`
5. `intent_service` owner path
6. `policy_tool_projector` binding
7. `turn_executor`
8. fact/runtime helpers plus legacy info-side surfaces
9. `dialog_state_service`
10. trace/meta emission and response commit

## Step-by-step walkthrough

### 1. Ingress normalizes the public request
The public WhatsApp/HTTP request lands in the mounted webhook path and is normalized by the public entrypoint layer.
Current code anchor:
- `truffles-api/app/routers/public_entrypoint_contract.py`
- mounted from `truffles-api/app/routers/webhook/http.py`

Architectural role:
- enforce entrypoint materialization contract
- pass the request into the consultant runtime shell
- do not decide user meaning

### 2. The compatibility shell enters the runtime spine
`consultant_core_v2` is the top shell around the current runtime.
Current code anchor:
- `truffles-api/app/core/consultant_core_v2.py`

Architectural role:
- provide one named runtime path (`consultant_core_v2`)
- delegate to `consultant_runtime`
- keep the cutover shell narrow

### 3. Planner prepares owner input
`turn_planner.plan(...)` normalizes the inbound text, merges booking-state slots into memory if needed, and calls the owner gateway.
Current code anchor:
- `truffles-api/app/core/turn_planner.py`

Architectural role:
- prepare normalized owner input
- coerce owner output into typed runtime artifacts
- degrade explicitly when projection fails

### 4. Policy-core owner emits the semantic decision
For this turn, the owner path classifies the request as a parking fact request.
Live replay evidence from `responses.jsonl` / `trace_bundle.jsonl`:
- `llm_policy_core.intent = parking`
- `decision = fact`
- `resolution_mode = policy_fact`
- `subject_kind = branch`

Current code anchor:
- `truffles-api/app/services/intent_service.py`
- typed model in `truffles-api/app/core/semantic_decision.py`

Architectural meaning:
- this is where semantic ownership should happen exactly once
- the owner decides that the turn is a fact request, not a collect or handoff turn

Important current nuance:
- the current artifacts still show fact-side drift even here: the trace event for this turn shows `pack_refs=['parking','hours']`, while the human audit classified the recovered family as parking-grounded on the visible path
- this is one reason the fact-side architecture is still the main open structural gap

### 5. Binding translates meaning into an executable plan
After semantic meaning is available, binding resolves an execution plan.
Current code anchors:
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/app/core/binding_plan.py`

Architectural role:
- choose the registered execution route for the already chosen meaning
- keep deterministic authorization and execution wiring out of the semantic owner

For fact turns like this one, the bound action continues into the fact/info reply path.

### 6. Legacy info-side surfaces still influence fact composition
This is the most important part of the walkthrough.
Even though the owner recognized a parking fact request, the downstream trace for the same turn shows:
- `class_router` emitted `info_bundle`
- `info_class` resolved `fact_refs=['address','hours','parking']`
- `fact_resolver` resolved the same combined truth bundle

Live replay evidence:
- `decision_meta.intent = info_bundle`
- `decision_meta.info_sections = ['address', 'hours', 'parking']`
- visible reply includes all three facts

Architectural meaning:
- the original fact request survives,
- but downstream fact selection/composition still broadens the answer.

This is why the current weak residue is classified as:
- shared mechanism: `fact selection / fact composition`
- not as a new second semantic owner claim

### 7. Executor produces the reply payload
`turn_executor.execute(...)` consumes the binding result.
Current code anchor:
- `truffles-api/app/core/turn_executor.py`

Architectural role:
- execute the bound outcome
- hand off collect/workflow paths to booking prompts when needed
- hand fact paths to fact/runtime resolution
- avoid becoming a second semantic owner

In this scenario, the execution path returns a factual reply payload that still includes the broadened fact bundle.

### 8. State writer records current state and projections
`dialog_state_service` materializes the state/projection side of the turn.
Current code anchor:
- `truffles-api/app/core/dialog_state_service.py`

Architectural role:
- write canonical and compatibility state surfaces
- maintain projection and continuity state
- append journal/projection-compatible data

This is where the system's typed-state progress and remaining migration debt meet:
- the projection machinery exists,
- but several compatibility carriers still coexist around it.

### 9. Trace/meta contracts expose the causal path
The same turn also emits a structured trace/meta view.
Live replay evidence shows stages such as:
- `llm_policy_core`
- `class_router`
- `info_class`
- `fact_resolver`
- `contract`

Current code anchors:
- `truffles-api/app/core/runtime_trace_contract.py`
- replay artifacts under `/tmp/booking_quality/a922-practical-proof-20260330-r35f/`

Architectural role:
- make owner, binding, action, and state transitions auditable
- make disagreement between semantic owner and downstream fact behavior visible

### 10. Final visible outcome and current debt
Final visible reply answers the parking question but also includes address and hours.
So the turn demonstrates both truths at once:
- semantic-owner recovery work is real;
- fact-side architecture remains structurally incomplete.

## What this scenario proves about the system
1. The runtime now has a recognizable hot path instead of one total monolith.
2. A typed semantic-owner contract really exists.
3. Binding is a real separate object, not only a design note.
4. State/projection/journal concepts are present in code.
5. The fact-side path still broadens meaning after the initial semantic classification.
6. Trace/meta evidence is rich enough to show where that broadening happens.

## What this scenario does not prove
1. It does not prove a second semantic owner.
2. It does not prove the target architecture is already achieved.
3. It does not prove the fact-side contract is fixed.
4. It does not prove product/practical closure.

## Why this walkthrough is the right outside-reader artifact
Outside researchers need one scenario that is concrete enough to reason about the real system, but representative enough to expose the main architecture gap.
This turn does that:
- it starts at the public runtime path,
- touches the owner, binding, fact, state, and trace layers,
- and ends on a still-open mechanism-level weakness rather than a solved idealized path.
