# Boundary And Degrade Deep Audit

Status: `open_first_pass`
Purpose: re-derive the real boundary/degrade architecture from the live repo and explain where deterministic layers only validate versus where they still create, reshape, or carry business meaning.

## What this document covers
This is the fresh primary deep audit for boundary and degrade authority.
It answers:
- what the typed boundary seam actually guarantees,
- where synthetic block/degrade artifacts are still minted,
- where degrade services still own continuity and reply shaping,
- and why boundary authority remains one of the main remaining architecture asymmetries.

## Current boundary/degrade stack
### Layer 1. Typed boundary override seam
`truffles-api/app/core/boundary_validator.py`
- defines `BoundaryOverride`, `BoundaryValidationResult`, and `BoundaryValidator`
- sanitizes `preserve_fields` down to `outcome`, `interaction_owner`, `interaction_target`, `interaction_relation`, and `pending_question_contract`
- strips semantic meta keys such as `semantic_contract`, `semantic_frame`, `slots`, `referents`, `fact_refs`, and `tool_args`
Meaning:
- the typed seam already tries to keep boundary meta from becoming a second semantic carrier.
- this is the healthiest part of the current boundary story.

### Layer 2. Planner/runtime degrade application
`truffles-api/app/core/consultant_runtime.py`
- `_plan_turn(...)` converts several planner guard failures into `build_controlled_degrade(...)` plus `BoundaryValidator.build_degrade_override(...)`:
  - `manager_active`
  - `planner:missing_semantic_owner`
  - `planner:missing_binding_plan`
  - `planner:invalid_outcome`
  - `planner:semantic_decision_post_owner_mutation`
- `_apply_execution_boundary_override(...)` can also transform `execution.request_handoff` into a degrade override with `activate_handoff=True`

`truffles-api/app/core/turn_planner.py`
- `build_controlled_degrade(...)` explicitly rewrites the turn outcome to `HANDOFF`
Meaning:
- even in the typed spine, boundary is not only pass/fail validation.
- the runtime actively re-materializes degraded decisions and uses boundary meta to drive later handoff activation.

### Layer 3. Boundary artifact minting in the executor
`truffles-api/app/core/turn_executor.py`
- `build_block_boundary_artifact_from_request(...)` constructs:
  - a synthetic planner decision via `TurnPlanner().build_preflight_reject(...)`
  - a synthetic dialog state via `DialogStateService().build_blocked_state(...)`
  - a synthetic reply through `ResponseRealizer().realize(...)`
- `build_degrade_boundary_artifact_from_request(...)` constructs:
  - a synthetic controlled degrade decision via `TurnPlanner().build_controlled_degrade(...)`
  - a synthetic degraded dialog state via `DialogStateService().build_degraded_state(...)`
  - a degraded turn outcome through `BoundaryValidator().build_degrade_turn_outcome(...)`
Meaning:
- the boundary path can mint a full turn result stack on its own.
- this is much more than validation. It is an alternate authoring path for blocked/degraded turns.

### Layer 4. Compatibility shim still manufactures boundary outcomes
`truffles-api/app/services/reasoning_core.py`
- explicitly describes itself as a compatibility shim, but still owns `_build_*_artifact(...)` helpers for:
  - runtime exception degrade
  - empty message preflight reject
  - missing remote JID reject
  - missing tenant context reject
  - sender branch ignore
  - remote branch phone ignore
  - duplicate message ignore
- all of these call `TurnExecutor().build_*_boundary_artifact_from_request(...)`
Meaning:
- the repo still has a compatibility-era service that manufactures typed block/degrade artifacts before or around the new core.
- that keeps boundary authority split between the typed runtime and the compatibility shim.

### Layer 5. Guard orchestration services shape visible degraded behavior
`truffles-api/app/services/policy_core_guard_orchestration_service.py`
- handles modes such as:
  - `handoff_policy_blocked_safe_reply`
  - `guard_handoff_safe`
  - `pending_hold`
  - `timeout_booking_completion`
  - `degraded_collect_reschedule_handoff`
  - `degraded_collect`
- directly applies policy guard overrides, writes traces and decision metadata, sends the bot response, and commits state
Meaning:
- this service is not a thin validator.
- it acts as a second-stage degrade orchestrator with user-visible reply authority.

### Layer 6. Timeout and specialist boundary services own continuity-heavy recovery
`truffles-api/app/services/timeout_owner_boundary_service.py`
- resolves timeout owner boundary matches through `owner_resolver`
- then writes booking context, expected reply state, canonical dialog state, session memory, decision trace, and decision metadata before sending the prompt

`truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
- reconstructs time follow-up state, pending-question trace, session-memory interaction state, and bot response for timeout-degraded booking continuity

`truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
- reconstructs specialist follow-up or master-info interrupt behavior under timeout degrade
Meaning:
- these services are useful extractions compared with one giant router file,
- but they still prove that degraded paths own continuity state and user-visible question shaping, not only guard decisions.

### Layer 7. Owner-matrix degrade contract exists, but enforcement is distributed
`truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- contains `allowed_degrade_requirements`, `allowed_degrade_raw`, and many row-specific degrade constraints
Meaning:
- the intended contract is documented in machine-readable form.
- but the live enforcement still spans `consultant_runtime.py`, `turn_executor.py`, `reasoning_core.py`, timeout boundary services, guard orchestration services, and `dialog_state_service.py`.

## What is healthy
1. `BoundaryValidator` actively strips semantic meta fields that would otherwise let boundary override owner meaning directly.
2. `reason_code`, `root_reason_code`, `decision_meta`, and `decision_trace` are first-class, so degraded paths are at least observable.
3. Several old boundary families have already been extracted out of `decision.py` into narrower services.
4. The owner matrix now describes many degrade expectations explicitly instead of leaving them only in narrative docs.

## Where boundary still exceeds a strict validator role
### Problem 1. Boundary can mint a whole turn artifact stack
`turn_executor.py` request-based builders create synthetic planner decision, dialog state, reply, and turn outcome.
That means boundary is still an authoring surface, not only a gate.

### Problem 2. Compatibility preflight still sits outside the typed runtime
`reasoning_core.py` can create typed block/degrade artifacts for preflight and exception paths.
That keeps a legacy compatibility author alive on the degraded path.

### Problem 3. Guard services still shape product continuity
`policy_core_guard_orchestration_service.py` and timeout boundary services write:
- expected reply state
- booking state
- canonical dialog state
- session memory
- message decision metadata
- decision trace
- user-visible recovery prompts
This is broader than a pure deterministic validator.

### Problem 4. Degrade policy is described centrally but executed diffusely
The matrix says what degrade should preserve.
The runtime still enforces that through several scattered services and compatibility surfaces.
That gap is where hidden secondary authority can re-enter.

### Problem 5. The realizer can still replace visible reply text on the degraded path
`truffles-api/app/core/response_realizer.py` consumes `BoundaryOverride.public_message`.
Meaning:
- once a degraded override exists, the visible reply no longer comes from the owner text path.
- this is contractually observable, but it is still a second authoring path for user-visible meaning.

## Main verdicts
### Verdict 1. The typed boundary seam is healthier than before, but it is not the whole boundary architecture
`boundary_validator.py` is disciplined.
The rest of the degrade stack is still much broader than that file.

### Verdict 2. Boundary/degrade is still a split architecture
Authority is spread across:
- `consultant_runtime.py`
- `turn_executor.py`
- `reasoning_core.py`
- `policy_core_guard_orchestration_service.py`
- timeout boundary services
- `dialog_state_service.py`

### Verdict 3. The main problem is not that degrade exists; it is that degrade still owns continuity reconstruction
A safe degrade path is allowed.
The problem is that degraded paths still restore state, choose prompts, and shape interaction continuity themselves.

### Verdict 4. The current best salvage path is constriction, not deletion-by-rewrite
The repo already has useful parts:
- sanitized boundary overrides
- typed turn outcomes
- machine-readable degrade expectations in the owner matrix
The recovery move is to force more boundary logic to consume those contracts without minting new semantic/continuity authority.

## Main blockers surfaced by this audit
- synthetic boundary artifact minting still exists as a first-class execution path
- compatibility shim `reasoning_core.py` still creates preflight/degrade outcomes
- degrade recovery services still own state writes and user-visible prompt shaping
- owner-matrix degrade policy is not yet enforced from one narrow execution owner

## Evidence anchors
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/policy_core_guard_orchestration_service.py`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
- `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/files/app_core_turn_executor.md`
- `docs/system_forensics/files/app_services_reasoning_core.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
