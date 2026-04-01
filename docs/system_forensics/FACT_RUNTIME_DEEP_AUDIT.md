# Fact Runtime Deep Audit

Status: `open_first_pass`
Purpose: explain the current fact-side execution path and why fact selection, composition, and rendering remain the biggest structural gap.

## What this document covers
This is the first fresh deep audit of the fact-side path.
It answers:
- how a fact answer is currently built,
- which modules participate,
- where pack/runtime behavior is mixed,
- and why the current packet still points to fact architecture as the first implementation slice.

## Current fact path
### Step 1. Runtime primes truth and capabilities
`truffles-api/app/core/consultant_runtime.py:_prime_runtime_context`
- loads runtime capabilities and truth through:
  - `truffles-api/app/services/capabilities_runtime.py`
  - `truffles-api/app/services/knowledge_runtime.py`
Meaning:
- pack truth is loaded directly into runtime context before the turn is executed.
- fact behavior already depends on shared runtime truth state, not only on a late renderer call.

### Step 2. Semantic owner chooses outcome and grounding
`truffles-api/app/services/intent_service.py:route_llm_policy_core`
- emits `SemanticDecisionV1`
- supplies grounding requirements such as `pack_refs`, `entity_refs`, `referents`, `subject_kind`, and `resolution_mode`
`truffles-api/app/core/policy_tool_projector.py:build_binding_plan`
- maps policy `tool_action_hint`, especially `info`, into concrete tool/workflow actions
Meaning:
- fact/tool selection is already influenced by a mix of owner payload and registry/projector logic.

### Step 3. Turn executor runs the fact outcome chain
`truffles-api/app/core/turn_executor.py:execute`
- routes tool-call outcomes into `_execute_fact(...)`

`truffles-api/app/core/turn_executor.py:_execute_fact`
- tries several fact delivery routes in sequence:
  - master-query pack path via `truffles-api/app/services/pack_runtime_service.py`
  - tool registry execution via `truffles-api/app/services/tool_registry_service.py`
  - direct truth formatting via `pack_runtime_service.format_reply_from_truth(...)`
  - logical info-tool candidates via tool-registry snapshots
  - pack fallback via `pack_runtime_service.get_pack_decision(...)`
  - generic fallback
- merges pack grounding into semantic contract via `_merge_pack_grounding_semantic_contract(...)`
Meaning:
- one fact request can still travel through several render/selection branches before final text is chosen.
- there is no single governing fact resolver/renderer seam yet.

### Step 4. Pack/runtime facade delegates to adapters
`truffles-api/app/services/pack_runtime_service.py`
- exposes pack resolver/renderer behavior to the runtime

`truffles-api/app/services/pack_runtime_default.py`
- dispatches by `client_slug` through `_resolve_adapter(...)`
- exposes `format_reply_from_truth(...)`, `build_info_combined_reply(...)`, `get_pack_decision(...)`, and related helpers
Meaning:
- the runtime has a pack facade, but final factual behavior still depends on adapter code rather than a single fact manifest contract.

### Step 5. Pack-specific adapters and legacy helpers still shape factual output
`truffles-api/app/services/pack_runtime_neutral_adapter.py`
- already expresses a cleaner single-fact contract for `location`, `hours`, and `parking`

`truffles-api/app/services/demo_salon_knowledge.py`
- still uses `build_info_combined_reply(...)` and can widen single intents into combined replies

`truffles-api/app/routers/webhook/info.py`
- still contains legacy fact rendering/orchestration helpers such as `_build_info_intent_reply(...)`
Meaning:
- fact rendering currently exists in parallel in core execution, pack adapters, tool execution, and legacy webhook info helpers.

### Step 6. Reply is wrapped and delivered
`truffles-api/app/core/response_realizer.py:realize`
- turns the chosen factual text into a `ReplyEnvelope`
Meaning:
- the response realizer is the last delivery wrapper, not the place where fact scope should be decided.

## Proven structural problem
### Over-composition is not just wording
When a user asks one fact, the system should normally emit one fact scope unless the contract explicitly allows composition.
The current implementation breaks this because:
- `info.py` still chooses broad reply helpers
- adapter resolution hides pack-specific behavior behind a generic interface
- `demo_salon_knowledge.py` still returns combined replies for single intents like `location`, `hours`, and `parking`

This is why `fact over-composition on location/parking replies` is not a small symptom.
It is evidence of a missing executable fact contract.

## Why this is the biggest current asymmetry
Interaction-side architecture already has typed artifacts:
- semantic decision
- binding plan
- turn journal
- conversation projection

Fact-side architecture does not yet have a comparable governing object for:
- requested fact ids
- allowed standalone/composite combinations
- emitted fact refs
- render policy
- fallback rules

That asymmetry explains why the next implementation slice still points to `fact architecture contract materialization`.

## Main verdicts
### Verdict 1. Fact selection/composition/rendering is still spread across layers
The fact path currently crosses:
- runtime truth priming
- semantic owner output
- policy tool projection
- turn executor fact fallback chain
- runtime adapter resolution
- tool-registry rendering
- pack-specific implementations
- legacy webhook info helpers

### Verdict 2. Pack/runtime separation is still incomplete
The adapter seam exists, but pack-specific implementations and some runtime helpers still encode behavior, not only data representation.

### Verdict 3. The current runtime does not yet enforce emitted fact scope
Nothing in the live path guarantees that one requested fact stays one emitted fact across projector, executor, tool-registry, adapter, and legacy-helper paths.
That is the core structural issue.

### Verdict 4. This is the best candidate for the first architecture-recovery runtime slice
The biggest open weak product residue and the biggest missing architecture object point to the same seam:
- fact selection / composition / rendering

## Main blockers surfaced by this audit
- no machine-readable fact manifest governs standalone vs composite replies
- `info.py` still makes composition decisions instead of delegating to a strict renderer contract
- adapter indirection does not by itself guarantee exact fact scope
- demo-salon pack behavior still widens some single-fact intents into bundles

## Evidence anchors
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_services_intent_service.md`
